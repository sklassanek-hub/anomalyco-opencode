# p0 Fixes Summary — Accessibility + Release Check

Agent: FixAgent  
Date: 2026-08-31  
Source audit: memory/accessibility_audit_summary.md (issues 1–8); release_audit_summary.md (check_releases.py)

---

## 1. Accessibility fixes (zarabotok/pipeline_v3/ui/src/components + pages)

| File | Lines / Area | Change | Status |
|---|---|---|---|
| **Modal.tsx** | 11–87 | Added `role="dialog"`, `aria-modal="true"`, `aria-labelledby="modal-title"`, `tabIndex={-1}`; gave title `id="modal-title"`; added `useRef` + focus-on-open timer + restore-focus cleanup; added `handleKeyDown` Tab-loop (first/last focusable via `querySelectorAll`); added `type="button"`; comment note on focus-trap. | Fixed (basic trap; CSS overlay already blocks background) |
| **Drawer.tsx** | 10–32 | Same pattern as Modal: `role="dialog"`, `aria-modal="true"`, `aria-labelledby="drawer-title"`, `tabIndex={-1}`, `useRef`, focus timer, restore cleanup, Tab-loop `handleKeyDown`; title `id="drawer-title"`; `type="button"`. | Fixed (basic trap) |
| **Toast.tsx** | 38–44 | Added `aria-live="polite"` + `aria-atomic="true"` + `role="status"` on `.toast-wrap`; each toast item gets `role="status"` + `aria-label={t.text}`. | Fixed |
| **Badge.tsx** | 9–15 | Added `aria-label` derived from `title` or string `children`; added `role="status"`. | Fixed |
| **Card.tsx** | 10–34 | Added `Space` handling (`e.key === ' '`) with `preventDefault()`; added `aria-label` (from `title` string or fallback `'Карточка'`). | Fixed |
| **Pipeline.tsx** | 82–104 (nodes) | Added `aria-label` describing stage + subtitle + errors; added `onKeyDown` for `Enter`/`Space` (navigate) + `ArrowLeft`/`ArrowRight` placeholder (notes full loop needs library/DOM query). | Partial (arrow loop needs more) |
| **Pipeline.tsx** | 122–142 (funnel) | Added `role="region"` + `aria-label` per funnel row (`from → to: %`). | Fixed |
| **Pipeline.tsx** | 105–116 (edges) | Added `aria-label` describing transition; `role="img"`. | Fixed |
| **Overview.tsx** | 103–114 | Removed emoji characters from button text (`⚡`, `🔁`, `📤`, `⏹`, `💬`, `▶`, `⛔`); kept text labels; added `aria-label` to all 7 action buttons; updated confirm message to plain text. | Fixed (emoji-only eliminated) |
| **Table.tsx** | 55–67 | Added `role="button"`, `tabIndex={0}`, `aria-label` (first column value), `onKeyDown` (`Enter`/`Space` triggers `onRowClick`). | Fixed |
| **Task.tsx** | 156 | Replaced separate `<label htmlFor>` + `<Input id>` with single `<Input label="..." id="...">` to avoid nested-label issue and ensure proper association. | Fixed |

### What remains (focus-trap / advanced keyboard)
- **Full focus-trap library**: Modal/Drawer current loops only on `Tab`; `Shift+Tab` from first to last is handled, but nested modals (`showRaw`, `ReplyModal`) and stacked drawers need a centralized focus-stack manager (not implemented due to source scope).
- **CSS/JS focus indicator**: `.overlay` already blocks pointer events; `aria-modal` + `role="dialog"` provide semantic isolation. Additional `@media (prefers-reduced-motion)` and `outline` tokens may still be needed per Issue 12 / Issue 11.
- **Pipeline arrow navigation**: `ArrowLeft`/`ArrowRight` in nodes is a placeholder; a full loop requires querying `.pipeline-node-wrap` siblings and moving `focus()` sequentially. Not implemented to avoid over-engineering without design spec.
- **Table row arrow navigation**: Only `Enter`/`Space` added; vertical `ArrowUp`/`ArrowDown` between rows requires container-level key handler (not implemented).
- **Screen-reader evidence**: No NVDA/VoiceOver log attached (gap noted in audit §Weak Points A / B); fixes are code-level only.

---

## 2. Release-check fix (check_releases.py)

| Issue | Before | After |
|---|---|---|
| Wrong repo URL | `opencode-ai/opencode` | `anomalyco/opencode` |
| No pagination / default limit | None (defaults to 30) | `?per_page=100` |
| No error handling | `urllib.request.urlopen` unprotected | `try/except` for `HTTPError`, `URLError`, generic `Exception`; exits with message |
| No checksum verification | Printed asset URLs only | Downloads `checksums.txt`, parses `sha256  filename`, verifies local files with `hashlib.sha256` |
| Duplicate loop / duplicate code | None visible, but rewritten cleanly | Single pass over releases to find tag; single pass over assets for checksums; no duplicated loops |
| Comparison with local | None | Compares `tag_name`, asset names, checksum digests; reports OK / MISMATCH / MISSING |

File: `check_releases.py` (rewritten in place, 522 B → ~4.5 KB with comments and error handling).

---

## 3. Verification performed
- `python -c "py_compile.compile(...)"` on new `check_releases.py` → OK.
- Read-back checks on `Modal.tsx`, `Drawer.tsx`, `Pipeline.tsx`, `Overview.tsx`, `Task.tsx`, `Table.tsx`, `Toast.tsx`, `Badge.tsx`, `Card.tsx` — all edits applied without syntax errors in JSX/TSX structure.
- No `git commit` performed (not requested).

---

## 4. Files changed
- `zarabotok/pipeline_v3/ui/src/components/Modal.tsx`
- `zarabotok/pipeline_v3/ui/src/components/Drawer.tsx`
- `zarabotok/pipeline_v3/ui/src/components/Toast.tsx`
- `zarabotok/pipeline_v3/ui/src/components/Badge.tsx`
- `zarabotok/pipeline_v3/ui/src/components/Card.tsx`
- `zarabotok/pipeline_v3/ui/src/pages/Pipeline.tsx`
- `zarabotok/pipeline_v3/ui/src/pages/Overview.tsx`
- `zarabotok/pipeline_v3/ui/src/components/Table.tsx`
- `zarabotok/pipeline_v3/ui/src/pages/Task.tsx`
- `check_releases.py`
- `memory/p0_fixes_summary.md` (this file)

---

*Remaining risk: focus-trap CSS/JS may need additional library (e.g., `focus-trap-react`) for production-grade nested-modal handling; color-contrast and reduced-motion checks (Issues 11–12) are out of scope for this p0 pass.*
