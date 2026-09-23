"""
Embedding and Vector Store Module - PHASE 3
Handles chunk embeddings and FAISS-based semantic search

Retry/backoff strategy
-----------------------
* Retryable errors (ResourceExhausted, ServiceUnavailable, DeadlineExceeded) are
  retried with exponential back-off via tenacity.  A batch that exhausts all
  retries is *skipped* (logged as a warning) rather than aborting the whole job —
  partial indexes are far more useful than no index at all.

* Non-retryable errors (bad API key, malformed request, …) propagate immediately
  so they are surfaced to the caller rather than hidden behind retries.

* `create_index()` now returns a structured dict instead of a bare bool so that
  `app.py` can return an actionable HTTP response to the frontend.
"""

import logging
import time
import numpy as np
import faiss
import pickle
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    before_sleep_log,
)
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, DeadlineExceeded
from langchain_google_genai.chat_models import GoogleGenerativeAIError # Might be different, let's just use Exception checking

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from config import Config
from tools.chunker import LineNumberChunk, ChunkStore

logger = logging.getLogger(__name__)


@lru_cache(maxsize=8)
def _load_index_cached(
    index_path_str: str,
    chunks_path_str: str,
    mtime_index: float,
    mtime_chunks: float,
):
    """
    Load FAISS index + chunk list from disk, cached by file path and mtime.
    Cache auto-invalidates when either file is modified (e.g. after re-embedding).
    ponytail: global LRU, per-process — fine for single-worker Flask dev server;
              add per-process isolation if multi-worker gunicorn is used.
    """
    index = faiss.read_index(index_path_str)
    with open(chunks_path_str, "rb") as f:
        chunks = pickle.load(f)
    return index, chunks

def is_retryable_error(e: Exception) -> bool:
    """Check if the exception is a rate limit or transient error."""
    if isinstance(e, (ResourceExhausted, ServiceUnavailable, DeadlineExceeded)):
        return True
    
    # langchain_google_genai wraps errors in GoogleGenerativeAIError
    err_str = str(e).upper()
    if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str or "503" in err_str or "QUOTA" in err_str:
        return True
        
    return False


class EmbeddingBatchError(Exception):
    """Raised when *all* embedding batches fail after retries."""

    def __init__(self, message: str, failed_indices: List[int]):
        super().__init__(message)
        self.failed_indices = failed_indices


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
                google_api_key=Config.GOOGLE_API_KEY,
            )
        return self.embeddings_model

    # ── per-batch call, decorated with retry ───────────────────────────────
    def _embed_batch_with_retry(self, model, batch: List[str]) -> List:
        """
        Embed a single batch with exponential back-off retry.
        Decorated dynamically so Config values are resolved at call time.
        """
        @retry(
            stop=stop_after_attempt(Config.EMBEDDING_MAX_RETRIES),
            wait=wait_exponential(
                multiplier=1,
                min=Config.EMBEDDING_RETRY_MIN_WAIT,
                max=Config.EMBEDDING_RETRY_MAX_WAIT,
            ),
            retry=retry_if_exception(is_retryable_error),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        def _call():
            return model.embed_documents(batch)

        return _call()

    # ── main embedding loop ─────────────────────────────────────────────────
    def embed_chunks(
        self, chunks: List[LineNumberChunk]
    ) -> Tuple[np.ndarray, List[LineNumberChunk]]:
        """
        Generate embeddings for chunks.

        Returns:
            (embeddings_array, surviving_chunks)  — chunks whose batches failed
            are dropped; their indices are logged as warnings.

        Raises:
            EmbeddingBatchError  — if every single batch fails.
            Exception            — non-retryable errors propagate immediately.
        """
        if not chunks:
            return np.array([]), []

        model = self._get_embeddings_model()

        texts_to_embed = [
            f"File: {c.file_path}\nLanguage: {c.language}\n\n{c.content}"
            for c in chunks
        ]

        logger.info(f"Generating embeddings for {len(chunks)} chunks...")

        batch_size = Config.EMBEDDING_BATCH_SIZE
        total_batches = (len(texts_to_embed) + batch_size - 1) // batch_size
        raw_embeddings: List[Optional[list]] = []
        failed_indices: List[int] = []

        for batch_num, i in enumerate(range(0, len(texts_to_embed), batch_size)):
            batch = texts_to_embed[i : i + batch_size]
            try:
                batch_embeddings = self._embed_batch_with_retry(model, batch)
                raw_embeddings.extend(batch_embeddings)
                logger.info(
                    f"Batch {batch_num + 1}/{total_batches} embedded "
                    f"({len(batch)} chunks)"
                )
            except Exception as e:
                if is_retryable_error(e):
                    # All retries exhausted — skip this batch, keep going
                    logger.error(
                        f"Batch {batch_num + 1}/{total_batches} failed after "
                        f"{Config.EMBEDDING_MAX_RETRIES} retries: {e}"
                    )
                    failed_indices.extend(range(i, i + len(batch)))
                    raw_embeddings.extend([None] * len(batch))
                else:
                    # Non-retryable (bad key, malformed request, …) — fail fast
                    logger.error(f"Non-retryable error in batch {batch_num + 1}: {e}")
                    raise

            # Pause between batches to stay under free-tier RPM
            if batch_num < total_batches - 1:
                time.sleep(Config.EMBEDDING_BATCH_DELAY_SEC)

        # Drop failed chunks, keep chunks+embeddings aligned
        good_pairs = [
            (c, e) for c, e in zip(chunks, raw_embeddings) if e is not None
        ]

        if not good_pairs:
            raise EmbeddingBatchError(
                "All embedding batches failed — quota exhausted or network error.",
                failed_indices,
            )

        surviving_chunks, surviving_embeddings = zip(*good_pairs)
        embeddings_array = np.array(surviving_embeddings, dtype="float32")

        if failed_indices:
            logger.warning(
                f"⚠️  {len(failed_indices)}/{len(chunks)} chunks could not be "
                f"embedded and were skipped. Index will be partial."
            )
        else:
            logger.info(f"✅ Generated embeddings: shape {embeddings_array.shape}")

        return embeddings_array, list(surviving_chunks)

    # ── index creation ──────────────────────────────────────────────────────
    def create_index(self, repo_id: str, chunks: List[LineNumberChunk]) -> Dict[str, Any]:
        """
        Create FAISS index for repository chunks.

        Returns a structured dict:
            {"success": True,  "total_chunks": N, "chunks_skipped": K}
            {"success": False, "error": "<tag>", "detail": "<message>"}

        Error tags:
            "quota_exhausted"  — all batches failed, likely rate-limited
            "no_embeddings"    — no chunks / zero-size result
            "internal_error"   — unexpected exception
        """
        if not chunks:
            logger.warning("No chunks to index")
            return {"success": False, "error": "no_embeddings", "detail": "No chunks provided"}

        try:
            embeddings, surviving_chunks = self.embed_chunks(chunks)

            if embeddings.size == 0:
                return {
                    "success": False,
                    "error": "no_embeddings",
                    "detail": "Embeddings array is empty",
                }

            # Build FAISS index
            dimension = embeddings.shape[1]
            index = faiss.IndexFlatL2(dimension)
            index.add(embeddings)

            # Persist index
            index_path = self.storage_dir / f"{repo_id}.faiss"
            faiss.write_index(index, str(index_path))

            # Persist surviving chunks (aligned to index)
            chunks_path = self.storage_dir / f"{repo_id}_chunks.pkl"
            with open(chunks_path, "wb") as f:
                pickle.dump(surviving_chunks, f)

            # Persist metadata
            skipped = len(chunks) - len(surviving_chunks)
            info_path = self.storage_dir / f"{repo_id}_info.pkl"
            with open(info_path, "wb") as f:
                pickle.dump(
                    {
                        "total_chunks": len(surviving_chunks),
                        "chunks_skipped": skipped,
                        "dimension": dimension,
                        "repo_id": repo_id,
                    },
                    f,
                )

            logger.info(
                f"✅ Indexed {repo_id}: {len(surviving_chunks)} chunks "
                f"({skipped} skipped)"
            )
            return {
                "success": True,
                "total_chunks": len(surviving_chunks),
                "chunks_skipped": skipped,
            }

        except EmbeddingBatchError as e:
            logger.error(f"All embeddings failed for {repo_id}: {e}")
            return {
                "success": False,
                "error": "quota_exhausted",
                "detail": str(e),
            }
        except Exception as e:
            logger.error(f"Failed to create index for {repo_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": "internal_error",
                "detail": str(e),
            }

    # ── index presence check ────────────────────────────────────────────────
    def has_index(self, repo_id: str) -> bool:
        """Check if index exists for repository"""
        index_path = self.storage_dir / f"{repo_id}.faiss"
        chunks_path = self.storage_dir / f"{repo_id}_chunks.pkl"
        return index_path.exists() and chunks_path.exists()

    # ── semantic search ─────────────────────────────────────────────────────
    def search_similar(
        self,
        repo_id: str,
        query: str,
        k: int = 5,
    ) -> List[Tuple[LineNumberChunk, float]]:
        """
        Search for semantically similar chunks.

        Returns:
            List of (chunk, similarity_score) tuples.
            Lower score = more similar (L2 distance).
        """
        if not self.has_index(repo_id):
            logger.error(f"No index found for {repo_id}")
            return []

        index_path = self.storage_dir / f"{repo_id}.faiss"
        chunks_path = self.storage_dir / f"{repo_id}_chunks.pkl"

        # Use mtime-keyed cache to avoid disk I/O on every query
        index, chunks = _load_index_cached(
            str(index_path), str(chunks_path),
            index_path.stat().st_mtime, chunks_path.stat().st_mtime,
        )

        model = self._get_embeddings_model()
        query_embedding = np.array([model.embed_query(query)], dtype="float32")

        distances, indices = index.search(query_embedding, min(k, len(chunks)))

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(chunks):
                results.append((chunks[idx], float(dist)))

        logger.info(f"Found {len(results)} similar chunks for query")
        return results

    # ── selection-based retrieval ───────────────────────────────────────────
    def search_by_selection(
        self,
        repo_id: str,
        file_path: str,
        start_line: int,
        end_line: int,
        additional_context_k: int = 3,
    ) -> Dict[str, List[LineNumberChunk]]:
        """
        CRITICAL METHOD for selection-based retrieval.

        Given a file + line selection:
        1. Get exact chunks that overlap with selection (from ChunkStore)
        2. Get semantically related chunks (from FAISS)
        3. Return both sets

        Returns:
            {
                "selected_chunks": [...],  # Chunks overlapping with selection
                "context_chunks": [...]    # Additional semantic context
            }
        """
        chunk_store = ChunkStore(Config.CHUNKS_DIR)

        selected_chunks = chunk_store.get_chunks_by_lines(
            repo_id, file_path, start_line, end_line
        )
        logger.info(f"Found {len(selected_chunks)} chunks for lines {start_line}-{end_line}")

        context_chunks = []
        if selected_chunks and self.has_index(repo_id):
            query_text = selected_chunks[0].content
            similar_results = self.search_similar(
                repo_id, query_text, k=additional_context_k + len(selected_chunks)
            )
            selected_ids = {c.chunk_id for c in selected_chunks}
            for chunk, score in similar_results:
                if chunk.chunk_id not in selected_ids:
                    context_chunks.append(chunk)
                    if len(context_chunks) >= additional_context_k:
                        break

        logger.info(f"Found {len(context_chunks)} additional context chunks")
        return {
            "selected_chunks": selected_chunks,
            "context_chunks": context_chunks,
        }

    # ── stats ───────────────────────────────────────────────────────────────
    def get_index_stats(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics about the index"""
        if not self.has_index(repo_id):
            return None

        info_path = self.storage_dir / f"{repo_id}_info.pkl"
        if info_path.exists():
            with open(info_path, "rb") as f:
                return pickle.load(f)

        return None
