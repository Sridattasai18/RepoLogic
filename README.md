# RepoLogic — Intelligent Codebase Research Tool

RepoLogic turns any GitHub repository into an interactive, conversation-first knowledge base. Powered by Google Gemini and FAISS semantic search, it delivers grounded code explanations, inline citation evidence, and multi-workspace repository exploration.

![Status](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Key Capabilities

- **Conversation-First Exploration**: Code is treated as supporting evidence directly inside conversation streams rather than requiring a separate IDE pane.
- **Inline Citation Evidence**: Clickable source chips (`README.md:16-53`) expand syntax-highlighted code blocks with line numbers directly beneath the response.
- **Confidence Badging**: Every response self-reports retrieval quality (`grounded`, `partial`, `insufficient_context`).
- **4-Stage Pipeline with Live Stepper**: Clear visual feedback across repository cloning, code structure analysis, index generation, and readiness.
- **Multi-Project Workspace Rail**: Ultra-compact 44px vertical rail with dynamic space switching and a popover file tree modal.
- **RAG Architecture**: Recursive per-language code chunking with FAISS vector similarity search.
- **Fail-Fast Startup Probe & Exponential Retry**: Startup sanity health check catches missing or invalid API keys before serving; embedding batch workers automatically back off on free-tier rate limits (`429 RESOURCE_EXHAUSTED`).

---

## Architecture & Pipeline

```
GitHub Repository
   │
   ▼
[ 1. Ingest ] ──► git clone to ~/.ecode/repo_cache + file traversal
   │
   ▼
[ 2. Chunk  ] ──► RecursiveCharacterTextSplitter (language-aware, line-number tracking)
   │
   ▼
[ 3. Embed  ] ──► GoogleGenerativeAIEmbeddings (models/gemini-embedding-001) + FAISS Index
   │
   ▼
[ 4. Query  ] ──► Vector similarity search (top-k) + Gemini LLM with structured JSON output
```

---

## Tech Stack

- **Backend**: Python 3.8+, Flask, Tenacity (retry handling)
- **AI / Embeddings**: Google Gemini API (`models/gemini-embedding-001`, `gemini-flash-lite-latest`), LangChain
- **Vector Search**: FAISS (Facebook AI Similarity Search)
- **Frontend**: Vanilla JavaScript (ES6+), HTML5, CSS3 (IBM Plex Sans & IBM Plex Mono)
- **Syntax Highlighting & Formatting**: highlight.js, marked.js

---

## Prerequisites

- Python 3.8 or higher
- Git
- Google Gemini API key ([AI Studio](https://aistudio.google.com/app/apikey))

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/Sridattasai18/RepoLogic.git
cd RepoLogic
```

### 2. Create Virtual Environment

```bash
python -m venv venv
# Linux / macOS:
source venv/bin/activate
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### 5. Run Application

```bash
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## Project Structure

```
RepoLogic/
├── app.py                     # Main Flask application & API routes
├── config.py                  # Global settings, paths & embedding configuration
├── requirements.txt           # Python dependencies
├── static/
│   ├── index.html             # Option A conversation-first UI structure
│   ├── index.css              # Technical dark design system (IBM Plex)
│   └── index.js               # Client orchestration, spaces & inline citations
├── tools/
│   ├── github_loader.py       # Repository cloning & git utilities
│   ├── repo_ingestor.py       # File structure traversal & filtering
│   ├── chunker.py             # Language-aware chunking with line preservation
│   ├── embedder.py            # FAISS vector store & resilient batch embedding
│   └── github_api.py          # GitHub API integration
├── tests/
│   └── test_startup_health.py # Startup key probe unit tests
└── .env.example               # Environment template
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves the web interface |
| `/ingest` | POST | Clones and indexes repository file list |
| `/chunk` | POST | Chunks source code with line tracking |
| `/embed` | POST | Generates embeddings and builds the FAISS index |
| `/status` | GET | Checks ingestion and embedding progress state |
| `/file-content`| GET | Retrieves raw file content for code evidence |
| `/ask` | POST | Answers natural language questions with source citations |
| `/explain` | POST | Explains selected code ranges in context |

---

## License

MIT License — see [LICENSE](LICENSE) for details.

Built by **Kaligotla Sri Datta Sai Vithal**
