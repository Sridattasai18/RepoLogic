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
from langchain_google_genai import ChatGoogleGenerativeAI
from pathlib import Path
import logging
import os

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

env_name = "Vercel (Serverless)" if Config.IS_VERCEL else "Local Development"
print(f"🔄 Initializing RepoLogic ({env_name})...")
Config.validate_api_key()

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
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(repo_path)
                ext = file_path.suffix.lower()
                
                if ext not in INCLUDED_EXTENSIONS:
                    continue
                
                if file_path.stat().st_size > 1_000_000:
                    continue
                
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    if not content.strip():
                        continue
                    
                    language = detect_language(file_path)
                    file_chunks = chunker.chunk_file(
                        repo_id=repo_id,
                        file_path=str(rel_path).replace('\\', '/'),
                        content=content,
                        language=language,
                        extension=ext
                    )
                    
                    all_chunks.extend(file_chunks)
                    files_chunked += 1
                    
                except Exception as e:
                    logger.warning(f"[CHUNK] Error chunking {rel_path}: {e}")
                    continue
        
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
        
        embedding_store = EmbeddingStore()
        success = embedding_store.create_index(repo_id, chunks)
        
        if not success:
            return jsonify({"error": "Failed to create embeddings"}), 500
        
        logger.info(f"[EMBED] ✅ Complete for {repo_id}")
        
        return jsonify({
            "repo_id": repo_id,
            "total_chunks": len(chunks),
            "index_created": True
        }), 200
        
    except Exception as e:
        logger.error(f"[EMBED] Failed: {e}", exc_info=True)
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

Use Markdown formatting. Be educational and clear.

Explanation:"""


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
        repo_id = get_repo_id(repo_url)
        
        embedding_store = EmbeddingStore()
        
        context_data = embedding_store.search_by_selection(
            repo_id=repo_id,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            additional_context_k=3
        )
        
        # Build context
        context_parts = []
        for chunk in context_data['selected_chunks']:
            context_parts.append(
                f"[{chunk.file_path}:{chunk.start_line}-{chunk.end_line}]\n{chunk.content}"
            )
        for chunk in context_data['context_chunks']:
            context_parts.append(
                f"[Related: {chunk.file_path}:{chunk.start_line}-{chunk.end_line}]\n{chunk.content}"
            )
        
        context_text = "\n\n---\n\n".join(context_parts) if context_parts else selected_code
        
        prompt = EXPLAIN_PROMPT.format(
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            selected_code=selected_code,
            context=context_text
        )
        
        response = llm.invoke(prompt)
        explanation = response.content
        
        logger.info(f"[EXPLAIN] ✅ Complete for {file_path}")
        
        return jsonify({
            "file_path": file_path,
            "line_range": f"{start_line}-{end_line}",
            "explanation": explanation,
            "context_chunks_used": len(context_data['selected_chunks']) + len(context_data['context_chunks'])
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
4. **Admit limitations**: If the context doesn't contain the answer, clearly state: "I couldn't find information about [topic] in the retrieved context."
5. **Structured response**: Use bullet points, code snippets, and clear sections

Use Markdown formatting. Be educational and precise.

Answer:"""


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
    data = request.json
    if not data or 'repo_url' not in data or 'question' not in data:
        return jsonify({"error": "Please provide repo_url and question"}), 400
    
    repo_url = data['repo_url'].strip()
    question = data['question'].strip()
    
    if not repo_url or not question:
        return jsonify({"error": "repo_url and question cannot be empty"}), 400
    
    logger.info(f"[ASK] Question: {question}")
    
    try:
        repo_id = get_repo_id(repo_url)
        
        # Check if embeddings exist
        embedding_store = EmbeddingStore()
        if not embedding_store.has_index(repo_id):
            return jsonify({"error": "Repository not indexed. Please analyze the repository first."}), 400
        
        # Search for relevant chunks using the question
        similar_chunks = embedding_store.search_similar(
            repo_id=repo_id,
            query=question,
            k=5  # Retrieve top 5 relevant chunks
        )
        
        if not similar_chunks:
            return jsonify({
                "question": question,
                "answer": "I couldn't find relevant information in the repository to answer this question.",
                "chunks_used": 0
            }), 200
        
        # Build context from retrieved chunks
        context_parts = []
        for chunk, score in similar_chunks:
            context_parts.append(
                f"[{chunk.file_path}:{chunk.start_line}-{chunk.end_line}]\n{chunk.content}"
            )
        
        context_text = "\n\n---\n\n".join(context_parts)
        
        # Generate answer
        prompt = QA_PROMPT.format(
            question=question,
            context=context_text
        )
        
        response = llm.invoke(prompt)
        answer = response.content
        
        logger.info(f"[ASK] ✅ Complete with {len(similar_chunks)} chunks")
        
        return jsonify({
            "question": question,
            "answer": answer,
            "chunks_used": len(similar_chunks)
        }), 200
        
    except Exception as e:
        logger.error(f"[ASK] Failed: {e}", exc_info=True)
        return jsonify({"error": f"Q&A failed: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
