# Полный список работ — исправить и дополнить всё (P0→P2)
**Источники:** WORKFLOW.md (14 этапов), audit_accessibility.md (479 стр), memory/accessibility_audit_summary.md, memory/workflow_audit_summary.md, memory/release_audit_summary.md, memory/code_audit_summary.md, memory/memory_audit_summary.md, memory/p0_fixes_summary.md, memory/full_audit_master.md.
**Метод:** каждый пункт = файл/строка + проверка. Необратимые действия только через ручное подтверждение (WORKFLOW.md §3).

---

## P0 — Критично (блокирует или небезопасно)

### A. Доступность (Accessibility) — `zarabotok/pipeline_v3/ui/src/`
- [ ] **A1** `Modal.tsx` / `Drawer.tsx` — проверить на реальном скринридере (NVDA/VoiceOver) `role="dialog"` + `aria-modal` + focus-trap + restore (сделано в p0; нужна верификация).
- [ ] **A2** `Toast.tsx` — проверить `aria-live="polite"` + `aria-label` звучание.
- [ ] **A3** `Table.tsx` — вертикальная стрелка `ArrowUp`/`ArrowDown` между строками (`tabIndex` + `onKeyDown`); сейчас только `Enter`/`Space`.
- [ ] **A4** `Pipeline.tsx` — полный `ArrowLeft`/`ArrowRight` DOM-цикл между нодами (сейчас placeholder; нужен `querySelectorAll('.pipeline-node-wrap')` + `focus()` на соседа).
- [ ] **A5** `Task.tsx` / `Input.tsx` / `Select.tsx` — `3.3.1` ошибка формы: `aria-invalid`, `aria-describedby` на ошибку, `role="alert"` (сейчас только цвет).
- [ ] **A6** `Layout.tsx` / `index.html` — `skip-link` (`<a href="#main">`) + `id="main"` на каждой странице (`2.4.1`).
- [ ] **A7** `styles.css` — `focus-visible` (`outline`) для всех интерактивных элементов (кнопки, ссылки, табы, карточки).
- [ ] **A8** `Layout.tsx` `NavLink` — `aria-current="page"` для активной ссылки.
- [ ] **A9** `Tabs.tsx` — `ArrowLeft`/`ArrowRight` + `aria-selected` + `tabIndex={-1}` для неактивных; вертикальный цикл (если нужно).
- [ ] **A10** `Overview.tsx` / `Pipeline.tsx` — убрать emoji или дать `aria-label` без emoji; тексты кнопок читаемы.

### B. Рабочий процесс (Workflow) — `zarabotok/pipeline_v3/`
- [ ] **W1** `sandbox.py` — `DOCKER_ENABLED=True`; создать `Dockerfile.sandbox`; изолировать `executor.py` / агентов (WORKFLOW.md §21).
- [ ] **W2** `modules/kill_switch.py` — реализовать глобальный Kill Switch + `events.json`; блокировка доставки/оплаты (WORKFLOW.md §25).
- [ ] **W3** `conversation.py` — интегрировать с `listener.py` + `tg_common.py`; единный `Conversation` сервис с `threading` (WORKFLOW.md §20).
- [ ] **W4** `modules/scanner.py` + `watchdog.pid` — стабилизировать `watchdog`; `test_ok_scanner.py` проходит; устранить ошибки сканирования.
- [ ] **W5** `modules/store.py` — формализовать хеши + embedding-дедупликация (`is_scam`); устранить дубли.
- [ ] **W6** `modules/ranker.py` / `audit.py` — внедрить формулу Score (§6.4); проверить корректность ранжирования.
- [ ] **W7** `.opencode/agents_index.json` — добавить `autonomy`, `validators`, `max_size`; уровни L0–L4 для каждого агента (WORKFLOW.md §18).
- [ ] **W8** `modules/billing_service.py` — `verify_hmac()` подключить к `billing.py`; модели `Invoice` + `label`; webhook ЮMoney / ЮKassa (WORKFLOW.md §24).
- [ ] **W9** `modules/executor.py` + `spec_matrix.py` — живая матрица ТЗ↔результат (`package_manifest.json` + `deliver_lock.json`) (WORKFLOW.md §22).
- [ ] **W10** `tests/test_exec_pipeline.py` — добавить матрицу проверки соответствия (§11.6).

### C. Релизы и сборка (Release / Build)
- [ ] **R1** `check_releases.py` — прошёл верификацию (p0 исправлен); теперь добавить в CI.
- [ ] **R2** `.github/workflows/` — создать pipeline: test (`pytest`) → vuln-scan (`trivy`/`semgrep`) → SBOM → sign (`goreleaser`/`sigstore`) → release (`releases/`).
- [ ] **R3** `opencode.exe` — подписать (`.goreleaser.yml` + `signs`); убрать из репо или добавить `.gitignore`; проверять происхождение.
- [ ] **R4** `release.json` — генерировать автоматически; включать `checksums.txt`, `sbom.spdx.json`.
- [ ] **R5** `install.sh` — проверять SHA256/HMAC `release.json` / binary перед установкой.

### D. Код и безопасность (Code / Security) — `opencode-src/`
- [ ] **C1** `internal/auth/` или `cmd/` — auth middleware (API-key / token); проверка перед вызовом LLM.
- [ ] **C2** Rate limit — middleware или `internal/limit/` для запросов.
- [ ] **C3** `llm/provider/openai.go` — валидация `baseURL`; запрет неожиданных endpoint.
- [ ] **C4** `internal/config/config.go` — валидация входных параметров по `opencode-schema.json`.
- [ ] **C5** `tests/` — расширить (`test_openai.go`, `test_request.json`, `test_stream.json` → unit + integration + security).
- [ ] **C6** `audit.log` / `events.json` — лог всех событий `Kill Switch`, доступа, ошибок.
- [ ] **C7** Проверка секретов — `grep -rni 'token\|secret\|password\|api_key'` в репо (кроме `.env.example`).

---

## P1 — Высокий (следующий спринт, без блокировки, но критично для качества)

### A. Доступность (Accessibility) — продолжение
- [ ] **A11** `styles.css` — `@media (prefers-reduced-motion: reduce)` для `.animation` / `.fade` (строки 465-476, 825-831).
- [ ] **A12** Контраст — проверить ВСЕ токены (`--text-faint` #667080, `--accent`, `--green`, `--yellow`, `--red`, `--blue`, `--text`) на `--bg` / `--panel`; исправить если <4.5:1.
- [ ] **A13** `FunnelMetrics.tsx` / `Pipeline.tsx` (122-142) — `aria-label` для KPI-контейнеров + `aria-describedby` связывание `.kpi-label` → `.kpi-value`.
- [ ] **A14** `KanbanBoard.tsx` — клавиатурная навигация (`ArrowUp`/`ArrowDown`/`Left`/`Right`) + `role="grid"` или `application`; drag с `Space`.
- [ ] **A15** `LLMFilter.tsx` (288-305) — `aria-label` для переключателей + `aria-checked`.
- [ ] **A16** `index.html` / страницы — динамические `<title>` (`Overview`, `Pipeline`, `Billing`, `Orders`).
- [ ] **A17** `Button.tsx` — убедиться, что `focus-visible` работает (если не, добавить CSS).
- [ ] **A18** `Chart.tsx` / `DealDetail.tsx` — `aria-label` / `role="img"` + текстовая альтернатива графиков.

### B. Рабочий процесс (Workflow) — продолжение
- [ ] **W11** `proposals.py` / `judge.py` — рецензент-агент (`reviewer`); запрет ложных фраз (`false_alarms`).
- [ ] **W12** `listener.py` — единный `inbox` с `threading`; интеграция `tg_common.py`.
- [ ] **W13** `modules/filter.py` — формализовать `is_scam`; использовать `embedding` + хеш.
- [ ] **W14** `dashboard` / `ui/` v7 — агрегировать метрики из `Order` + `Payment`; `metrics_funnel.json`; `MetricsFunnel.jsx`; единная воронка.
- [ ] **W15** `modules/billing.py` — заменить заглушки на реальную модель (`Invoice`, `label`, webhook); проверка HMAC.
- [ ] **W16** `state/` — стабилизировать `watchdog.pid`; `activity.json`; `agents_activity.json` для метрик агентов.
- [ ] **W17** `tests/test_sandbox.py` — проверить изоляцию (контейнер не выходит на хост).
- [ ] **W18** `docs/recommendations.md` / `plans/` — обновить планы после исправлений.

### C. Релизы / Build — продолжение
- [ ] **R6** `opencode-scheme` / `.opencode.json` — обновить при смене схемы / верси.
- [ ] **R7** `install.sh` — проверка `os` / `arch`; сообщение об ошибках; fallback.
- [ ] **R8** `README.md` / `opencode-src/README.md` — обновить инструкции по установке, безопасности, аудиту.

---

## P2 — Средний / масштаб (оптимизация, расширение)

### A. Доступность
- [ ] **A19** Полная проверка `axe-core` CI для каждого PR.
- [ ] **A20** Мануальная проверка NVDA / VoiceOver / JAWS на ключевых страницах (Pipeline, Order, Billing).
- [ ] **A21** Контраст-верификация через инструмент (`axe` или `color-contrast-checker`).
- [ ] **A22** `focus-trap` библиотека (`focus-trap-react`) для вложенных модалок (`showRaw`, `ReplyModal`).

### B. Workflow / Pipeline
- [ ] **W19** `.opencode/agents_index.json` — полный каталог 400+ агентов с `autonomy`, `validators`, `max_size`.
- [ ] **W20** `modules/autoreply.py` / `chat.py` — улучшить автоответ; интеграция с `conversation`.
- [ ] **W21** `pipeline_v3/d/` — очистить временные тестовые папки (`abs.txt`, `inside.txt`);
- [ ] **W22** `deliverables/` — проверить соответствие `manifest.json` каждому `v1/`; исправить несоответствия.
- [ ] **W23** `state/` — создать `metrics_funnel.json`; связать с `agents_activity.json`.

### C. Code / Security
- [ ] **C8** `opencode-schema.json` — добавить валидацию `auth`, `sandbox`, `audit`.
- [ ] **C9** Безопасность `workspace/` — очистить временные `sbtest_*/t.py`; ограничить права доступа.
- [ ] **C10** `go.mod` — обновить зависимости; проверить уязвимости (`go list -m -json` + `gosec`).

### D. Memory / Strategy
- [ ] **M1** `memory/2026-08-21.md` … `2026-08-24.md` — восстановить или объяснить пробел.
- [ ] **M2** `memory/decisions/` — создать `decision-YYYY-MM-DD.md` с проблемой, вариантами, выбором, результатом.
- [ ] **M3** `memory/risks/` — `risk-YYYY-MM-DD.md`; вероятность / влияние / уменьшение.
- [ ] **M4** `memory/experiments/` — регистр экспериментов (гипотеза → метод → результат → вывод).
- [ ] **M5** `memory/feedback/` — обратная связь из `deliverables/` / `chat` → действие.
- [ ] **M6** `memory/YYYY-MM-DD.md` — шаблон с полями: что сделано, что заблокировано, что дальше, агенты, ссылки на `state/`/`deliverables/`.
- [ ] **M7** `MEMORY.md` — обновить с решениями из этого аудита; добавить ссылку на `full_audit_master.md`.
- [ ] **M8** `state/agents_activity.json` — метрики агентов (скорость, точность, исправления); связать с `memory/`.

---

## Проверка завершения (Quality Gates — WORKFLOW.md §34-38)

- [ ] `python -m pytest tests/ -v` — без ошибок.
- [ ] `python modules/executor.py` — sanity pass.
- [ ] `python check_releases.py` — OK (верификация SHA256 + совпадение с `release.json`).
- [ ] Accessibility: `axe-core` CI + ручная проверка 8 критических + `Arrow`-цикл + `focus-visible` + `skip-link`.
- [ ] Security: `sandbox` изоляция + `kill_switch` активен + `audit` лог + auth middleware.
- [ ] Workflow: `conversation` работает + `spec_matrix` живой + `delivery` заблокирован без подтверждения.
- [ ] Memory: нет пробела >2 дней; есть `decisions/` + `risks/` + `experiments/` + `feedback/`; связь с `state/` и `deliverables/`.

---

## Ссылки на отчёты и исправленные файлы

- `memory/full_audit_master.md` — общий мастер-отчёт (все направления, агенты, план P0-P2).
- `memory/p0_fixes_summary.md` — что исправлено в P0 (accessibility 8 крит + release).
- `memory/accessibility_audit_summary.md` — детально по WCAG 2.1 AA.
- `memory/workflow_audit_summary.md` — 14 этапов, gaps, рекомендации.
- `memory/release_audit_summary.md` — проверка релизов, CI, подписывание.
- `memory/code_audit_summary.md` — архитектура, безопасность, тесты.
- `memory/memory_audit_summary.md` — стратегия, пробелы, регистры.
- Исправленные исходники: `zarabotok/pipeline_v3/ui/src/components/Modal.tsx`, `Drawer.tsx`, `Toast.tsx`, `Badge.tsx`, `Card.tsx`, `Pipeline.tsx`, `Table.tsx`, `Task.tsx`; `check_releases.py`.
- Не исправлено / требует следующего шага: `Arrow`-цикл `Pipeline`, контраст, `reduced-motion`, `skip-link`, `sandbox`, `conversation`, `billing`, `metrics_funnel`, `memory/decisions/` и т.д. (см. список выше).

---

*Учёт: если пункт требует изменения кода клиента или доставки — только через ручное подтверждение оператора (WORKFLOW.md §3). После каждого изменения запускать проверку (§36-38).*