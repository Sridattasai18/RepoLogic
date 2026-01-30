# RepoLogic - Project Documentation

## 1. Project Requirements Document (PRD)

### 1.1 Project Overview
**RepoLogic** is an AI-powered repository analyzer that provides deep, value-driven insights into codebases. Unlike generic chat-based coding assistants, RepoLogic offers a structured, selection-based exploration experience. It allows users to navigate a file tree, select specific blocks of code, and receive instant, context-aware explanations grounded in the repository's logic.

### 1.2 User Problem
Developers often struggle to understand complex, unfamiliar codebases.
- **Problem**: Reading code without context is difficult; tracing logic across multiple files is time-consuming.
- **Current Solutions**: Generic chatbots hallucinate or lack deep file context; clicking through files manually is slow.
- **RepoLogic Solution**: A "Select & Explain" interface that combines an IDE-like explorer with deep RAG-powered retrieval to explain *exactly* what a specific piece of code does within the broader project context.

### 1.3 Key Features
1.  **Repository Ingestion**: One-click cloning and analysis of public GitHub repositories.
2.  **Interactive File Explorer**: A familiar, IDE-style file tree for navigation.
3.  **Code Viewer**: Syntax-highlighted code display with line number tracking.
4.  **Selection-Based Explanation**: Users highlight specific lines of code to trigger a targeted AI explanation.
5.  **Context-Aware RAG**: The system retrieves relevant code chunks from across the repository to ground its answers, ensuring accuracy and preventing hallucinations.
6.  **Natural Language Q&A**: A chat interface to ask high-level questions about the repository (e.g., "How does authentication work?").

### 1.4 Target Audience
- Developers onboarding to new projects.
- Open-source contributors trying to understand a repo's architecture.
- Code reviewers needing quick context on specific functions.

---

## 2. Design Requirements Document (DRD)

### 2.1 Design Philosophy
**"Functional Beauty"**: The UI aims to be as usable as an IDE but as polished as a consumer app (inspired by Spotify). It prioritizes dark mode, high contrast, and smooth interactions.

### 2.2 UI Layout
The interface follows a strict **Three-Panel Layout**:
1.  **Left Panel (Navigation)**:
    - File tree structure.
    - Search bar to filter files.
    - Glassmorphic background (updated design).
2.  **Center Panel (Code)**:
    - Main reading area.
    - Syntax highlighting (JetBrains Mono font).
    - Mouse-driven text selection for interaction.
    - Action bar with "Explain Selection" button.
3.  **Right Panel (Insights)**:
    - AI Explanation output area.
    - Markdown rendering for rich text responses.
    - Q&A input field for general repository questions.

### 2.3 Visual Design System
- **Theme**: Dark Mode (Primary BG: `#121212`, Surface: `#181818`).
- **Typography**:
    - **UI**: *Manrope* (Sans-serif, clean, modern).
    - **Code**: *JetBrains Mono* (Monospace, legible).
- **Color Palette**:
    - **Primary Accent**: `#1ED760` (Spotify Green) - Used for primary actions and active states.
    - **Gradients**: Linear gradients of Green to Teal for brand identity.
    - **Text**: White `#FFFFFF` (Primary), Grey `#B3B3B3` (Secondary).
- **Interactions**:
    - Hover effects with glow/shadows.
    - Smooth transitions (0.2s ease).
    - Micro-animations for loading states and empty states.
    - **Glassmorphism**: Backdrop blur on headers and floating elements for depth.

---

## 3. Tech Stack Requirements Document (TRD)

### 3.1 Backend
- **Language**: Python 3.8+
- **Framework**: Flask (Lightweight, robust web server).
- **AI Engine**:
    - **LLM**: Google Gemini 1.5 Flash (via `langchain-google-genai`).
        - *Reasoning*: Large context window (1M tokens), fast inference, cost-effective.
    - **Framework**: LangChain (for orchestration and prompt management).
- **Vector Search (RAG)**:
    - **Database**: FAISS (Facebook AI Similarity Search) - Local, ultra-fast vector store.
    - **Embeddings**: Google `text-embedding-004`.
- **Repository Handling**:
    - `GitPython`: For cloning and file operations.
    - Custom recursive file loader for handling directory structures.

### 3.2 Frontend
- **Core**: Vanilla HTML5, CSS3, JavaScript (ES6+).
    - *Constraint*: No build steps (React/Vue) required; keeps deployment simple and fast.
- **Dependencies**:
    - `Highlight.js`: For code syntax highlighting.
    - `Marked.js`: For rendering Markdown responses from the AI.
    - Google Fonts API: Manrope & JetBrains Mono.

### 3.3 Data Flow Architecture
1.  **Ingestion**:
    - User inputs URL -> Server clones Repo -> Loader crawls files -> Text Splitter chunks code -> Embeddings generated -> Stored in FAISS.
2.  **Retrieval (Selection)**:
    - User Selects Text -> Server receives file path & line numbers -> Retrieves specific code block -> Searches FAISS for related chunks (dependencies, usages) -> Sends Context + Code to Gemini -> Returns Explanation.
3.  **Retrieval (Q&A)**:
    - User asks question -> Server converts query to vector -> Semantic Search in FAISS -> Top k relevant chunks retrieved -> LLM synthesizes answer.

### 3.4 Deployment Requirements
- **Environment Variables**:
    - `GOOGLE_API_KEY`: Required for Gemini and Embeddings.
- **Runtime**:
    - Python environment with `requirements.txt` installed.
    - Write access to local disk (for cloning repos into `./temp` or similar directory).
