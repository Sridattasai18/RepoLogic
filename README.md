# 🚀 RepoLogic - AI-Powered Repository Analyzer

**The IDE that explains itself.** RepoLogic turns any GitHub repository into an interactive knowledge base with AI-powered explanations, multi-project workspace management, and natural language Q&A.

![RepoLogic Preview](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

- 🎯 **Selection-Based Explanations**: Highlight code → Click "Explain" → Get understanding
- 💬 **Natural Language Q&A**: Ask questions about the repository without selecting code
- 🗂️ **Multi-Project Spaces**: Manage multiple repositories with persistent sessions
- 📁 **File Tree Navigation**: Browse repository structure like an IDE
- 🧠 **RAG-Powered**: Uses embeddings and vector search for accurate context
- 🎨 **Premium UI**: Beautiful dark theme with smooth animations and modern design
- ⚡ **Fast Retrieval**: FAISS vector database for instant semantic search
- 🔍 **Line-Number Tracking**: Precise code location awareness
- 💾 **Session Persistence**: Your analyzed repos are saved locally
- ⌨️ **Keyboard Shortcuts**: Ctrl+E to explain selected code

## 🎬 How It Works

### Multi-Space Workflow
1. **Landing Page**: Visit RepoLogic and click "Analyze a Repository"
2. **Create Space**: Enter a GitHub URL → Space is created automatically
3. **Analysis**: Repository is cloned, chunked, and embedded
4. **Explore**: Browse files, select code, and get AI explanations
5. **Switch**: Easily switch between multiple project spaces

### Selection-Based Explanations
1. **Navigate**: Browse the file tree and click to view code
2. **Select**: Highlight any code section with your mouse
3. **Explain**: Click "Explain Selection" or press Ctrl+E
4. **Learn**: Get context-aware explanations with source references

### Natural Language Q&A
1. **Ask**: Type questions like "How does authentication work?"
2. **Get Answers**: Receive context-grounded responses with file references
3. **Explore**: Click on source files to dive deeper

## 🛠️ Tech Stack

- **Backend**: Python, Flask
- **AI/ML**: Google Gemini API, LangChain
- **Vector DB**: FAISS
- **Embeddings**: Google text-embedding-004
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Markdown**: marked.js, highlight.js

## 📋 Prerequisites

- Python 3.8 or higher
- Google Gemini API key ([Get it here](https://aistudio.google.com/app/apikey))
- Git

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/Sridattasai18/RepoLogic.git
cd RepoLogic
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
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

### 5. Run the Application

```bash
python app.py
```

Open http://127.0.0.1:5000 in your browser.

## 📁 Project Structure

```
RepoLogic/
├── app.py              # Main Flask application
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── static/
│   ├── index.html      # Frontend UI
│   ├── index.css       # Premium dark theme styling
│   └── index.js        # Frontend logic + SpaceManager
├── tools/
│   ├── github_loader.py    # GitHub repository handling
│   ├── repo_ingestor.py    # Repository ingestion
│   ├── chunker.py          # Code chunking with line numbers
│   ├── embedder.py         # FAISS embeddings
│   └── github_api.py       # GitHub API integration
├── data/               # Cached repos, chunks, embeddings
└── .env.example        # Environment template
```

## 🔧 Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | Google Gemini API key | Yes |

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve frontend |
| `/ingest` | POST | Ingest repository |
| `/chunk` | POST | Chunk repository files |
| `/embed` | POST | Generate embeddings |
| `/file-content` | GET | Get file content |
| `/explain` | POST | Explain selected code |
| `/ask` | POST | Answer natural language questions |

## 🎨 UI Features

- **Landing Page**: Professional intro with workflow showcase
- **Multi-Space Sidebar**: Switch between projects instantly
- **Three-Panel Layout**: Files → Code → Explanation
- **IDE-Like Experience**: Navigate and explore code naturally
- **Natural Language Q&A**: Ask questions in plain English
- **Syntax Highlighting**: Language-aware code display
- **Selection Tracking**: See exactly what lines you've selected
- **Markdown Rendering**: Rich formatted explanations
- **Source References**: Click to jump to referenced files
- **Response Metadata**: See response time and chunks used

## ⌨️ Keyboard Shortcuts

- `Ctrl+E` / `Cmd+E` - Explain selected code
- `Escape` - Close modals

## 🔐 Security

- API keys are never exposed to the client
- Environment variables for sensitive data
- `.gitignore` protects local files and data
- No backend modifications to RAG pipeline

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

Built with ❤️ by **Kaligotla Sri Datta Sai Vithal**

Powered by Google Gemini, LangChain, and FAISS
