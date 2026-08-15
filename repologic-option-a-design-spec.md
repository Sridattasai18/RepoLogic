# RepoLogic — Option A Design Spec
## Conversation-first, code-as-evidence

**Status:** Build-ready for Antigravity  
**Target:** Full HTML/CSS restructure + minimal JS layout changes  
**Constraint:** No emojis, no icon glyphs, technical-doc aesthetic  

---

## 1. Reference

**Linear product UI (late 2024)** mixed with **Perplexity's answer-with-citations layout**.

Why: Linear's restraint (minimal chrome, generous whitespace, monospace accents for data) + Perplexity's UX (chat as the hero, citations as supporting evidence rather than destination). Not an IDE clone — a research tool that happens to show code.

---

## 2. Forbidden

- Emojis or Unicode symbol characters anywhere (no lightbulb, sparkle, checkmark glyphs)
- Three-pane layout with simultaneous visibility
- Tabs, breadcrumbs, or traditional file-browser chrome
- Rounded pill buttons or badges (use `border-radius: 4px` or `3px` only)
- Soft shadows, glassmorphism, ambient glows
- Generic "AI tool" copy ("Transform your workflow," "Analyze anything," marketing speak)
- Icon fonts or SVG icons unless absolutely necessary for state (loading spinner OK, emoji-replacement OK, decorative icons NOT OK)

---

## 3. Typography

**Display (headlines):** IBM Plex Sans, 600 weight, 20–24px  
**Body (prose/chat):** IBM Plex Sans, 400 weight, 13–14px, line-height 1.6  
**UI labels & metadata:** IBM Plex Sans, 500 weight, 12px  
**Code / monospace:** IBM Plex Mono, 400 weight, 12px  
**Captions / timestamps:** IBM Plex Mono, 400 weight, 11px, color: `--text-tertiary`

**No letter-spacing on body text.** Use letter-spacing 0.06em only on ALL-CAPS labels (file names, status, "SOURCES").

---

## 4. Palette

**Background & Structure:**
- Primary bg: `#111214` (near-black charcoal)
- Elevated surfaces: `#17181b` (slightly lighter, for cards/panels)
- Component surfaces: `#1c1d20` (code blocks, callouts)
- Borders: `#2a2b2f` (1px hairlines, never shadows)

**Text:**
- Primary: `#e4e4e1` (off-white, not pure white)
- Secondary: `#9a9b9f` (body text, secondary labels)
- Tertiary: `#67686c` (captions, disabled states, faint text)

**Functional:**
- Accent (confidence=grounded, active states): `#1ed760` (Spotify green, use sparingly)
- Partial confidence: `#fbbf24` (amber, only for confidence badge)
- Error (insufficient_context, failed): `#ef4444` (red, only for failures)
- Info/Loading: `#60a5fa` (blue, for active/in-progress states)

**Rules:**
- Green is reserved for "confidence" and "success" states only.
- Every color choice must map to a semantic meaning (not used decoratively).
- Borders are always `1px solid var(--border)`, never shadows.
- Hover states lighten borders by one value (e.g., `rgba(42, 43, 47, 0.5)`), not by adding effects.

---

## 5. Layout

### 5.1 Overall structure

```
┌─────────────────────────────────────────┐
│  HEADER: RepoLogic + Repo URL + Status  │  [40–56px, sticky]
├──────────────────┬──────────────────────┤
│ FILE RAIL (icon  │  MAIN CHAT AREA      │  [full height below header]
│ only, 44–56px)   │  (full width minus   │
│                  │   rail)              │
└──────────────────┴──────────────────────┘
```

### 5.2 Header (sticky, full-width)

**Height:** 56px  
**Padding:** 12px 24px  
**Background:** `var(--bg-elevated)` with `1px solid var(--border)` bottom edge  
**Layout:** 3-column flex:
1. **Left:** RepoLogic logo/brand mark (24x24px) + repo URL (truncated monospace, 12px)
2. **Center:** (empty, flex-grow: 1)
3. **Right:** Status badge (e.g., "5 files indexed", "Analyzing…", "Error: embedding failed") + mode toggle (if including Option C's idle state, "< Back to start" button here)

**Repo URL display:** Truncate with ellipsis, show full on hover in a tooltip. Use `text-overflow: ellipsis; overflow: hidden; white-space: nowrap;`

---

### 5.3 File rail (left sidebar)

**Width:** 44px (icon only, no labels visible at rest)  
**Background:** `var(--bg-surface)`  
**Border:** `1px solid var(--border)` on the right  
**Padding:** 8px top/bottom  
**Content:** Stacked file icons (48x48px clickable areas, 24x24px icon in center)

**States:**
- Default: icon only, `color: var(--text-tertiary)`
- Hover: icon + small label popup (tooltip), border glow to `rgba(30, 215, 96, 0.2)`
- Active: icon + label visible, `color: var(--accent)`

**Expand interaction:** Click any icon → file tree expands as a **popover modal** (not in-page, floats over main chat), anchored to the rail. Modal closes on click-outside or Escape key.

**File tree modal:**
- Position: fixed, top 56px (below header), left 0, width 280–320px
- Background: `var(--bg-surface)`
- Border: `1px solid var(--border)` on right
- z-index: ensures it sits above chat content
- Close button: small X or just click outside
- Scrollable if tree is deep

---

### 5.4 Main chat area

**Padding:** 24px 48px (horizontal), 24px top, 24px bottom (space for composer at bottom)  
**Max-width:** 720px (optimal reading width for prose + code)
**Margin:** 0 auto (center the column on wide screens)  
**Layout:** flex column, gap 16px

**Messages (user & assistant):**

**User message:**
- Align: right
- Background: `rgba(30, 215, 96, 0.06)` (subtle green tint)
- Border: `1px solid rgba(30, 215, 96, 0.15)`
- Padding: 12px 16px
- Border-radius: `4px`
- Font: body (13px), color: `var(--text-primary)`
- Max-width: 85% (leave margin on left)

**Assistant message:**
- Align: left
- Background: `var(--bg-surface)`
- Border: `1px solid var(--border)`
- Padding: 16px
- Border-radius: `4px`
- Font: body (13px), color: `var(--text-primary)`
- Max-width: 100%

**Assistant message structure:**
```
┌─ Assistant message container ──────────┐
│ ┌─ Summary row ──────────────────────┐ │
│ │ summary text [confidence-badge]    │ │
│ └───────────────────────────────────┘ │
│ ┌─ Explanation body ─────────────────┐ │
│ │ multi-paragraph answer text        │ │
│ └───────────────────────────────────┘ │
│ ┌─ File references (citations) ──────┐ │
│ │ SOURCES                            │ │
│ │ [readme:16-53] [app.js:102-145]    │ │
│ └───────────────────────────────────┘ │
│ ┌─ Inline code block (if expanded) ──┐ │
│ │ >>> file: README.md, lines 16–53   │ │
│ │ [actual code snippet]              │ │
│ │                                    │ │
│ │ [collapse button ▲]                │ │
│ └───────────────────────────────────┘ │
└────────────────────────────────────────┘
```

---

### 5.5 Confidence badge

**Size:** inline (`padding: 2px 8px`)  
**Shape:** `border-radius: 4px` (rectangular, not pill)  
**Font:** 11px, 600 weight, monospace  
**States:**
- `grounded`: bg `rgba(30, 215, 96, 0.12)`, text `#1ed760`, border `rgba(30, 215, 96, 0.25)`
- `partial`: bg `rgba(251, 191, 36, 0.12)`, text `#fbbf24`, border `rgba(251, 191, 36, 0.25)`
- `insufficient_context`: bg `rgba(239, 68, 68, 0.12)`, text `#ef4444`, border `rgba(239, 68, 68, 0.25)`
- `unknown`: bg `var(--bg-hover)`, text `var(--text-tertiary)`, border `var(--border)`

**Placement:** inline with summary text on the right side, flex-shrink: 0 (never wraps)

---

### 5.6 File reference chips (sources section)

**Section header:** "SOURCES" (uppercase, 11px monospace, `--text-tertiary`, letter-spacing 0.06em)  
**Chips layout:** flex wrap, gap 8px

**Each chip:**
- Display: inline-flex, gap 4px
- Padding: 4px 10px
- Border: `1px solid var(--border)`
- Border-radius: `3px`
- Font: monospace 11px, color `var(--text-secondary)`
- Background: transparent (no tinted bg on default)
- Format: `filename:start-end` (e.g., `README.md:16-53`)

**Chip states:**
- Default: neutral, slightly dimmed
- Hover: border → `rgba(30, 215, 96, 0.4)`, color → `var(--accent)`, cursor: pointer
- Click: opens file in the expanded tree OR scrolls inline code block into view if already rendered

**Inline code block (cite expansion):**
- When user clicks a chip, a code block renders below it with:
  - Header: `→ [filename] [lines]` (neutral gray)
  - Code: monospace, with line numbers, readonly
  - Footer: small "[collapse ▲]" text-link to hide it again
  - Background: `var(--bg-surface)`
  - Border: `1px solid var(--border)`, top edge only (no full box)
  - Padding: 12px, overflow-x: auto for long lines

---

### 5.7 Message composer (sticky bottom)

**Position:** sticky, bottom 0, inside main chat area OR fixed at bottom (TBD — sticky inside flex column is cleaner)  
**Background:** `var(--bg-elevated)` (slightly lighter to distinguish from chat bg)  
**Border:** `1px solid var(--border)` on top  
**Padding:** 12px 16px  
**Layout:** flex row, gap 8px

**Components:**
- Input: `<textarea>`, placeholder "Ask anything about this repo…" (plain, no emoji)
- Button: "Ask" (background: `var(--accent)`, text: black, 600 weight, `border-radius: 3px`, padding 8px 16px)
- Button states:
  - Default: `var(--accent)` green
  - Hover: `#16a34a` (darker green)
  - Disabled (empty input): `var(--text-tertiary)` gray, opacity 0.5, cursor: not-allowed

**Auto-expand textarea:** Use `resize: none` and JS to grow height as user types (min 40px, max 120px)

---

## 6. Hierarchy

**One dominant element per state:**

**Idle/loading state:**
- The composer input is the only focal point
- Everything else (past messages, file rail) recedes to `--text-tertiary` color or reduced opacity
- No competing visual weight

**Active conversation:**
- The current answer being displayed is the dominant element (slightly larger, prominent bg color)
- Past messages fade to secondary weight (`--text-secondary`)
- File references are clickable but visually quiet (small, neutral borders, green only on hover)

**File tree expanded (modal):**
- Modal has `z-index: 1000`, overlay darkens the main area slightly (`background: rgba(0,0,0,0.3)`)
- Main chat is less interactive while modal is open

---

## 7. Voice

**Tone:** Technical and precise. Status text reads like a build log, not a chatbot.

**Copy guidelines:**
- Composer placeholder: "Ask anything about this repo…" (not "Tell me about…" or "What would you like to know?")
- Error message: "Embedding failed: quota exceeded" (not "Oops! Let's try that again!")
- Empty state (no messages yet): "Start by asking a question above." (not "Welcome! What can I help with today?")
- Loading indicator: "Indexing…" or "Searching…" (not "Working on it…" or "Thinking…")
- No punctuation on short labels (SOURCES, FILES, not "Sources:", "Files:")

---

## 8. Signature Element

**The inline code citation block that expands below each answer.**

This is the core UX differentiator for Option A — it's the "show your work" moment. When a user sees code cited inline, right where they asked the question, without leaving the conversation, it signals "this is grounded, here's the proof." No click to a separate pane, no context switch — evidence appears where the claim is made.

**Visual treatment:** Subtle but present. A thin top border in accent green, monospace font, line numbers in tertiary gray, read-only interaction. Not flashy, but unmistakably "this is source code from your repo."

---

## 9. State Transitions & Interactions

### 9.1 Idle state (on page load or after "new repo")

- Stepper is hidden or minimized
- File rail shows icon-only placeholder (empty state: `--text-tertiary`)
- Main chat area shows: "Start by asking a question about [repo name]." in large (18px) `--text-secondary` color, centered vertically
- Composer has focus (cursor blinking)

### 9.2 Analysis in progress (if Option C is implemented)

- Stepper appears above composer, shows progress
- Composer is disabled (`opacity: 0.5, pointer-events: none`)
- "Analyzing…" text in file rail
- Main chat area shows a progress indicator or remains blank

### 9.3 Ready state (analysis complete)

- Stepper turns green, disappears (or collapses to a small chip showing "5 files indexed")
- File rail is interactive, icons have colors (`--text-secondary`)
- Composer is enabled
- User can start asking questions

### 9.4 Message flow (each `/ask` call)

1. User types question, presses "Ask" or Cmd+Enter
2. User message appears immediately (optimistic render), right-aligned
3. Composer clears, stays focused
4. Assistant typing indicator appears (optional: just a "…" in secondary text, no animated dots)
5. Assistant message streams in (optional: character-by-character, or full response at once)
6. Confidence badge, explanation, sources, and inline code blocks render in sequence
7. User can click a source chip to expand the code block
8. User can ask a follow-up question

---

## 10. Responsive Behavior

**Breakpoint 1: < 760px (mobile)**

- File rail collapses to icon-only (always 44px)
- Main chat area padding reduces to 12px 16px
- Max-width on chat column: 100% (no center margin)
- Composer button text becomes just an icon or abbreviates to "⏎" (no, wait — no emoji, so make it a full "Ask" button that wraps to next line if needed, or use a standard form submit behavior)

**Breakpoint 2: > 1200px (wide)**

- Chat max-width can increase to 800px (still bounded for readability)
- File rail stays 44px (doesn't scale)
- Padding can increase to 24px 64px

---

## 11. Implementation Notes for Antigravity

### HTML structure

```html
<body class="repologic-a">
  <header class="sticky-header">
    <!-- logo, repo URL, status -->
  </header>
  
  <div class="workspace">
    <aside class="file-rail">
      <!-- file icons, clickable to open modal -->
    </aside>
    
    <main class="chat-area">
      <!-- conversation messages, centered max-width column -->
      <div class="messages">
        <!-- user & assistant messages stack here -->
      </div>
      
      <div class="composer sticky-bottom">
        <!-- textarea + send button -->
      </div>
    </main>
  </div>
  
  <div class="file-tree-modal hidden">
    <!-- file tree popover, z-index 1000 -->
  </div>
</body>
```

### CSS structure

- CSS variables: all colors, sizes, fonts as documented above
- No shadow utilities — use borders only
- No rounded-pill utilities — use `border-radius: 4px` or `3px` exclusively
- Flexbox for layouts (not Grid for message flows)
- No animations except optional typing indicator pulse (subtle, respectful of prefers-reduced-motion)

### JavaScript changes

- Remove the 3-pane layout JS
- Add file-rail icon click handler → open/close file-tree modal
- Add source-chip click handler → toggle inline code block visibility
- Keep the existing `/ask` and `/explain` logic, just re-theme the response rendering

---

## 12. Non-negotiables

1. **No emojis or icon glyphs** — anywhere, ever. Use text, monospace format, or nothing.
2. **No three-pane simultaneous layout** — file rail is always thin/collapsed unless modal is open.
3. **Chat max-width: 720px** (reading comfort) — don't let it stretch full screen.
4. **Confidence badge always visible** on assistant messages — not hidden, not optional.
5. **Source citations must be clickable** — clicking a source chip expands the code block.
6. **Borders, not shadows** — `1px solid` is the only depth tool allowed.
7. **Green is reserved** — for confidence/success/active states only. No green accents, no green decoration.

---

## 13. Acceptance Criteria (for Antigravity)

- [ ] Header is sticky, repo URL visible, status badge updates dynamically
- [ ] File rail is 44px wide, icons only, clickable to open modal
- [ ] File tree modal opens on click, closes on click-outside or Escape
- [ ] Chat area max-width 720px, centered on screen
- [ ] User messages right-aligned, green tinted background
- [ ] Assistant messages left-aligned, neutral background
- [ ] Confidence badge renders on all assistant messages with correct color
- [ ] Source section renders with chips, chips are clickable
- [ ] Clicking source chip expands inline code block with line numbers
- [ ] Composer textarea auto-expands as user types
- [ ] "Ask" button disabled when input is empty
- [ ] No emojis, glyphs, or icon fonts in the UI
- [ ] All borders are 1px solid, no shadows anywhere
- [ ] Responsive: collapses gracefully on mobile (file rail stays 44px, chat padding reduces)
- [ ] Colors match the palette exactly (charcoal, off-white, green for accents)
- [ ] No rounded pills anywhere (badge border-radius is 4px, not 100px)
