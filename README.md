# RepoLogic — AI-Powered Codebase Analysis

**Understand any GitHub repository in minutes.**

RepoLogic is an AI-powered codebase analysis tool for faster developer onboarding. It transforms GitHub repositories into interactive knowledge bases with grounded explanations, inline code citations, and intelligent navigation.

![Status](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Key Features

### **Full Repository Context**
RepoLogic analyzes the repository structure, files, dependencies, and code relationships to build a complete understanding of the project.

### **Grounded Analysis**
RAG-based analysis keeps explanations connected to the actual code instead of relying only on general model knowledge. Every answer includes:
- **Confidence badges** (`grounded`, `partial`, `insufficient_context`)
- **Inline citations** with clickable source chips
- **Syntax-highlighted code blocks** with line numbers

### **Instant Code Insight**
- Click any file to view it in the chat
- Select code and get contextual explanations
- Navigate through the file tree with visual feedback
- Multi-workspace support for managing multiple repositories

### **Developer-First UX**
- **Auto-opening file explorer** when repository is ready
- **Smart loading states** with large, centered progress indicators
- **Interactive tooltips** for first-time guidance
- **Confirmation dialogs** to prevent accidental actions
- **Clean, professional design** optimized for developers

---

## 🎯 How It Works

```
01. CONNECT                02. ANALYZE                   03. UNDERSTAND
Paste a public      →      RepoLogic indexes the   →    Explore files and get
GitHub repository          repository and builds         AI explanations grounded
                           searchable context            in the code
```

### Pipeline Architecture

```
GitHub Repository
   │
   ▼
[ 1. Ingest ] ──► Git clone + file traversal + metadata extraction
   │
   ▼
[ 2. Chunk  ] ──► Language-aware code splitting with line tracking
   │
   ▼
[ 3. Embed  ] ──► Vector embeddings (Gemini) + FAISS indexing
   │
   ▼
[ 4. Query  ] ──► Semantic search + LLM analysis with citations
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Git
- Google Gemini API key ([Get one here](https://aistudio.google.com/app/apikey))

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/Sridattasai18/RepoLogic.git
cd RepoLogic
```

2. **Create virtual environment**
```bash
python -m venv venv

# Linux/macOS:
source venv/bin/activate

# Windows:
.\venv\Scripts\Activate.ps1
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure API key**
```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

5. **Run the application**
```bash
python app.py
```

6. **Open in browser**
```
http://127.0.0.1:5000
```

---

## 💡 Usage

1. **Create a Space**: Click "Try with a GitHub Repo"
2. **Enter Repository URL**: e.g., `https://github.com/facebook/react`
3. **Wait for Analysis**: Watch the progress indicator
4. **Explore**: File explorer opens automatically
5. **Ask Questions**: Use natural language queries
6. **View Code**: Click files or citations to see code

---

## 🏗️ Project Structure

```
RepoLogic/
├── app.py                     # Flask app & API routes
├── config.py                  # Configuration & settings
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
├── static/
│   ├── index.html            # Landing page & app UI
│   ├── index.css             # Design system (dark theme, IBM Plex)
│   └── index.js              # Frontend logic & interactions
├── tools/
│   ├── github_loader.py      # Repository cloning
│   ├── repo_ingestor.py      # File structure analysis
│   ├── chunker.py            # Code splitting with line numbers
│   ├── embedder.py           # FAISS vector store & embeddings
│   └── github_api.py         # GitHub API integration
└── tests/
    ├── test_startup_health.py # Health check tests
    └── test_path_traversal.py # Security tests
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves web interface |
| `/health` | GET | Health check & API key validation |
| `/ingest` | POST | Clone repository & extract file list |
| `/chunk` | POST | Split code into searchable chunks |
| `/embed` | POST | Generate vector embeddings |
| `/status` | GET | Check analysis progress |
| `/file-content` | GET | Retrieve file content |
| `/ask` | POST | Answer questions with citations |
| `/explain` | POST | Explain selected code |

---

## 🛠️ Tech Stack

**Backend**
- Python 3.8+, Flask
- Google Gemini API (embeddings + generation)
- LangChain, FAISS
- Tenacity (retry handling)

**Frontend**
- Vanilla JavaScript (ES6+)
- HTML5, CSS3
- IBM Plex Sans & Mono fonts
- Highlight.js, Marked.js, DOMPurify

**Infrastructure**
- Git integration
- Vector similarity search
- RAG (Retrieval-Augmented Generation)

---

## 🎨 Design Philosophy

RepoLogic follows a **developer-tool aesthetic**:
- Dark, restrained color scheme
- Green accent (#1ed760) for emphasis
- IBM Plex typeface for technical clarity
- Minimal animations, maximum information density
- No gradients, glowing effects, or unnecessary decoration

The interface prioritizes **immediate understanding**:
- Large, readable text for loading states
- Clear visual hierarchy
- Inline code evidence
- Contextual tooltips

---

## 🔒 Security

- API keys stored in `.env` (never committed)
- Path traversal prevention
- Input validation on all endpoints
- Secure file operations
- Rate limiting on embeddings

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 👤 Author

**Kaligotla Sri Datta Sai Vithal**

Built with ❤️ for developers who want to understand codebases faster.

---

## 🙏 Acknowledgments

- Google Gemini for powerful embeddings and generation
- Facebook FAISS for efficient vector search
- IBM Plex for beautiful developer fonts
- The open-source community
