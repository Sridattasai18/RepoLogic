# Ecode Performance Guide

## Why Repository Loading Takes Time

### First-Time Indexing (10-30 seconds)
When you load a repository for the first time, Ecode performs these steps:

1. **Fetch Repository** (2-5 seconds)
   - Clones the repository using Git
   - Filters out binary files, images, node_modules, etc.
   - Extracts readable text from code files

2. **Chunking** (<1 second)
   - Splits files into 600-token chunks with 100-token overlap
   - Preserves file metadata for each chunk

3. **Embedding Generation** (8-25 seconds) ⏱️ **SLOWEST STEP**
   - Sends chunks to Gemini API for vectorization
   - Uses batch API (`batchEmbedContents`) to optimize
   - Limited by:
     - Network latency to Google servers
     - Gemini API rate limits (free tier)
     - Batch size limits (~100 items per request)
   - Example: 67 chunks ≈ 15-20 seconds

4. **FAISS Indexing** (<1 second)
   - Creates vector index for fast similarity search
   - Saves to `~/.ecode/vector_store/<repo_id>/`

### Subsequent Loads (Instant)
Once indexed, the repository loads instantly because:
- FAISS index is cached locally
- No re-cloning or re-embedding needed
- Only retrieval queries hit the API

### Query Time (1-3 seconds)
When you ask a question:
1. Embed the question (1 API call, ~200ms)
2. Search FAISS index (local, <10ms)
3. Generate answer from Gemini (~1-2 seconds)

---

## Performance Optimizations Already Implemented

✅ **Batch Embedding** - Uses `batchEmbedContents` API  
✅ **Local Caching** - FAISS indexes stored in `~/.ecode/`  
✅ **Lazy Loading** - Models initialized only when needed  
✅ **Smart Chunking** - Optimized chunk size (600 tokens)  
✅ **File Filtering** - Ignores binaries, images, dependencies  

---

## Why We Can't Go Faster (Free Tier Constraints)

1. **Gemini API Limits**
   - Free tier has rate limits
   - Batch size capped at ~100 items
   - Network latency (unavoidable)

2. **No Local Embeddings**
   - Using local models (e.g., sentence-transformers) would be faster
   - But requires downloading 400MB+ models
   - Gemini embeddings are higher quality

3. **Git Clone Speed**
   - Depends on repository size
   - Depends on internet speed
   - Already optimized with `--depth=1` (shallow clone)

---

## Expected Timings

| Repository Size | First Load | Subsequent Loads | Query Time |
|----------------|-----------|------------------|------------|
| Small (5-10 files) | 10-15s | Instant | 1-2s |
| Medium (20-50 files) | 20-30s | Instant | 1-3s |
| Large (100+ files) | 40-60s | Instant | 2-4s |

---

## Tips for Users

1. **Be patient on first load** - Indexing is a one-time cost
2. **Reuse indexed repos** - Subsequent loads are instant
3. **Use specific URLs** - Avoid re-indexing the same repo with different URLs
4. **Check logs** - Server logs show detailed progress

---

## Future Optimizations (Not Implemented)

- **Streaming progress updates** to frontend
- **Parallel embedding** (if API allows)
- **Incremental indexing** (only new files)
- **Local embedding models** (optional)
