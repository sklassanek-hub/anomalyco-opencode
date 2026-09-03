# Senior Developer Review — Audit Execution Edits

**Reviewer:** EngineeringSeniorDeveloper (Senior Full-Stack / Premium Craftsmanship)  
**Session:** 2026-08-31  
**Source audit references:** `memory/accessibility_audit_summary.md` (WCAG 2.1 AA, 479-line source `audit_accessibility.md`); `memory/code_audit_summary.md` (security/code audit, 167 lines, `opencode-src/` + root artifacts)  
**Files reviewed (edited/created from audit execution):**
- `zarabotok/pipeline_v3/ui/src/components/Modal.tsx`
- `zarabotok/pipeline_v3/ui/src/components/Drawer.tsx`
- `zarabotok/pipeline_v3/ui/src/components/Toast.tsx`
- `zarabotok/pipeline_v3/ui/src/components/Badge.tsx`
- `zarabotok/pipeline_v3/ui/src/components/Card.tsx`
- `zarabotok/pipeline_v3/ui/src/pages/Pipeline.tsx`
- `zarabotok/pipeline_v3/ui/src/components/Table.tsx`
- `zarabotok/pipeline_v3/ui/src/components/Layout.tsx`
- `zarabotok/pipeline_v3/Dockerfile.sandbox`
- `zarabotok/pipeline_v3/modules/kill_switch.py` (created/edited)
- `zarabotok/pipeline_v3/modules/listener_bridge.py` (edited)
- `check_releases.py` (edited)
- `.github/workflows/release.yml` (edited)
- `scripts/verify_release.py` (edited)
- `opencode-src/` changes: only `.goreleaser.yml` (31.08.2026 2:37) — no source modifications in `cmd/`, `internal/`, `main.go`; reference only.

---

## Executive Summary

The audit execution produced **partial remediation** of WCAG 2.1 AA Critical/Important findings (Modal/Drawer focus-trap added, Badge aria-label added, Table arrow keys added, Layout skip-link / nav aria-current / main id added, Toast aria-live added, Card role="button" added, Pipeline node role/button added). However, **most fixes are manual/basic rather than library-grade**, several audit recommendations remain unaddressed, security gaps (auth middleware, rate limit, structured audit log, sandbox build verification) are unremediated, and **no new tests were added** for accessibility, keyboard navigation, or workflow security. Code quality ranges from **B (acceptable with known debt)** for components with basic focus loops to **C (needs refactoring)** for Pipeline/Table where Arrow navigation is placeholder/incomplete and focus management relies on `document.querySelectorAll` / `document.activeElement` loops.

**Premium enhancement opportunity:** The UI components could benefit from a unified `useFocusTrap` hook, `react-focus-lock` or `focus-trap-react` integration, and a `PrefersReducedMotion` media block in `styles.css` (referenced but not verified in edited files). Security needs an auth middleware layer (`internal/permission/` is session-level only, no user/auth gate), rate-limiting on `listener_bridge.poll_and_link()` and `check_releases.fetch_releases()`, and a real sandbox CI job that builds `Dockerfile.sandbox` with `--network none` verification.

---

## 1. Code Quality Score per File (A / B / C)

Scoring aligns with `memory/code_audit_summary.md` (§5 Weak Points: weak input sanitization, unverified external endpoints, minimal tests, no container isolation, binary exposure) and `memory/accessibility_audit_summary.md` (Issues 1–20, Critical/Important/Minor).

### Modal.tsx — **B** (Good structure, basic trap, debt in loop & IDs)
- **Strengths:** `role="dialog"`, `aria-modal="true"`, `aria-labelledby="modal-title"`, `Escape` closes, overlay click-to-close (`role="presentation"`), focus restoration to `prevFocusedRef`, focus-first-focusable on open.
- **Issues (with audit refs):**
  - **Not library-based focus-trap** (`accessibility_audit_summary.md` §4.5). Uses manual `querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')` loop at lines 22–24, 50–60. No `Shift+Tab` loop verification documented (audit §3.A). Recommendation: adopt `focus-trap-react` or extract `useFocusTrap`.
  - **Static ID `modal-title`** (line 77, 72) — duplicate-ID risk for nested modals (`Orders` `showRaw`, `ReplyModal`; audit Issue 1 line 53, Issue 15 line 323). Needs `id={`modal-title-${instanceId}`}`.
  - **No `aria-describedby`** linking body content to title (audit Issue 15 / 4.2). Should link body region via `aria-describedby` to a content-id.
  - **No `focus-visible` CSS confirmation** in component (audit Issue 1 / 4.5). Focus indicator may rely solely on browser default; needs `.modal:focus-visible` or `.modal *:focus-visible` rule.
  - **No reduced-motion** check for any modal-enter animation (audit Issue 12 / 4.7 — CSS `@media (prefers-reduced-motion: reduce)` missing in edited source).
- **Line refs:** 11 (comment notes trap requires loop), 22 (querySelectorAll), 50–60 (Tab loop), 64 (`aria-label` hardcoded Russian), 72 (`aria-labelledby` static), 77 (`id="modal-title"`).

### Drawer.tsx — **B- / C+** (Similar to Modal but missing restoration & labeled overlay)
- **Strengths:** `role="dialog"`, `aria-modal="true"`, `aria-labelledby="drawer-title"`, `Escape` closes, `tabIndex={-1}` on container, basic `Tab` loop (lines 35–50).
- **Issues:**
  - **No focus restoration** — missing `prevFocusedRef` entirely (compare Modal 15, 31–35). Audit Issue 1 line 52 / §4.5 requires restore on close.
  - **Same manual `querySelectorAll` loop** (line 25, 39) — not library-based.
  - **Static `drawer-title` ID** (line 66, 61) — nested drawer duplicate risk.
  - **Overlay only `role="presentation"` with `aria-label="Фоновое затемнение"`** — okay for screen reader, but no `aria-modal` on overlay (correctly on inner div).
  - **No `aria-describedby`**, no `focus-visible` confirmation.
- **Line refs:** 10 (comment), 25 (querySelectorAll), 35–50 (Tab loop), 61 (`aria-labelledby`), 66 (`id="drawer-title"`).

### Toast.tsx — **B** (Live region present, error severity missing)
- **Strengths:** `aria-live="polite"`, `aria-atomic="true"` on container (line 38); `role="status"` on container and items (line 40); `key` stable via `nextId`.
- **Issues:**
  - **Errors should be assertive** — audit Issue 2 (§4.3) notes `Toast` must distinguish `polite` vs `assertive`. Currently all toasts use `polite`; `type='err'` should render with `aria-live="assertive"` or `role="alert"` (or split container regions).
  - **No keyboard dismiss** — no close button / `role="button"` for dismiss (audit Issue 2 / 2.1.1, 2.4.7). Users must wait 4s (line 29–31).
  - **No reduced-motion** — `.toast-in` animation not guarded (audit Issue 12).
  - **No focus management** when toast appears — focus should not steal but should be announced (audit §4.3 status messages).
- **Line refs:** 38 (live region), 40 (item role/status), 28–31 (auto-dismiss timeout, no user control).

### Badge.tsx — **B-** (ARIA label added, tone not announced, contrast unverified)
- **Strengths:** `aria-label={label}` (line 12) where `label = title || string children`; `role="status"`; uses `Tone` import for typing.
- **Issues:**
  - **Tone not announced to screen readers** — audit Issue 3 (line 79–83) critical. `aria-label` only carries text, not `ok`/`warn`/`err`/`info`; should include tone, e.g., `aria-label={\`${label}, статус: ${tone}\`}` or use `aria-describedby` linking to tone-text.
  - **No contrast audit** for `badge-${tone}` backgrounds/text (audit Issue 11 / §4.3 — only `--text-faint` `#667080` evaluated; `--accent`, `--green`, `--yellow`, `--red`, `--blue` not verified).
  - **No `focus-visible` needed** (not focusable by default; okay).
- **Line refs:** 10 (label computation), 12 (`aria-label` basic), 9 (`tone` prop default 'gray').

### Card.tsx — **B** (Button role for click, basic aria-label)
- **Strengths:** `role={onClick ? 'button' : undefined}` (line 15), `tabIndex={onClick ? 0 : undefined}` (16), Enter/Space activation (17–22), `aria-label` from title (23).
- **Issues:**
  - **No `aria-describedby`** linking card body/content to title (audit Issue 4 / §4.2 — "Переход в раздел Заказы, 5 новых" needs descriptive linkage).
  - **No `focus-visible` CSS** confirmation for `.card-clickable` (audit Issue 4 / 4.5).
  - **No arrow-key group navigation** for card lists (not required for single card, but `Pipeline` node cards and `KanbanBoard` need it; audit Issue 5 / 17).
  - **Accent prop typed as union** (`'ok' | 'warn' | 'err' | 'info' | 'none' | 'blue' | 'gray'`) — okay but could derive from `Tone` for consistency.
- **Line refs:** 15 (role), 23 (`aria-label` basic), 13 (`className` concatenation).

### Pipeline.tsx — **C** (Arrow navigation placeholder, incomplete focus management)
- **Strengths:** Nodes have `role="button"`, `tabIndex={0}`, `aria-label` with title/subtitle/errors (lines 89–91); `onKeyDown` with ArrowUp/ArrowDown (line 92); funnel rows `role="region"` with aria-label (lines 136–137).
- **Issues:**
  - **Arrow navigation is a placeholder** — `if (e.key === 'ArrowUp' || e.key === 'ArrowDown') { /* placeholder for funnel vertical navigation */ }` (line 153). Audit Issue 5 (§4.1) requires full arrow navigation for Pipeline nodes; this is incomplete.
  - **No focus-visible CSS** for `.pipeline-node` or `.card-clickable` (audit Issues 4, 5, 8, 9, 10).
  - **No `aria-current`** or selection state for active pipeline stage (audit §4.4 region / 2.4.10).
  - **No skip-link verification** inside Pipeline subpages; relies on `Layout` skip-link only.
- **Line refs:** 89–92 (node button), 136–137 (funnel region placeholder), 153 (arrow placeholder comment).

### Table.tsx — **B / C** (Arrow loop with basic querySelector, missing selection state)
- **Strengths:** `<table>`, `<thead>`, `<th>` semantics correct (audit §2 — pass); `onKeyDown` ArrowUp/ArrowDown on `<tbody>` (lines 40–55); `role="button"` + `tabIndex={0}` + Enter/Space for clickable rows (76–84); `aria-label` with selection text (78).
- **Issues:**
  - **Basic `querySelectorAll` loop** for Arrow navigation — `tbody.querySelectorAll('tr.table-row-click')` (line 43), `document.activeElement` (45), `closest('tr.table-row-click')` (46). Not library-based, vulnerable to DOM changes, no `Shift+Tab` loop verification (audit Issue 8 / §4.5).
  - **No `aria-selected` / `aria-current`** for selected row; audit Issue 8 notes interactive rows not fully keyboard accessible.
  - **No `focus-visible`** for `.table-row-click` (audit Issue 8 / 4.5).
  - **No error-boundary** around table rendering; `rowKey` throws if `row` missing key.
- **Line refs:** 43 (`querySelectorAll`), 45 (`document.activeElement`), 46 (`closest`), 72–84 (row click/access), 78 (`aria-label` basic).

### Layout.tsx — **B** (Landmarks/skips/nav improved; dashboard regions missing)
- **Strengths:** Skip-link `<a href="#main" className="skip-link">` (line 111); `<nav aria-label="...">` (121); `NavLink` with `aria-current={active ? 'page' : undefined}` (129); `<main id="main">` (140); `SystemStatusBar` `role="button"` (56) with click to monitoring; `h1` present per audit §2.
- **Issues:**
  - **No region roles / `aria-label` for KPI/dashboard widget groups** — audit §4.4 notes missing `region` for `Overview` cards, `Monitoring` logs, `Billing` sections, `Pipeline` nodes.
  - **No `aria-describedby` for metric value/label linkage** (`.kpi-label` / `.kpi-value`; audit Issue 18).
  - **`sysbar` `role="button"` lacks `aria-label` describing status text** — screen reader may only hear "button" without context of Healthy/Degraded/Error.
  - **No focus-visible** for `.nav-link`, `.user-btn` (audit Issue 9 / 13).
- **Line refs:** 56 (`sysbar` role/button), 111 (skip-link), 121 (nav aria-label), 129 (`aria-current`), 140 (`main` id).

---

## 2. Security Review

Based on `memory/code_audit_summary.md` (§3.1–3.6, §5 Weak Points 1–8, §6 Gaps) and edited artifacts.

### Auth Middleware — **MISSING (Critical)**
- **Evidence:** `Layout.tsx` (line 17 `ROLES`, 20–23 `loadRole`) reads `localStorage` role `zb_role` but does **not** enforce authentication or authorization before rendering `NavLink` items, `SystemStatusBar`, or `Outlet`. There is no `auth` middleware, no `requireAuth` guard, no session token validation.
- **Audit ref:** `code_audit_summary.md` §3.2 — "No auth middleware in `cmd/root.go`; CLI runs with user privileges only." For the UI pipeline (`zarabotok/pipeline_v3/ui/`), the same gap applies: any user with localStorage access can assume `admin` role.
- **Recommendation:** Add `useAuth()` hook with token validation; guard routes (`/billing`, `/agents`, `/monitoring`) behind role checks; encode role server-side, not only `localStorage`.

### Rate Limiting — **MISSING (Important)**
- **Evidence:** `listener_bridge.py` (line 29 `poll_and_link`) has no throttle / token-bucket; `check_releases.py` (line 16 `fetch_releases`) calls GitHub API with `timeout=30` but no retry/backoff/rate guard; `modules/kill_switch.py` (line 23 `is_blocked`) reads file synchronously with no rate limit on writes.
- **Audit ref:** `code_audit_summary.md` §3.6 — "No token-bucket, request throttling, or per-session LLM-rate guard." `release.yml` (line 30 `pytest`) runs without rate-test steps.
- **Recommendation:** Add `ratelimit` decorator to `poll_and_link()` and `fetch_releases()`; enforce `X-RateLimit-Remaining` check; add CI step testing rate-limit behavior.

### Audit Log — **BASIC / INCOMPLETE (Important)**
- **Evidence:** `modules/kill_switch.py` (lines 6–7, 19 `EVENTS_FILE`, 39–55 `set_blocked`) writes to `state/events.json` with basic `{"ts":..., "event":..., "source":..., "detail":...}`. No rotation, no schema validation, no tamper-proofing, no structured audit event types for permission grants, LLM calls, or tool execution (audit §3.4, §5 Weak Point 7).
- **Audit ref:** `code_audit_summary.md` §5.7 — "No structured audit logging." §6 — "Audit logging (security events) — Missing."
- **Recommendation:** Replace JSON append with structured audit schema (`audit_event: {ts, actor, action, resource, result, ip?}`); add log rotation (`logrotate` or `python-logging` rotator); verify JSON integrity via checksum.

### Sandbox / Isolation — **NOT BUILT / NOT VERIFIED (Critical)**
- **Evidence:** `Dockerfile.sandbox` (line 8 `FROM python:3.11-slim`, line 18 `nameserver 127.0.0.1`, line 29 `CMD ["python", "-c", "print(...)"`) exists but **is not referenced in `.github/workflows/release.yml`** (no `docker build` job, no `--network none` verification, no `memory-capped` test). The `COPY --chmod=755` at line 26 uses `|| true`, allowing missing config. Net isolation is only at runtime (`docker run --network none`), never enforced in CI.
- **Audit ref:** `code_audit_summary.md` §3.4 — "Agent/tool execution occurs in-process... No container (`docker`/`podman`), `chroot`, `seccomp`, or subprocess isolation." §6 — "Sandbox / container isolation — Missing." §5.5 — "No container isolation for agent execution."
- **Recommendation:** Add `sandbox` CI job in `release.yml` that builds `Dockerfile.sandbox`, runs with `--network none --memory="1g"`, executes `python script.py`, verifies `DOCKER_ENABLED=1` in output; remove `|| true` from COPY.

### Input Sanitization — **PARTIAL / WEAK**
- **Evidence:** `listener_bridge.py` (lines 12–20) catches import exceptions but does not sanitize `source` (`"tg" | "email"`) before passing to `ls.poll_telegram`. `check_releases.py` (line 13 `API_URL`) uses f-string with `REPO` but no URL validation or allow-list.
- **Audit ref:** `code_audit_summary.md` §3.1 — "Weakness: No visible sanitization of `prompt` string or file paths... `permission.go`: `Params any` untyped."
- **Recommendation:** Validate `source` against allow-list; sanitize `REPO` with regex `/^[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$/`; use `urllib.parse.urlparse` to enforce `https://` and host allow-list.

### Kill-Switch / Timeout — **PARTIAL**
- **Evidence:** `kill_switch.py` (lines 23–35 `is_blocked`, 37–55 `set_blocked`) implements file-based block, but **no execution timeout per agent call** (audit §3.5, §6 — "Kill-switch / execution timeout per agent call — Missing"). `context.WithCancel` exists in `opencode-src/cmd/root.go` but no `context.WithTimeout` enforced at agent/tool level.
- **Recommendation:** Add `context.WithTimeout(30*time.Second)` around `poll_and_link()` and agent execution; enforce `SIGTERM` handler for graceful abort.

---

## 3. Test Coverage Gaps

Based on `memory/code_audit_summary.md` (§4 — minimal test files, no `tests/` folder inside `opencode-src/`), `accessibility_audit_summary.md` (§3.A, §3.C — no automated axe-core output, no screen-reader transcript, no keyboard-trap verification), and edited file inspection.

### Accessibility / Keyboard / Focus Tests — **NONE ADDED (Critical Gap)**
- **Evidence:** No `test_modal_accessibility.py`, `test_table_arrow.py`, `test_focus_trap.py`, or `test_drawer_keyboard.py` created or edited. Existing `zarabotok/pipeline_v3/test_api*.py` files (30.08 21:15) test API only, not UI components.
- **Audit refs:** `accessibility_audit_summary.md` §3.A — "No keyboard-trap / focus-loop verification report." §4.1 — needs systematic `focus-visible` CSS verification; §4.5 — focus management needs verification with `Shift+Tab` from first/last element.
- **Recommendation:** Add Jest/React Testing Library tests for `Modal` (Escape, Tab loop, focus restoration, aria-labelledby), `Drawer` (same), `Table` (ArrowUp/Down, Enter activation, focus restoration), `Pipeline` (Arrow navigation, role/button), `Layout` (skip-link visibility on focus, `aria-current` announcement). Include `axe-core` (`jest-axe`) run in CI.

### Workflow / CI Tests — **NO ACCESSIBILITY OR RATE TESTS (Important)**
- **Evidence:** `.github/workflows/release.yml` (lines 18–30 `test` = `pytest` only; 32–45 `vuln-scan`; 47–56 `sbom`; 58+ `build-sign-release`) has **no** `axe-core`, `keyboard-navigation`, `accessibility`, or `rate-limit` steps.
- **Audit refs:** `accessibility_audit_summary.md` §4.1 / §4.7 / §4.8 — recommendations for CI inclusion.
- **Recommendation:** Add `accessibility` job running `axe-cli` or `pa11y` against build output; add `rate-limit` test verifying `fetch_releases` respects GitHub limits; add `sandbox` build + run job.

### Component Unit Tests — **NONE FOR EDITED COMPONENTS**
- **Evidence:** `Modal.tsx`, `Drawer.tsx`, `Toast.tsx`, `Badge.tsx`, `Card.tsx`, `Pipeline.tsx`, `Table.tsx`, `Layout.tsx` have zero corresponding `*.test.tsx` files. `py.test` runs on `zarabotok/pipeline_v3/` but hangs/timeouts (120s+) — likely due to API tests or missing fixtures.
- **Recommendation:** Write `Modal.test.tsx` (focus trap, Escape, overlay click, aria-modal); `Drawer.test.tsx`; `Table.test.tsx` (keyboard navigation); `Layout.test.tsx` (skip-link focus, nav active state).

### Security Tests — **NONE FOR KILL-SWITCH / LISTENER / RELEASE**
- **Evidence:** No tests for `is_blocked()` / `set_blocked()` correctness; no `listener_bridge.poll_and_link()` exception path tests; no `verify_release.py` integration with `release.json`; no `check_releases.py` HTTP error / timeout test.
- **Recommendation:** Add `test_kill_switch.py`, `test_listener_bridge.py`, `test_check_releases.py` with `responses`/`unittest.mock` mocking.

---

## 4. Refactoring Recommendations

Ordered by impact / premium-quality improvement. All recommendations reference `memory/accessibility_audit_summary.md` and `memory/code_audit_summary.md` recommendations.

### 4.1 Extract Focus Manager (High Impact)
- **Problem:** Modal (line 11 comment, 22–60) and Drawer (line 10, 25–50) duplicate manual `querySelectorAll` + `Tab` loop logic.
- **Solution:** Create `hooks/useFocusTrap.ts` using `focus-trap-react` or a lightweight custom hook with `first` / `last` refs, `Tab` interception, and `Shift+Tab` loop. Apply to both components; remove inline `querySelectorAll`.
- **Audit alignment:** §4.5 — "Focus-lock implementation (focus first focusable / modal title; loop on `Tab`; restore on close)."

### 4.2 Add Unit Tests for Arrow Navigation (Medium-High)
- **Problem:** `Table.tsx` (43–55) and `Pipeline.tsx` (92, 153) implement Arrow navigation with basic selectors; untested.
- **Solution:** Write `Table.test.tsx` using React Testing Library `fireEvent.keyDown` with `ArrowDown`; assert `document.activeElement` moves to next row. Write `Pipeline.test.tsx` for node arrow keys (when complete).
- **Audit alignment:** §4.1 — "Systematic `focus-visible` CSS for every interactive component... Arrow-key navigation for `Tabs`; `Space` activation..."

### 4.3 Improve Type Safety in .tsx Props (Medium)
- **Problem:** Some props use loose types (`className?: string`, `accent?: 'ok' | ...`). `Pipeline.tsx` `Block` interface (line 9–15) is okay but `onRowClick?: (row: T) => void` could use stricter generic constraints.
- **Solution:** Derive `Tone` from `../lib/types` consistently; use `React.FC` with `PropsWithChildren`; add `React.Arrow` types for event handlers; avoid `any` in `Table.tsx` row casts (`String((row as Record<string, unknown>)[...])` at line 88).
- **Audit alignment:** `code_audit_summary.md` §3.1 — "`Params any` untyped; could carry arbitrary JSON payload."

### 4.4 Add Error Boundary (Medium)
- **Problem:** No `ErrorBoundary` around `Pipeline`, `Table`, `Card`, or `Layout`. A faulty `rowKey` or `metrics.data?.throughput_per_stage` access could crash SPA.
- **Solution:** Add `ErrorBoundary` component (`components/ErrorBoundary.tsx`) with `getDerivedStateFromError`; wrap `Outlet` in `Layout` and page components.
- **Audit alignment:** `code_audit_summary.md` §3.5 — panic recovery exists in Go CLI (`RecoverPanic`) but UI has none.

### 4.5 Add `aria-describedby` to Modal / Drawer (Medium)
- **Problem:** Modal `aria-labelledby="modal-title"` (line 72) links title but body content not described.
- **Solution:** Generate `body-id` (`id={`modal-body-${instanceId}`}`) and add `aria-describedby={bodyId}`.
- **Audit alignment:** §4.2 — "`aria-label` / `aria-describedby` verification for `Card`; `aria-live` verification for `Toast`."

### 4.6 Implement Reduced-Motion CSS (Medium)
- **Problem:** `styles.css` (not edited, but audit Issue 12 lines 255–278) missing `@media (prefers-reduced-motion: reduce)`; edited components add animation-prone elements (`toast-in`, `.btn-spinner`, `.card-clickable` transition) without guards.
- **Solution:** Add block to `styles.css` (or component-level `media` queries): disable `animation` / reduce `transition-duration` to `0.01ms` for `.btn-spinner`, `.toast`, `.card-clickable`, `.modal`, `.drawer`.
- **Audit alignment:** §4.7 — "Add `@media` block to `styles.css` (line 269–275 recommended)."

### 4.7 Add Skip-Link Focus Visibility (Low-Medium)
- **Problem:** `Layout.tsx` skip-link (line 111) exists but CSS visibility on focus not verified in edited file.
- **Solution:** Confirm `.skip-link` is `position: absolute; top: -40px;` and `left: 0;` with `:focus` bringing to `top: 0`; verify keyboard-only users can access.
- **Audit alignment:** §4.6 — "Add `skip-link` component to `Layout` ... verify visible on `focus`, hidden otherwise."

---

## 5. Technical Debt List (File / Line References)

All items include severity (**S** = Security / Critical, **A** = Accessibility / AA, **Q** = Code Quality / Maintainability), the file/line, outstanding issue, and recommended action.

| # | File | Line(s) | Severity | Issue | Action |
|---|---|---|---|---|---|
| 1 | `Modal.tsx` | 11, 22–24, 50–60 | A / Q | Manual focus-trap loop; no library | Extract `useFocusTrap`; replace `querySelectorAll` |
| 2 | `Modal.tsx` | 72, 77 | A | Static `modal-title` ID; duplicate risk | Dynamic `id={{\`modal-title-${uid}\`}}` |
| 3 | `Modal.tsx` | 64 | A | Hardcoded Russian `aria-label` on overlay | Use localized string / `aria-label={t('overlay')}` |
| 4 | `Drawer.tsx` | 10, 25, 35–50 | A / Q | Same manual loop; missing restoration | Add `prevFocusedRef`; reuse `useFocusTrap` |
| 5 | `Drawer.tsx` | 61, 66 | A | Static `drawer-title` ID | Dynamic id |
| 6 | `Drawer.tsx` | — | A | No `aria-describedby` for drawer body | Add `aria-describedby` to content |
| 7 | `Toast.tsx` | 28–31, 40 | A | All toasts `polite`; errors need `assertive`; no dismiss | Condition `aria-live={type==='err'?'assertive':'polite'}`; add close button |
| 8 | `Toast.tsx` | — | A | No reduced-motion guard | Add `@media (prefers-reduced-motion)` |
| 9 | `Badge.tsx` | 12 | A | `aria-label` misses tone announcement | Include tone: `aria-label={\`${label}, статус ${tone}\`}` |
| 10 | `Badge.tsx` | 9, 12 | A | Contrast for tone colors unverified | Audit all `badge-${tone}` combos vs `#0e1014` / `--panel` |
| 11 | `Card.tsx` | 15, 23 | A / Q | `aria-label` basic; no `aria-describedby` | Add `id={bodyId}` + `aria-describedby` |
| 12 | `Card.tsx` | 13 | Q | `className` string concat; no `clsx` | Use `clsx` / `tailwind-merge` for premium polish |
| 13 | `Pipeline.tsx` | 89–92 | A | Node button okay but no arrow-key completion | Complete ArrowUp/Down navigation; add `focus-visible` |
| 14 | `Pipeline.tsx` | 153 | A / Q | Arrow navigation placeholder (`/* placeholder */`) | Implement full vertical arrow loop for funnel rows |
| 15 | `Pipeline.tsx` | 136–137 | A | Funnel `role="region"` okay but placeholder for navigation | Add `aria-labelledby` to region; complete keyboard nav |
| 16 | `Table.tsx` | 43, 45–46 | A / Q | Basic `querySelectorAll` + `document.activeElement` / `closest` | Replace with `useArrowNav` hook using refs |
| 17 | `Table.tsx` | 72–84 | A | No `aria-selected` / `aria-current` for clicked row | Add `aria-selected` when `onRowClick` active |
| 18 | `Table.tsx` | 88 | Q | `String((row as Record<string, unknown>)[...])` cast | Stronger generic render type; avoid `unknown` |
| 19 | `Layout.tsx` | 56 | A | `sysbar` `role="button"` without context label | Add `aria-label={\`Статус системы: ${label}\`}` |
| 20 | `Layout.tsx` | 111 | A / Q | Skip-link exists; visibility unverified | Confirm CSS `:focus`; add test |
| 21 | `Layout.tsx` | 121, 129, 140 | A | Nav/landmarks improved; dashboard regions still missing | Add `section aria-label="..."` to KPI cards / metrics |
| 22 | `Layout.tsx` | — | A / Q | No `region` roles for `Overview`, `Pipeline`, `Billing` | Add `<section aria-label={...}>` wrappers |
| 23 | `Dockerfile.sandbox` | 26, 29 | S / Q | `COPY ... || true` weak; `CMD` only prints | Remove `|| true`; add `python script.py` validation |
| 24 | `.github/workflows/release.yml` | 30, 58+ | S / A | No accessibility / sandbox / rate tests | Add `accessibility`, `sandbox`, `rate-limit` jobs |
| 25 | `modules/kill_switch.py` | 19, 39–55 | S | Basic JSON audit; no rotation / tamper-proofing | Structured schema + rotation + checksum |
| 26 | `modules/kill_switch.py` | 23–35 | S | File read synchronous; no rate limit on writes | Add file-lock / timestamp throttle |
| 27 | `modules/listener_bridge.py` | 12–20 | S | Import exception swallowed; no input sanitization | Validate `source`; sanitize imports; raise on unknown |
| 28 | `modules/listener_bridge.py` | 29–40 | S | No rate limit / timeout on `poll_and_link` | Add `ratelimit`; enforce `timeout=10` |
| 29 | `check_releases.py` | 13, 16–30 | S | `API_URL` f-string; no rate/backoff; `timeout=30` only | Add URL allow-list; retry with `urllib` backoff; rate check |
| 30 | `check_releases.py` | 38+ | S / Q | `main()` no auth / token verification | Add `GITHUB_TOKEN` check if private repo access needed |
| 31 | `scripts/verify_release.py` | 10–124 | Q | SHA256 check present; no SBOM verification test | Add SBOM presence + tag comparison asserts |
| 32 | `opencode-src/` | `.goreleaser.yml` only | Q | Only `.goreleaser.yml` edited (31.08 2:37); no `cmd/`, `internal/`, `main.go` changes | Verify build/sign settings; no source regression |

---

## 6. Comparison with Audit Recommendations

| Audit Recommendation (Source Line / Section) | Edited File Status | Gap / Note |
|---|---|---|
| Focus-trap library-based (`accessibility_audit_summary.md` §4.5, Issue 1) | `Modal.tsx` 22–60, `Drawer.tsx` 25–50 — basic loop, not library | **Partial** — loop works but is manual; needs library extraction |
| Arrow navigation for `Tabs` / `Table` (`§4.1`, Issue 8, 10) | `Table.tsx` 40–55 — basic `querySelectorAll`; `Pipeline.tsx` 153 — placeholder | **Partial / Incomplete** — Table works for basic case; Pipeline unfixed |
| `aria-label` / `aria-describedby` (`§4.2`) | `Badge.tsx` 12 added; `Card.tsx` 23 basic; `Modal/Drawer` missing body desc | **Partial** — Badge improved; others still basic |
| `focus-visible` for all interactive (`§4.5`) | No `focus-visible` CSS added to edited `.tsx` files | **Missing** — depends on `styles.css` not edited |
| Skip links (`§4.6`) | `Layout.tsx` 111 added | **Pass** — skip-link present; verify CSS visibility |
| `aria-current="page"` (`§4.2`, Issue 9) | `Layout.tsx` 129 added | **Pass** — NavLink has it |
| Color contrast audit (`§4.3`, Issue 11) | No contrast fixes in `Badge.tsx` or `Pipeline.tsx` | **Missing** — only `accessibility_audit_summary.md` notes `--text-faint` failing |
| Reduced-motion (`§4.7`, Issue 12) | No `@media` added to edited files or `styles.css` | **Missing** |
| Error identification (`§4.8`, 3.3.1) | No `aria-invalid` / `aria-describedby` added to forms in edited files | **Missing** — `LLMFilter`, `Task`, `Orders` not in edit set |
| Auth middleware (`code_audit_summary.md` §3.2, §6) | `Layout.tsx` `loadRole()` localStorage only; no middleware | **Missing** — critical security gap |
| Rate limit (`§3.6`, §6) | `listener_bridge.py`, `check_releases.py` unthrottled; `release.yml` no test | **Missing** |
| Sandbox build / verification (`§3.4`, §5.5, §6) | `Dockerfile.sandbox` exists; `release.yml` no build/run | **Not built / verified** |
| Structured audit log (`§3.4`, §5.7, §6) | `kill_switch.py` basic JSON; no rotation / schema | **Basic only** |
| Unit / integration tests (`§4`, §6) | No new `.test.tsx` or `.py` tests for edited components / workflow | **Missing** |
| Binary / build verification (`§5.3`, §5.6) | `opencode.exe` present; `.goreleaser.yml` edited only | **Not verified** — binary unsigned; CI build only |

---

## 7. Premium Craftsmanship Notes (EngineeringSeniorDeveloper)

- **Glass / premium feel:** The UI uses dark theme (`--bg` `#0e1014`) with good main contrast (`--text` `#e7eaf0` ≈ 15:1). If premium luxury is the goal, consider adding `backdrop-filter: blur(12px)` to `.modal` and `.drawer` overlays with `rgba(255,255,255,0.03)` borders — already partially present via `overlay` class but could be refined.
- **Animation discipline:** All new interactive elements (`Card` clickable, `Toast` enter, `Badge` tone change) must respect `prefers-reduced-motion`; otherwise premium experience becomes inaccessible. Add CSS now, not later.
- **Typography scale:** `Layout` nav, `Card` title, and `Pipeline` node labels should verify `h1` → `h2` hierarchy inside cards; currently `Card` uses `.card-title` (div, not heading) — consider `h3` with `aria-labelledby` linkage.
- **Performance:** Manual `querySelectorAll` loops in `Modal`/`Drawer`/`Table` run on every `Tab`. For large tables / nested modals, this creates O(n) DOM scanning per key event. Replacing with refs and a `useFocusTrap` hook removes DOM scanning and improves 60fps guarantee.
- **Error boundary premium:** A luxury UI never crashes. Adding `ErrorBoundary` with graceful fallback (e.g., `"Ошибка загрузки раздела"` with retry button) protects the experience.

---

## 8. Action Checklist (Immediate → Short-Term → Long-Term)

**Immediate (this session / next commit):**
- [ ] Replace `Modal.tsx` / `Drawer.tsx` manual loops with `useFocusTrap` hook.
- [ ] Add `aria-describedby` to Modal/Drawer bodies; make IDs dynamic.
- [ ] Add `focus-visible` CSS rules to `styles.css` for `.modal`, `.drawer`, `.table-row-click`, `.pipeline-node`, `.card-clickable`, `.nav-link`.
- [ ] Complete `Pipeline.tsx` ArrowUp/ArrowDown placeholder (line 153) — implement full loop.
- [ ] Replace `Table.tsx` `querySelectorAll` Arrow loop with ref-based `useArrowNavigation`.
- [ ] Add `@media (prefers-reduced-motion: reduce)` to `styles.css`.

**Short-Term (next sprint):**
- [ ] Write `Modal.test.tsx`, `Drawer.test.tsx`, `Table.test.tsx`, `Layout.test.tsx` with React Testing Library + `axe-core`.
- [ ] Add `accessibility` CI job to `.github/workflows/release.yml`; include `axe-cli` or `pa11y`.
- [ ] Add `sandbox` build + verify job to workflow; build `Dockerfile.sandbox`; test `--network none`.
- [ ] Implement `useAuth()` and guard `Layout` routes (`/billing`, `/agents`, `/monitoring`) behind role server-validation; remove `localStorage`-only trust.
- [ ] Add `ratelimit` to `listener_bridge.poll_and_link()` and `check_releases.fetch_releases()`.
- [ ] Replace `kill_switch.py` basic JSON with structured audit schema + rotation.

**Long-Term (architecture / premium):**
- [ ] Extract all focus / keyboard / ARIA logic into reusable `components/accessibility/` (FocusTrap, ArrowNav, LiveRegion, SkipLink, RoleGuard).
- [ ] Add error boundaries to all page components.
- [ ] Integrate `react-focus-lock` / `focus-trap-react` as dependency; remove all manual loops.
- [ ] Conduct screen-reader verification (NVDA / VoiceOver) per audit recommendation (`accessibility_audit_summary.md` §3.B, line 449).
- [ ] Verify all color tokens (`--accent`, `--green`, `--yellow`, `--red`, `--blue`) against backgrounds for 4.5:1 AA.

---

*Review completed per `ai/agents/dev.md` methodology: task analysis, premium enhancement planning, quality assurance (every interactive element checked), innovation integration (focus management, accessibility, security), and documentation of technical debt with exact file/line references.*

*Memory update: this review captured audit-to-code comparison, identified 32 technical-debt items, confirmed 4 security gaps (auth, rate, audit, sandbox), noted 5 accessibility partial-fixes with 3 missing (focus-visible, reduced-motion, error-boundary), and produced an executable checklist aligned with premium craftsmanship standards (60fps, glass morphism, smooth transitions, accessibility AA).*