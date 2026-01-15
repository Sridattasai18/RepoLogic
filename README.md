# 🚀 RepoLogic - AI-Powered Repository Analyzer

RepoLogic is a selection-based repository analyzer that helps developers understand code through AI-powered explanations. Select any code in a repository, and get instant, contextual explanations.

![RepoLogic Preview](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

- 🎯 **Selection-Based Explanations**: Highlight code → Click "Explain" → Get understanding
- 💬 **Natural Language Q&A**: Ask questions about the repository without selecting code
- 📁 **File Tree Navigation**: Browse repository structure like an IDE
- 🧠 **RAG-Powered**: Uses embeddings and vector search for accurate context
- 🎨 **Spotify-Inspired UI**: Beautiful dark theme with Manrope typography
- ⚡ **Fast Retrieval**: FAISS vector database for instant semantic search
- 🔍 **Line-Number Tracking**: Precise code location awareness

## 🎬 How It Works

### Selection-Based Explanations
1. **Analyze**: Enter any public GitHub repository URL
2. **Navigate**: Browse the file tree and click to view code
3. **Select**: Highlight any code section with your mouse
4. **Explain**: Click "Explain Selection" for AI-powered explanation
5. **Learn**: Get context-aware explanations grounded in the actual code

### Natural Language Q&A
1. **Analyze**: Enter any public GitHub repository URL
2. **Ask**: Type questions like "How does authentication work?" or "Which files handle routing?"
3. **Get Answers**: Receive context-grounded responses with file references

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
│   ├── index.css       # Spotify-inspired styling
│   └── index.js        # Frontend logic
├── tools/
│   ├── github_loader.py    # GitHub repository handling
│   ├── repo_ingestor.py    # Repository ingestion
│   ├── chunker.py          # Code chunking with line numbers
│   ├── embedder.py         # FAISS embeddings
│   └── vector_store.py     # Vector database operations
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

- **Three-Panel Layout**: Files → Code → Explanation
- **IDE-Like Experience**: Navigate and explore code naturally
- **Natural Language Q&A**: Ask questions about the repo in plain English
- **Syntax Highlighting**: Language-aware code display
- **Selection Tracking**: See exactly what lines you've selected
- **Markdown Rendering**: Rich formatted explanations

## 🔐 Security

- API keys are never exposed to the client
- Environment variables for sensitive data
- `.gitignore` protects local files

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
