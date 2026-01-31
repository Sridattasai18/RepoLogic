/**
 * RepoLogic - Selection-Based Repository Analyzer
 * Multi-Space Architecture with IDE-Inspired UI
 */

// ══════════════════════════════════════════════════════════════
// Space Manager (localStorage persistence)
// ══════════════════════════════════════════════════════════════

class SpaceManager {
    constructor() {
        this.storageKey = 'repoLogicSpaces';
        this.spaces = this.load();
    }

    load() {
        try {
            const data = localStorage.getItem(this.storageKey);
            return data ? JSON.parse(data) : { spaces: [], activeSpaceId: null };
        } catch (e) {
            console.error('Failed to load spaces:', e);
            return { spaces: [], activeSpaceId: null };
        }
    }

    save() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.spaces));
        } catch (e) {
            console.error('Failed to save spaces:', e);
        }
    }

    generateId() {
        return 'space_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    extractRepoName(url) {
        // Extract owner/repo from GitHub URL
        const match = url.match(/github\.com[\/:]([^\/]+)\/([^\/\.]+)/i);
        if (match) {
            return `${match[1]}/${match[2]}`;
        }
        return url;
    }

    create(repoUrl) {
        const id = this.generateId();
        const name = this.extractRepoName(repoUrl);
        const now = new Date().toISOString();

        const newSpace = {
            id,
            name,
            repoUrl,
            createdAt: now,
            lastAccessedAt: now,
            analyzed: false
        };

        this.spaces.spaces.push(newSpace);
        this.spaces.activeSpaceId = id;
        this.save();
        return newSpace;
    }

    getAll() {
        return this.spaces.spaces.sort((a, b) =>
            new Date(b.lastAccessedAt) - new Date(a.lastAccessedAt)
        );
    }

    getActive() {
        if (!this.spaces.activeSpaceId) return null;
        return this.spaces.spaces.find(s => s.id === this.spaces.activeSpaceId) || null;
    }

    setActive(spaceId) {
        const space = this.spaces.spaces.find(s => s.id === spaceId);
        if (space) {
            space.lastAccessedAt = new Date().toISOString();
            this.spaces.activeSpaceId = spaceId;
            this.save();
            return space;
        }
        return null;
    }

    markAnalyzed(spaceId) {
        const space = this.spaces.spaces.find(s => s.id === spaceId);
        if (space) {
            space.analyzed = true;
            space.lastAccessedAt = new Date().toISOString();
            this.save();
        }
    }

    delete(spaceId) {
        this.spaces.spaces = this.spaces.spaces.filter(s => s.id !== spaceId);
        if (this.spaces.activeSpaceId === spaceId) {
            this.spaces.activeSpaceId = this.spaces.spaces[0]?.id || null;
        }
        this.save();
    }

    hasSpaces() {
        return this.spaces.spaces.length > 0;
    }

    findByRepoUrl(url) {
        const normalized = url.toLowerCase().replace(/\.git$/, '').replace(/\/$/, '');
        return this.spaces.spaces.find(s =>
            s.repoUrl.toLowerCase().replace(/\.git$/, '').replace(/\/$/, '') === normalized
        );
    }
}

// Initialize space manager
const spaceManager = new SpaceManager();

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
    qaEnabled: false,
    lastExplanation: null,
    activeSpace: null,
    currentView: 'landing' // 'landing' | 'create' | 'app'
};

// ══════════════════════════════════════════════════════════════
// DOM Elements
// ══════════════════════════════════════════════════════════════

const elements = {
    landing: document.getElementById('landing'),
    mainApp: document.getElementById('main-app'),
    launchAppBtn: document.getElementById('launch-app-btn'),
    homeBtn: document.getElementById('home-btn'),
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
    copyBtn: document.getElementById('copy-btn'),
    selectionInfo: document.getElementById('selection-info'),
    selectionRange: document.getElementById('selection-range'),
    explanationEmpty: document.getElementById('explanation-empty'),
    explanationResult: document.getElementById('explanation-result'),
    explanationLoading: document.getElementById('explanation-loading'),
    errorToast: document.getElementById('error-toast'),
    errorMessage: document.getElementById('error-message'),
    qaInput: document.getElementById('qa-input'),
    qaBtn: document.getElementById('qa-btn'),
    // Space Management Elements
    spaceModalOverlay: document.getElementById('space-modal-overlay'),
    spaceModal: document.getElementById('space-modal'),
    spaceRepoUrl: document.getElementById('space-repo-url'),
    spaceNamePreview: document.getElementById('space-name-preview'),
    spacePreview: document.getElementById('space-preview'),
    createSpaceBtn: document.getElementById('create-space-btn'),
    modalCloseBtn: document.getElementById('modal-close-btn'),
    modalCancelBtn: document.getElementById('modal-cancel-btn'),
    addSpaceBtn: document.getElementById('add-space-btn'),
    spacesList: document.getElementById('spaces-list')
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

    // Enable copy button
    if (elements.copyBtn) {
        elements.copyBtn.disabled = false;
    }
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

        // Render explanation with metadata
        elements.explanationLoading.classList.add('hidden');
        elements.explanationResult.classList.remove('hidden');

        // Build response HTML with metadata header
        const metadataHtml = buildResponseMetadata(result.response_time_ms, result.context_chunks_used);
        const sourcesHtml = buildSourcesSection(result.sources || []);
        const copyButtonHtml = `<button class="btn-copy-explanation" onclick="copyExplanation()">📋 Copy Explanation</button>`;

        elements.explanationResult.innerHTML =
            metadataHtml +
            copyButtonHtml +
            '<div class="explanation-text">' + marked.parse(result.explanation) + '</div>' +
            sourcesHtml;

        // Store last explanation for copy
        state.lastExplanation = result.explanation;

        // Highlight code blocks in explanation
        elements.explanationResult.querySelectorAll('pre code').forEach(block => {
            hljs.highlightElement(block);
        });

        setStatus('success', `Done in ${(result.response_time_ms / 1000).toFixed(1)}s`);

    } catch (error) {
        elements.explanationLoading.classList.add('hidden');
        elements.explanationEmpty.classList.remove('hidden');
        showError(error.message);
        setStatus('error', 'Failed');
    } finally {
        elements.explainBtn.disabled = false;
    }
}

// Helper: Build response metadata header
function buildResponseMetadata(timeMs, chunksUsed) {
    return `
        <div class="response-metadata">
            <span class="meta-item">⚡ ${(timeMs / 1000).toFixed(1)}s</span>
            <span class="meta-item">📦 ${chunksUsed} chunks</span>
        </div>
    `;
}

// Helper: Build sources section
function buildSourcesSection(sources) {
    if (!sources || sources.length === 0) return '';

    const sourceItems = sources.map(s => {
        const icon = s.type === 'selected' ? '📍' : '🔗';
        const label = s.type === 'selected' ? 'Selected' : 'Related';
        return `<div class="source-item"><span class="source-icon">${icon}</span><span class="source-file">${s.file}</span><span class="source-lines">L${s.lines}</span><span class="source-type">${label}</span></div>`;
    }).join('');

    return `
        <div class="sources-section">
            <div class="sources-header">📚 Sources Used</div>
            <div class="sources-list">${sourceItems}</div>
        </div>
    `;
}

// Copy explanation to clipboard
async function copyExplanation() {
    if (!state.lastExplanation) return;

    try {
        await navigator.clipboard.writeText(state.lastExplanation);
        showCopyFeedback();
    } catch (err) {
        showError('Failed to copy explanation');
    }
}

function showCopyFeedback() {
    const btn = document.querySelector('.btn-copy-explanation');
    if (btn) {
        const original = btn.innerHTML;
        btn.innerHTML = '✓ Copied!';
        btn.classList.add('copied');
        setTimeout(() => {
            btn.innerHTML = original;
            btn.classList.remove('copied');
        }, 2000);
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

        // Render answer with metadata
        elements.explanationLoading.classList.add('hidden');
        elements.explanationResult.classList.remove('hidden');

        // Build response HTML with metadata header
        const metadataHtml = buildResponseMetadata(result.response_time_ms, result.chunks_used);
        const sourcesHtml = buildQASourcesSection(result.sources || []);
        const copyButtonHtml = `<button class="btn-copy-explanation" onclick="copyExplanation()">📋 Copy Answer</button>`;

        elements.explanationResult.innerHTML =
            metadataHtml +
            copyButtonHtml +
            '<div class="explanation-text">' + marked.parse(result.answer) + '</div>' +
            sourcesHtml;

        // Store last answer for copy
        state.lastExplanation = result.answer;

        // Highlight code blocks in answer
        elements.explanationResult.querySelectorAll('pre code').forEach(block => {
            hljs.highlightElement(block);
        });

        // Clear input
        elements.qaInput.value = '';

        setStatus('success', `Done in ${(result.response_time_ms / 1000).toFixed(1)}s`);

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

// Helper: Build Q&A sources section (with relevance scores)
function buildQASourcesSection(sources) {
    if (!sources || sources.length === 0) return '';

    const sourceItems = sources.map(s => {
        const relevance = s.relevance_score ? `${Math.round(s.relevance_score * 100)}%` : '';
        return `<div class="source-item"><span class="source-icon">📄</span><span class="source-file">${s.file}</span><span class="source-lines">L${s.lines}</span>${relevance ? `<span class="source-relevance">${relevance}</span>` : ''}</div>`;
    }).join('');

    return `
        <div class="sources-section">
            <div class="sources-header">📚 Sources Used</div>
            <div class="sources-list">${sourceItems}</div>
        </div>
    `;
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
// Copy Functionality
// ══════════════════════════════════════════════════════════════

if (elements.copyBtn) {
    elements.copyBtn.addEventListener('click', async () => {
        if (!state.currentFileContent) return;

        try {
            await navigator.clipboard.writeText(state.currentFileContent);

            // Visual feedback
            const originalIcon = elements.copyBtn.innerHTML;
            elements.copyBtn.innerHTML = '<span class="btn-icon">✓</span>';
            elements.copyBtn.classList.add('success');

            setTimeout(() => {
                elements.copyBtn.innerHTML = originalIcon;
                elements.copyBtn.classList.remove('success');
            }, 2000);

        } catch (err) {
            showError('Failed to copy to clipboard');
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

        // Mark space as analyzed
        if (state.activeSpace) {
            spaceManager.markAnalyzed(state.activeSpace.id);
        }

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
// Landing Page Toggle
// ══════════════════════════════════════════════════════════════

function showLanding() {
    elements.landing.classList.add('active');
    elements.mainApp.classList.add('hidden');
    elements.mainApp.classList.remove('active');
}

function launchApp(addHistory = true) {
    elements.landing.classList.remove('active');
    elements.mainApp.classList.remove('hidden');
    elements.mainApp.classList.add('active'); // ensure flex display

    // Add to history stack
    if (addHistory) {
        history.pushState({ view: 'app' }, '', '#app');
    }
    localStorage.setItem('repoLogicSeenLanding', 'true'); // Keep this for initial load logic
}

// Handle Browser Back Button
window.addEventListener('popstate', (event) => {
    if (event.state && event.state.view === 'app') {
        launchApp(false);
    } else {
        showLanding();
    }
});

if (elements.homeBtn) {
    elements.homeBtn.addEventListener('click', () => {
        // Go back in history if possible, otherwise force landing
        if (history.state && history.state.view === 'app') {
            history.back();
        } else {
            showLanding();
            history.replaceState(null, '', ' ');
        }
    });
}

// ══════════════════════════════════════════════════════════════
// Initialization
// ══════════════════════════════════════════════════════════════

// Check if user has seen landing page before
// Check initial load with space support
const hasSeenLanding = localStorage.getItem('repoLogicSeenLanding');

// Initialize based on existing spaces
if (spaceManager.hasSpaces()) {
    // User has spaces, show app with last active space
    const activeSpace = spaceManager.getActive();
    if (activeSpace) {
        state.activeSpace = activeSpace;
        state.repoUrl = activeSpace.repoUrl;
        elements.repoUrlInput.value = activeSpace.repoUrl;
    }
    launchApp(false);
    renderSpacesList();
} else if (window.location.hash === '#app' || hasSeenLanding) {
    launchApp(false);
} else {
    showLanding();
}

// ══════════════════════════════════════════════════════════════
// Keyboard Shortcuts
// ══════════════════════════════════════════════════════════════

document.addEventListener('keydown', (e) => {
    // Ctrl+E or Cmd+E to explain selection
    if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
        e.preventDefault();
        if (state.selection.text && state.currentFile && !elements.explainBtn.disabled) {
            explainSelection();
        }
    }
    // Escape to close modal
    if (e.key === 'Escape' && !elements.spaceModalOverlay.classList.contains('hidden')) {
        closeSpaceModal();
    }
});

// ══════════════════════════════════════════════════════════════
// Space Management UI
// ══════════════════════════════════════════════════════════════

function openSpaceModal() {
    elements.spaceModalOverlay.classList.remove('hidden');
    elements.spaceRepoUrl.value = '';
    elements.spacePreview.classList.add('hidden');
    elements.createSpaceBtn.disabled = true;
    setTimeout(() => elements.spaceRepoUrl.focus(), 100);
}

function closeSpaceModal() {
    elements.spaceModalOverlay.classList.add('hidden');
}

function renderSpacesList() {
    const spaces = spaceManager.getAll();
    const activeId = spaceManager.getActive()?.id;

    if (!elements.spacesList) return;

    elements.spacesList.innerHTML = spaces.map(space => {
        const initials = space.name.split('/').pop().substring(0, 2).toUpperCase();
        const isActive = space.id === activeId;
        return `
            <div class="space-item ${isActive ? 'active' : ''}" data-space-id="${space.id}">
                ${initials}
                <span class="space-item-tooltip">${space.name}</span>
                <button class="space-item-delete" data-delete-id="${space.id}" title="Delete Space">×</button>
            </div>
        `;
    }).join('');

    // Attach click handlers
    elements.spacesList.querySelectorAll('.space-item').forEach(item => {
        item.addEventListener('click', (e) => {
            if (e.target.classList.contains('space-item-delete')) return;
            const spaceId = item.dataset.spaceId;
            switchToSpace(spaceId);
        });
    });

    // Attach delete handlers
    elements.spacesList.querySelectorAll('.space-item-delete').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const spaceId = btn.dataset.deleteId;
            deleteSpace(spaceId);
        });
    });
}

function switchToSpace(spaceId) {
    const space = spaceManager.setActive(spaceId);
    if (!space) return;

    state.activeSpace = space;
    state.repoUrl = space.repoUrl;

    // Clear current state
    state.currentFile = null;
    state.files = [];
    state.selection = { startLine: null, endLine: null, text: null };

    // Update UI
    elements.repoUrlInput.value = space.repoUrl;
    renderSpacesList();

    // If already analyzed, try to load
    if (space.analyzed) {
        // Trigger a re-analyze to load the cached data
        analyzeRepository();
    } else {
        // Reset UI for new space
        resetWorkspace();
    }
}

function deleteSpace(spaceId) {
    spaceManager.delete(spaceId);
    renderSpacesList();

    // If deleted active space, switch to another or show landing
    if (state.activeSpace?.id === spaceId) {
        const nextSpace = spaceManager.getActive();
        if (nextSpace) {
            switchToSpace(nextSpace.id);
        } else {
            showLanding();
        }
    }
}

function resetWorkspace() {
    elements.fileTree.innerHTML = '';
    elements.filesEmpty.classList.remove('hidden');
    elements.codeEmpty.classList.remove('hidden');
    elements.codeContent.classList.add('hidden');
    elements.explanationEmpty.classList.remove('hidden');
    elements.explanationResult.classList.add('hidden');
    setStatus('idle', 'Ready');
}

function createSpaceAndAnalyze(repoUrl) {
    // Check if space already exists
    let space = spaceManager.findByRepoUrl(repoUrl);
    if (!space) {
        space = spaceManager.create(repoUrl);
    } else {
        spaceManager.setActive(space.id);
    }

    state.activeSpace = space;
    state.repoUrl = repoUrl;

    closeSpaceModal();
    launchApp(true);
    renderSpacesList();

    // Set URL and trigger analyze
    elements.repoUrlInput.value = repoUrl;
    analyzeRepository();
}

// Modal event listeners
if (elements.launchAppBtn) {
    elements.launchAppBtn.addEventListener('click', () => {
        openSpaceModal();
    });
}

if (elements.modalCloseBtn) {
    elements.modalCloseBtn.addEventListener('click', closeSpaceModal);
}

if (elements.modalCancelBtn) {
    elements.modalCancelBtn.addEventListener('click', closeSpaceModal);
}

if (elements.spaceModalOverlay) {
    elements.spaceModalOverlay.addEventListener('click', (e) => {
        if (e.target === elements.spaceModalOverlay) {
            closeSpaceModal();
        }
    });
}

if (elements.addSpaceBtn) {
    elements.addSpaceBtn.addEventListener('click', openSpaceModal);
}

// Space URL input handling
if (elements.spaceRepoUrl) {
    elements.spaceRepoUrl.addEventListener('input', (e) => {
        const url = e.target.value.trim();
        const name = spaceManager.extractRepoName(url);

        if (url && name !== url) {
            elements.spaceNamePreview.textContent = name;
            elements.spacePreview.classList.remove('hidden');
            elements.createSpaceBtn.disabled = false;
        } else {
            elements.spacePreview.classList.add('hidden');
            elements.createSpaceBtn.disabled = true;
        }
    });

    elements.spaceRepoUrl.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !elements.createSpaceBtn.disabled) {
            createSpaceAndAnalyze(elements.spaceRepoUrl.value.trim());
        }
    });
}

if (elements.createSpaceBtn) {
    elements.createSpaceBtn.addEventListener('click', () => {
        const url = elements.spaceRepoUrl.value.trim();
        if (url) {
            createSpaceAndAnalyze(url);
        }
    });
}

console.log('◈ RepoLogic initialized — Multi-Space Architecture | Ctrl+E to explain');

// 
// Resizable Panels
// 

function initResizers() {
    const resizerLeft = document.getElementById('resizer-left');
    const resizerRight = document.getElementById('resizer-right');
    const filesPanel = document.getElementById('files-panel');
    const explanationPanel = document.getElementById('explanation-panel');
    const root = document.documentElement;

    // Helper: Handle resizing logic
    function makeResizable(resizer, targetPanel, isRightPanel) {
        if (!resizer || !targetPanel) return;

        resizer.addEventListener('mousedown', (e) => {
            e.preventDefault();
            resizer.classList.add('active');
            document.body.style.cursor = 'col-resize';

            const startX = e.clientX;
            const startWidth = targetPanel.getBoundingClientRect().width;

            function onMouseMove(e) {
                let newWidth;
                if (isRightPanel) {
                    // Right panel resizing (dragging left increases width)
                    newWidth = startWidth - (e.clientX - startX);
                } else {
                    // Left panel resizing (dragging right increases width)
                    newWidth = startWidth + (e.clientX - startX);
                }

                // Update CSS variable
                const varName = isRightPanel ? '--panel-explanation-width' : '--panel-files-width';
                root.style.setProperty(varName, newWidth + 'px');
            }

            function onMouseUp() {
                resizer.classList.remove('active');
                document.body.style.cursor = '';
                window.removeEventListener('mousemove', onMouseMove);
                window.removeEventListener('mouseup', onMouseUp);
            }

            window.addEventListener('mousemove', onMouseMove);
            window.addEventListener('mouseup', onMouseUp);
        });
    }

    makeResizable(resizerLeft, filesPanel, false);
    makeResizable(resizerRight, explanationPanel, true);
}

// Initialize resizers when app loads
document.addEventListener('DOMContentLoaded', initResizers);
// Also try initializing if app view is already active (for SPA navigation)
initResizers();
