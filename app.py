"""
RepoLogic - Selection-Based Repository Analyzer
Clean Flask API with RAG pipeline for code explanation
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from config import Config
from tools.github_loader import validate_github_url, get_repo_id
from tools.repo_ingestor import RepoIngestor, INCLUDED_EXTENSIONS, IGNORE_DIRS, detect_language
from tools.chunker import FileChunker, ChunkStore
from tools.embedder import EmbeddingStore
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from google.api_core.exceptions import PermissionDenied, InvalidArgument
from pathlib import Path
import logging
import os
import time
import concurrent.futures


# ═══════════════════════════════════════════════════════════════
# Logging Setup
# ═══════════════════════════════════════════════════════════════

log_handlers = [logging.StreamHandler()]

if not Config.IS_VERCEL:
    try:
        log_handlers.append(logging.FileHandler('repologic.log', encoding='utf-8'))
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# App Initialization
# ═══════════════════════════════════════════════════════════════

app = Flask(__name__, static_folder='static')
CORS(app)

Config.ensure_dirs()

# ── Global API key health flag (set once at startup) ────────────────────────
# True  → key validated; False → key missing/invalid; None → check skipped
api_key_valid: bool = False


def validate_api_key_on_startup() -> None:
    """
    Make one cheap embed_query("healthcheck") call to verify the Gemini API
    key is present and accepted.  Runs exactly once at server startup.

    Sets the module-level `api_key_valid` flag:
      True   → key accepted by the API
      False  → key missing, invalid, or explicitly rejected (PermissionDenied /
               InvalidArgument / message contains 'API_KEY_INVALID')
    Transient errors (network, timeout) leave the flag unchanged (False) but
    are logged as warnings rather than hard failures — we don't want a flaky
    network at boot time to permanently flag a good key as bad.
    """
    global api_key_valid

    if not Config.GOOGLE_API_KEY:
        logger.error(
            "❌ GOOGLE_API_KEY is not set. "
            "Get a valid key at https://aistudio.google.com/app/apikey "
            "and set it in .env, then restart the server."
        )
        api_key_valid = False
        return

    try:
        probe = GoogleGenerativeAIEmbeddings(
            model=Config.EMBEDDING_MODEL,
            google_api_key=Config.GOOGLE_API_KEY,
        )
        probe.embed_query("healthcheck")
        logger.info("✅ Gemini API key validated.")
        api_key_valid = True

    except (PermissionDenied, InvalidArgument) as e:
        logger.error(
            "❌ GOOGLE_API_KEY is invalid or not enabled. "
            "Get a valid key at https://aistudio.google.com/app/apikey "
            "and set it in .env, then restart the server. "
            f"(Detail: {e})"
        )
        api_key_valid = False

    except Exception as e:
        # Catch any other exception whose message mentions API_KEY_INVALID
        if "API_KEY_INVALID" in str(e):
            logger.error(
                "❌ GOOGLE_API_KEY is invalid or not enabled. "
                "Get a valid key at https://aistudio.google.com/app/apikey "
                "and set it in .env, then restart the server. "
                f"(Detail: {e})"
            )
            api_key_valid = False
        else:
            # Transient network / timeout — don't penalise the key
            logger.warning(
                f"⚠️  Gemini API key check could not complete (transient error: {e}). "
                "Startup will continue — the key may still be valid."
            )
            # Leave api_key_valid as False (conservative default) but do not
            # treat this as a confirmed bad-key situation.


env_name = "Vercel (Serverless)" if Config.IS_VERCEL else "Local Development"
print(f"🔄 Initializing RepoLogic ({env_name})...")

validate_api_key_on_startup()

llm = ChatGoogleGenerativeAI(
    model=Config.LLM_MODEL,
    google_api_key=Config.GOOGLE_API_KEY,
    temperature=0
)
print("✅ System ready!")

# ═══════════════════════════════════════════════════════════════
# Static File Routes
# ═══════════════════════════════════════════════════════════════

@app.route('/')
def serve_index():
    """Serve the frontend"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory(app.static_folder, path)


# ═══════════════════════════════════════════════════════════════
# Health Endpoint
# ═══════════════════════════════════════════════════════════════

@app.route('/health', methods=['GET'])
def health_check():
    """
    GET /health
    Returns overall server status and whether the Gemini API key passed
    the startup validation probe.

    Response:
        { "status": "ok" | "degraded", "api_key_valid": true | false }

    The frontend should call this on page load and display a banner if
    api_key_valid is false, so users know before they try to embed a repo.
    """
    status = "ok" if api_key_valid else "degraded"
    return jsonify({"status": status, "api_key_valid": api_key_valid}), 200


# ═══════════════════════════════════════════════════════════════
# PHASE 1: Repository Ingestion
# ═══════════════════════════════════════════════════════════════

@app.route('/ingest', methods=['POST'])
def ingest_repo():
    """
    Ingest repository and return structured data
    POST /ingest
    Body: { "repo_url": "..." }
    """
    data = request.json
    if not data or 'repo_url' not in data:
        return jsonify({"error": "Please provide repo_url"}), 400
    
    repo_url = data['repo_url'].strip()
    if not repo_url:
        return jsonify({"error": "repo_url cannot be empty"}), 400
    
    logger.info(f"[INGEST] Starting: {repo_url}")
    
    try:
        ingestor = RepoIngestor()
        result = ingestor.ingest(repo_url)
        
        logger.info(f"[INGEST] ✅ Complete: {result['stats']['total_files']} files")
        return jsonify(result), 200
        
    except ValueError as e:
        logger.error(f"[INGEST] Validation error: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"[INGEST] Failed: {e}", exc_info=True)
        return jsonify({"error": f"Ingestion failed: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════
# PHASE 2: Chunking
# ═══════════════════════════════════════════════════════════════

@app.route('/chunk', methods=['POST'])
def chunk_repo():
    """
    Chunk repository files with line number tracking
    POST /chunk
    Body: { "repo_url": "..." }
    """
    data = request.json
    if not data or 'repo_url' not in data:
        return jsonify({"error": "Please provide repo_url"}), 400
    
    repo_url = data['repo_url'].strip()
    if not repo_url:
        return jsonify({"error": "repo_url cannot be empty"}), 400
    
    logger.info(f"[CHUNK] Starting: {repo_url}")
    
    try:
        repo_id = get_repo_id(repo_url)
        repo_path = Config.REPO_CACHE_DIR / repo_id
        
        if not repo_path.exists():
            return jsonify({"error": "Repository not ingested. Call /ingest first."}), 400
        
        chunker = FileChunker(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP
        )
        chunk_store = ChunkStore(Config.CHUNKS_DIR)
        
        all_chunks = []
        files_chunked = 0
        
        # Collect all files to process first
        files_to_process = []
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                file_path = Path(root) / file
                
                # Fast checks before adding to list
                if file_path.suffix.lower() not in INCLUDED_EXTENSIONS:
                    continue
                    
                files_to_process.append(file_path)

        def process_file(file_path):
            """Helper to process a single file"""
            try:
                if file_path.stat().st_size > 1_000_000:
                    return []
                
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                if not content.strip():
                    return []
                
                rel_path = file_path.relative_to(repo_path)
                ext = file_path.suffix.lower()
                language = detect_language(file_path)
                
                return chunker.chunk_file(
                    repo_id=repo_id,
                    file_path=str(rel_path).replace('\\', '/'),
                    content=content,
                    language=language,
                    extension=ext
                )
            except Exception as e:
                logger.warning(f"[CHUNK] Error processing {file_path}: {e}")
                return []

        # Process files in parallel
        # Using a modest number of workers (e.g. 10) to balance I/O and CPU
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_file = {executor.submit(process_file, fp): fp for fp in files_to_process}
            
            for future in concurrent.futures.as_completed(future_to_file):
                try:
                    chunks = future.result()
                    if chunks:
                        all_chunks.extend(chunks)
                        files_chunked += 1
                except Exception as e:
                    logger.error(f"Worker failed: {e}")
        
        chunk_store.save_chunks(repo_id, all_chunks)
        
        logger.info(f"[CHUNK] ✅ Complete: {len(all_chunks)} chunks from {files_chunked} files")
        
        return jsonify({
            "repo_id": repo_id,
            "total_chunks": len(all_chunks),
            "files_chunked": files_chunked
        }), 200
        
    except Exception as e:
        logger.error(f"[CHUNK] Failed: {e}", exc_info=True)
        return jsonify({"error": f"Chunking failed: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════
# PHASE 3: Embeddings
# ═══════════════════════════════════════════════════════════════

@app.route('/embed', methods=['POST'])
def embed_repo():
    """
    Generate embeddings and create FAISS index
    POST /embed
    Body: { "repo_url": "..." }
    """
    data = request.json
    if not data or 'repo_url' not in data:
        return jsonify({"error": "Please provide repo_url"}), 400
    
    repo_url = data['repo_url'].strip()
    if not repo_url:
        return jsonify({"error": "repo_url cannot be empty"}), 400
    
    logger.info(f"[EMBED] Starting: {repo_url}")
    
    try:
        repo_id = get_repo_id(repo_url)
        
        chunk_store = ChunkStore(Config.CHUNKS_DIR)
        if not chunk_store.has_chunks(repo_id):
            return jsonify({"error": "No chunks found. Call /chunk first."}), 400
        
        chunks = chunk_store.load_chunks(repo_id)
        if not chunks:
            return jsonify({"error": "No chunks to embed"}), 400
        
        logger.info(f"[EMBED] Loaded {len(chunks)} chunks")

        # Clear any prior embed error file on a new embedding attempt
        error_file = Config.CHUNKS_DIR / f"{repo_id}_embed_error.txt"
        if error_file.exists():
            try:
                error_file.unlink()
            except Exception as unlink_err:
                logger.warning(f"Could not delete old embed error file: {unlink_err}")

        embedding_store = EmbeddingStore()
        result = embedding_store.create_index(repo_id, chunks)

        if not result["success"]:
            error_tag = result.get("error", "unknown_error")
            detail = result.get("detail", "")

            if error_tag == "quota_exhausted":
                user_message = (
                    "Gemini API quota / rate limit hit. Some or all chunks could not "
                    "be embedded. Wait a minute and retry, or try a smaller repository."
                )
                status_code = 429
            elif error_tag == "no_embeddings":
                user_message = "No embeddings were generated — the chunk list may be empty."
                status_code = 400
            else:
                user_message = "Embedding failed due to an internal error. Check server logs."
                status_code = 500

            # Option B: Write error sentinel
            try:
                error_file.write_text(user_message, encoding="utf-8")
            except Exception as write_err:
                logger.error(f"Failed to write embed error file: {write_err}")

            return jsonify({
                "error": error_tag,
                "message": user_message,
                "detail": detail,
            }), status_code

        logger.info(f"[EMBED] ✅ Complete for {repo_id}")

        return jsonify({
            "repo_id": repo_id,
            "total_chunks": result["total_chunks"],
            "chunks_skipped": result.get("chunks_skipped", 0),
            "index_created": True,
        }), 200

    except Exception as e:
        logger.error(f"[EMBED] Failed: {e}", exc_info=True)
        # Write generic error sentinel
        try:
            error_file = Config.CHUNKS_DIR / f"{repo_id}_embed_error.txt"
            error_file.write_text(f"Embedding failed: {str(e)}", encoding="utf-8")
        except Exception:
            pass
        return jsonify({"error": f"Embedding failed: {str(e)}"}), 500



# ═══════════════════════════════════════════════════════════════
# PHASE 4: File Content
# ═══════════════════════════════════════════════════════════════

@app.route('/file-content', methods=['GET'])
def get_file_content():
    """
    Get file content for code viewer
    GET /file-content?repo_id=xxx&path=src/app.py
    """
    repo_id = request.args.get('repo_id')
    file_path = request.args.get('path')
    
    if not repo_id or not file_path:
        return jsonify({"error": "Please provide repo_id and path"}), 400
    
    logger.info(f"[FILE] Loading: {repo_id}/{file_path}")
    
    try:
        repo_path = Config.REPO_CACHE_DIR / repo_id
        
        if not repo_path.exists():
            return jsonify({"error": "Repository not found"}), 404
        
        clean_path = file_path.replace('..', '').lstrip('/')
        full_path = repo_path / clean_path
        
        if not full_path.exists():
            return jsonify({"error": "File not found"}), 404
        
        if not full_path.is_file():
            return jsonify({"error": "Path is not a file"}), 400
        
        content = full_path.read_text(encoding='utf-8', errors='ignore')
        language = detect_language(full_path).lower()
        
        return jsonify({
            "path": file_path,
            "content": content,
            "language": language,
            "lines": content.count('\n') + 1
        }), 200
        
    except Exception as e:
        logger.error(f"[FILE] Failed: {e}", exc_info=True)
        return jsonify({"error": f"Failed to load file: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════
# PHASE 5: Selection-Based Explanation (CORE FEATURE)
# ═══════════════════════════════════════════════════════════════

EXPLAIN_PROMPT = """You are an expert code analyst explaining selected code to a developer.

**Selected Code** (from {file_path}, lines {start_line}-{end_line}):
```
{selected_code}
```

**Repository Context**:
{context}

**Your Task**: Explain the selected code clearly and thoroughly.

Guidelines:
1. **What it does**: Explain the functionality in plain English
2. **How it works**: Break down the logic step by step
3. **Key concepts**: Highlight important patterns, algorithms, or design decisions
4. **Dependencies**: Note any important imports, functions, or classes it relies on
5. **Context**: Explain how it fits into the broader codebase (if visible from context)

Return ONLY valid JSON, no markdown fences or preamble:
{{
  "summary": "1-2 sentence summary of what the selected code does",
  "explanation": "full markdown explanation with headers, bullets, and code blocks as needed",
  "confidence": "grounded|partial|insufficient_context",
  "file_references": [{{"file": "path/to/file.py", "lines": "10-25", "reason": "why referenced"}}]
}}"""


@app.route('/explain', methods=['POST'])
def explain_selection():
    """
    Explain selected code using RAG
    POST /explain
    Body: {
        "repo_url": "...",
        "file_path": "src/app.py",
        "start_line": 10,
        "end_line": 25,
        "selected_code": "..."
    }
    """
    import json as _json

    data = request.json
    required = ['repo_url', 'file_path', 'start_line', 'end_line', 'selected_code']

    if not data or not all(k in data for k in required):
        return jsonify({"error": f"Please provide: {', '.join(required)}"}), 400

    repo_url = data['repo_url'].strip()
    file_path = data['file_path'].strip()
    start_line = data['start_line']
    end_line = data['end_line']
    selected_code = data['selected_code']

    logger.info(f"[EXPLAIN] {file_path} L{start_line}-{end_line}")

    try:
        start_time = time.time()
        repo_id = get_repo_id(repo_url)

        embedding_store = EmbeddingStore()

        context_data = embedding_store.search_by_selection(
            repo_id=repo_id,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            additional_context_k=3
        )

        # Build context and collect sources
        context_parts = []
        sources = []

        for chunk in context_data['selected_chunks']:
            context_parts.append(
                f"[{chunk.file_path}:{chunk.start_line}-{chunk.end_line}]\n{chunk.content}"
            )
            sources.append({
                "file": chunk.file_path,
                "lines": f"{chunk.start_line}-{chunk.end_line}",
                "type": "selected"
            })

        for chunk in context_data['context_chunks']:
            context_parts.append(
                f"[Related: {chunk.file_path}:{chunk.start_line}-{chunk.end_line}]\n{chunk.content}"
            )
            sources.append({
                "file": chunk.file_path,
                "lines": f"{chunk.start_line}-{chunk.end_line}",
                "type": "related"
            })

        context_text = "\n\n---\n\n".join(context_parts) if context_parts else selected_code

        prompt = EXPLAIN_PROMPT.format(
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            selected_code=selected_code,
            context=context_text
        )

        response = llm.invoke(prompt)
        raw = response.content
        if isinstance(raw, list):
            raw = "".join(part.get("text", str(part)) if isinstance(part, dict) else str(part) for part in raw)
        elif not isinstance(raw, str):
            raw = str(raw)

        response_time_ms = int((time.time() - start_time) * 1000)

        # Token-use diagnostic (rough 4-chars-per-token estimate)
        input_tok = len(prompt) // 4
        output_tok = len(raw) // 4
        logger.info(
            f"[EXPLAIN] tokens≈ input={input_tok} output={output_tok} "
            f"file={file_path} time={response_time_ms}ms"
        )

        # Parse structured JSON response; fall back to raw text on failure
        try:
            clean_raw = raw.strip()
            if clean_raw.startswith("```json"):
                clean_raw = clean_raw[7:]
            elif clean_raw.startswith("```"):
                clean_raw = clean_raw[3:]
            if clean_raw.endswith("```"):
                clean_raw = clean_raw[:-3]
            clean_raw = clean_raw.strip()

            parsed = _json.loads(clean_raw)
            explanation  = parsed.get("explanation", raw)
            summary      = parsed.get("summary", "")
            confidence   = parsed.get("confidence", "unknown")
            file_refs    = parsed.get("file_references", [])
        except Exception:
            logger.warning("[EXPLAIN] LLM did not return valid JSON — falling back to raw text")
            explanation, summary, confidence, file_refs = raw, "", "unknown", []

        logger.info(f"[EXPLAIN] ✅ Complete for {file_path} in {response_time_ms}ms")

        return jsonify({
            "file_path": file_path,
            "line_range": f"{start_line}-{end_line}",
            "summary": summary,
            "explanation": explanation,
            "confidence": confidence,
            "file_references": file_refs,
            "context_chunks_used": len(context_data['selected_chunks']) + len(context_data['context_chunks']),
            "sources": sources,
            "response_time_ms": response_time_ms,
            "tokens_approx": {"input": input_tok, "output": output_tok},
        }), 200

    except Exception as e:
        logger.error(f"[EXPLAIN] Failed: {e}", exc_info=True)
        return jsonify({"error": f"Explanation failed: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════
# PHASE 6: Natural Language Q&A (NEW FEATURE)
# ═══════════════════════════════════════════════════════════════

QA_PROMPT = """You are an expert code analyst helping a developer understand a repository.

**User Question**: {question}

**Retrieved Repository Context**:
{context}

**Your Task**: Answer the user's question based ONLY on the retrieved context.

Guidelines:
1. **Be specific**: Reference exact files, functions, and line ranges when possible
2. **Multi-file reasoning**: If the answer spans multiple files, explain the connections
3. **Grounded answers**: Only use information from the context above
4. **Admit limitations**: If the context doesn't contain the answer, clearly state it
5. **Structured response**: Use bullet points, code snippets, and clear sections

Return ONLY valid JSON, no markdown fences or preamble:
{{
  "summary": "1-2 sentence direct answer to the question",
  "explanation": "full markdown answer with headers, bullets, and code blocks as needed",
  "confidence": "grounded|partial|insufficient_context",
  "file_references": [{{"file": "path/to/file.py", "lines": "10-25", "reason": "why referenced"}}]
}}"""


@app.route('/ask', methods=['POST'])
def ask_question():
    """
    Answer natural language questions about the repository
    POST /ask
    Body: {
        "repo_url": "...",
        "question": "How does authentication work?"
    }
    """
    import json as _json

    data = request.json
    if not data or 'repo_url' not in data or 'question' not in data:
        return jsonify({"error": "Please provide repo_url and question"}), 400

    repo_url = data['repo_url'].strip()
    question = data['question'].strip()

    if not repo_url or not question:
        return jsonify({"error": "repo_url and question cannot be empty"}), 400

    logger.info(f"[ASK] Question: {question}")

    try:
        start_time = time.time()
        repo_id = get_repo_id(repo_url)

        # Check if embeddings exist
        embedding_store = EmbeddingStore()
        if not embedding_store.has_index(repo_id):
            return jsonify({"error": "Repository not indexed. Please analyze the repository first."}), 400

        # Search for relevant chunks using the question
        similar_chunks = embedding_store.search_similar(
            repo_id=repo_id,
            query=question,
            k=5
        )

        if not similar_chunks:
            return jsonify({
                "question": question,
                "summary": "",
                "answer": "I couldn't find relevant information in the repository to answer this question.",
                "confidence": "insufficient_context",
                "file_references": [],
                "chunks_used": 0,
                "sources": [],
                "response_time_ms": int((time.time() - start_time) * 1000),
                "tokens_approx": {"input": 0, "output": 0},
            }), 200

        # Build context from retrieved chunks and collect sources
        context_parts = []
        sources = []
        for chunk, score in similar_chunks:
            context_parts.append(
                f"[{chunk.file_path}:{chunk.start_line}-{chunk.end_line}]\n{chunk.content}"
            )
            sources.append({
                "file": chunk.file_path,
                "lines": f"{chunk.start_line}-{chunk.end_line}",
                "relevance_score": round(1 / (1 + score), 2)
            })

        context_text = "\n\n---\n\n".join(context_parts)

        # Generate answer
        prompt = QA_PROMPT.format(question=question, context=context_text)
        response = llm.invoke(prompt)
        raw = response.content
        if isinstance(raw, list):
            raw = "".join(part.get("text", str(part)) if isinstance(part, dict) else str(part) for part in raw)
        elif not isinstance(raw, str):
            raw = str(raw)

        response_time_ms = int((time.time() - start_time) * 1000)

        # Token-use diagnostic (rough 4-chars-per-token estimate)
        input_tok = len(prompt) // 4
        output_tok = len(raw) // 4
        logger.info(
            f"[ASK] tokens≈ input={input_tok} output={output_tok} "
            f"chunks={len(similar_chunks)} time={response_time_ms}ms"
        )

        # Parse structured JSON response; fall back to raw text on failure
        try:
            clean_raw = raw.strip()
            if clean_raw.startswith("```json"):
                clean_raw = clean_raw[7:]
            elif clean_raw.startswith("```"):
                clean_raw = clean_raw[3:]
            if clean_raw.endswith("```"):
                clean_raw = clean_raw[:-3]
            clean_raw = clean_raw.strip()

            parsed = _json.loads(clean_raw)
            answer      = parsed.get("explanation", raw)
            summary     = parsed.get("summary", "")
            confidence  = parsed.get("confidence", "unknown")
            file_refs   = parsed.get("file_references", [])
        except Exception:
            logger.warning("[ASK] LLM did not return valid JSON — falling back to raw text")
            answer, summary, confidence, file_refs = raw, "", "unknown", []

        logger.info(f"[ASK] ✅ Complete with {len(similar_chunks)} chunks in {response_time_ms}ms")

        return jsonify({
            "question": question,
            "summary": summary,
            "answer": answer,
            "confidence": confidence,
            "file_references": file_refs,
            "chunks_used": len(similar_chunks),
            "sources": sources,
            "response_time_ms": response_time_ms,
            "tokens_approx": {"input": input_tok, "output": output_tok},
        }), 200

    except Exception as e:
        logger.error(f"[ASK] Failed: {e}", exc_info=True)
        return jsonify({"error": f"Q&A failed: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════
# Repo Pipeline Status
# ═══════════════════════════════════════════════════════════════

@app.route('/status', methods=['GET'])
def repo_status():
    """
    GET /status?repo_url=<github_url>

    Returns the current pipeline stage for a repository, derived purely
    from which on-disk artefacts exist — no extra state storage needed.

    State machine:
        not_started  →  ingested  →  chunked  →  embedded  →  ready

    Response:
        {
          "repo_id": "owner_repo",
          "stage":   "not_started|ingested|chunked|embedded",
          "ready":   true|false,        # true only when fully embedded
          "details": {
            "repo_cached":   bool,
            "chunks_saved":  bool,
            "index_exists":  bool,
            "total_chunks":  int|null,  # from index metadata if available
            "chunks_skipped": int|null
          }
        }
    """
    repo_url = request.args.get('repo_url', '').strip()
    if not repo_url:
        return jsonify({"error": "Please provide repo_url query parameter"}), 400

    try:
        repo_id = get_repo_id(repo_url)

        # ── check each artefact tier ─────────────────────────────────────────
        repo_cached  = (Config.REPO_CACHE_DIR / repo_id).exists()
        chunk_store  = ChunkStore(Config.CHUNKS_DIR)
        chunks_saved = chunk_store.has_chunks(repo_id)
        embed_store  = EmbeddingStore()
        index_exists = embed_store.has_index(repo_id)

        # Check for embed error file (Option B)
        error_file = Config.CHUNKS_DIR / f"{repo_id}_embed_error.txt"
        embed_error = None
        if error_file.exists():
            try:
                embed_error = error_file.read_text(encoding='utf-8').strip()
            except Exception as read_err:
                logger.warning(f"Could not read embed error file: {read_err}")

        # ── derive stage ─────────────────────────────────────────────────────
        if index_exists:
            stage = "embedded"
        elif embed_error:
            stage = "failed:embed"
        elif chunks_saved:
            stage = "chunked"
        elif repo_cached:
            stage = "ingested"
        else:
            stage = "not_started"

        ready = index_exists  # can answer questions only when fully embedded

        # ── pull metadata from saved index info if available ─────────────────
        index_meta = embed_store.get_index_stats(repo_id) if index_exists else None
        total_chunks   = index_meta.get("total_chunks")   if index_meta else None
        chunks_skipped = index_meta.get("chunks_skipped") if index_meta else None

        logger.info(f"[STATUS] {repo_id} → {stage}")

        return jsonify({
            "repo_id": repo_id,
            "stage":   stage,
            "ready":   ready,
            "error_message": embed_error,
            "details": {
                "repo_cached":    repo_cached,
                "chunks_saved":   chunks_saved,
                "index_exists":   index_exists,
                "total_chunks":   total_chunks,
                "chunks_skipped": chunks_skipped,
            },
        }), 200

    except Exception as e:
        logger.error(f"[STATUS] Failed: {e}", exc_info=True)
        return jsonify({"error": f"Status check failed: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
