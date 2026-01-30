"""
Embedding and Vector Store Module - PHASE 3
Handles chunk embeddings and FAISS-based semantic search
"""

import logging
import numpy as np
import faiss
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from config import Config
from tools.chunker import LineNumberChunk, ChunkStore

logger = logging.getLogger(__name__)


class EmbeddingStore:
    """Manages embeddings and FAISS vector search"""
    
    def __init__(self):
        self.embeddings_model = None
        self.storage_dir = Config.VECTOR_DB_PATH
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_embeddings_model(self) -> GoogleGenerativeAIEmbeddings:
        """Lazy initialization of embeddings model"""
        if self.embeddings_model is None:
            self.embeddings_model = GoogleGenerativeAIEmbeddings(
                model=Config.EMBEDDING_MODEL,
                google_api_key=Config.GOOGLE_API_KEY
            )
        return self.embeddings_model
    
    def embed_chunks(self, chunks: List[LineNumberChunk]) -> np.ndarray:
        """
        Generate embeddings for chunks
        
        We embed: file_path + language + content
        This gives better semantic understanding
        """
        if not chunks:
            return np.array([])
        
        model = self._get_embeddings_model()
        
        # Create enriched text for embedding
        texts_to_embed = []
        for chunk in chunks:
            # Include file path and language as context
            enriched_text = f"File: {chunk.file_path}\nLanguage: {chunk.language}\n\n{chunk.content}"
            texts_to_embed.append(enriched_text)
        
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        
        # Batch embedding generation
        embeddings = []
        batch_size = 100
        
        for i in range(0, len(texts_to_embed), batch_size):
            batch = texts_to_embed[i:i + batch_size]
            try:
                batch_embeddings = model.embed_documents(batch)
                embeddings.extend(batch_embeddings)
                logger.info(f"Processed batch {i//batch_size + 1}/{(len(texts_to_embed) + batch_size - 1)//batch_size}")
            except Exception as e:
                logger.error(f"Error embedding batch {i}-{i+batch_size}: {e}")
                # Optional: Add empty embeddings or handle retry
                # For now, we'll just fail the batch which is safer than misaligning indices
                raise e
        
        embeddings_array = np.array(embeddings, dtype='float32')
        logger.info(f"✅ Generated embeddings: shape {embeddings_array.shape}")
        
        return embeddings_array
    
    def create_index(self, repo_id: str, chunks: List[LineNumberChunk]) -> bool:
        """
        Create FAISS index for repository chunks
        
        Stores:
        - FAISS index file
        - Chunk metadata (pickled)
        - Index metadata (JSON)
        """
        if not chunks:
            logger.warning("No chunks to index")
            return False
        
        try:
            # Generate embeddings
            embeddings = self.embed_chunks(chunks)
            
            if embeddings.size == 0:
                logger.error("Failed to generate embeddings")
                return False
            
            # Create FAISS index
            dimension = embeddings.shape[1]
            index = faiss.IndexFlatL2(dimension)  # L2 distance (Euclidean)
            index.add(embeddings)
            
            # Save index
            index_path = self.storage_dir / f"{repo_id}.faiss"
            faiss.write_index(index, str(index_path))
            
            # Save chunk metadata
            chunks_path = self.storage_dir / f"{repo_id}_chunks.pkl"
            with open(chunks_path, 'wb') as f:
                pickle.dump(chunks, f)
            
            # Save index info
            info_path = self.storage_dir / f"{repo_id}_info.pkl"
            with open(info_path, 'wb') as f:
                pickle.dump({
                    'total_chunks': len(chunks),
                    'dimension': dimension,
                    'repo_id': repo_id
                }, f)
            
            logger.info(f"✅ Created FAISS index for {repo_id}: {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create index: {e}", exc_info=True)
            return False
    
    def has_index(self, repo_id: str) -> bool:
        """Check if index exists for repository"""
        index_path = self.storage_dir / f"{repo_id}.faiss"
        chunks_path = self.storage_dir / f"{repo_id}_chunks.pkl"
        return index_path.exists() and chunks_path.exists()
    
    def search_similar(
        self,
        repo_id: str,
        query: str,
        k: int = 5
    ) -> List[Tuple[LineNumberChunk, float]]:
        """
        Search for semantically similar chunks
        
        Returns:
            List of (chunk, similarity_score) tuples
            Lower score = more similar (L2 distance)
        """
        if not self.has_index(repo_id):
            logger.error(f"No index found for {repo_id}")
            return []
        
        try:
            # Load index
            index_path = self.storage_dir / f"{repo_id}.faiss"
            index = faiss.read_index(str(index_path))
            
            # Load chunks
            chunks_path = self.storage_dir / f"{repo_id}_chunks.pkl"
            with open(chunks_path, 'rb') as f:
                chunks = pickle.load(f)
            
            # Embed query
            model = self._get_embeddings_model()
            query_embedding = np.array([model.embed_query(query)], dtype='float32')
            
            # Search
            distances, indices = index.search(query_embedding, min(k, len(chunks)))
            
            # Collect results
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < len(chunks):
                    results.append((chunks[idx], float(dist)))
            
            logger.info(f"Found {len(results)} similar chunks for query")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            return []
    
    def search_by_selection(
        self,
        repo_id: str,
        file_path: str,
        start_line: int,
        end_line: int,
        additional_context_k: int = 3
    ) -> Dict[str, List[LineNumberChunk]]:
        """
        CRITICAL METHOD for selection-based retrieval
        
        Given a file + line selection:
        1. Get exact chunks that overlap with selection (from ChunkStore)
        2. Get semantically related chunks (from FAISS)
        3. Return both sets
        
        Returns:
            {
                "selected_chunks": [...],  # Chunks overlapping with selection
                "context_chunks": [...]     # Additional semantic context
            }
        """
        chunk_store = ChunkStore(Config.CHUNKS_DIR)
        
        # 1. Get chunks that overlap with selected lines
        selected_chunks = chunk_store.get_chunks_by_lines(
            repo_id, file_path, start_line, end_line
        )
        
        logger.info(f"Found {len(selected_chunks)} chunks for lines {start_line}-{end_line}")
        
        # 2. Get semantically similar chunks using the selected content as query
        context_chunks = []
        if selected_chunks and self.has_index(repo_id):
            # Use first selected chunk as query
            query_text = selected_chunks[0].content
            
            # Search for similar chunks
            similar_results = self.search_similar(repo_id, query_text, k=additional_context_k + len(selected_chunks))
            
            # Filter out chunks that are already in selected_chunks
            selected_ids = {c.chunk_id for c in selected_chunks}
            for chunk, score in similar_results:
                if chunk.chunk_id not in selected_ids:
                    context_chunks.append(chunk)
                    if len(context_chunks) >= additional_context_k:
                        break
        
        logger.info(f"Found {len(context_chunks)} additional context chunks")
        
        return {
            "selected_chunks": selected_chunks,
            "context_chunks": context_chunks
        }
    
    def get_index_stats(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics about the index"""
        if not self.has_index(repo_id):
            return None
        
        info_path = self.storage_dir / f"{repo_id}_info.pkl"
        if info_path.exists():
            with open(info_path, 'rb') as f:
                return pickle.load(f)
        
        return None
