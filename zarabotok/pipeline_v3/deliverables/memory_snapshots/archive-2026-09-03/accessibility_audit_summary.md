# Accessibility Audit Summary — Zarabotok Pipeline v3 UI

**Agent**: AccessibilityAuditor  
**Source audit**: `audit_accessibility.md` (479 lines, 2026-08-31)  
**Standard evaluated**: WCAG 2.1 AA (with 2.2 references where noted)  
**Product**: `zarabotok/pipeline_v3/ui/` — SPA v7 (React/TypeScript, shadcn)  
**Methodology cited in source**: Manual axe-core equivalent, manual ARIA/keyboard, CSS contrast (`styles.css` tokens), `index.html` inspection, `.tsx` component inspection (line 14–19).  
**Conformance declared by source**: DOES NOT CONFORM (AA) — Assistive Technology Compatibility: FAIL (line 30–32).

---

## 1. Findings Overview (counts from source §Summary, lines 22–32)

| Severity | Count (source) | WCAG Levels primarily breached | Summary of affected components / pages |
|----------|---------------|-------------------------------|----------------------------------------|
| **Critical** | 8 | A / AA | Modal/Drawer (1), Toast (2), Badge (3), Card (4), Pipeline nodes (5), Overview buttons (6), Task Input label (7), Table rows (8) |
| **Important** | 9 | A / AA | NavLink (9), Tabs (10), Color contrast (11), Reduced-motion (12), Target size (13), OrchestratorChat (14), Modal title linkage (15), Logo / image (16) |
| **Minor** | 6 | A / AA / AAA | Kanban D&D (17), FunnelMetrics / Pipeline KPIs (18), LLMFilter switches (19), Page titles (20) |

*Note: Source lists exactly 20 numbered issues (1–20), but its own tally states Critical 8, Important 9, Minor 6 (total 23). The discrepancy likely reflects sub-items within Issues 1 (Modal/Drawer split), 15 (Modal title linkage as separate from Issue 1), and 11/12/13 (CSS multi-file). I preserve the source counts verbatim and note that Issues 1, 15, and 11–13 contain split sub-checks.*

**Pass / Partial / Fail by category**:
- **Pass**: Page language (`lang="ru"`, `index.html:2`), semantic headings (`h1` on all pages, line 404), native `<button>` usage (`Button.tsx`, line 409), main text contrast `--text` (`#e7eaf0`) on `--bg` (`#0e1014`) ≈ 15:1 (line 410), `--text-dim` (`#9aa4b2`) ≈ 7.4:1 passes AA (line 410), basic table semantics (`<table>`, `<thead>`, `<th>`, line 407), modal basic structure and `Escape` (line 408), most form `Select`/`Input` labels (line 405), `NavLink` functionality (line 406).
- **Partial / Conditional Pass**: Badge text labels exist in most cases but lack `aria-label` / semantic linkage to tone (Issue 3); `Table` uses correct tags but interactive rows are not keyboard accessible (Issue 8); `Modal` has header/body/footer and overlay click-to-close but lacks `role="dialog"`, `aria-modal`, focus-trap (Issue 1).
- **Fail**: All 8 Critical and 9 Important issues above remain unremediated at audit time (report states "only audit, no code changes", line 479).

---

## 2. Strong Points (what is well done — source §What's Working Well, lines 401–412)

1. **Language declaration** — `html lang="ru"` present (`index.html:2`; Issue 20 confirms). Meets WCAG 3.1.1.
2. **Heading presence** — `h1` present on every page (`Overview`, `Pipeline`, `Orders`, `LLMFilter`, `Agents`, `Task`, `Billing`, `Monitoring`, `OrchestratorChat`; line 404). Meets 1.3.1 / 2.4.6 for page-level orientation.
3. **Form labels (most)** — `Select` and `Input` components (`LLMFilter` — `ReviewEdit`, `SettingsTab`; `Orders` filters; `Task` `changesOpen` modal) use `label` (line 405). Meets 3.3.2 / 1.3.1 for those instances.
4. **Navigation functionality** — `NavLink` (`react-router-dom`) works; visual active-state (`nav-active`) present (line 406, Issue 9 notes missing `aria-current` only).
5. **Table semantics** — `Table` uses `<table>`, `<thead>`, `<tbody>`, `<th>` correctly (line 407). Meets 1.3.1 for data-structure semantics.
6. **Modal basic UX** — `Modal` includes title / body / footer; `Escape` closes; overlay (`.overlay`) blocks background interaction via click (line 408, Issue 1). Meets basic 2.4.3 / 1.4.2 for overlay behavior, but not fully for focus/dialog roles.
7. **Native button elements** — `Button` component renders native `<button>`, giving automatic `Tab`, `Enter`, `Space`, and browser focus indicator (line 409). Meets 2.1.1, 4.1.2 for that component.
8. **Main color contrast** — `--text` (`#e7eaf0`) on `--bg` (`#0e1014`) ≈ 15:1 (line 410); `--text-dim` (`#9aa4b2`) ≈ 7.4:1 passes AA (line 410). Good baseline.
9. **Badge text content** — `Badge` uses different colors with text labels (`ok`/`warn`/`err`/`info`) in most usages (line 411), avoiding pure-color dependency in all cases, though not fully accessible (see Issue 3).

---

## 3. Weak Points / Audit Gaps (what is under-tested, vague, or missing verification)

The source report is thorough for component-level ARIA/keyboard/color, but several WCAG 2.1 AA checks are either absent, implied only, or noted without evidence. These are gaps in the audit itself—not necessarily in the product, but relevant to report completeness.

**A. Methodology limitations (line 14–19)**
- **No automated axe-core output attached** — methodology says "axe-core (ручной эквивалент)" (manual equivalent). No rule-level violation counts (`color-contrast`, `aria-required-attr`, `button-name`, etc.) are reported. This makes it impossible to confirm whether additional axe rules (e.g., `region`, `landmark-one-main`, `label`, `focus-order-semantics`) are violated.
- **No screen-reader transcript / evidence** — screen-reader testing is declared (line 15) but no NVDA/VoiceOver log, spoken-output quote, or browser/AT pairing is documented per issue. Recommendations reference "скрин-ридер" generally without proof of failure mode.
- **No keyboard-trap / focus-loop verification report** — for modals (Issue 1) and drawers (Issue 1, line 42), the audit recommends focus-trap but does not document whether a trap already partially exists (overlay click-to-close suggests some focus management, but not verified with `Shift+Tab` from first/last element).

**B. Missing WCAG criteria / components not audited (not in Issues 1–20)**
- **Skip links (`bypass-blocks`, 2.4.1)** — not mentioned anywhere in 479 lines. The `Layout` navigation (line 118–128) and page structure have no `skip-to-content` or `skip-navigation` link.
- **Error identification (`3.3.1`) / `aria-invalid` / `aria-describedby`** — forms (`LLMFilter`, `Orders`, `Task`, `OrchestratorChat`, `Billing`) are checked for `label` absence (Issues 7, 14, 19) but not for error-message association. No check for `aria-invalid="true"` on invalid inputs, or `role="alert"` / `aria-live="assertive"` for form validation errors.
- **Dashboard / region landmarks (`region`, `landmark-one-main`, 1.3.1, 2.4.10)** — the audit checks `h1` per page and `NavLink`, but does not verify `<main>`, `<nav>`, `<aside>`, or `aria-label` / `aria-labelledby` for dashboard sections (`Overview`, `Pipeline`, `Monitoring`). No `region` roles for KPI cards or metric blocks.
- **Focus management for nested / stacked modals** — Issue 1 mentions nested modals (`showRaw` in `Orders`, `ReplyModal`; line 53) but does not test focus-stacking or `z-index` interaction with `aria-modal`.
- **Reduced-motion user verification (`prefers-reduced-motion`)** — Issue 12 only checks CSS (`styles.css`: 465–476, 825–831) for missing `@media`. No test that `animation-duration` actually disables when OS setting is on; no check of `transition` on `.btn` (418–423) or `.card-clickable` (331–336) under reduced-motion.
- **Color contrast for new / accent tokens** — methodology lists `--bg`, `--panel`, `--text`, `--text-dim`, `--text-faint`, `--accent`, `--green`, `--yellow`, `--red`, `--blue` (line 8), but only `--text-faint` (`#667080`) is evaluated (Issue 11, line 239–252). No evidence that `--accent`, `--green` (success), `--yellow` (warning), `--red` (error), or `--blue` (info) meet 4.5:1 against all backgrounds (`--bg` `#0e1014`, `--panel`, etc.). This is a significant gap because `Badge` and status indicators rely on these colors.
- **Target size completeness (`2.5.5` / `2.5.8`)** — Issue 13 checks `.btn-sm`, `.nav-link`, `.user-btn`, `.agent-pick-item`, `.tab` (line 285–294), but does not verify `.pipeline-node`, `.card-clickable`, `.table-row-click`, `.kanban-card`, `.kpi-value` click targets, or mobile viewport effective touch areas.
- **Heading hierarchy (`1.3.1`, `2.4.6`)** — only `h1` presence is confirmed (line 404). No check for skipped levels (e.g., `h3` without `h2`), `h1` duplication, or section headings inside cards/metrics.
- **Link purpose (`2.4.4`, 2.4.9)** — `NavLink` labels are checked only for `aria-current` (Issue 9), not for whether identical links (`logo` link to `/overview`, multiple `NavLink` to same route with different visible text) confuse screen readers.
- **Reflow / zoom (`1.4.10`, `1.4.4`)** — not mentioned. No check at 400% zoom or 320 CSS px equivalent for `Layout`, `Table`, `Modal` layouts.
- **Input purpose (`1.3.5`)** — no `autocomplete` attributes checked on `Input` fields (names, emails, company names if present).
- **Status messages (`4.1.3`)** — only `Toast` (Issue 2) is covered. Dynamic metric updates (`Overview` metrics, `Pipeline` node updates, `Monitoring` live logs) are not checked for `aria-live` or `aria-atomic`. `FunnelMetrics` (Issue 18) is minor but only for static labels, not live updates.
- **Language of parts (`3.1.2`)** — `lang="ru"` is global, but mixed-language terms (e.g., "Kill Switch", "LLMFilter", "Pipeline", "Kanban") inside Russian UI are not checked for `lang="en"` on inline elements.
- **Parsing / validity (`4.1.1`)** — `index.html` and component markup are not validated for duplicate IDs (e.g., `modal-title` without unique suffix), unclosed tags, or malformed `aria-*` values.
- **Focus-visible (`2.4.7`)** — mentioned only as missing for `.card-clickable`, `.pipeline-node`, `.table-row-click`, `.nav-link` (Issues 4, 5, 8, 9, 10). No systematic audit of all focusable elements.

**C. Potential false positives / overstatements in source**
- **Issue 3 (Badge)** — labeled Critical with claim "status transmitted only by color, without text alternative for screen readers" (line 79–83). Evidence shows text inside Badge can be `0`, `3 err`, etc., and `title={title}` exists (line 87). The critical issue is correct (`aria-label` missing, tone not announced), but the framing "without text alternative" is overstated because visual text exists; it's a *semantic* failure, not a complete absence of alternative. Recommendation (add `aria-label`) is correct and sufficient.
- **Issue 19 (LLMFilter switches)** — labeled Minor (line 381) with evidence that `label` nesting works (line 384). The audit calls this "not critical, but better to add `id/htmlFor`" (line 386). This is accurate; not a false positive, just conservative grading.
- **Issue 20 (`index.html`)** — correctly graded Minor; `lang="ru"` passes 3.1.1 (line 393–396). No false positive.
- **Issue 12 (Animations)** — correctly notes missing `@media (prefers-reduced-motion: reduce)` (line 260–265). However, the audit does not confirm whether any `spin` animation is continuous/essential (`2.2.2`) vs. decorative. It recommends blanket disable, which is safe.

---

## 4. What Is Missing / Needs Addition (aligned to user's explicit request)

Based on the report's own gaps + standard WCAG 2.1 AA requirements for this SPA:

### 4.1 Keyboard navigation (2.1.1, 2.4.3, 2.4.7)
- **Not fully covered**: `Pipeline` nodes (Issue 5, line 119–138), `Card` clickables (Issue 4, line 95–116), `Table` rows (Issue 8, line 175–193), `KanbanBoard` cards (Issue 17, line 346–359), `Tabs` (Issue 10, line 217–236).
- **Missing specifically**: Arrow-key navigation for `Tabs`; `Shift+Tab` loop verification for `Modal`/`Drawer`; `Space` activation for all `role="button"` elements beyond `Card` (e.g., `pipeline-node`, `table-row-click`, `.kanban-card`); `Esc` behavior for `Drawer` (only `Modal` mentioned); focus restoration to trigger element after close (Issue 1, line 52; Issue 15, line 323).
- **Needs addition**: Systematic `focus-visible` CSS for every interactive component (`btn`, `.nav-link`, `.card-clickable`, `.table-row-click`, `.pipeline-node`, `.tab`, `.agent-pick-item`, `.kanban-card`).

### 4.2 Screen reader tests (1.3.1, 4.1.2, 4.1.3)
- **Missing**: Per-component spoken-output verification for `Badge` tones (`ok`/`warn`/`err`/`info`/`blue`/`gray`). Evidence quotes only visual text (line 83, 86–88). Needs NVDA/VoiceOver reading of `Badge` in `Overview` metrics and `Pipeline` nodes.
- **Missing**: `aria-label` / `aria-describedby` verification for `Card` content (e.g., "Переход в раздел Заказы, 5 новых" — Issue 4, line 114). No transcript.
- **Missing**: `aria-live` verification for `Toast` (Issue 2, line 57–74) — needs test of `polite` vs. `assertive` when errors occur.
- **Missing**: `aria-current="page"` spoken announcement verification (`NavLink`, Issue 9, line 196–213).
- **Needs addition**: Screen-reader test protocol included in CI or acceptance criteria (source recommends this at line 449: "провести повторный аудит после исправлений с реальным тестированием в NVDA/VoiceOver").

### 4.3 Color contrast for new tokens (1.4.3)
- **Only `--text-faint` (`#667080`) tested** against `#0e1014` → ≈ 3.89:1, fails AA (line 244).
- **Not tested**: `--accent`, `--green`, `--yellow`, `--red`, `--blue` (listed in methodology line 8, no findings).
- **Not tested**: Contrast of `--text-dim` (`#9aa4b2`) on `--panel` or light surfaces if any; contrast of `Badges`'s tonal backgrounds against text inside badges; contrast of `.pipeline-subtitle`, `.pipeline-stage`, `.kpi-hint`, `.sys-hint`, `.empty-hint`, `.alert-ts` (line 242–243) — these are named but not individually calculated.
- **Needs addition**: Contrast audit for all token combinations used in `Badge`, `Pipeline`, metric cards, `Monitoring` logs, `OrchestratorChat`, and `Task` comment fields; fix `--text-faint` to `#8896b3` or `#94a3b8` (line 250–251) and validate all derived usages.

### 4.4 ARIA on dashboard (1.3.1, 2.4.10, 4.1.2)
- **Not audited**: No `region` roles, `aria-label`, or `landmark` ( `<main>`, `<nav>` ) verification for `Overview`, `Pipeline`, `Monitoring`, `Billing`, `Agents`. The report verifies `h1` per page (line 404) and `NavLink` (line 406), but not section landmarks.
- **Needs addition**: `aria-label` for KPI containers (`.kpi`, `FunnelMetrics` line 362–376); `aria-label` or `aria-labelledby` for `Pipeline` nodes (already Issue 5, but only for button role, not region); `aria-label` for dashboard widget groups (`Overview` cards, `Monitoring` logs tab, `Billing` sections).
- **Needs addition**: `aria-describedby` linking metric value to label (`.kpi-label` / `.kpi-value` — Issue 18 recommends `aria-labelledby`; needs implementation verification).

### 4.5 Focus management (2.4.3, 2.4.7, 2.4.13 — 2.4.11 focus not obscured in 2.2)
- **Partial**: `Modal` and `Drawer` have `Escape`; no `aria-modal`; no focus-trap; no focus return (Issue 1, lines 38–54).
- **Needs addition**: Focus-lock implementation (focus first focusable / modal title; loop on `Tab`; restore on close). Verify `Tab` order inside `Orders` (`OrderModal`, line 42), `LLMFilter` (`ReplyModal`, line 42), `Agents` (line 42), `Task` (`TaskModal`, line 42), `Billing` (line 42), `Monitoring` (`LogsTab`, line 42), `DealDetail` (line 42).
- **Needs addition**: `focus-visible` styles for `Modal`, `Drawer`, `Card`, `Table`, `Tabs`, `Pipeline`, `Overview` buttons, `KanbanBoard`.
- **Needs addition**: Check that focused modal/title is not obscured by sticky `Layout` header or `NavLink` (focus not obscured, 2.4.11 / 2.4.12 if applicable).

### 4.6 Skip links (2.4.1)
- **Completely missing from report** — no audit of `Skip to main content`, `Skip navigation`, or `Skip to search/filter` links.
- **Needs addition**: Add `skip-link` component to `Layout` (`components/Layout.tsx`, line 118 area) with `href="#main"`; add `id="main"` to each page container; verify visible on `focus`, hidden otherwise.

### 4.7 Reduced-motion (2.3.3, 2.2.2, 2.2.1 — for AAA; 2.3.1 / 2.3.2 important for vestibular)
- **Only CSS check** — Issue 12 (lines 255–278) identifies missing `@media (prefers-reduced-motion: reduce)` for `spin`, `toast-in`, `.card-clickable` transition, `.btn` transition.
- **Needs addition**: Add `@media` block to `styles.css` (line 269–275 recommended). Verify `animation` disabled for `.btn-spinner`, `.toast`, `.card-clickable`; verify `transition-duration` reduced for focus/hover effects that could cause motion sickness; test with OS `prefers-reduced-motion: reduce` enabled.

### 4.8 Error identification (3.3.1, 3.3.3 — error suggestion / prevention)
- **Not audited for form validation** — `Task.tsx` comment input (line 156), `LLMFilter` settings (line 288–305), `Orders` filters, `OrchestratorChat` command input (line 48–49), `Billing` forms.
- **Needs addition**: For any invalid fields: `aria-invalid="true"`, `aria-describedby` pointing to error message ID, `role="alert"` or `aria-live="polite"` for inline errors, and error messages in text (not color-only — e.g., red border + text message). Verify `Title` / `label` association for error messages.

---

## 5. Actionable Recommendations — Prioritized (Critical / High / Medium)

*Priorities mapped to source Remediation Priority (§Remediation Priority, lines 415–442) with refinements for the gaps above. All file/line references are from `audit_accessibility.md` unless noted.*

### Critical — Fix before release / next deployment (source §Immediate, lines 417–426)

| # | Fix | Source Issue / Lines | WCAG Criterion | Verification needed |
|---|-----|----------------------|----------------|---------------------|
| C1 | **Modal / Drawer**: Add `role="dialog"`, `aria-modal="true"`, `aria-labelledby` (link to `modal-title` id); implement focus-trap (first focusable / title; loop Tab; restore focus on Escape/close); prevent background interaction; manage nested stacks (`showRaw`, `ReplyModal`). | Issue 1 (lines 38–54); Issue 15 (lines 315–324); files: `components/Modal.tsx` (11–34), `components/Drawer.tsx` (1–32); usages `Orders.tsx` (15–133), `LLMFilter.tsx` (127–162), `Agents.tsx` (116–170), `Task.tsx` (160–175), `Billing.tsx` (123–203), `Monitoring.tsx` (236–264), `DealDetail.tsx` (231–323) | 2.4.3, 4.1.2 | NVDA/VoiceOver: announce "dialog", focus on open, loop verified, restore on close |
| C2 | **Toast**: Add `aria-live="polite"` and `aria-atomic="true"` to `.toast-wrap`; add `role="status"` (or `role="alert"` for errors); consider `assertive` for critical errors (`toast-err`). | Issue 2 (lines 57–74); file `components/Toast.tsx` (21–47) | 4.1.3 | Screen reader: announce "ok" / "err" text when pushed |
| C3 | **Badge**: Add `aria-label` with tone + context (`aria-label={`${tone}: ${children}`}` or `aria-describedby`); for metrics (`Overview`, `Pipeline`) add contextual `aria-label` (e.g., `"Ошибки на этапе Заказы: 0"`). | Issue 3 (lines 78–93); file `components/Badge.tsx` (1–15); usages across `Overview`, `Pipeline`, `Orders`, `LLMFilter`, `Agents`, `Task`, `Billing`, `Monitoring`, `DealDetail` | 1.4.1, 1.3.1 | VoiceOver/NVDA: announce status, not just number |
| C4 | **Task Input label**: Add `label="Текст комментария"` or `label="Комментарий для сделки"` to `Input` (line 156, `pages/Task.tsx`). Do not rely only on `placeholder`. | Issue 7 (lines 159–173); file `pages/Task.tsx` (156) | 1.3.1, 3.3.2, 4.1.2 | Focus to field: label read; placeholder visible but not sole identifier |
| C5 | **Table rows**: Add `tabIndex={0}` when `onRowClick`; add `role="button"`; add `aria-label` or `aria-labelledby`; add `onKeyDown` (`Enter`/`Space`); add `.table-row-click:focus-visible`. | Issue 8 (lines 175–193); file `components/Table.tsx` (55–67); usages `Orders`, `LLMFilter`, `Agents`, `Monitoring` | 2.1.1, 4.1.2 | Keyboard: Tab to row, Enter/Space activates; focus indicator visible |
| C6 | **Card clickable**: Add `Space` (`e.key === ' '`) handling; add `aria-label` describing content + action; add `.card-clickable:focus-visible`. | Issue 4 (lines 95–116); file `components/Card.tsx` (10–27); usages `Overview` (119–125), `Agents` (75–99), `LLMFilter` (193–203), `Monitoring` | 2.1.1, 4.1.2 | Keyboard: Enter and Space both activate; label read on focus |
| C7 | **Pipeline nodes**: Add `onKeyDown` (`Enter`/`Space`) calling `navigate(b.route)`; add `aria-label` with stage + metrics; add `.pipeline-node:focus-visible`. | Issue 5 (lines 119–138); file `pages/Pipeline.tsx` (82–104) | 2.1.1, 1.3.1 | Keyboard: activate with Space; screen reader: announces stage + capacity |
| C8 | **Overview buttons**: Add `aria-label` without emoji (`aria-label="Сгенерировать отклик"`, `"Остановить автоотклики"`, `"Аварийная остановка, Kill Switch. Подтвердите оператором."`); hide emoji from screen reader (`aria-hidden="true"` or remove from text content, keep visual). | Issue 6 (lines 141–156); file `pages/Overview.tsx` (103–114) | 4.1.2, 2.4.4 | Screen reader: no emoji noise; action is clear |

### High — Fix within next sprint / release (source §Short-term, lines 427–436; plus gap additions)

| # | Fix | Source Issue / Lines / Gap | WCAG Criterion | Verification needed |
|---|-----|---------------------------|----------------|---------------------|
| H1 | **NavLink `aria-current`**: Add `aria-current={isActive ? 'page' : undefined}` in `Layout` (line 118–128, `components/Layout.tsx`). | Issue 9 (lines 196–213) | 2.4.5 (AA) / 4.1.2 | Active page announced; visual `nav-active` preserved |
| H2 | **Tabs arrow navigation + `tabIndex`**: Implement WAI-ARIA Tabs: active `tabIndex={0}`, others `-1`; handle `ArrowLeft`/`ArrowRight`/`Home`/`End`; `Tab` moves to `tabpanel`. | Issue 10 (lines 217–236); file `components/Tabs.tsx` (13–29); usages `LLMFilter`, `Monitoring`, `DealDetail` | 2.1.1, 4.1.2 | Keyboard: arrows switch tab; focus not lost |
| H3 | **Contrast `--text-faint`**: Change to `#8896b3` or `#94a3b8`; verify `.pipeline-subtitle`, `.pipeline-stage`, `.kpi-hint`, `.sys-hint`, `.empty-hint`, `.alert-ts` (all using token or derived). Also audit `--accent`, `--green`, `--yellow`, `--red`, `--blue`. | Issue 11 (lines 239–252); file `src/styles.css` (4–29) | 1.4.3 | Contrast calculator ≥ 4.5:1 on `#0e1014` and `--panel` |
| H4 | **Reduced-motion**: Add `@media (prefers-reduced-motion: reduce)` disabling `animation`/`transition` for `spin`, `toast-in`, `.btn`, `.card-clickable`. Test OS setting. | Issue 12 (lines 255–278); file `src/styles.css` (465–476, 825–831, 331–336, 418–423) | 2.3.3 / 2.2.2 | OS reduced-motion on: no animation; functionality preserved |
| H5 | **Target size**: Increase `.btn-sm` to `min-height: 44px` / `padding: 10px 14px`; `.nav-link`, `.user-btn`, `.tab`, `.agent-pick-item` to `min-height: 44px`; verify `.pipeline-node`, `.table-row-click`, `.kanban-card`, `.card-clickable`. | Issue 13 (lines 281–295); file `src/styles.css` (430–431, 146–153, 169–179, 1367–1379, 609–627) | 2.5.5 / 2.5.8 | Touch test / measurement ≥ 44×44 CSS px |
| H6 | **OrchestratorChat labels**: Add `<label htmlFor="orch-cmd">Команда оркестратору</label>` (or use `Input` with `label`) for command input; add `aria-label="Отправить команду оркестратору"` on send button (or rely on visible text + `aria-label` clarification). | Issue 14 (lines 298–312); file `pages/OrchestratorChat.tsx` (48–49) | 1.3.1, 3.3.2 | Focus to input: label read; button: action announced |
| H7 | **Modal title linkage**: Add unique `id` on `.modal-title`; link with `aria-labelledby` on `role="dialog"`; at open, focus to title or first interactive; verify for `ReplyModal`, `OrderModal`, `TaskModal`, all `Billing`/`Monitoring` modals. | Issue 15 (lines 315–324); file `components/Modal.tsx` (11–34) | 4.1.2, 2.4.3 | Screen reader: title read on open; focus placed |
| H8 | **Logo / image**: Add `aria-label="Главная страница, Zarabotok Pipeline v3"` on `.logo` (`Layout`; line 335–338); add `<title>` to `public/favicon.svg` (line 332). | Issue 16 (lines 327–343); file `components/Layout.tsx` (111–117), `public/favicon.svg` (1) | 1.1.1, 1.3.1 | Logo link announced as main page; favicon decorative or titled |
| H9 | **Skip links** (new gap): Add `skip-link` to `Layout`; add `id="main"` to page containers; verify visible on focus, hidden otherwise. | Not in source | 2.4.1 | Keyboard: skip to content works; focus moves correctly |
| H10 | **Dashboard landmarks** (new gap): Add `<main>` / `<nav>` / `region` roles or `aria-label` to `Overview`, `Pipeline`, `Monitoring`, `Billing`; link `.kpi-label` to `.kpi-value` via `aria-labelledby`; add `aria-label` to metric containers. | Not fully in source (Issue 18 is minor static only) | 1.3.1, 2.4.10 | Screen reader: region names read; KPI context clear |
| H11 | **Error identification** (new gap): For form errors (`Task` comment, `LLMFilter` settings, `Orders` filters, `OrchestratorChat`): add `aria-invalid="true"`, `aria-describedby` linking error message, `role="alert"` for inline errors; never rely on color alone for errors. | Not audited in source | 3.3.1, 3.3.3, 1.4.1 | Invalid input: error text read; focus management to error |

### Medium — Ongoing / maintenance (source §Ongoing, lines 437–441; plus additions)

| # | Fix | Source Issue / Lines | WCAG Criterion | Notes |
|---|-----|---------------------|----------------|-------|
| M1 | **Kanban keyboard alt**: Add buttons "Переместить в колонку X" or `ArrowLeft`/`ArrowRight` with `aria-label`; verify `draggable` not blocking keyboard. | Issue 17 (lines 346–359); file `components/KanbanBoard.tsx` (22–71), `pages/CRM.tsx` (82–102) | 2.1.1 | Minor per source; still needed for keyboard-only users |
| M2 | **FunnelMetrics / Pipeline KPI `aria-label`**: Add container `aria-label="Конверсия: X%"`; link `.kpi-label` to `.kpi-value`; verify dynamic updates announce (if live). | Issue 18 (lines 362–376); files `pages/FunnelMetrics.tsx` (52–79), `pages/Pipeline.tsx` (122–142), `pages/Overview.tsx` (118–126) | 1.3.1, 4.1.2 | Source grades Minor; important for screen-reader metric comprehension |
| M3 | **LLMFilter switches explicit link**: Add `id` on `input`, `htmlFor` on `label` (line 288–305, `pages/LLMFilter.tsx`). | Issue 19 (lines 379–387) | 1.3.1 | Source notes nesting works; explicit link improves robustness |
| M4 | **Dynamic page titles**: Use `react-helmet` / `useEffect` + `document.title` per route (`Overview`: "Обзор конвейера"; `Pipeline`: "Пайплайн"; etc.). | Issue 20 (lines 390–398); `index.html` (7) | 2.4.2 | Source grades Minor; improves orientation |
| M5 | **ARIA live for dynamic metrics** (new): If `Overview` metrics update without page reload, add `aria-live="polite"` / `aria-atomic="true"` to metric container or use `aria-describedby` updates. | Not in source | 4.1.3 | Only needed if live updates occur |
| M6 | **Heading hierarchy verification** (new): Confirm `h2` after `h1`; no skipped levels inside cards/sections; `h1` unique per page. | Not in source | 1.3.1, 2.4.6 | Add to CI / acceptance criteria |

---

## 6. Verification Protocol Recommended (from source §Recommended Next Steps, lines 445–450; refined)

Before declaring AA conformance, execute:

1. **Automated**: Run `axe-core` / `@axe-core/react` in CI against all routes (`Overview`, `Pipeline`, `Orders`, `LLMFilter`, `Agents`, `Task`, `Billing`, `Monitoring`, `OrchestratorChat`, `CRM`). Check rules: `color-contrast`, `button-name`, `label`, `aria-required-attr`, `region`, `landmark-one-main`, `focus-order-semantics`, `skip-link` (if added).
2. **Keyboard**: Full `Tab` / `Shift+Tab` / `Enter` / `Space` / `Escape` / `Arrow` path through each page; verify no dead-ends, no focus loss behind modals, focus loop inside `Modal`/`Drawer`, focus return after close.
3. **Screen Reader** (NVDA + VoiceOver): Read `Badge` tones, open `Modal`, navigate `Tabs`, activate `Card`, select `Table` row, read `Pipeline` node, verify `Toast` announcement, verify `NavLink` `aria-current` announcement, verify `skip-link` skips correctly.
4. **Visual / Contrast**: Measure all token combinations (`--text-faint`, `--accent`, `--green`, `--yellow`, `--red`, `--blue`) against all surfaces; verify 4.5:1 minimum; check `Badge` text on tone backgrounds; check `.pipeline-subtitle`, `.pipeline-stage`, `.kpi-hint`, `.sys-hint`.
5. **Reduced-motion**: Enable OS `prefers-reduced-motion: reduce`; verify animations stop; verify all functionality (open modal, submit form, navigate pipeline) still works.
6. **Target size**: Measure `.btn-sm`, `.nav-link`, `.user-btn`, `.tab`, `.agent-pick-item`, `.pipeline-node`, `.table-row-click`, `.card-clickable`, `.kanban-card` at 100% zoom; ensure ≥ 44×44 CSS px or sufficient spacing per 2.5.8.
7. **Re-test after fixes**: Re-audit with same protocol within 1 sprint; document results against Issue 1–20 checklist plus H1–H11 and M1–M6.

---

*Report generated from `audit_accessibility.md` (479 lines, dated 2026-08-31). All line references and file paths are taken directly from the source audit. No source findings were altered; only gaps, false-positive assessments, and missing-criterion additions were added by this auditor.*
