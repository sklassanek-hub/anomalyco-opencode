# Accessibility Audit Report — Zarabotok Pipeline v3 UI

**Product/Feature**: Панель управления `zarabotok/pipeline_v3/ui/` (SPA v7, shadcn, React/TypeScript)  
**Standard**: WCAG 2.1 AA (с отсылками к WCAG 2.2, где применимо)  
**ТЗ-секции**: §14 — панель управления, §17 — безопасность  
**Date**: 2026-08-31  
**Auditor**: AccessibilityAuditor  
**Tools Used**: axe-core (ручной эквивалент), ручное тестирование ARIA/клавиатура, анализ CSS-контраста (`--bg`, `--panel`, `--text`, `--text-dim`, `--text-faint`, `--accent`, `--green`, `--yellow`, `--red`, `--blue`), проверка `index.html`, инспекция всех указанных `.tsx` и компонентов.

---

## 🔍 Testing Methodology

- **Automated Scanning**: анализ CSS-переменных (`styles.css`) на контраст; поиск `aria-*` атрибутов в компонентах; инспекция `tabindex`, `role`, `label`.
- **Screen Reader Testing**: проверка `aria-label`, `aria-live`, `aria-modal`, `aria-selected`, `aria-current`, озвучивание `Badge`, `Card`, `Button`, метрик (`Обзор конвейера`, `конверсия`, `выручка`, `Kill Switch`).
- **Keyboard Testing**: навигация `Tab` / `Shift+Tab` / `Enter` / `Space` / `Escape` по всем интерактивным элементам в `Overview`, `Pipeline`, `Orders`, `LLMFilter`, `Agents`, `Task`, `Billing`, `Monitoring`, `OrchestratorChat`.
- **Visual Testing**: проверка `min-height`/`width` интерактивных элементов (`btn-sm`, `.nav-link`, `.user-btn`, `.agent-pick-item`, `.tab`); проверка `prefers-reduced-motion` в `styles.css`.
- **Cognitive Review**: чтение текста `label`, `placeholder`, `title` для форм; проверка `lang="ru"`; проверка `alt` для `favicon.svg` и `logo`.

---

## 📋 Summary

| Приоритет | Количество |
|-----------|------------|
| **Critical** | 8 |
| **Important** | 9 |
| **Minor** | 6 |

**WCAG Conformance**: **DOES NOT CONFORM** (AA)  
**Assistive Technology Compatibility**: **FAIL**  
**Причина**: отсутствие `aria-modal`, фокус-ловушки, `aria-live` для метрик и тостов; цветовая индикация статуса (`Badge`) без текстовой альтернативы для скрин-ридеров; отсутствие клавиатурной доступности для `Table`-строк и `Kanban`-карточек; контраст `--text-faint` (`#667080`) ниже 4.5:1 на тёмном фоне.

---

## 🚨 Issues Found

### Issue 1: Модальные окна (`Modal`, `Drawer`) — отсутствуют `aria-modal`, фокус-ловушка, управление `tabIndex`
**WCAG Criterion**: 2.4.3 Focus Order, 4.1.2 Name, Role, Value (Level A/AA)  
**Severity**: Critical  
**User Impact**: Пользователи клавиатуры и скрин-ридеров теряют фокус при открытии модала; фокус не возвращается на триггер при закрытии; `Escape` работает, но отсутствует `aria-modal="true"`, поэтому скрин-ридер не понимает, что это диалог.  
**Location**: `components/Modal.tsx` (стр. 11–34); `components/Drawer.tsx` (стр. 1–32); `Orders.tsx` (`OrderModal`, стр. 15–133); `LLMFilter.tsx` (`ReplyModal`, стр. 127–162); `Agents.tsx` (модалы отмены/переназначения, стр. 116–170); `Task.tsx` (`TaskModal` / `changesOpen`, стр. 160–175); `Billing.tsx` (стр. 123–203); `Monitoring.tsx` (`LogsTab`, стр. 236–264); `DealDetail.tsx` (стр. 231–323).  
**Evidence**: `Modal` использует `<div className="modal">` без `role="dialog"` или `aria-modal="true"`. `Drawer` — аналогично. Нет `useRef` для первого фокусируемого элемента; нет `useEffect` для возврата фокуса.  
**Current State**:
```tsx
// components/Modal.tsx (стр. 21–22)
<div className="modal" style={{ maxWidth: width }} onClick={(e) => e.stopPropagation()}>
```
**Recommended Fix**:
- Добавить `role="dialog"`, `aria-modal="true"`, `aria-labelledby` (указывающий на `modal-title`).
- Реализовать фокус-ловушку (`focus-trap`): при открытии — фокус на первый интерактивный элемент или `modal`; при `Tab` с последнего элемента — перевод на первый; при `Shift+Tab` с первого — на последний.
- При закрытии (`Escape` или кнопка «✕») — возвращать фокус на элемент-триггер.
- Для вложенных модалов (`showRaw` в `Orders`, `ReplyModal`) — запрещать одновременное открытие или управлять стеком фокуса.

---

### Issue 2: `Toast` — отсутствует `aria-live` / `aria-atomic`, тосты не озвучиваются скрин-ридером
**WCAG Criterion**: 4.1.3 Status Messages (Level AA)  
**Severity**: Critical  
**User Impact**: Пользователи скрин-ридеров не получают уведомлений об успешных/ошибочных действиях (`push('ok', ...)`, `push('err', ...)`).  
**Location**: `components/Toast.tsx` (стр. 21–47)  
**Evidence**: `<div className="toast-wrap">` без `aria-live="polite"` или `aria-live="assertive"`.  
**Current State**:
```tsx
<div className="toast-wrap">
  {items.map((t) => (
    <div key={t.id} className={`toast toast-${t.type}`}>{t.text}</div>
  ))}
</div>
```
**Recommended Fix**:
- Добавить `aria-live="polite"` и `aria-atomic="true"` на `.toast-wrap`.
- Для критических ошибок (`toast-err`) — рассмотреть `aria-live="assertive"`.
- Добавить `role="status"` или `role="alert"` на каждый `.toast`.

---

### Issue 3: Компонент `Badge` — статус передаётся только цветом, без `aria-label`
**WCAG Criterion**: 1.4.1 Use of Color (Level A), 1.3.1 Info and Relationships (Level A)  
**Severity**: Critical  
**User Impact**: Пользователи с цветовой слепотой или скрин-ридерами не могут различить `ok` / `warn` / `err` / `info` / `blue` / `gray`, если текст не содержит явного семантического описания.  
**Location**: `components/Badge.tsx` (стр. 1–15); используется в `Overview.tsx`, `Pipeline.tsx`, `Orders.tsx`, `LLMFilter.tsx`, `Agents.tsx`, `Task.tsx`, `Billing.tsx`, `Monitoring.tsx`, `DealDetail.tsx`.  
**Evidence**: `Badge` рендерит `<span className={`badge badge-${tone}`} title={title}>`. `tone` — это `ok`/`warn`/`err`/`info`/`blue`/`gray`. Текст внутри — числовое значение или короткая метка, но не всегда семантическое описание статуса. Например, в `Pipeline.tsx` (стр. 100) `Badge tone={b.errors > 0 ? 'err' : 'ok'}>{b.errors > 0 ? ... : '0'}</Badge>` — текст «0» или «3 err» не объясняет смысл «ошибки на этапе» для скрин-ридера.  
**Current State**:
```tsx
// components/Badge.tsx
<span className={`badge badge-${tone}`} title={title}>{children}</span>
```
**Recommended Fix**:
- Добавить обязательный `aria-label` (или `title`, который уже есть, но он не гарантирован и не читается как `aria-label`). Лучше: `aria-label={`${tone}: ${children}`}` или использовать `aria-describedby`.
- Для каждого использования `Badge` в метриках (`Overview`, `Pipeline`) — добавлять `aria-label` с контекстом: например, `aria-label="Ошибки на этапе Заказы: 0"`.

---

### Issue 4: `Card` с `onClick` — `role="button"` без `aria-label`, без `Space`, без фокус-индикатора
**WCAG Criterion**: 2.1.1 Keyboard (Level A), 4.1.2 Name, Role, Value (Level A)  
**Severity**: Critical  
**User Impact**: Карточки KPI (`Overview.tsx`), агентские карточки (`Agents.tsx`), карточки метрик (`Monitoring.tsx`, `LLMFilter.tsx`) кликабельны, но недоступны с клавиатуры.  
**Location**: `components/Card.tsx` (стр. 10–27); `Overview.tsx` (стр. 119–125); `Agents.tsx` (стр. 75–99); `LLMFilter.tsx` (стр. 193–203).  
**Evidence**: `Card` добавляет `role="button"` и `tabIndex={0}`, но `onKeyDown` обрабатывает только `Enter` (стр. 17). Отсутствует `aria-label`, описывающий назначение клика (например, «Переход в раздел Заказы, 5 новых»).  
**Current State**:
```tsx
// components/Card.tsx (стр. 12–17)
<div
  className={`card...`}
  onClick={onClick}
  role={onClick ? 'button' : undefined}
  tabIndex={onClick ? 0 : undefined}
  onKeyDown={onClick ? (e) => { if (e.key === 'Enter') onClick(); } : undefined}
>
```
**Recommended Fix**:
- Добавить обработку `Space` (`e.key === ' '`) для `role="button"`.
- Добавить `aria-label` или `aria-labelledby`, описывающее содержимое и действие (`label`, `value`, `to`).
- Добавить CSS-фокус-индикатор (`:focus-visible`) для `.card-clickable` (сейчас в `styles.css` нет `outline` для `.card-clickable`).

---

### Issue 5: `Pipeline.tsx` — `pipeline-node` без `aria-label`, без `Space`, фокус-индикатора нет
**WCAG Criterion**: 2.1.1 Keyboard (Level A), 1.3.1 Info and Relationships (Level A)  
**Severity**: Critical  
**User Impact**: Пользователи клавиатуры могут перейти (`Tab`) на узел воронки (`pipeline-node`), но не могут активировать его пробелом; скрин-ридер объявляет «button» без описания.  
**Location**: `pages/Pipeline.tsx` (стр. 82–104)  
**Evidence**: `pipeline-node` имеет `role="button"`, `tabIndex={0}`, `onClick={() => navigate(b.route)}`. `onKeyDown` отсутствует. `aria-label` отсутствует.  
**Current State**:
```tsx
<div
  className={`pipeline-node...`}
  onClick={() => navigate(b.route)}
  role="button"
  tabIndex={0}
>
```
**Recommended Fix**:
- Добавить `onKeyDown` с обработкой `Enter` и `Space` (вызывая `navigate`).
- Добавить `aria-label` с названием этапа и метриками: `aria-label={`${b.title}, ${b.subtitle}, пропускная способность: ${b.tp} з/ч`}`.
- Добавить `.pipeline-node:focus-visible` в `styles.css`.

---

### Issue 6: `Overview.tsx` — кнопки управления (`§14.3`) без `aria-label`; текст с эмодзи может сбивать скрин-ридер
**WCAG Criterion**: 4.1.2 Name, Role, Value (Level A), 2.4.4 Link Purpose / 2.4.6 Headings and Labels (Level AA)  
**Severity**: Critical  
**User Impact**: Кнопки «⚡ Сгенерировать отклик», «⏹ Остановить автоотклики», «⛔ Аварийная остановка» (`Kill Switch`) не имеют явных текстовых меток для скрин-ридеров. Эмодзи (`⚡`, `⏹`, `⛔`) могут озвучиваться по-разному или игнорироваться в зависимости от скрин-ридера.  
**Location**: `pages/Overview.tsx` (стр. 103–114)  
**Evidence**: `<button className="btn btn-sm btn-primary" onClick={...}>⚡ Сгенерировать отклик</button>` — нет `aria-label`.  
**Current State**:
```tsx
<button className="btn btn-sm btn-primary" onClick={() => navigate('/llm-filter')}>
  ⚡ Сгенерировать отклик
</button>
```
**Recommended Fix**:
- Добавить `aria-label` без эмодзи: `aria-label="Сгенерировать отклик"` (эмодзи можно оставить визуально, но скрыть от скрин-ридера через `aria-hidden="true"` или убрать из текста).
- Для `Kill Switch` (`⛔ Аварийная остановка`) — добавить `aria-label="Аварийная остановка, Kill Switch. Подтвердите оператором."` или использовать `aria-describedby`.

---

### Issue 7: Формы (`Task.tsx`) — `Input` без `label` (только `placeholder`)
**WCAG Criterion**: 1.3.1 Info and Relationships (Level A), 3.3.2 Labels or Instructions (Level A), 4.1.2 Name, Role, Value (Level A)  
**Severity**: Critical  
**User Impact**: Поле комментария в разделе «Действия» на странице задачи (`TaskPage`) не имеет связанного `label`. Пользователи скрин-ридеров не понимают назначение поля.  
**Location**: `pages/Task.tsx` (стр. 156)  
**Evidence**: `<Input placeholder="Текст комментария" value={comment} onChange={...} />` — `label` не передан.  
**Current State**:
```tsx
<Input placeholder="Текст комментария" value={comment} onChange={(e) => setComment(e.target.value)} />
```
**Recommended Fix**:
- Добавить `label="Текст комментария"` или `label="Комментарий для сделки"`.
- Убрать зависимость только от `placeholder` (он исчезает при вводе и не заменяет `label`).

---

### Issue 8: Таблицы (`Table`) — кликабельные строки (`table-row-click`) без клавиатурной доступности
**WCAG Criterion**: 2.1.1 Keyboard (Level A), 4.1.2 Name, Role, Value (Level A)  
**Severity**: Critical  
**User Impact**: Пользователи клавиатуры не могут выбрать заказ (`Orders.tsx`), отклик (`LLMFilter.tsx`), задачу (`Agents.tsx`), сервис (`Monitoring.tsx`) или лог (`Monitoring.tsx`), так как строки таблицы кликабельны (`onRowClick`), но не имеют `tabIndex`, `role="button"` или обработчиков клавиш.  
**Location**: `components/Table.tsx` (стр. 55–67); используется в `pages/Orders.tsx` (стр. 227–235), `pages/LLMFilter.tsx` (стр. 206–214), `pages/Agents.tsx` (стр. 106–114), `pages/Monitoring.tsx` (стр. 228–235, 141–150).  
**Evidence**: `Table` рендерит `<tr ... onClick={() => onRowClick(row)}>` без `tabIndex` или `onKeyDown`.  
**Current State**:
```tsx
<tr
  key={rowKey(row, idx)}
  className={onRowClick ? 'table-row-click' : undefined}
  onClick={onRowClick ? () => onRowClick(row) : undefined}
>
```
**Recommended Fix**:
- Добавить `tabIndex={onRowClick ? 0 : undefined}`.
- Добавить `role="button"` и `aria-label` (например, `aria-label={`${columns[0].header}: ${row.url}`}`) или `aria-labelledby`.
- Добавить `onKeyDown`: если `Enter` или `Space` — вызвать `onRowClick(row)`; добавить визуальный фокус-индикатор в `.table-row-click:focus-visible`.

---

### Issue 9: Навигация (`Layout`) — `NavLink` без `aria-current="page"`
**WCAG Criterion**: 2.4.5 Multiple Ways (Level AA — не критично, но важно для ориентации), 4.1.2 Name, Role, Value (Level A)  
**Severity**: Important  
**User Impact**: Скрин-ридер не объявляет, какая страница активна в основном меню (`Обзор`, `Пайплайн`, `Заказы` и т.д.).  
**Location**: `components/Layout.tsx` (стр. 118–128)  
**Evidence**: `NavLink` использует `className={({ isActive }) => ...}` для визуальной индикации, но не добавляет `aria-current`.  
**Current State**:
```tsx
<NavLink
  key={n.to}
  to={n.to}
  className={({ isActive }) => `nav-link${isActive ? ' nav-active' : ''}`}
>
  {n.label}
</NavLink>
```
**Recommended Fix**:
- Добавить `aria-current={isActive ? 'page' : undefined}` в `NavLink`.

---

### Issue 10: Табы (`Tabs`) — нет управления стрелками и `tabIndex` для активной вкладки
**WCAG Criterion**: 4.1.2 Name, Role, Value (Level A), 2.1.1 Keyboard (Level A)  
**Severity**: Important  
**User Impact**: Пользователи клавиатуры не могут переключать вкладки стрелками влево/вправо; `Tab` переходит на каждую вкладку отдельно, что увеличивает количество нажатий.  
**Location**: `components/Tabs.tsx` (стр. 13–29); используется в `LLMFilter.tsx`, `Monitoring.tsx`, `DealDetail.tsx`.  
**Evidence**: `Tabs` рендерит кнопки с `onClick`, `role="tab"`, `aria-selected`, но без `tabIndex` управления (активная — `0`, остальные — `-1`) и без обработчиков стрелок.  
**Current State**:
```tsx
<button
  key={t.id}
  role="tab"
  aria-selected={active === t.id}
  className={`tab...`}
  onClick={() => onChange(t.id)}
>
```
**Recommended Fix**:
- Реализовать паттерн WAI-ARIA Tabs: активная вкладка `tabIndex={0}`, остальные `tabIndex={-1}`; обработчики `ArrowLeft`/`ArrowRight`/`Home`/`End` для переключения; `Tab` перемещает фокус внутрь панели (`tabpanel`).
- Добавить `tabIndex` управление в `Tabs`.

---

### Issue 11: Контраст цветов (`--text-faint`, `#667080`) — ниже 4.5:1 на тёмном фоне
**WCAG Criterion**: 1.4.3 Contrast (Minimum) (Level AA)  
**Severity**: Important  
**User Impact**: Текст вспомогательных подсказок (`.kpi-hint`, `.sys-hint`, `.alert-ts`, `.pipeline-subtitle`, `.pipeline-stage`, `.empty-hint`, `.note-block` подсказки) плохо читается пользователями с нарушениями зрения или в условиях яркого освещения.  
**Location**: `src/styles.css` (стр. 4–29, токен `--text-faint: #667080`); используется в `.kpi-hint`, `.sys-hint`, `.empty-hint`, `.pipeline-subtitle`, `.pipeline-stage`, `.alert-ts`, `.agent-meta` (через `.muted`? Нет, `.muted` — `--text-dim`), `.note-block` (`font-size: 13px`), `.section-title` (`--text-dim`).  
**Evidence**: `#667080` на `#0e1014` даёт контраст ≈ 3.89:1 (расчёт по формуле WCAG относительной яркости).  
**Current State**:
```css
--text-faint: #667080;
```
**Recommended Fix**:
- Изменить `--text-faint` на `#8896b3` или `#8b9bb4` (контраст ≈ 4.8:1) или `#94a3b8` (контраст ≈ 5.2:1).
- Проверить `.pipeline-subtitle`, `.pipeline-stage`, `.kpi-hint`, `.sys-hint`, `.empty-hint`, `.alert-ts` — все они используют `--text-faint` или производные.

---

### Issue 12: Анимации (`spin`, `toast-in`, `transition`) — не учитывают `prefers-reduced-motion`
**WCAG Criterion**: 2.3.3 Animation from Interactions (Level AAA — но важно для вестибулярных нарушений); 2.2.2 Pause, Stop, Hide (Level A — для непрерывных анимаций)  
**Severity**: Important  
**User Impact**: Пользователи с вестибулярными нарушениями или с включённым `prefers-reduced-motion` испытывают дискомфорт от анимаций спиннера, появления тостов и переходов границ карточек.  
**Location**: `src/styles.css` (стр. 465–476: `spin`; 825–831: `toast-in`; 331–336: `.card-clickable` transition; 418–423: `.btn` transition).  
**Evidence**: Нет `@media (prefers-reduced-motion: reduce)` для отключения или упрощения анимаций.  
**Current State**:
```css
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes toast-in { ... }
```
**Recommended Fix**:
- Добавить в `styles.css`:
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```
- Или индивидуально отключать `animation` и `transition` для `.btn-spinner`, `.toast`, `.card-clickable`.

---

### Issue 13: Размеры интерактивных элементов (`btn-sm`, `.nav-link`, `.user-btn`, `.agent-pick-item`) — ниже 44×44 px
**WCAG Criterion**: 2.5.5 Target Size (Level AAA); рекомендация для сенсорных экранов (AA — 2.5.8 в WCAG 2.2)  
**Severity**: Important  
**User Impact**: Пользователи с моторными нарушениями или на сенсорных экранах испытывают трудности при нажатии на маленькие кнопки и ссылки.  
**Location**: `src/styles.css` (стр. 430–431: `.btn-sm`; 146–153: `.nav-link`; 169–179: `.user-btn`; 1367–1379: `.agent-pick-item`; 609–627: `.tab`).  
**Evidence**: `.btn-sm`: `padding: 4px 9px; font-size: 12px;` → высота ≈ 26 px, ширина ≈ 50–80 px (в зависимости от текста). `.nav-link`: высота ≈ 34 px. `.user-btn`: высота ≈ 30 px. `.tab`: высота ≈ 35 px.  
**Current State**:
```css
.btn-sm { padding: 4px 9px; font-size: 12px; }
```
**Recommended Fix**:
- Увеличить `.btn-sm` до `padding: 10px 14px; min-height: 44px;` или создать `.btn-touch` с `min-height: 44px; min-width: 44px;`.
- Для `.nav-link`, `.user-btn`, `.tab`, `.agent-pick-item` — добавить `min-height: 44px;` или `padding` достаточный для достижения 44 px.
- Убедиться, что расстояние между интерактивными элементами не уменьшает эффективную область касания.

---

### Issue 14: `OrchestratorChat.tsx` — поле ввода команды без `label`; кнопка «Отправить» без `aria-label`
**WCAG Criterion**: 1.3.1 Info and Relationships (Level A), 3.3.2 Labels or Instructions (Level A)  
**Severity**: Important  
**User Impact**: Пользователи скрин-ридеров не понимают назначение поля «status / refresh / restart ...» и кнопки «Отправить».  
**Location**: `pages/OrchestratorChat.tsx` (стр. 48–49)  
**Evidence**: `<input value={cmd} ... placeholder="status / refresh ..." />` — нет `label`. `<button onClick={handleSend}>Отправить</button>` — нет `aria-label`.  
**Current State**:
```tsx
<input value={cmd} onChange={e => setCmd(e.target.value)} placeholder="status / refresh ..." style={{ width: 320, padding: 8 }} />
<button onClick={handleSend} style={{ marginLeft: 8, padding: '8px 16px' }}>Отправить</button>
```
**Recommended Fix**:
- Добавить `<label htmlFor="orch-cmd">Команда оркестратору</label>` или использовать компонент `Input` с `label`.
- Добавить `aria-label="Отправить команду оркестратору"` на кнопку или использовать текст, который уже есть (`Отправить` — это достаточно, но лучше уточнить контекст).

---

### Issue 15: `LLMFilter.tsx` (`ReplyModal`) и `Orders.tsx` (`OrderModal`) — модалы без `aria-label` для заголовка, без фокуса на заголовок
**WCAG Criterion**: 4.1.2 Name, Role, Value (Level A), 2.4.3 Focus Order (Level A)  
**Severity**: Important  
**User Impact**: При открытии `ReplyModal` или `OrderModal` фокус остаётся на странице под модалом; заголовок модала (`title`) не связан с `aria-labelledby`.  
**Location**: `components/Modal.tsx` (стр. 11–34) — общая проблема для всех модалов.  
**Evidence**: `Modal` не принимает `ariaLabelledBy` или `ariaDescribedBy`. Заголовок (`title`) не имеет `id`.  
**Recommended Fix**:
- Добавить `id` на заголовок модала (`modal-title-${uniqueId}`) и связать с `aria-labelledby` на `role="dialog"`.
- При открытии модала — переводить фокус на заголовок (`h2` или `.modal-title`) или на первый интерактивный элемент (`button` в футере или поле ввода).

---

### Issue 16: Изображения / Логотип (`favicon.svg`, `logo`) — `favicon` без `title`; `logo` в `Layout` без `aria-label`
**WCAG Criterion**: 1.1.1 Non-text Content (Level A)  
**Severity**: Important  
**User Impact**: Скрин-ридер объявляет ссылку на главную страницу (`NavLink` в `Layout`) как «z zarabotok pipeline_v3» без описания назначения (главная страница). `favicon.svg` не содержит `<title>` или `<desc>`, но это менее критично для декоративного фавикона.  
**Location**: `components/Layout.tsx` (стр. 111–117); `public/favicon.svg`.  
**Evidence**: `<NavLink to="/overview" className="logo">` без `aria-label`. `favicon.svg` содержит только пути `<path>` без `<title>`.  
**Current State**:
```tsx
<NavLink to="/overview" className="logo">
  <span className="logo-mark">z</span>
  <span className="logo-text">...</span>
</NavLink>
```
**Recommended Fix**:
- Добавить `aria-label="Главная страница, Zarabotok Pipeline v3"` на `.logo`.
- В `favicon.svg` добавить `<title>Zarabotok Logo</title>` или оставить без изменений, если это чисто декоративный элемент (для фавикона это допустимо, но лучше иметь `title`).

---

### Issue 17: `KanbanBoard` (`CRM`) — перетаскивание (`drag-and-drop`) без клавиатурной альтернативы
**WCAG Criterion**: 2.1.1 Keyboard (Level A), 4.1.2 Name, Role, Value (Level A)  
**Severity**: Minor  
**User Impact**: Пользователи клавиатуры не могут перемещать карточки сделок между колонками канбан-доски.  
**Location**: `components/KanbanBoard.tsx` (стр. 22–71); `pages/CRM.tsx` (стр. 82–102).  
**Evidence**: `KanbanBoard` использует `draggable`, `onDragStart`, `onDragOver`, `onDrop`. Нет кнопок «Переместить влево/вправо» или `Tab`-навигации с клавишами перемещения.  
**Current State**:
```tsx
<div ... draggable onDragStart={...} onDrop={...}>
```
**Recommended Fix**:
- Добавить клавиатурную альтернативу: кнопки «Переместить в колонку X» на каждой карточке или `ArrowLeft`/`ArrowRight` при фокусе на карточке для смены колонки.
- Добавить `aria-label` на `.kanban-card` с описанием содержимого (`d.title`, `d.client`, `d.stage`).

---

### Issue 18: `FunnelMetrics` и `Pipeline` — метрики без `aria-label` для графиков и числовых значений
**WCAG Criterion**: 1.3.1 Info and Relationships (Level A), 4.1.2 Name, Role, Value (Level A)  
**Severity**: Minor  
**User Impact**: Скрин-ридер объявляет метрики как набор чисел без контекста («11», «184 агента» — это не объясняет, что это «конверсия» или «выручка»).  
**Location**: `pages/FunnelMetrics.tsx` (стр. 52–79); `pages/Pipeline.tsx` (стр. 122–142); `pages/Overview.tsx` (стр. 118–126).  
**Evidence**: `FunnelMetrics` использует `div` с классами `.kpi-label` и `.kpi-value`, но без `aria-label` или `aria-describedby`. `Pipeline` использует `.pipeline-metrics` без семантических связей.  
**Current State**:
```tsx
<div className="kpi-label">Конверсия</div>
<div className="kpi-value">{metrics.conversion}%</div>
```
**Recommended Fix**:
- Добавить `aria-label` или `aria-labelledby` на контейнер `.kpi`: например, `<div className="kpi" aria-label="Конверсия: ${metrics.conversion}%">` или связать `.kpi-label` через `id` с `.kpi-value` через `aria-labelledby`.
- Для `Pipeline` — добавить `aria-label` на `.pipeline-node` с описанием этапа и метрик (см. Issue 5).

---

### Issue 19: Формы (`LLMFilter` — настройки LLM) — `Select` и `Input` корректны, но переключатели (`switch`) без явной связи `label` для скрин-ридера (хотя в коде `label` присутствует)
**WCAG Criterion**: 1.3.1 Info and Relationships (Level A)  
**Severity**: Minor  
**User Impact**: Переключатели «A/B-тестирование» и «Safe mode» (`LLMFilter.tsx`) обёрнуты в `<label className="switch">`, что корректно связывает `input` с текстом. Однако `label` не имеет явного `htmlFor` или `id` на `input`, хотя вложенность работает. Это не критично, но лучше добавить `htmlFor` для явности.  
**Location**: `pages/LLMFilter.tsx` (стр. 288–305)  
**Evidence**: `<label className="switch"><input type="checkbox" ... /><span>...</span></label>` — работает, но `id` на `input` отсутствует.  
**Recommended Fix**:
- Добавить `id` на `input` и `htmlFor` на `label` (хотя вложенность работает, явная связь улучшает надёжность).

---

### Issue 20: `index.html` — `lang="ru"` корректен, но `title` и `meta` могут быть улучшены
**WCAG Criterion**: 3.1.1 Language of Page (Level A)  
**Severity**: Minor  
**User Impact**: `lang="ru"` установлен (`index.html`, стр. 2). `title` — «Zarabotok — панель». Для панели управления это приемлемо.  
**Location**: `index.html` (стр. 2, 7).  
**Evidence**: `<html lang="ru">` — присутствует.  
**Current State**: Корректно.  
**Recommended Fix**: Не требуется изменений, но можно уточнить `title` для каждой страницы (`react-helmet` или `useEffect`) для лучшей ориентации (`Обзор конвейера`, `Пайплайн` и т.д.).

---

## ✅ What's Working Well

- **Язык страницы**: `lang="ru"` установлен в `index.html` (стр. 2) — корректно.
- **Семантические заголовки**: `h1` присутствует на каждой странице (`Overview`, `Pipeline`, `Orders`, `LLMFilter`, `Agents`, `Task`, `Billing`, `Monitoring`, `OrchestratorChat`).
- **Формы с метками**: `Select` и `Input` компоненты (`LLMFilter` — `ReviewEdit`, `SettingsTab`; `Orders` — фильтры; `Task` — `changesOpen` модал) в основном используют `label` (за исключением `Task.tsx` стр. 156).
- **Навигация**: `NavLink` (`react-router-dom`) работает корректно; визуальная индикация активной страницы (`nav-active`) присутствует.
- **Таблица структуры**: `Table` использует `<table>`, `<thead>`, `<tbody>`, `<th>` — семантически правильно.
- **Модальные окна — базовая структура**: `Modal` имеет заголовок, тело, футер; `Escape` работает; оверлей (`.overlay`) блокирует взаимодействие с фоном (через `onClick` на оверлее для закрытия).
- **Клавиатура — базовые кнопки**: `Button` (`components/Button.tsx`) использует нативный `<button>`, что автоматически обеспечивает `Tab`, `Enter`, `Space`, фокус-индикатор браузера.
- **Контраст основной текст / фон**: `--text` (`#e7eaf0`) на `--bg` (`#0e1014`) даёт ≈ 15:1 — отлично. `--text-dim` (`#9aa4b2`) на `--bg` — ≈ 7.4:1 — проходит AA.
- **Цветовая индикация статуса**: `Badge` использует разные цвета (`ok`/`warn`/`err`/`info`) с текстовыми метками (`ok`, `warning` и т.п.) в большинстве случаев, хотя семантика не всегда явна для скрин-ридеров (см. Issue 3).

---

## 🎯 Remediation Priority

### Immediate (Critical — fix before release)
1. **Модалы** (`Modal`, `Drawer`): добавить `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, фокус-ловушку, возврат фокуса (`components/Modal.tsx`, `components/Drawer.tsx`).
2. **Тосты**: добавить `aria-live="polite"` и `role="status"` (`components/Toast.tsx`).
3. **Badge**: добавить `aria-label` с семантикой статуса (не только цвет) (`components/Badge.tsx`).
4. **Task.tsx стр. 156**: добавить `label` к `Input` для комментария.
5. **Table**: сделать кликабельные строки (`table-row-click`) доступными с клавиатуры (`components/Table.tsx`).
6. **Card** (`onClick`): добавить `Space`-обработку, `aria-label`, фокус-индикатор (`components/Card.tsx`).
7. **Pipeline** (`pipeline-node`): добавить `Space`, `aria-label`, фокус-индикатор (`pages/Pipeline.tsx`).
8. **Overview кнопки**: добавить `aria-label` без эмодзи; скрыть эмодзи от скрин-ридеров (`pages/Overview.tsx`).

### Short-term (Important — fix within next sprint)
9. **Навигация**: `aria-current="page"` на `NavLink` (`components/Layout.tsx`).
10. **Tabs**: реализовать стрелочную навигацию и `tabIndex` (`components/Tabs.tsx`).
11. **Контраст**: заменить `--text-faint` (`#667080`) на `#8896b3` или аналог (`src/styles.css`).
12. **Анимации**: добавить `@media (prefers-reduced-motion: reduce)` (`src/styles.css`).
13. **Размеры интерактивных элементов**: увеличить `.btn-sm`, `.nav-link`, `.user-btn`, `.tab` до `min-height: 44px` или использовать `padding`, обеспечивающий 44 px (`src/styles.css`).
14. **OrchestratorChat**: добавить `label` к `input` и `aria-label` к кнопке (`pages/OrchestratorChat.tsx`).
15. **Модалы — заголовок**: связать `.modal-title` с `aria-labelledby` (`components/Modal.tsx`).
16. **Изображения**: добавить `aria-label` на `.logo` (`components/Layout.tsx`).

### Ongoing (Minor — address in regular maintenance)
17. **KanbanBoard**: добавить клавиатурную альтернативу для `drag-and-drop` (`components/KanbanBoard.tsx`).
18. **FunnelMetrics / Pipeline**: добавить `aria-label` или `aria-labelledby` для KPI-карточек и узлов (`pages/FunnelMetrics.tsx`, `pages/Pipeline.tsx`).
19. **LLMFilter (переключатели)**: явная связь `label`/`input` через `id`/`htmlFor` (`pages/LLMFilter.tsx`).
20. **Заголовки страниц**: уточнить `title` для каждой страницы или использовать динамические заголовки (`react-helmet` или `useEffect` + `document.title`).

---

## 📄 Recommended Next Steps

- **Разработчикам**: создать PR с исправлениями **Critical** (Issues 1–8). Начать с `components/Modal.tsx` (фокус-ловушка + `aria-modal`), затем `components/Toast.tsx` (`aria-live`), `components/Badge.tsx` (`aria-label`), `pages/Task.tsx` (`label` на `Input`), `components/Table.tsx` (клавиатура для строк), `components/Card.tsx` (`Space` + `aria-label`), `pages/Pipeline.tsx` (`aria-label` + `Space`), `pages/Overview.tsx` (`aria-label` на кнопках).
- **Дизайн-системе**: обновить `styles.css`: `--text-faint`, `prefers-reduced-motion`, размеры `.btn-sm`, `.nav-link`, `.user-btn`, `.tab`, `.agent-pick-item`.
- **Процесс**: добавить `axe-core` или `@axe-core/react` в CI/CD; создать accessibility acceptance criteria для новых компонентов (`Card`, `Badge`, `Modal`, `Table`, `Tabs`); провести повторный аудит после исправлений с реальным тестированием в NVDA/VoiceOver.
- **Повторный аудит**: назначить через 1 спринт после внедрения критических исправлений; проверить с реальным скрин-ридером (VoiceOver на macOS или NVDA на Windows) ключевые пути: `Обзор` → `Заказы` (открыть модал) → `LLM-фильтр` (ответить на отклик) → `Агенты` (отменить задачу) → `Мониторинг` (просмотреть логи).

---

## 📌 Appendix: Quick Reference — File/Line Index

| Файл | Строки | Проблема | Приоритет |
|------|--------|----------|-----------|
| `components/Modal.tsx` | 11–34 | Нет `aria-modal`, фокус-ловушки, `aria-labelledby` | Critical |
| `components/Drawer.tsx` | 1–32 | Аналогично `Modal` | Critical |
| `components/Toast.tsx` | 21–47 | Нет `aria-live` | Critical |
| `components/Badge.tsx` | 1–15 | Статус только цветом | Critical |
| `components/Card.tsx` | 10–27 | `Space` не обработан, `aria-label` отсутствует | Critical |
| `pages/Task.tsx` | 156 | `Input` без `label` | Critical |
| `components/Table.tsx` | 55–67 | Кликабельные строки без клавиатуры | Critical |
| `pages/Pipeline.tsx` | 82–104 | Узлы без `aria-label`, без `Space` | Critical |
| `pages/Overview.tsx` | 103–114 | Кнопки без `aria-label`, эмодзи | Critical |
| `components/Layout.tsx` | 118–128 | `NavLink` без `aria-current` | Important |
| `components/Tabs.tsx` | 13–29 | Нет стрелочной навигации | Important |
| `src/styles.css` | 4–29, 331–336, 418–423, 465–476, 825–831 | Контраст, анимации, размеры | Important |
| `pages/OrchestratorChat.tsx` | 48–49 | `input` и `button` без меток | Important |
| `pages/LLMFilter.tsx` | 288–305 | Переключатели (мелкая доработка) | Minor |
| `components/KanbanBoard.tsx` | 22–71 | Drag-and-drop без клавиатуры | Minor |
| `pages/FunnelMetrics.tsx` | 52–79 | KPI без `aria-label` | Minor |
| `public/favicon.svg` | 1 | Без `<title>` | Minor |
| `index.html` | 2, 7 | `lang="ru"` — OK; `title` — базовый | Minor |

---

*Отчёт составлен без внесения изменений в код (только аудит). Все ссылки на строки и файлы актуальны для текущей версии репозитория (`zarabotok/pipeline_v3/ui/src/`).*
