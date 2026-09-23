"""
GitHub API Helper Module
Handles GitHub API interactions for repository metadata and file tree
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import time
from .constants import IGNORE_DIRS

logger = logging.getLogger(__name__)

class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors"""
    pass

class GitHubAPI:
    """Helper class for GitHub API interactions"""
    
    BASE_URL = "https://api.github.com"
    RATE_LIMIT_WAIT = 60  # seconds to wait if rate limited
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Ecode-Repository-Analyzer'
        })
    
    def _make_request(self, url: str, retries: int = 3) -> Dict[str, Any]:
        """
        Make a request to GitHub API with retry logic and rate limit handling
        """
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                
                # Handle rate limiting
                if response.status_code == 403 and 'rate limit' in response.text.lower():
                    if attempt < retries - 1:
                        logger.warning(f"Rate limited, waiting {self.RATE_LIMIT_WAIT}s...")
                        time.sleep(self.RATE_LIMIT_WAIT)
                        continue
                    else:
                        raise GitHubAPIError("GitHub API rate limit exceeded")
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.Timeout:
                if attempt < retries - 1:
                    logger.warning(f"Request timeout, retrying... (attempt {attempt + 1}/{retries})")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    raise GitHubAPIError("Request timeout after multiple retries")
                    
            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    logger.warning(f"Request failed: {e}, retrying...")
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise GitHubAPIError(f"Failed to fetch from GitHub API: {e}")
        
        raise GitHubAPIError("Failed after all retry attempts")
    
    def get_repo_metadata(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Fetch repository metadata from GitHub API
        
        Returns:
            {
                'name': str,
                'description': str,
                'stars': int,
                'forks': int,
                'language': str,
                'topics': List[str],
                'default_branch': str,
                'size': int (KB),
                'open_issues': int,
                'created_at': str,
                'updated_at': str
            }
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}"
        
        try:
            data = self._make_request(url)
            
            return {
                'name': data.get('name', ''),
                'full_name': data.get('full_name', ''),
                'description': data.get('description', 'No description available'),
                'stars': data.get('stargazers_count', 0),
                'forks': data.get('forks_count', 0),
                'language': data.get('language', 'Unknown'),
                'topics': data.get('topics', []),
                'default_branch': data.get('default_branch', 'main'),
                'size': data.get('size', 0),  # Size in KB
                'open_issues': data.get('open_issues_count', 0),
                'created_at': data.get('created_at', ''),
                'updated_at': data.get('updated_at', ''),
                'homepage': data.get('homepage', ''),
                'license': data.get('license', {}).get('name', 'No license') if data.get('license') else 'No license'
            }
            
        except GitHubAPIError as e:
            logger.error(f"Failed to fetch repo metadata: {e}")
            # Return minimal metadata on failure
            return {
                'name': repo,
                'full_name': f"{owner}/{repo}",
                'description': 'Metadata unavailable',
                'stars': 0,
                'forks': 0,
                'language': 'Unknown',
                'topics': [],
                'default_branch': 'main',
                'size': 0,
                'open_issues': 0,
                'created_at': '',
                'updated_at': '',
                'homepage': '',
                'license': 'Unknown'
            }
    
    def get_languages(self, owner: str, repo: str) -> Dict[str, int]:
        """
        Fetch language breakdown for the repository
        
        Returns:
            {'Python': 12345, 'JavaScript': 6789, ...}
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/languages"
        
        try:
            return self._make_request(url)
        except GitHubAPIError as e:
            logger.error(f"Failed to fetch languages: {e}")
            return {}


def build_file_tree(repo_path: Path, max_depth: int = 5) -> Dict[str, Any]:
    """
    Build a file tree structure from a local repository path
    
    Args:
        repo_path: Path to the cloned repository
        max_depth: Maximum depth to traverse
    
    Returns:
        {
            'name': 'repo_name',
            'type': 'directory',
            'children': [
                {'name': 'file.py', 'type': 'file', 'size': 1234, 'extension': '.py'},
                {'name': 'folder', 'type': 'directory', 'children': [...]}
            ]
        }
    """
    
    def get_file_type_category(extension: str) -> str:
        """Categorize file by extension"""
        code_exts = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.rb', '.php', '.swift', '.kt'}
        doc_exts = {'.md', '.txt', '.rst', '.pdf', '.doc', '.docx'}
        config_exts = {'.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.xml'}
        
        if extension in code_exts:
            return 'code'
        elif extension in doc_exts:
            return 'documentation'
        elif extension in config_exts:
            return 'configuration'
        else:
            return 'other'
    
    def build_tree_recursive(path: Path, current_depth: int = 0) -> Optional[Dict[str, Any]]:
        """Recursively build tree structure"""
        if current_depth > max_depth:
            return None
        
        if not path.exists():
            return None
        
        name = path.name
        
        # Skip ignored directories
        if path.is_dir() and name in IGNORE_DIRS:
            return None
        
        if path.is_file():
            extension = path.suffix.lower()
            return {
                'name': name,
                'type': 'file',
                'size': path.stat().st_size,
                'extension': extension,
                'category': get_file_type_category(extension)
            }
        
        elif path.is_dir():
            children = []
            try:
                for child in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                    child_node = build_tree_recursive(child, current_depth + 1)
                    if child_node:
                        children.append(child_node)
            except PermissionError:
                logger.warning(f"Permission denied: {path}")
                return None
            
            return {
                'name': name,
                'type': 'directory',
                'children': children
            }
        
        return None
    
    tree = build_tree_recursive(repo_path)
    return tree if tree else {'name': repo_path.name, 'type': 'directory', 'children': []}


def get_file_count_by_type(tree: Dict[str, Any]) -> Dict[str, int]:
    """
    Count files by category in the file tree
    
    Returns:
        {'code': 45, 'documentation': 5, 'configuration': 8, 'other': 12}
    """
    counts = {'code': 0, 'documentation': 0, 'configuration': 0, 'other': 0}
    
    def count_recursive(node: Dict[str, Any]):
        if node['type'] == 'file':
            category = node.get('category', 'other')
            counts[category] = counts.get(category, 0) + 1
        elif node['type'] == 'directory' and 'children' in node:
            for child in node['children']:
                count_recursive(child)
    
    count_recursive(tree)
    return counts


def parse_github_url(url: str) -> tuple[str, str]:
    """
    Parse GitHub URL to extract owner and repo name
    
    Args:
        url: GitHub URL (e.g., https://github.com/owner/repo)
    
    Returns:
        (owner, repo) tuple
    
    Raises:
        ValueError: If URL is invalid
    """
    # Normalize URL
    url = url.rstrip('/').removesuffix('.git')
    
    # Strip path segments
    if '/tree/' in url or '/blob/' in url:
        url = url.split('/tree/')[0].split('/blob/')[0]
    
    # Extract owner and repo
    parts = url.replace('https://github.com/', '').split('/')
    
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {url}")
    
    return parts[0], parts[1]
