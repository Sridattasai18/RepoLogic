"""
Repository Ingestion Module - PHASE 1
Fetches, filters, and structures repository data
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from .constants import (
    IGNORE_DIRS, INCLUDED_EXTENSIONS, CODE_EXTENSIONS, TEXT_EXTENSIONS, DETECT_LANGUAGE_MAP
)
from .github_api import GitHubAPI, parse_github_url
from .github_loader import validate_github_url, _normalize_github_url, get_repo_id
from config import Config
import git

logger = logging.getLogger(__name__)


def count_lines(file_path: Path) -> int:
    """Count non-empty lines in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def detect_language(file_path: Path) -> str:
    """Detect programming language from file extension"""
    return DETECT_LANGUAGE_MAP.get(file_path.suffix.lower(), 'Unknown')


def classify_file_type(file_path: Path) -> str:
    """Classify file into category"""
    ext = file_path.suffix.lower()
    name = file_path.name.lower()
    
    # Config files
    if ext in {'.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.env.example'}:
        return 'config'
    
    # Documentation
    if ext in {'.md', '.txt', '.rst'} or 'readme' in name or 'changelog' in name:
        return 'documentation'
    
    # Code files
    if ext in CODE_EXTENSIONS:
        return 'code'
    
    return 'other'


class RepoIngestor:
    """Handles repository ingestion and structured data extraction"""
    
    def __init__(self):
        self.api = GitHubAPI(timeout=Config.REQUEST_TIMEOUT)
    
    def ingest(self, repo_url: str) -> Dict[str, Any]:
        """
        Main ingestion function - returns structured repo data
        
        Returns:
            {
                "repo_id": str,
                "metadata": {...},
                "files": [...],
                "stats": {...}
            }
        """
        logger.info(f"Starting ingestion for: {repo_url}")
        
        # Validate URL
        if not validate_github_url(repo_url):
            raise ValueError("Invalid or unreachable GitHub URL")
        
        # Get repo ID
        repo_id = get_repo_id(repo_url)
        
        # Fetch metadata from GitHub API
        owner, repo = parse_github_url(repo_url)
        metadata = self.api.get_repo_metadata(owner, repo)
        languages = self.api.get_languages(owner, repo)
        
        # Check size
        size_mb = metadata.get('size', 0) / 1024
        if size_mb > Config.MAX_REPO_SIZE_MB:
            raise ValueError(
                f"Repository too large ({size_mb:.1f}MB). "
                f"Max: {Config.MAX_REPO_SIZE_MB}MB"
            )
        
        # Clone repository
        repo_path = self._clone_repo(repo_url, repo_id)
        
        # Extract file data
        files_data = self._extract_files(repo_path, repo_id)
        
        # Calculate statistics
        stats = self._calculate_stats(files_data)
        
        result = {
            "repo_id": repo_id,
            "metadata": {
                **metadata,
                "languages": languages
            },
            "files": files_data,
            "stats": stats
        }
        
        logger.info(f"✅ Ingestion complete: {stats['total_files']} files, {stats['total_lines']} lines")
        return result
    
    def _clone_repo(self, url: str, repo_id: str) -> Path:
        """Clone repository if not already cached"""
        repo_path = Config.REPO_CACHE_DIR / repo_id
        clone_url = _normalize_github_url(url)
        
        if repo_path.exists():
            logger.info(f"Using cached repo at {repo_path}")
            return repo_path
        
        logger.info(f"Cloning {clone_url}...")
        
        # Clone with retry logic
        for attempt in range(Config.MAX_RETRIES):
            try:
                git.Repo.clone_from(clone_url, repo_path, depth=1)
                logger.info("✅ Clone successful")
                return repo_path
            except git.exc.GitCommandError as e:
                if "not found" in str(e).lower():
                    raise ValueError("Repository not found or is private")
                elif attempt < Config.MAX_RETRIES - 1:
                    logger.warning(f"Clone failed, retrying... ({attempt + 1}/{Config.MAX_RETRIES})")
                    import time
                    time.sleep(2 ** attempt)
                else:
                    raise ValueError(f"Failed to clone: {str(e)}")
        
        raise ValueError("Clone failed after retries")
    
    def _extract_files(self, repo_path: Path, repo_id: str) -> List[Dict[str, Any]]:
        """Extract structured file data"""
        files_data = []
        
        for root, dirs, files in os.walk(repo_path):
            # Filter directories
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(repo_path)
                ext = file_path.suffix.lower()
                
                # Only include allowed extensions
                if ext not in INCLUDED_EXTENSIONS:
                    continue
                
                # Skip large files
                try:
                    file_size = file_path.stat().st_size
                    if file_size > 1_000_000:  # 1MB limit
                        logger.debug(f"Skipping large file: {rel_path}")
                        continue
                except Exception:
                    continue
                
                # Count lines
                line_count = count_lines(file_path)
                
                file_info = {
                    "path": str(rel_path).replace('\\', '/'),  # Normalize path separators
                    "name": file,
                    "type": classify_file_type(file_path),
                    "language": detect_language(file_path),
                    "extension": ext,
                    "size": file_size,
                    "lines": line_count
                }
                
                files_data.append(file_info)
        
        # Sort by path for consistency
        files_data.sort(key=lambda x: x['path'])
        
        return files_data
    
    def _calculate_stats(self, files_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate repository statistics"""
        stats = {
            "total_files": len(files_data),
            "total_lines": sum(f['lines'] for f in files_data),
            "total_size": sum(f['size'] for f in files_data),
            "by_type": {},
            "by_language": {}
        }
        
        # Count by type
        for file in files_data:
            file_type = file['type']
            stats['by_type'][file_type] = stats['by_type'].get(file_type, 0) + 1
        
        # Count by language
        for file in files_data:
            lang = file['language']
            if lang != 'Unknown':
                stats['by_language'][lang] = stats['by_language'].get(lang, 0) + 1
        
        return stats
