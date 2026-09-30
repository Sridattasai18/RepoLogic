# Changelog

All notable changes to RepoLogic will be documented in this file.

## [Unreleased] - 2026-09-24

### ✨ New Features

#### File Explorer Improvements
- **Auto-open file explorer** after successful repository analysis
- **Active state indicator** on folder toggle button (📁) with visual feedback
- **First-time tooltip notification** explaining toggle behavior (shows once per session)
- **Session-based persistence** for improved user experience

#### Smart Citation Display
- Citations now capped at **4 maximum** (sorted by relevance)
- **File deduplication** - same file merged into one chip
- **Up to 3 line ranges per file** displayed
- **Hidden relevance scores** - debug info logged to console only
- Clean, user-friendly citation chips with no percentages

#### User Safety
- **Delete space confirmation dialog** prevents accidental deletions
- Clear warning message explaining action consequences
- Repository data on GitHub remains unaffected

#### Enhanced Loading States
- Replaced small numbered stepper with **large centered status text**
- **18px IBM Plex Mono typography** for better readability
- **Smooth progress bar** with both determinate and indeterminate states
- **Stage-based updates**: Cloning → Analyzing → Generating → Ready
- No card borders - just text and motion for cleaner appearance

### 🎨 Landing Page Redesign

#### Hero Section
- Updated subtitle: "AI-powered codebase analysis for faster developer onboarding"
- Added **interaction flow text** below CTA: "Paste a public GitHub repository → explore its codebase → understand it faster"
- **Screenshot enlarged by 15%** (max-width: 920px) for better product visibility

#### Feature Cards
- Replaced **"Zero Hallucination"** with **"Grounded Analysis"**
- All three cards rewritten with concrete technical descriptions:
  - **Full Repository Context** - explains project analysis
  - **Grounded Analysis** - explains RAG architecture
  - **Instant Code Insight** - explains workflow

#### New "How It Works" Section
- **3-step visual flow**: 01 Connect → 02 Analyze → 03 Understand
- Horizontal layout with arrows on desktop
- Vertical stacking on mobile (responsive)
- Green accent numbers matching brand color

#### Modal Improvements
- Placeholder updated to full `https://github.com/owner/repository`
- Added **concrete example**: `https://github.com/facebook/react`
- Code styling for better visual distinction

### 🔧 Technical Improvements

#### Frontend Architecture
- Refactored `buildFileRefs()` function with proper:
  - File grouping and merging logic
  - Relevance-based sorting
  - Maximum citations cap
  - Debug logging for developers
- Enhanced `toggleExplorer()` with active state management
- New `showExplorerTooltip()` function with positioning logic
- Improved loading status system with stage-based updates

#### Code Organization
- Separated loading status from stepper logic
- Legacy function compatibility maintained
- Better error handling and user feedback
- Session storage for tooltip state

#### Security
- Added path traversal security tests (`test_path_traversal.py`)
- Input validation on all endpoints
- Secure file operations

### 📝 Documentation

#### README.md Complete Rewrite
- Clear project description and value proposition
- **"How It Works"** section with visual flow
- Improved installation instructions
- API endpoint documentation
- Tech stack breakdown
- Design philosophy section
- Security considerations
- Better structure and readability

#### Updated .gitignore
- Excluded temporary test files (`test_*.html`, `test_*.js`, etc.)
- Added `.ecode/` and `repo_cache/` directories
- Better organization of ignored paths

### 🐛 Bug Fixes
- Fixed citation display showing internal debug percentages
- Improved file tree rendering performance
- Better button active state synchronization
- Enhanced error message clarity

### 🎯 UX Improvements
- **Immediate visual feedback** on all interactions
- **Clear loading states** that fill space instead of floating
- **Helpful notifications** for first-time users
- **Confirmation dialogs** for destructive actions
- **Professional, developer-focused design** throughout

### 📊 Metrics
- **17 files changed**
- **999 insertions**
- **831 deletions**
- Net improvement in code clarity and user experience

---

## Previous Versions

See git history for earlier changes.

## Links

- **Repository**: https://github.com/Sridattasai18/RepoLogic
- **Issues**: https://github.com/Sridattasai18/RepoLogic/issues
- **Author**: Kaligotla Sri Datta Sai Vithal
