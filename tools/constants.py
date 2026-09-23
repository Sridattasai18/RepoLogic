"""
Shared constants for the RepoLogic tools package.
Single source of truth — import from here instead of defining locally.
"""

from langchain_text_splitters import Language

# Directories to skip during repo traversal
IGNORE_DIRS = {
    '.git', 'node_modules', '__pycache__', 'venv', 'env', 'virtualenv',
    'build', 'dist', 'target', 'bin', 'obj', '.idea', '.vscode', '.vs',
    'vendor', 'packages', '.next', '.nuxt', 'coverage', '.pytest_cache',
    '.mypy_cache', '.tox', 'eggs', '.eggs', 'lib', 'lib64', 'parts',
    'sdist', 'wheels', '*.egg-info', '.cache'
}

# Binary / media extensions to skip
IGNORE_EXTS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.mp4',
    '.zip', '.tar', '.gz', '.pyc', '.exe', '.dll', '.so', '.dylib', '.class'
}

# Source code extensions to include
CODE_EXTENSIONS = {
    '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
    '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.cs', '.r',
    '.m', '.mm', '.sh', '.bash', '.sql', '.html', '.css', '.scss', '.sass',
    '.vue', '.svelte', '.lua', '.pl', '.pm', '.jl', '.R'
}

# Plain-text / config extensions to include
TEXT_EXTENSIONS = {
    '.md', '.txt', '.rst', '.json', '.yaml', '.yml', '.toml', '.ini',
    '.cfg', '.conf', '.xml', '.env.example'
}

# Union of everything the chunker and ingestor should process
INCLUDED_EXTENSIONS = CODE_EXTENSIONS | TEXT_EXTENSIONS

# Maps file extension -> LangChain Language enum (for language-aware splitters)
LANGUAGE_MAP = {
    '.py':    Language.PYTHON,
    '.js':    Language.JS,
    '.ts':    Language.TS,
    '.java':  Language.JAVA,
    '.cpp':   Language.CPP,
    '.c':     Language.C,
    '.cs':    Language.CSHARP,
    '.go':    Language.GO,
    '.rs':    Language.RUST,
    '.php':   Language.PHP,
    '.rb':    Language.RUBY,
    '.swift': Language.SWIFT,
    '.kt':    Language.KOTLIN,
    '.scala': Language.SCALA,
    '.html':  Language.HTML,
    '.md':    Language.MARKDOWN,
}

# Maps file extension -> human-readable language name (for metadata / display)
DETECT_LANGUAGE_MAP = {
    '.py':   'Python',
    '.js':   'JavaScript',
    '.jsx':  'JavaScript',
    '.ts':   'TypeScript',
    '.tsx':  'TypeScript',
    '.java': 'Java',
    '.cpp':  'C++',
    '.c':    'C',
    '.h':    'C/C++',
    '.hpp':  'C++',
    '.go':   'Go',
    '.rs':   'Rust',
    '.rb':   'Ruby',
    '.php':  'PHP',
    '.swift':'Swift',
    '.kt':   'Kotlin',
    '.scala':'Scala',
    '.cs':   'C#',
    '.r':    'R',
    '.R':    'R',
    '.html': 'HTML',
    '.css':  'CSS',
    '.scss': 'SCSS',
    '.vue':  'Vue',
    '.sh':   'Shell',
    '.bash': 'Shell',
    '.sql':  'SQL',
    '.md':   'Markdown',
    '.json': 'JSON',
    '.yaml': 'YAML',
    '.yml':  'YAML',
}
