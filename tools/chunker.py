"""
Chunking Module with Line Number Tracking - PHASE 2
Chunks files while preserving exact line number ranges
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .constants import LANGUAGE_MAP
from config import Config
import json
import re

logger = logging.getLogger(__name__)


class LineNumberChunk:
    """Represents a code chunk with line number tracking"""
    
    def __init__(
        self,
        repo_id: str,
        file_path: str,
        content: str,
        start_line: int,
        end_line: int,
        language: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.repo_id = repo_id
        self.file_path = file_path
        self.content = content
        self.start_line = start_line
        self.end_line = end_line
        self.language = language
        self.metadata = metadata or {}
        
        # Generate unique chunk ID
        self.chunk_id = self._generate_chunk_id()
    
    def _generate_chunk_id(self) -> str:
        """Generate unique chunk identifier"""
        return f"{self.repo_id}__{self.file_path}__L{self.start_line}-L{self.end_line}".replace('/', '_').replace('\\', '_')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "chunk_id": self.chunk_id,
            "repo_id": self.repo_id,
            "file_path": self.file_path,
            "language": self.language,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "line_count": self.end_line - self.start_line + 1,
            "content": self.content,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LineNumberChunk':
        """Create from dictionary"""
        return cls(
            repo_id=data['repo_id'],
            file_path=data['file_path'],
            content=data['content'],
            start_line=data['start_line'],
            end_line=data['end_line'],
            language=data['language'],
            metadata=data.get('metadata', {})
        )


class FileChunker:
    """Chunks files while tracking line numbers"""
    
    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_file(
        self,
        repo_id: str,
        file_path: str,
        content: str,
        language: str,
        extension: str
    ) -> List[LineNumberChunk]:
        """
        Chunk a file while preserving line numbers
        
        Strategy:
        1. Split content into lines
        2. Use language-aware splitter to get chunk boundaries
        3. Map chunks back to original line numbers
        4. Create LineNumberChunk objects
        """
        if not content.strip():
            return []
        
        lines = content.split('\n')
        total_lines = len(lines)
        
        # Get language-aware splitter
        splitter = self._get_splitter(extension)
        
        # For very small files, create single chunk
        if total_lines <= self.chunk_size // 10:  # Rough estimate: ~10 chars per line
            return [LineNumberChunk(
                repo_id=repo_id,
                file_path=file_path,
                content=content,
                start_line=1,
                end_line=total_lines,
                language=language,
                metadata=self._extract_metadata(content, language)
            )]
        
        # Split content into chunks
        text_chunks = splitter.split_text(content)
        
        # Map chunks to line numbers
        chunks_with_lines = self._map_chunks_to_lines(
            text_chunks, lines, repo_id, file_path, language
        )
        
        return chunks_with_lines
    
    def _get_splitter(self, extension: str) -> RecursiveCharacterTextSplitter:
        """Get language-aware text splitter"""
        language = LANGUAGE_MAP.get(extension.lower())
        
        if language:
            return RecursiveCharacterTextSplitter.from_language(
                language=language,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
        else:
            return RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=["\n\n", "\n", " ", ""],
                keep_separator=True
            )
    
    def _map_chunks_to_lines(
        self,
        text_chunks: List[str],
        original_lines: List[str],
        repo_id: str,
        file_path: str,
        language: str
    ) -> List[LineNumberChunk]:
        """
        Map text chunks back to original line numbers
        
        Algorithm:
        - For each chunk, find where it appears in the original content
        - Calculate which lines it spans
        - Handle overlaps gracefully
        """
        chunks = []
        full_content = '\n'.join(original_lines)
        current_search_start = 0
        
        for chunk_text in text_chunks:
            # Find chunk position in full content
            chunk_start_pos = full_content.find(chunk_text, current_search_start)
            
            if chunk_start_pos == -1:
                logger.warning(f"Could not locate chunk in {file_path}, skipping")
                continue
            
            chunk_end_pos = chunk_start_pos + len(chunk_text)
            
            # Calculate line numbers
            start_line = full_content[:chunk_start_pos].count('\n') + 1
            end_line = full_content[:chunk_end_pos].count('\n') + 1
            
            # Extract metadata
            metadata = self._extract_metadata(chunk_text, language)
            
            chunk = LineNumberChunk(
                repo_id=repo_id,
                file_path=file_path,
                content=chunk_text,
                start_line=start_line,
                end_line=end_line,
                language=language,
                metadata=metadata
            )
            
            chunks.append(chunk)
            
            # Move search pointer forward (accounting for overlap)
            current_search_start = chunk_start_pos + len(chunk_text) - self.chunk_overlap
        
        return chunks
    
    def _extract_metadata(self, content: str, language: str) -> Dict[str, Any]:
        """
        Extract basic metadata from chunk content
        Simple heuristic-based extraction
        """
        metadata = {
            "has_classes": False,
            "has_functions": False,
            "has_imports": False,
            "class_names": [],
            "function_names": []
        }
        
        lines = content.split('\n')
        
        for line in lines:
            stripped = line.strip()
            
            # Python patterns
            if language == "Python":
                if stripped.startswith('class '):
                    metadata['has_classes'] = True
                    match = re.match(r'class\s+(\w+)', stripped)
                    if match:
                        metadata['class_names'].append(match.group(1))
                
                if stripped.startswith('def '):
                    metadata['has_functions'] = True
                    match = re.match(r'def\s+(\w+)', stripped)
                    if match:
                        metadata['function_names'].append(match.group(1))
                
                if stripped.startswith(('import ', 'from ')):
                    metadata['has_imports'] = True
            
            # JavaScript/TypeScript patterns
            elif language in ["JavaScript", "TypeScript"]:
                if 'class ' in stripped:
                    metadata['has_classes'] = True
                
                if any(pattern in stripped for pattern in ['function ', 'const ', 'let ', 'var ']):
                    if '=' in stripped and '=>' in stripped or 'function' in stripped:
                        metadata['has_functions'] = True
                
                if stripped.startswith(('import ', 'require(')):
                    metadata['has_imports'] = True
        
        return metadata


class ChunkStore:
    """Stores and retrieves chunks"""
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def save_chunks(self, repo_id: str, chunks: List[LineNumberChunk]):
        """Save chunks to storage"""
        chunk_file = self.storage_dir / f"{repo_id}_chunks.json"
        
        chunks_data = [chunk.to_dict() for chunk in chunks]
        
        with open(chunk_file, 'w', encoding='utf-8') as f:
            json.dump({
                "repo_id": repo_id,
                "total_chunks": len(chunks),
                "chunks": chunks_data
            }, f, indent=2)
        
        logger.info(f"✅ Saved {len(chunks)} chunks for {repo_id}")
    
    def load_chunks(self, repo_id: str) -> List[LineNumberChunk]:
        """Load chunks from storage"""
        chunk_file = self.storage_dir / f"{repo_id}_chunks.json"
        
        if not chunk_file.exists():
            return []
        
        with open(chunk_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        chunks = [LineNumberChunk.from_dict(c) for c in data['chunks']]
        logger.info(f"Loaded {len(chunks)} chunks for {repo_id}")
        return chunks
    
    def get_chunks_by_file(self, repo_id: str, file_path: str) -> List[LineNumberChunk]:
        """Get all chunks for a specific file"""
        all_chunks = self.load_chunks(repo_id)
        return [c for c in all_chunks if c.file_path == file_path]
    
    def get_chunks_by_lines(
        self,
        repo_id: str,
        file_path: str,
        start_line: int,
        end_line: int
    ) -> List[LineNumberChunk]:
        """
        Get chunks that overlap with specified line range
        Used for selection-based retrieval
        """
        file_chunks = self.get_chunks_by_file(repo_id, file_path)
        
        overlapping = []
        for chunk in file_chunks:
            # Check if chunk overlaps with requested range
            if not (chunk.end_line < start_line or chunk.start_line > end_line):
                overlapping.append(chunk)
        
        return overlapping
    
    def has_chunks(self, repo_id: str) -> bool:
        """Check if chunks exist for repository"""
        chunk_file = self.storage_dir / f"{repo_id}_chunks.json"
        return chunk_file.exists()
