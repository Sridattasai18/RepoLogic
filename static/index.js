/**
 * RepoLogic - Conversation-First Repository Explorer
 * Option A Design Spec Implementation
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
        const match = url.match(/github\.com[\/:]([^\/]+)\/([^\/\.]+)/i);
        return match ? `${match[1]}/${match[2]}` : url;
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
        text: null,
        filePath: null
    },
    files: [],
    isLoading: false,
    qaEnabled: false,
    lastExplanation: null,
    activeSpace: null,
    currentView: 'landing'
};

// ══════════════════════════════════════════════════════════════
// DOM Elements
// ══════════════════════════════════════════════════════════════

const elements = {
    landing: document.getElementById('landing'),
    mainApp: document.getElementById('main-app'),
    launchAppBtn: document.getElementById('launch-app-btn'),
    homeBtn: document.getElementById('home-btn'),
    backStartBtn: document.getElementById('back-start-btn'),
    repoUrlDisplay: document.getElementById('repo-url-display'),
    statusDot: document.getElementById('status-indicator'),
    statusText: document.getElementById('status-text'),
    spacesList: document.getElementById('spaces-list'),
    addSpaceBtn: document.getElementById('add-space-btn'),
    toggleExplorerBtn: document.getElementById('toggle-explorer-btn'),
    closeExplorerBtn: document.getElementById('close-explorer-btn'),
    fileTreeModal: document.getElementById('file-tree-modal'),
    fileSearch: document.getElementById('file-search'),
    fileTree: document.getElementById('file-tree'),
    chatMessages: document.getElementById('chat-messages'),
    chatWelcome: document.getElementById('chat-welcome'),
    qaInput: document.getElementById('qa-input'),
    qaBtn: document.getElementById('qa-btn'),
    // Modals
    spaceModalOverlay: document.getElementById('space-modal-overlay'),
    spaceModal: document.getElementById('space-modal'),
    spaceRepoUrl: document.getElementById('space-repo-url'),
    spaceNamePreview: document.getElementById('space-name-preview'),
    spacePreview: document.getElementById('space-preview'),
    createSpaceBtn: document.getElementById('create-space-btn'),
    modalCloseBtn: document.getElementById('modal-close-btn'),
    modalCancelBtn: document.getElementById('modal-cancel-btn'),
    // Dummy fields for backend compatibility
    repoUrlInput: document.createElement('input'),
    analyzeBtn: document.createElement('button'),
    explanationLoading: document.createElement('div'),
    explanationResult: document.createElement('div'),
    explanationEmpty: document.createElement('div'),
    errorToast: document.getElementById('error-toast'),
    errorMessage: document.getElementById('error-message')
};

// Bind analysis dummy buttons
elements.repoUrlInput.id = 'dummy-repo-url-input';
elements.analyzeBtn.id = 'dummy-analyze-btn';

// ══════════════════════════════════════════════════════════════
// Status & Error
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
// API Utilities
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

function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/[&<>"']/g, m =>
        ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m])
    );
}

// ══════════════════════════════════════════════════════════════
// File Explorer & Popover Modal
// ══════════════════════════════════════════════════════════════

function toggleExplorer() {
    elements.fileTreeModal.classList.toggle('hidden');
    if (!elements.fileTreeModal.classList.contains('hidden')) {
        elements.fileSearch.focus();
    }
}

function closeExplorer() {
    elements.fileTreeModal.classList.add('hidden');
}

// Close popover on click outside
document.addEventListener('mousedown', (e) => {
    if (!elements.fileTreeModal.classList.contains('hidden')) {
        const isClickInside = elements.fileTreeModal.contains(e.target) || 
                              elements.toggleExplorerBtn.contains(e.target);
        if (!isClickInside) {
            closeExplorer();
        }
    }
});

if (elements.toggleExplorerBtn) {
    elements.toggleExplorerBtn.addEventListener('click', toggleExplorer);
}
if (elements.closeExplorerBtn) {
    elements.closeExplorerBtn.addEventListener('click', closeExplorer);
}

// ══════════════════════════════════════════════════════════════
// File Tree Rendering
// ══════════════════════════════════════════════════════════════

function getFileIcon(fileName) {
    const ext = fileName.split('.').pop().toLowerCase();
    const iconMap = {
        'py': 'py', 'js': 'js', 'ts': 'ts', 'jsx': 'jsx', 'tsx': 'tsx',
        'html': 'html', 'css': 'css', 'json': 'json', 'md': 'md',
        'yaml': 'yml', 'yml': 'yml', 'sh': 'sh'
    };
    return iconMap[ext] || 'file';
}

function renderFileTree(files) {
    const tree = document.createElement('div');
    tree.className = 'file-tree';

    // Sort: directories first (if directory structure is present in names, but list is flat)
    const sortedFiles = [...files].sort((a, b) => a.path.localeCompare(b.path));

    sortedFiles.forEach(file => {
        const item = document.createElement('div');
        item.className = 'file-item';
        item.dataset.path = file.path;

        const depth = (file.path.match(/\//g) || []).length;
        const indent = document.createElement('span');
        item.appendChild(indent);

        const icon = document.createElement('span');
        icon.className = 'file-icon';
        icon.textContent = `[${getFileIcon(file.name)}]`;

        const name = document.createElement('span');
        name.className = 'file-name';
        name.textContent = file.name;
        name.title = file.path;

        item.appendChild(icon);
        item.appendChild(name);

        item.style.paddingLeft = `${depth * 8 + 8}px`;

        item.addEventListener('click', () => {
            closeExplorer();
            loadFile(file.path);
        });

        tree.appendChild(item);
    });

    elements.fileTree.innerHTML = '';
    elements.fileTree.appendChild(tree);
}

// Search Filter
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
// File Loading (Code-as-Evidence in Chat)
// ══════════════════════════════════════════════════════════════

async function loadFile(filePath) {
    if (state.isLoading) return;
    setStatus('loading', 'Loading file...');

    try {
        const response = await fetch(`/file-content?repo_id=${state.repoId}&path=${encodeURIComponent(filePath)}`);
        if (!response.ok) throw new Error('Failed to load file');

        const data = await response.json();
        state.currentFile = filePath;
        state.currentFileContent = data.content;

        // Hide welcome message
        elements.chatWelcome.classList.add('hidden');

        // Append file block message to the chat container
        const fileMsgEl = document.createElement('div');
        fileMsgEl.className = 'chat-message-assistant';
        fileMsgEl.dataset.file = filePath;

        const lines = data.content.split('\n');
        const lineNumsHtml = lines.map((_, i) => `<span class="line-number">${i + 1}</span>`).join('\n');

        fileMsgEl.innerHTML = `
            <div class="citation-block-header">
                <span class="citation-block-title">→ VIEWING: ${escapeHtml(filePath)}</span>
            </div>
            <div class="citation-block-viewer">
                <div class="citation-line-numbers">${lineNumsHtml}</div>
                <pre class="citation-code-pre"><code class="citation-code-text language-${data.language || 'plaintext'}">${escapeHtml(data.content)}</code></pre>
            </div>
        `;

        elements.chatMessages.appendChild(fileMsgEl);
        elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;

        // Apply syntax highlighting
        const codeEl = fileMsgEl.querySelector('.citation-code-text');
        hljs.highlightElement(codeEl);

        setStatus('success', 'File loaded');

    } catch (error) {
        showError(error.message);
        setStatus('error', 'Load failed');
    }
}

// ══════════════════════════════════════════════════════════════
// Selection Tracking inside rendered code containers
// ══════════════════════════════════════════════════════════════

function getLineFromPosition(content, position) {
    const textBefore = content.substring(0, position);
    return (textBefore.match(/\n/g) || []).length + 1;
}

document.addEventListener('mouseup', () => {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();

    if (!selectedText) {
        state.selection = { startLine: null, endLine: null, text: null, filePath: null };
        return;
    }

    // Check if selection is within a code block container
    const codeContainer = selection.anchorNode.parentElement.closest('.citation-block-viewer');
    if (!codeContainer) return;

    const fileBlock = codeContainer.closest('[data-file]');
    if (!fileBlock) return;

    const filePath = fileBlock.dataset.file;
    const codeTextEl = codeContainer.querySelector('.citation-code-text');
    if (!codeTextEl) return;

    // Estimate lines based on selection
    const range = selection.getRangeAt(0);
    const preSelectionRange = range.cloneRange();
    preSelectionRange.selectNodeContents(codeTextEl);
    preSelectionRange.setEnd(range.startContainer, range.startOffset);

    const startOffset = preSelectionRange.toString().length;
    const endOffset = startOffset + selectedText.length;

    // Use full content of code block (approximate match to content)
    const blockContent = codeTextEl.textContent;
    const startLine = getLineFromPosition(blockContent, startOffset);
    const endLine = getLineFromPosition(blockContent, endOffset);

    state.selection = {
        startLine,
        endLine,
        text: selectedText,
        filePath: filePath
    };
});

// ══════════════════════════════════════════════════════════════
// Response Rendering & Citations
// ══════════════════════════════════════════════════════════════

const CONFIDENCE_MAP = {
    grounded:             { label: 'Grounded',          dot: '●' },
    partial:              { label: 'Partial match',      dot: '◑' },
    insufficient_context: { label: 'Low confidence',    dot: '○' },
    unknown:              { label: 'Unknown',            dot: '?' },
};

function buildConfidenceBadge(confidence) {
    const conf = CONFIDENCE_MAP[confidence] || CONFIDENCE_MAP.unknown;
    const cls  = confidence || 'unknown';
    return `<span class="confidence-badge ${cls}">${conf.dot} ${conf.label}</span>`;
}

function buildSummaryRow(summary, confidence) {
    if (!summary) return '';
    return `
        <div class="response-summary-row">
            <span class="response-summary-text">${escapeHtml(summary)}</span>
            ${buildConfidenceBadge(confidence)}
        </div>`;
}

function buildFileRefs(refs) {
    if (!refs || refs.length === 0) return '';
    const chips = refs.map(ref => {
        const label = ref.file || '';
        const lines = ref.lines || '';
        const reason = ref.reason ? ` title="${escapeHtml(ref.reason)}"` : '';
        return `<a class="file-ref-chip" href="#"${reason} data-file="${escapeHtml(label)}" data-lines="${escapeHtml(lines)}"
            >${escapeHtml(label)}<span class="chip-lines">${lines ? ':' + lines : ''}</span></a>`;
    }).join('');
    return `
        <div class="file-refs-section">
            <div class="file-refs-header">SOURCES</div>
            <div class="file-refs-list">${chips}</div>
        </div>`;
}

function buildQASourcesSection(sources) {
    if (!sources || sources.length === 0) return '';
    const sourceItems = sources.map(s => {
        const relevance = s.relevance_score ? ` (${Math.round(s.relevance_score * 100)}%)` : '';
        return `<div class="source-item">
            <span class="source-icon">→</span>
            <span class="source-file">${escapeHtml(s.file)}</span>
            <span class="source-lines">L${escapeHtml(s.lines)}</span>
            <span class="source-type">${relevance}</span>
        </div>`;
    }).join('');
    return `
        <div class="sources-section">
            <div class="sources-header">SOURCES USED</div>
            <div class="sources-list">${sourceItems}</div>
        </div>`;
}

// ══════════════════════════════════════════════════════════════
// Inline Code Citation Block (The Signature Element)
// ══════════════════════════════════════════════════════════════

async function toggleInlineCitationBlock(chip, filePath, linesRange) {
    let block = chip.nextElementSibling;
    if (block && block.classList.contains('inline-code-citation-block')) {
        block.remove();
        return;
    }

    // Create loader block
    block = document.createElement('div');
    block.className = 'inline-code-citation-block';
    block.innerHTML = `<div class="citation-block-header"><span class="citation-block-title">Loading code citation...</span></div>`;
    chip.parentNode.insertBefore(block, chip.nextSibling);

    try {
        const response = await fetch(`/file-content?repo_id=${state.repoId}&path=${encodeURIComponent(filePath)}`);
        if (!response.ok) throw new Error();
        const data = await response.json();

        const allLines = data.content.split('\n');
        let startLine = 1;
        let endLine = allLines.length;

        if (linesRange) {
            const parts = linesRange.split('-');
            startLine = parseInt(parts[0]) || 1;
            endLine = parseInt(parts[1]) || allLines.length;
        }

        const slicedLines = allLines.slice(startLine - 1, endLine);
        const slicedContent = slicedLines.join('\n');
        const lineNumsHtml = slicedLines.map((_, idx) => `<span class="line-number">${startLine + idx}</span>`).join('\n');

        block.innerHTML = `
            <div class="citation-block-header">
                <span class="citation-block-title">→ ${escapeHtml(filePath)}:${linesRange || ''}</span>
            </div>
            <div class="citation-block-viewer">
                <div class="citation-line-numbers">${lineNumsHtml}</div>
                <pre class="citation-code-pre"><code class="citation-code-text language-${data.language || 'plaintext'}">${escapeHtml(slicedContent)}</code></pre>
            </div>
            <div class="citation-block-footer">
                <a href="#" class="btn-collapse-citation">collapse ▲</a>
            </div>
        `;
        block.dataset.file = filePath;

        // Syntax highlighting
        const codeEl = block.querySelector('.citation-code-text');
        hljs.highlightElement(codeEl);

        // Wire collapse link
        block.querySelector('.btn-collapse-citation').addEventListener('click', (e) => {
            e.preventDefault();
            block.remove();
        });

    } catch (_) {
        block.innerHTML = `<div class="citation-block-header"><span class="citation-block-title">Failed to load code citation.</span></div>`;
    }
}

// Click listener on file chips to toggle citation viewer
document.addEventListener('click', (e) => {
    const chip = e.target.closest('.file-ref-chip');
    if (!chip) return;
    e.preventDefault();
    const file = chip.dataset.file;
    const lines = chip.dataset.lines;
    if (file) {
        toggleInlineCitationBlock(chip, file, lines);
    }
});

// ══════════════════════════════════════════════════════════════
// Selection Explanation (/explain)
// ══════════════════════════════════════════════════════════════

async function explainSelection() {
    const sel = state.selection;
    if (!sel.text || !sel.filePath) return;

    setStatus('loading', 'Analyzing...');

    // Append User selection explanation request card
    const userMsg = document.createElement('div');
    userMsg.className = 'chat-message-user';
    userMsg.textContent = `Explain selected code in ${sel.filePath} (lines ${sel.startLine}-${sel.endLine}):\n"${sel.text.substring(0, 100)}${sel.text.length > 100 ? '...' : ''}"`;
    elements.chatMessages.appendChild(userMsg);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;

    // Append temporary loading container
    const loadMsg = document.createElement('div');
    loadMsg.className = 'chat-message-assistant';
    loadMsg.innerHTML = 'Searching logic path...';
    elements.chatMessages.appendChild(loadMsg);

    try {
        const result = await apiCall('/explain', {
            repo_url: state.repoUrl,
            file_path: sel.filePath,
            start_line: sel.startLine,
            end_line: sel.endLine,
            selected_code: sel.text
        });

        loadMsg.innerHTML = `
            ${buildSummaryRow(result.summary, result.confidence)}
            <div class="explanation-text">${marked.parse(result.explanation)}</div>
            ${buildFileRefs(result.file_references || [])}
            ${buildQASourcesSection(result.sources || [])}
        `;

        loadMsg.querySelectorAll('pre code').forEach(block => {
            hljs.highlightElement(block);
        });

        setStatus('success', 'Explanation finished');

    } catch (error) {
        loadMsg.innerHTML = `Explanation failed: ${escapeHtml(error.message)}`;
        setStatus('error', 'Analysis failed');
    } finally {
        elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    }
}

// ══════════════════════════════════════════════════════════════
// Natural Language Q&A
// ══════════════════════════════════════════════════════════════

async function askQuestion() {
    const question = elements.qaInput.value.trim();
    if (!question) return;

    if (!state.repoUrl || !state.qaEnabled) {
        showError('Please analyze a repository first.');
        return;
    }

    // Disable composer during query
    elements.qaBtn.disabled = true;
    elements.qaInput.disabled = true;
    setStatus('loading', 'Searching...');

    // Clear welcome message
    elements.chatWelcome.classList.add('hidden');

    // Append User Message to the stream
    const userMsg = document.createElement('div');
    userMsg.className = 'chat-message-user';
    userMsg.textContent = question;
    elements.chatMessages.appendChild(userMsg);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;

    // Clear input
    elements.qaInput.value = '';
    elements.qaInput.style.height = '';

    // Create assistant placeholder message
    const assistantMsg = document.createElement('div');
    assistantMsg.className = 'chat-message-assistant';
    assistantMsg.innerHTML = '<span class="status-text">Thinking...</span>';
    elements.chatMessages.appendChild(assistantMsg);

    try {
        const result = await apiCall('/ask', {
            repo_url: state.repoUrl,
            question: question
        });

        assistantMsg.innerHTML = `
            ${buildSummaryRow(result.summary, result.confidence)}
            <div class="explanation-text">${marked.parse(result.answer)}</div>
            ${buildFileRefs(result.file_references || [])}
            ${buildQASourcesSection(result.sources || [])}
        `;

        assistantMsg.querySelectorAll('pre code').forEach(block => {
            hljs.highlightElement(block);
        });

        setStatus('success', 'Answered');

    } catch (error) {
        assistantMsg.innerHTML = `<span class="status-text error">Search failed: ${escapeHtml(error.message)}</span>`;
        setStatus('error', 'Search failed');
    } finally {
        elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
        elements.qaBtn.disabled = false;
        elements.qaInput.disabled = false;
        elements.qaInput.focus();
    }
}

if (elements.qaBtn) elements.qaBtn.addEventListener('click', askQuestion);

if (elements.qaInput) {
    // Dynamic height resize
    elements.qaInput.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        elements.qaBtn.disabled = (this.value.trim() === '');
    });

    elements.qaInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!elements.qaBtn.disabled) askQuestion();
        }
    });
}

// ══════════════════════════════════════════════════════════════
// Stepper Helper Logic
// ══════════════════════════════════════════════════════════════

const stepperEl  = () => document.getElementById('analysis-stepper');
const errorBannerEl = () => document.getElementById('stepper-error');

function setStepperState(stepId, stepState, statusText) {
    const el = document.getElementById(`step-${stepId}`);
    if (!el) return;
    el.classList.remove('active', 'completed', 'failed');
    if (stepState) el.classList.add(stepState);
    el.querySelector('.step-status').textContent = statusText || '';
}

function showStepper() {
    const s = stepperEl();
    if (s) s.classList.remove('hidden');
}

function hideStepper() {
    const s = stepperEl();
    if (s) s.classList.add('hidden');
}

function resetStepper() {
    ['ingest', 'chunk', 'embed', 'ready'].forEach(id => setStepperState(id, null, ''));
    const eb = errorBannerEl();
    if (eb) eb.classList.add('hidden');
}

function showEmbedError(errorMessage, repoUrl) {
    const eb = errorBannerEl();
    if (!eb) return;
    eb.innerHTML = `
        <strong>⚠ Embedding failed</strong>
        ${escapeHtml(errorMessage || 'An unknown error occurred.')}
        <br><button class="btn-retry-embed" onclick="retryEmbed('${escapeHtml(repoUrl)}')">↺ Retry Embedding</button>
    `;
    eb.classList.remove('hidden');
}

async function retryEmbed(repoUrl) {
    const eb = errorBannerEl();
    if (eb) eb.classList.add('hidden');
    setStepperState('embed', 'active', 'Retrying...');

    const embedFetch = fetch('/embed', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: repoUrl })
    });

    let attempts = 0;
    const poll = setInterval(async () => {
        attempts++;
        try {
            const st = await fetch(`/status?repo_url=${encodeURIComponent(repoUrl)}`).then(r => r.json());
            if (st.stage === 'embedded') {
                clearInterval(poll);
                setStepperState('embed', 'completed', 'Indexed');
                setStepperState('ready', 'completed', 'Ready');
                setTimeout(() => hideStepper(), 1500);
                enableQAInterface();
            } else if (st.stage === 'failed:embed' || attempts > 30) {
                clearInterval(poll);
                setStepperState('embed', 'failed', 'Failed');
                showEmbedError(st.error_message || 'Retry failed', repoUrl);
            }
        } catch (_) {}
    }, 2000);

    try {
        await embedFetch;
        clearInterval(poll);
        const st = await fetch(`/status?repo_url=${encodeURIComponent(repoUrl)}`).then(r => r.json());
        if (st.stage === 'embedded') {
            setStepperState('embed', 'completed', 'Indexed');
            setStepperState('ready', 'completed', 'Ready');
            setTimeout(() => hideStepper(), 1500);
            enableQAInterface();
        } else {
            setStepperState('embed', 'failed', 'Failed');
            showEmbedError(st.error_message, repoUrl);
        }
    } catch (err) {
        clearInterval(poll);
        setStepperState('embed', 'failed', 'Failed');
        showEmbedError(err.message, repoUrl);
    }
}

function enableQAInterface() {
    state.qaEnabled = true;
    elements.qaInput.disabled  = false;
    if (state.activeSpace) spaceManager.markAnalyzed(state.activeSpace.id);
}

// ══════════════════════════════════════════════════════════════
// Repository Analysis
// ══════════════════════════════════════════════════════════════

async function analyzeRepository() {
    const url = state.repoUrl;
    if (!url) return;

    state.isLoading = true;
    showStepper();
    resetStepper();
    setStatus('loading', 'Analyzing...');

    try {
        setStepperState('ingest', 'active', 'Cloning...');
        const ingestResult = await apiCall('/ingest', { repo_url: url });
        state.repoId = ingestResult.repo_id;
        state.files  = ingestResult.files;
        setStepperState('ingest', 'completed', 'Cloned');

        setStepperState('chunk', 'active', 'Analyzing...');
        await apiCall('/chunk', { repo_url: url });
        setStepperState('chunk', 'completed', 'Analyzed');

        setStepperState('embed', 'active', 'Indexing...');
        const embedFetch = fetch('/embed', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ repo_url: url })
        });

        let pollDone = false;
        const pollInterval = setInterval(async () => {
            if (pollDone) return;
            try {
                const st = await fetch(`/status?repo_url=${encodeURIComponent(url)}`).then(r => r.json());
                if (st.stage === 'embedded') {
                    pollDone = true;
                    clearInterval(pollInterval);
                    setStepperState('embed', 'completed', 'Indexed');
                    setStepperState('ready',  'completed', 'Ready');
                    renderFileTree(state.files);
                    enableQAInterface();
                    setStatus('success', 'Ready');
                    setTimeout(() => hideStepper(), 1500);
                    state.isLoading = false;
                } else if (st.stage === 'failed:embed') {
                    pollDone = true;
                    clearInterval(pollInterval);
                    setStepperState('embed', 'failed', 'Failed');
                    showEmbedError(st.error_message, url);
                    setStatus('error', 'Embedding failed');
                    state.isLoading = false;
                }
            } catch (_) {}
        }, 2000);

        try {
            const embedRes = await embedFetch;
            const embedData = await embedRes.json();
            if (!pollDone) {
                clearInterval(pollInterval);
                pollDone = true;
                if (embedRes.ok) {
                    setStepperState('embed', 'completed', 'Indexed');
                    setStepperState('ready',  'completed', 'Ready');
                    renderFileTree(state.files);
                    enableQAInterface();
                    setStatus('success', 'Ready');
                    setTimeout(() => hideStepper(), 1500);
                } else {
                    setStepperState('embed', 'failed', 'Failed');
                    showEmbedError(embedData.message || embedData.error, url);
                    setStatus('error', 'Embedding failed');
                }
            }
        } catch (embedErr) {
            if (!pollDone) {
                clearInterval(pollInterval);
                setStepperState('embed', 'failed', 'Failed');
                showEmbedError(embedErr.message, url);
                setStatus('error', 'Embedding failed');
            }
        }

    } catch (error) {
        showError(error.message);
        setStatus('error', 'Analysis failed');
    } finally {
        state.isLoading = false;
    }
}

// ══════════════════════════════════════════════════════════════
// Routing & Navigation
// ══════════════════════════════════════════════════════════════

function showLanding() {
    state.currentView = 'landing';
    elements.landing.classList.remove('hidden');
    elements.mainApp.classList.add('hidden');
    elements.mainApp.classList.remove('active');
}

function launchApp(addHistory = true) {
    state.currentView = 'app';
    elements.landing.classList.add('hidden');
    elements.mainApp.classList.remove('hidden');
    elements.mainApp.classList.add('active');

    if (addHistory) {
        history.pushState({ view: 'app' }, '', '#app');
    }
    localStorage.setItem('repoLogicSeenLanding', 'true');
}

window.addEventListener('popstate', (event) => {
    if (event.state && event.state.view === 'app') {
        launchApp(false);
    } else {
        showLanding();
    }
});

if (elements.homeBtn) {
    elements.homeBtn.addEventListener('click', () => {
        showLanding();
        history.replaceState(null, '', ' ');
    });
}
if (elements.backStartBtn) {
    elements.backStartBtn.addEventListener('click', () => {
        showLanding();
        history.replaceState(null, '', ' ');
    });
}

// ══════════════════════════════════════════════════════════════
// Space Manager UI
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
            <div class="space-item ${isActive ? 'active' : ''}" data-space-id="${space.id}" title="${space.name}">
                ${initials}
                <button class="space-item-delete" data-delete-id="${space.id}" title="Delete Space">×</button>
            </div>
        `;
    }).join('');

    elements.spacesList.querySelectorAll('.space-item').forEach(item => {
        item.addEventListener('click', (e) => {
            if (e.target.classList.contains('space-item-delete')) return;
            switchToSpace(item.dataset.spaceId);
        });
    });

    elements.spacesList.querySelectorAll('.space-item-delete').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteSpace(btn.dataset.deleteId);
        });
    });
}

function switchToSpace(spaceId) {
    const space = spaceManager.setActive(spaceId);
    if (!space) return;

    state.activeSpace = space;
    state.repoUrl = space.repoUrl;
    elements.repoUrlDisplay.textContent = space.repoUrl;
    elements.repoUrlDisplay.title = space.repoUrl;

    // Reset chat
    elements.chatMessages.innerHTML = '';
    elements.chatWelcome.classList.remove('hidden');
    elements.chatWelcome.querySelector('.welcome-text').textContent = `Start by asking a question about ${space.name}.`;

    // Clear current state
    state.currentFile = null;
    state.files = [];
    state.selection = { startLine: null, endLine: null, text: null, filePath: null };

    renderSpacesList();

    if (space.analyzed) {
        analyzeRepository();
    } else {
        // Reset and show stepper
        showStepper();
        resetStepper();
        elements.fileTree.innerHTML = '';
        setStatus('idle', 'Ready');
    }
}

function deleteSpace(spaceId) {
    spaceManager.delete(spaceId);
    renderSpacesList();

    if (state.activeSpace?.id === spaceId) {
        const nextSpace = spaceManager.getActive();
        if (nextSpace) {
            switchToSpace(nextSpace.id);
        } else {
            showLanding();
        }
    }
}

function createSpaceAndAnalyze(repoUrl) {
    let space = spaceManager.findByRepoUrl(repoUrl);
    if (!space) {
        space = spaceManager.create(repoUrl);
    } else {
        spaceManager.setActive(space.id);
    }

    state.activeSpace = space;
    state.repoUrl = repoUrl;
    elements.repoUrlDisplay.textContent = repoUrl;
    elements.repoUrlDisplay.title = repoUrl;

    closeSpaceModal();
    launchApp(true);
    renderSpacesList();

    // Reset Chat
    elements.chatMessages.innerHTML = '';
    elements.chatWelcome.classList.remove('hidden');
    elements.chatWelcome.querySelector('.welcome-text').textContent = `Start by asking a question about ${space.name}.`;

    analyzeRepository();
}

// Modal event listeners
if (elements.launchAppBtn) elements.launchAppBtn.addEventListener('click', openSpaceModal);
if (elements.modalCloseBtn) elements.modalCloseBtn.addEventListener('click', closeSpaceModal);
if (elements.modalCancelBtn) elements.modalCancelBtn.addEventListener('click', closeSpaceModal);
if (elements.addSpaceBtn) elements.addSpaceBtn.addEventListener('click', openSpaceModal);

if (elements.spaceModalOverlay) {
    elements.spaceModalOverlay.addEventListener('click', (e) => {
        if (e.target === elements.spaceModalOverlay) closeSpaceModal();
    });
}

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
        if (url) createSpaceAndAnalyze(url);
    });
}

// Keyboards
document.addEventListener('keydown', (e) => {
    // Ctrl+E / Cmd+E to explain selection
    if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
        e.preventDefault();
        if (state.selection.text && state.selection.filePath) {
            explainSelection();
        }
    }
    // Escape to close explorer modal
    if (e.key === 'Escape') {
        closeExplorer();
        if (!elements.spaceModalOverlay.classList.contains('hidden')) {
            closeSpaceModal();
        }
    }
});

// Initial boot
const hasSeenLanding = localStorage.getItem('repoLogicSeenLanding');
if (spaceManager.hasSpaces()) {
    const activeSpace = spaceManager.getActive();
    if (activeSpace) {
        state.activeSpace = activeSpace;
        state.repoUrl = activeSpace.repoUrl;
        elements.repoUrlDisplay.textContent = activeSpace.repoUrl;
        elements.repoUrlDisplay.title = activeSpace.repoUrl;
    }
    launchApp(false);
    renderSpacesList();
    if (state.activeSpace?.analyzed) {
        analyzeRepository();
    }
} else if (window.location.hash === '#app' || hasSeenLanding) {
    launchApp(false);
} else {
    showLanding();
}

console.log('◈ RepoLogic initialized — Option A conversation-first UI | Ctrl+E to explain selection');
