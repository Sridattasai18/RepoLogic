/**
 * Ecode - Selection-Based Repository Analyzer
 * PHASE 4: IDE-Inspired UI with code selection
 */

// ══════════════════════════════════════════════════════════════
// State
// ══════════════════════════════════════════════════════════════

const state = {
    repoUrl: null,
    repoId: null,
    currentFile: null,
    currentFileContent: null,
    selection: {
        startLine: null,
        endLine: null,
        text: null
    },
    files: [],
    isLoading: false,
    qaEnabled: false  // NEW: Enable Q&A after embeddings are ready
};

// ══════════════════════════════════════════════════════════════
// DOM Elements
// ══════════════════════════════════════════════════════════════

const elements = {
    repoUrlInput: document.getElementById('repo-url-input'),
    analyzeBtn: document.getElementById('analyze-btn'),
    statusDot: document.getElementById('status-indicator'),
    statusText: document.getElementById('status-text'),
    fileTree: document.getElementById('file-tree'),
    fileCount: document.getElementById('file-count'),
    filesEmpty: document.getElementById('files-empty'),
    fileSearch: document.getElementById('file-search'),
    currentFileTitle: document.getElementById('current-file'),
    codeViewer: document.getElementById('code-viewer'),
    codeEmpty: document.getElementById('code-empty'),
    codeContent: document.getElementById('code-content'),
    lineNumbers: document.getElementById('line-numbers'),
    codeText: document.getElementById('code-text'),
    explainBtn: document.getElementById('explain-btn'),
    selectionInfo: document.getElementById('selection-info'),
    selectionRange: document.getElementById('selection-range'),
    explanationEmpty: document.getElementById('explanation-empty'),
    explanationResult: document.getElementById('explanation-result'),
    explanationLoading: document.getElementById('explanation-loading'),
    errorToast: document.getElementById('error-toast'),
    errorMessage: document.getElementById('error-message'),
    // NEW: Q&A elements
    qaInput: document.getElementById('qa-input'),
    qaBtn: document.getElementById('qa-btn')
};

// ══════════════════════════════════════════════════════════════
// Status & Error Handling
// ══════════════════════════════════════════════════════════════

function setStatus(status, text) {
    elements.statusDot.className = 'status-dot ' + status;
    elements.statusText.textContent = text;
}

function showError(message) {
    elements.errorMessage.textContent = message;
    elements.errorToast.classList.remove('hidden');
    setTimeout(() => hideError(), 5000);
}

function hideError() {
    elements.errorToast.classList.add('hidden');
}

// ══════════════════════════════════════════════════════════════
// API Functions
// ══════════════════════════════════════════════════════════════

async function apiCall(endpoint, data) {
    const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.error || 'API request failed');
    }

    return result;
}

// ══════════════════════════════════════════════════════════════
// File Tree
// ══════════════════════════════════════════════════════════════

function getFileIcon(fileName) {
    const ext = fileName.split('.').pop().toLowerCase();
    const iconMap = {
        'py': '🐍',
        'js': '📜',
        'ts': '📘',
        'jsx': '⚛️',
        'tsx': '⚛️',
        'html': '🌐',
        'css': '🎨',
        'json': '📋',
        'md': '📝',
        'yaml': '⚙️',
        'yml': '⚙️',
        'java': '☕',
        'go': '🔵',
        'rs': '🦀',
        'rb': '💎',
    };
    return iconMap[ext] || '📄';
}

function renderFileTree(files) {
    if (!files || files.length === 0) {
        elements.filesEmpty.classList.remove('hidden');
        elements.fileCount.textContent = '0';
        return;
    }

    elements.filesEmpty.classList.add('hidden');
    elements.fileCount.textContent = files.length;

    // Sort files: directories first, then alphabetically
    const sorted = [...files].sort((a, b) => {
        if (a.type === 'directory' && b.type !== 'directory') return -1;
        if (a.type !== 'directory' && b.type === 'directory') return 1;
        return a.path.localeCompare(b.path);
    });

    // Group by directory
    const tree = document.createDocumentFragment();

    sorted.forEach(file => {
        if (file.type !== 'code' && file.type !== 'documentation' && file.type !== 'configuration') {
            return; // Skip non-important files
        }

        const item = document.createElement('div');
        item.className = 'file-item';
        item.dataset.path = file.path;

        // Calculate indent based on path depth
        const depth = (file.path.match(/\//g) || []).length;
        const indent = document.createElement('span');
        indent.className = 'file-indent';
        indent.style.width = `${depth * 12}px`;

        const icon = document.createElement('span');
        icon.className = 'file-icon';
        icon.textContent = getFileIcon(file.name);

        const name = document.createElement('span');
        name.className = 'file-name';
        name.textContent = file.name;
        name.title = file.path;

        item.appendChild(indent);
        item.appendChild(icon);
        item.appendChild(name);

        item.addEventListener('click', () => loadFile(file.path));

        tree.appendChild(item);
    });

    elements.fileTree.innerHTML = '';
    elements.fileTree.appendChild(tree);
}

// File search filter
if (elements.fileSearch) {
    elements.fileSearch.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const items = elements.fileTree.querySelectorAll('.file-item');

        items.forEach(item => {
            const path = item.dataset.path.toLowerCase();
            item.style.display = path.includes(query) ? 'flex' : 'none';
        });
    });
}

// ══════════════════════════════════════════════════════════════
// Code Viewer
// ══════════════════════════════════════════════════════════════

async function loadFile(filePath) {
    if (state.isLoading) return;

    setStatus('loading', 'Loading file...');

    try {
        // Fetch file content from cloned repo via new endpoint
        const response = await fetch(`/file-content?repo_id=${state.repoId}&path=${encodeURIComponent(filePath)}`);

        if (!response.ok) {
            throw new Error('Failed to load file');
        }

        const data = await response.json();

        state.currentFile = filePath;
        state.currentFileContent = data.content;

        // Update UI
        elements.currentFileTitle.textContent = filePath;

        // Update file tree selection
        document.querySelectorAll('.file-item').forEach(item => {
            item.classList.toggle('active', item.dataset.path === filePath);
        });

        // Render code with line numbers
        renderCode(data.content, data.language);

        // Show code, hide empty state
        elements.codeEmpty.classList.add('hidden');
        elements.codeContent.classList.remove('hidden');

        setStatus('success', 'File loaded');

    } catch (error) {
        showError(error.message);
        setStatus('error', 'Load failed');
    }
}

function renderCode(content, language) {
    const lines = content.split('\n');

    // Render line numbers
    elements.lineNumbers.innerHTML = lines.map((_, i) =>
        `<span class="line-number">${i + 1}</span>`
    ).join('');

    // Render code with syntax highlighting
    elements.codeText.textContent = content;
    elements.codeText.className = `code-text language-${language || 'plaintext'}`;

    // Apply highlighting
    hljs.highlightElement(elements.codeText);

    // Reset selection
    clearSelection();
}

// ══════════════════════════════════════════════════════════════
// Text Selection Handling
// ══════════════════════════════════════════════════════════════

function clearSelection() {
    state.selection = { startLine: null, endLine: null, text: null };
    elements.selectionInfo.classList.add('hidden');
    elements.explainBtn.disabled = true;
}

function getLineFromPosition(content, position) {
    const textBefore = content.substring(0, position);
    return (textBefore.match(/\n/g) || []).length + 1;
}

elements.codeText.addEventListener('mouseup', () => {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();

    if (!selectedText || !state.currentFileContent) {
        clearSelection();
        return;
    }

    // Find start and end positions in content
    const range = selection.getRangeAt(0);
    const preSelectionRange = range.cloneRange();
    preSelectionRange.selectNodeContents(elements.codeText);
    preSelectionRange.setEnd(range.startContainer, range.startOffset);

    const startOffset = preSelectionRange.toString().length;
    const endOffset = startOffset + selectedText.length;

    // Calculate line numbers
    const startLine = getLineFromPosition(state.currentFileContent, startOffset);
    const endLine = getLineFromPosition(state.currentFileContent, endOffset);

    state.selection = {
        startLine,
        endLine,
        text: selectedText
    };

    // Update UI
    elements.selectionRange.textContent = startLine === endLine
        ? `Line ${startLine}`
        : `Lines ${startLine}-${endLine}`;
    elements.selectionInfo.classList.remove('hidden');
    elements.explainBtn.disabled = false;
});

// ══════════════════════════════════════════════════════════════
// Explanation
// ══════════════════════════════════════════════════════════════

async function explainSelection() {
    if (!state.selection.text || !state.currentFile) {
        showError('Please select code to explain');
        return;
    }

    // Show loading state
    elements.explanationEmpty.classList.add('hidden');
    elements.explanationResult.classList.add('hidden');
    elements.explanationLoading.classList.remove('hidden');
    elements.explainBtn.disabled = true;
    setStatus('loading', 'Analyzing...');

    try {
        // Call the explain endpoint
        const result = await apiCall('/explain', {
            repo_url: state.repoUrl,
            file_path: state.currentFile,
            start_line: state.selection.startLine,
            end_line: state.selection.endLine,
            selected_code: state.selection.text
        });

        // Render explanation
        elements.explanationLoading.classList.add('hidden');
        elements.explanationResult.classList.remove('hidden');
        elements.explanationResult.innerHTML = marked.parse(result.explanation);

        // Highlight code blocks in explanation
        elements.explanationResult.querySelectorAll('pre code').forEach(block => {
            hljs.highlightElement(block);
        });

        setStatus('success', 'Done');

    } catch (error) {
        elements.explanationLoading.classList.add('hidden');
        elements.explanationEmpty.classList.remove('hidden');
        showError(error.message);
        setStatus('error', 'Failed');
    } finally {
        elements.explainBtn.disabled = false;
    }
}

elements.explainBtn.addEventListener('click', explainSelection);

// ══════════════════════════════════════════════════════════════
// Natural Language Q&A (NEW FEATURE)
// ══════════════════════════════════════════════════════════════

async function askQuestion() {
    const question = elements.qaInput.value.trim();

    if (!question) {
        showError('Please enter a question');
        return;
    }

    if (!state.repoUrl || !state.qaEnabled) {
        showError('Please analyze a repository first');
        return;
    }

    // Show loading state
    elements.explanationEmpty.classList.add('hidden');
    elements.explanationResult.classList.add('hidden');
    elements.explanationLoading.classList.remove('hidden');
    elements.qaBtn.disabled = true;
    elements.qaInput.disabled = true;
    setStatus('loading', 'Thinking...');

    try {
        // Call the /ask endpoint
        const result = await apiCall('/ask', {
            repo_url: state.repoUrl,
            question: question
        });

        // Render answer
        elements.explanationLoading.classList.add('hidden');
        elements.explanationResult.classList.remove('hidden');
        elements.explanationResult.innerHTML = marked.parse(result.answer);

        // Highlight code blocks in answer
        elements.explanationResult.querySelectorAll('pre code').forEach(block => {
            hljs.highlightElement(block);
        });

        // Clear input
        elements.qaInput.value = '';

        setStatus('success', 'Done');

    } catch (error) {
        elements.explanationLoading.classList.add('hidden');
        elements.explanationEmpty.classList.remove('hidden');
        showError(error.message);
        setStatus('error', 'Failed');
    } finally {
        elements.qaBtn.disabled = false;
        elements.qaInput.disabled = false;
    }
}

// Event listeners for Q&A
if (elements.qaBtn) {
    elements.qaBtn.addEventListener('click', askQuestion);
}

if (elements.qaInput) {
    elements.qaInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !elements.qaBtn.disabled) {
            askQuestion();
        }
    });
}

// ══════════════════════════════════════════════════════════════
// Repository Analysis
// ══════════════════════════════════════════════════════════════

async function analyzeRepository() {
    const url = elements.repoUrlInput.value.trim();

    if (!url) {
        showError('Please enter a GitHub repository URL');
        return;
    }

    if (!url.includes('github.com')) {
        showError('Please enter a valid GitHub URL');
        return;
    }

    state.isLoading = true;
    elements.analyzeBtn.disabled = true;
    setStatus('loading', 'Ingesting...');

    try {
        // Step 1: Ingest repository
        setStatus('loading', 'Cloning repository...');
        const ingestResult = await apiCall('/ingest', { repo_url: url });

        state.repoUrl = url;
        state.repoId = ingestResult.repo_id;
        state.files = ingestResult.files;

        // Step 2: Chunk the repository
        setStatus('loading', 'Analyzing code structure...');
        await apiCall('/chunk', { repo_url: url });

        // Step 3: Create embeddings
        setStatus('loading', 'Generating embeddings...');
        await apiCall('/embed', { repo_url: url });

        // Render file tree
        renderFileTree(state.files);

        // NEW: Enable Q&A after successful embedding
        state.qaEnabled = true;
        elements.qaInput.disabled = false;
        elements.qaBtn.disabled = false;

        setStatus('success', `${ingestResult.stats.total_files} files indexed`);

    } catch (error) {
        showError(error.message);
        setStatus('error', 'Analysis failed');
    } finally {
        state.isLoading = false;
        elements.analyzeBtn.disabled = false;
    }
}

elements.analyzeBtn.addEventListener('click', analyzeRepository);

elements.repoUrlInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') analyzeRepository();
});

// ══════════════════════════════════════════════════════════════
// Initialization
// ══════════════════════════════════════════════════════════════

console.log('◈ RepoLogic initialized - Selection-based repository analyzer');
