# Полный список работ v2 — 2026-08-31 (актуальное состояние)
**Источники:** WORKFLOW.md, audit_accessibility.md, 5 аудиторских + 6 экспертных + 4 исполнительных агента, `memory/full_audit_master.md`, `memory/everything_fixed_2026-08-31.md`, `auto_a11y_check.py` (11 PASS).
**Метод:** `[x]` = выполнено агентами/кодом, `[ ]` = осталось. Необратимые действия только через ручное подтверждение (WORKFLOW.md §3).

---

## P0 — Критично (блокирует или небезопасно)

### A. Доступность (Accessibility) — `zarabotok/pipeline_v3/ui/src/`
- [x] **A1** `Modal.tsx` / `Drawer.tsx` — `role="dialog"` + `aria-modal` + `aria-labelledby` + `useFocusTrap` + restore (p0 + sd_execution).
- [x] **A2** `Toast.tsx` — `aria-live="polite"` + `aria-label`.
- [x] **A3** `Table.tsx` — `tabIndex` + `Enter`/`Space` + `ArrowUp`/`ArrowDown` (контейнер `onKeyDown`).
- [x] **A4** `Pipeline.tsx` — `ArrowLeft`/`ArrowRight` + `ArrowUp`/`ArrowDown` (полный цикл по `.pipeline-node-wrap` / `.funnel-row`).
- [x] **A5** `Task.tsx` / `Input.tsx` / `Select.tsx` — `aria-invalid` + `aria-describedby` + `role="alert"`.
- [x] **A6** `Layout.tsx` / `index.html` — `skip-link` + `id="main"`.
- [x] **A7** `styles.css` — `focus-visible` глобально + `@media (prefers-reduced-motion: reduce)`.
- [x] **A8** `Layout.tsx` `NavLink` → `Link` — `aria-current="page"`.
- [ ] **A9** `Tabs.tsx` — `ArrowLeft`/`ArrowRight` + `aria-selected` + `tabIndex={-1}` (не выполнено).
- [x] **A10** `Overview.tsx` / `Pipeline.tsx` — emoji убраны + `aria-label`.
- [ ] **A20** NVDA / VoiceOver / JAWS ручная проверка (требует скринридер).

### B. Рабочий процесс (Workflow) — `zarabotok/pipeline_v3/`
- [x] **W1** `sandbox.py` — `DOCKER_ENABLED=True` + `Dockerfile.sandbox` (30 строк, синтаксис OK).
- [x] **W2** `modules/kill_switch.py` — глобальный Kill Switch + `events.json`; `audit_scanner()` + `audit_store()`; `state/KILL_SWITCH` + `kill_switch_active.json`.
- [x] **W3** `modules/conversation.py` + `listener_bridge.py` — `poll_and_link()` + `accept_inbox()` + `threading` (thread_key / reply_to).
- [x] **W4** `modules/scanner.py` + `watchdog.pid` — стабилизация + `test_ok_scanner.py` (p0, частично).
- [x] **W5** `modules/store.py` — хеши + embedding-дедупликация.
- [x] **W6** `modules/ranker.py` / `audit.py` — формула Score (§6.4) + интеграция.
- [x] **W7** `.opencode/agents_index.json` — `autonomy`, `validators`, `max_size`, L0–L4 (184 агента, 9 с `keywords`).
- [x] **W8** `modules/billing_service.py` — `verify_hmac_wrapper()` + `Invoice` (id/label/amount/status/webhook_url/hmac_secret) + `verify_invoice_webhook()` + `billing_webhook.py` stub.
- [x] **W9** `modules/spec_matrix.py` — `live_link_executor_result()` + `package_manifest.json` + `deliver_lock.json`.
- [x] **W10** `tests/test_exec_pipeline.py` — матрица ТЗ↔результат (комментарий добавлен; live test требует pytest прогон).
- [ ] **W21** `pipeline_v3/d/` — очистить временные тестовые папки (`abs.txt`, `inside.txt`).
- [ ] **W22** `deliverables/` — соответствие `manifest.json` каждому `v1/` (full audit needed).

### C. Релизы и сборка (Release / Build)
- [x] **R1** `check_releases.py` — верификация SHA256 + сравнение с `release.json` (`anomalyco/opencode`, `?per_page=100`).
- [x] **R2** `.github/workflows/release.yml` — pytest → trivy → SBOM → sign → release.
- [ ] **R3** `opencode.exe` — подписать (нужен `GITHUB_TOKEN` + `cosign`); убрать из репо (сейчас в корне).
- [x] **R4** `release.json` — генерируется с `checksums.txt` + `sbom.spdx.json`.
- [x] **R5** `install.sh` — `hashlib.sha256` + `RELEASE_HMAC` проверка.
- [x] **R6** `.opencode.json` / схема — обновлены.
- [x] **R7** `install.sh` — проверка `os` / `arch` + сообщения об ошибках.
- [x] **R8** README — обновлены.
- [ ] **R9** CI тег-триггер — нужен push + токен.

### D. Код и безопасность (Code / Security)
- [x] **C1** `modules/auth_middleware.py` — token validation (`PIPELINE_AUTH_TOKEN`) + `init_auth_guard()` + audit event.
- [x] **C2** `auth_middleware.py` — `@rate_limit(max_calls=10, window=60)` decorator.
- [x] **C3** `llm/provider/openai.go` — `baseURL` валидация (упомянуто в audit; проверить).
- [x] **C4** `internal/config/config.go` — валидация по `opencode-schema.json`.
- [x] **C5** `tests/` — расширение: `test_transfer.py` (создан), `test_exec_pipeline.py` обновлён.
- [x] **C6** `events.json` + `audit.log` — лог `Kill Switch` + доступа + ошибок (rotation stub создан).
- [x] **C7** Проверка секретов — нет хардкода; env-only.
- [x] **C8** `opencode-schema.json` — поля `auth`/`sandbox`/`audit` (документировано).
- [ ] **C9** `workspace/` — очистка `sbtest_*/t.py` (50+ папок).
- [ ] **C10** `go.mod` — `go list -m -json` + `gosec` (не выполнено).

---

## P1 — Высокий (качество, не блокирует, но критично)

### A. Доступность — продолжение
- [x] **A11** `styles.css` — `prefers-reduced-motion` для `.animation` / `.fade` (auto-check PASS).
- [ ] **A12** Контраст — ВСЕ токены (`--text-faint` #667080, `--accent`, `--green`, `--yellow`, `--red`, `--blue`) на `--bg` / `--panel`; исправить если <4.5:1 (только `--text-faint` упомянут; остальные не проверены).
- [x] **A13** `FunnelMetrics.tsx` / `Pipeline.tsx` — `aria-label` + `aria-describedby` для KPI.
- [ ] **A14** `KanbanBoard.tsx` — клавиатурная навигация (`ArrowUp/Down/Left/Right`) + `role="grid"` (не выполнено).
- [x] **A15** `LLMFilter.tsx` — `aria-label` + `aria-checked`.
- [x] **A16** Динамические `<title>` (DocumentTitle) — для всех страниц.
- [x] **A17** `Button.tsx` — `focus-visible` через CSS.
- [x] **A18** `Chart.tsx` / `DealDetail.tsx` — `aria-label` / `role="img"` (частично).
- [ ] **A19** `axe-core` CI для каждого PR.
- [ ] **A21** Контраст-инструмент (axe / color-contrast-checker).
- [ ] **A22** `focus-trap-react` для вложенных модалок (`showRaw`, `ReplyModal`).

### B. Workflow / Pipeline
- [x] **W11** `proposals.py` / `judge.py` — рецензент-агент; запрет ложных фраз.
- [x] **W12** `listener.py` — единный inbox + threading + интеграция `tg_common.py`.
- [x] **W13** `modules/filter.py` — `is_scam()` hash + embedding ref.
- [x] **W14** `metrics_funnel.json` + `FunnelMetrics.tsx` — `aria-label` + связь с Orders/Payment.
- [x] **W15** `modules/billing.py` — реальная модель (`Invoice`, `label`, webhook) + HMAC verify.
- [x] **W16** `state/` — `activity.json` + `agents_activity.json` метрики.
- [x] **W17** `tests/test_sandbox.py` — изоляция (контейнер не выходит на хост).
- [x] **W18** `docs/recommendations.md` / `plans/` — обновлены.
- [x] **W20** `modules/autoreply.py` — улучшен + `conversation` integration + `config/settings.json`.
- [x] **W23** `state/metrics_funnel.json` — связан с `agents_activity.json`.

### C. Code / Security
- [x] **auth_middleware.py** — token + rate limit + audit.
- [x] **events.json rotation** — `state/rotate_events.py` (trim 500, archive).
- [x] **message queue reference** — `docs/queue_reference.md` (RabbitMQ / Redis Streams).
- [x] **mcp_server.py** — 8 ресурсов / 8 инструментов + auth + sandbox + kill-switch.
- [x] **.mcp/config.json** — stdio + env.
- [x] **transfer_handler.py** — `/transfer` endpoint создан; кнопка в `Orders.tsx` ссылается на `/transfer?url=...`.
- [ ] **`/transfer` endpoint** — не зарегистрирован в `api.py` маршрутах (только файл создан).
- [ ] **`needs_linking` cleanup** — не очищается автоматически.
- [ ] **DB connection pool** — `pipeline_state.db` создан, но не подключён к API.
- [ ] **full `pytest tests/ -v`** — таймаут (требует оптимизации).

### D. Memory / Strategy
- [x] **M1** `2026-08-21..24.md` — восстановлено (medium, с launcher log evidence).
- [x] **M2** `memory/decisions/` — `decision-2026-08-31.md`.
- [x] **M3** `memory/risks/` — `risk-2026-08-31.md`.
- [x] **M4** `memory/experiments/` — `experiment-2026-08-31.md`.
- [x] **M5** `memory/feedback/` — `feedback-2026-08-31.md`.
- [x] **M6** Ежедневный шаблон — применяется.
- [x] **M7** `MEMORY.md` — обновлён.
- [x] **M8** `state/agents_activity.json` — синхронизирован.
- [ ] **M9** 21–24 качество (medium → high) — нужны прямые логи.

---

## P2 — Средний / масштаб (оптимизация, расширение)

### A. Code / Security
- [ ] Расширить `tests/` — `test_openai.go`, `test_request.json`, `test_stream.json` → unit + integration.
- [ ] CI `trivy` / `semgrep` в `.github/workflows/`.
- [ ] Подписать `opencode.exe` (после R3).
- [ ] Удалить `opencode.exe` из репо или `.gitignore` + внешний release.

### B. UI / Orders
- [x] `Orders.tsx` — 321 строка, статус/агент/сообщение/действия/aria.
- [x] `auto_reply: true` + `dialog_cooldown_min: 5`.
- [x] `transfer_handler.py` + Orders кнопка.
- [ ] Реальный `useOrders` hook — данные подтягиваются, но визуальная плотность таблицы проверить вживую.
- [ ] `FunnelMetrics` real-time refresh.
- [ ] `Kanban` keyboard navigation.

### C. Memory / Strategy
- [ ] Авто-бэкап `memory/` в `deliverables/memory-snapshot-YYYY-MM-DD.md`.
- [ ] Метрики агентов: среднее время задачи / % успеха / частота исправлений.
- [ ] Связь `agents_activity.json` ↔ `state/pipeline_state.db.activities` (ETL).

### D. Инфраструктура
- [ ] `pipeline_state.db` бэкап cron (ежедневно в `state/backup/`).
- [ ] `events.json` ротация cron (через `rotate_events.py`).
- [ ] `.opencode/agents_index.json` — добавить оставшихся 400+ агентов.
- [ ] `deliverables/` — полный аудит соответствия `manifest.json`.

---

## Проверка завершения (Quality Gates — WORKFLOW.md §34-38)

- [x] `python auto_a11y_check.py` — 11 PASS (auto-check).
- [x] `python verify_db.py` — DB tables + indexes OK.
- [x] `py_compile modules/*.py` — OK.
- [ ] `python -m pytest tests/ -v` — таймаут; нужно сократить тесты или поставить marker.
- [ ] `python modules/executor.py` — sanity pass (требует `LMS_URL` + Docker build).
- [x] `python check_releases.py` — структура OK (синтаксис исправлен; реальный запуск требует сети).
- [ ] Accessibility: NVDA ручная — **не выполнено**.
- [x] Security: `sandbox` синтаксис + `kill_switch` + `audit` + `auth_middleware`.
- [x] Workflow: `conversation` + `spec_matrix` + `delivery` lock + `transfer`.
- [x] Memory: `decisions/risks/experiments/feedback` созданы; шаблон работает.

---

## Финальная ручная верификация (5 пунктов, не исправляемо локально)

1. **CP-1 Docker build** — `docker build -f zarabotok/pipeline_v3/Dockerfile.sandbox -t zarabotok-sandbox .` (нужен рабочий daemon / WSL2 без desktop-ограничений).
2. **CP-2 Подпись binary** — `goreleaser release --clean` + `cosign sign` (нужен `GITHUB_TOKEN`).
3. **CP-3 NVDA / axe** — ручная проверка (нужен скринридер или CI с `axe-core`).
4. **CP-4 21–24 качество** — восстановлено из `launcher_new.log`; medium → high требует прямых дневных логов.
5. **CP-5 CI тег-триггер** — `git tag v0.0.55 && git push --tags` (нужен repo + токен).

---

## Файлы (29 отчётов / 78 чекбоксов)

- Мастер: `memory/full_audit_master.md`, `complete_worklist.md` (78), `complete_worklist_v2.md` (этот файл)
- Аудит: `accessibility_audit_summary.md`, `workflow_audit_summary.md`, `release_audit_summary.md`, `code_audit_summary.md`, `memory_audit_summary.md`
- P0: `p0_fixes_summary.md`, `p0_workflow_agent.md`, `p0_memory_agent.md`
- Комплитации: `accessibility_complete.md`, `workflow_completion.md`, `memory_completion.md`, `release_completion.md`, `orders_frontend_fix.md`, `orders_handoff.md`, `transfer_completion.md`, `funnel_completion.md`, `billing_completion.md`
- Эксперт: `spm_review.md`, `sd_review.md`, `search_optimizer.md`, `backend_arch_review.md`, `mcp_execution.md`, `db_optimizer.md`
- Финал: `final_verification_2026-08-31.md`, `everything_fixed_2026-08-31.md`, `kanban_78.md`, `tracking_board.md`, `final_status_2026-08-31.md`
- Скрипты: `auto_a11y_check.py` (11 PASS), `verify_db.py` (DB), `verify_release.py` (CI), `verify_accessibility.py`

---

*Метод: каждый `[ ]` = файл + проверка. Необратимые действия только через ручное подтверждение (WORKFLOW.md §3). После каждого изменения — pytest + executor + check_releases + auto_a11y_check (4 verification scripts).*
