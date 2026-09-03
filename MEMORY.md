# MEMORY.md — долгосрочная память (обновлено 2026-08-27)

## Проект: Zarabotok (фриланс-автоматизация)

**Пути:**
- Код: `C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline_v3\` (v3 — живая версия)
- Легаси (мёртв, .py пропали, только .pyc): `zarabotok\pipeline\` и `zarabotok\pipeline_old_20260802\`
- Git-репо = `C:\` — коммитов почти нет. **ЖИЗНЕННО: после любой работы фиксировать память в `work\memory\YYYY-MM-DD.md` и этот файл, т.к. при перезагрузке ПК контекст сессии теряется.**

## Архитектура pipeline_v3 (рабочая! обновлено 27.08)
- **modules/**: `store.py` (JSON-хранилище с msvcrt-локом + `mutate()`, единый источник настроек: `config.dashboard` ↔ `state/settings.json` мерджит/зеркалит; НЕ удалять mutate — гонки затирают outbox), `scanners.py` (fl.ru, freelance.ru, habr, weworkremotely, TG веб + API-каналы + VK/OK сканеры), `tg_scrape.py`, `ranker.py`, `proposals.py` (build_outbox с скам-гейтом is_scam + гомоглифы), `sender.py` (auto_approve + стоп-слова + QA-гейт judge + тихие часы 23-08 + KILL_SWITCH), `http_client.py` (socks5 4067 с _proxy_alive fallback на прямой IP), `tg_auth.py`, `tg_common.py` (session_path + tg_lock), `report.py` (daily digest), `billing.py` (check_usdt_payments + заглушка check_yoomoney), `executor.py` (честный pipeline plan→gen→validate→lint→sandbox→review), `matcher.py` (nomic embeddings), `sandbox.py` (JobObject песочница без Docker).
- **workers/** (7 процессов): scanner (15 мин, TG+sources+fl_rss), orchestrator (5 мин, light_score + embedding boost), sender (60с, TG/email/FL-bidder, daily caps, random delay), listener (5 мин, TG+почта+FL + SLA-push 30мин + daily report 09:00), dashboard (127.0.0.1:8765, SPA v7 shadcn светлая, канбан, график /api/activity_days), api.py (127.0.0.1:8766, 24 эндпоинта + /api/system/stop|resume), exec_worker (PARALLEL 1, runtime QA), watchdog (с daily digest и tunnel diagnostics).
- **state/**: jobs.json, outbox.json, seen_jobs.json, settings.json (legacy, зеркалится в config.dashboard), tg_auth.json, *.pid / *.out.log / *.err.log, last_scan.json, fl_paid.json, sent_texts, watchdog.log.
- **config.json**: skills 277 (расширен маркетинг/дизайн/юриспруденция), sender (max_per_hour 8, max_per_day 30, delay 45-180с, quiet_hours, fl_auto_bid), dashboard {tg_poll, show_vacancies, auto_reply}, executors (omnicoder 9b единая модель, runtime_qa true, nomic embed), payment (ЮMoney, карта, USDT), proxy.enabled false (upstream мёртв, прямой IP), tg, storage postgres type, ui.

## Ключевые решения/уроки
- **Эта система НЕ для откликов на резюме-посты и скам**: контакты в TG-каналах в основном мусор (рекламные боты/скам-схемы) — отсекаем стоп-словами и contact_of() (ask-слова + reject-маркеры #резюме/#помогу/#вакансия и т.д.). Автоотправка: только approved + tg/email-канал + реальный контакт.
- **QR-вход Telegram**: tools/qr_cli.py (автообновление токена ~45 сек, state/qr.png + qr_status.txt). Аккаунт @aleksandr_kisilev_1999 авторизован ПОЛНОСТЬЮ (check_auth=True).
- **Gmail**: код TOTP 634015 НЕ работает для SMTP (534) — нужен пароль приложения (уже в settings).
- **Скам-сигналы**: «вложени», «криптообмен», «anydesk/rustdesk», «нейросети-схемы», «в день», «в час» — в stopwords.
- Сканы стабильны: 127–139 заданий/запуск, errors=0 при работающем sing-box.
- Дашборд v4 SPA ГОТОВ (16.08 вечер, см. дневник): workers/dashboard.py = JSON API + SPA-фронт + старые POST-роуты + /legacy. Эндпоинты: /api/overview|orders|order/<url>|chat/<url>|finance|agents|settings (GET), POST /api/scan, /api/chat/<url>/reply|read, /api/order/<url>/status|meta|approve|regen|dismiss|edit|read, /api/settings. Карточка заказа = модалка (CRM-статус, оплата, переписка 2-сторонняя, черновик, файлы, агенты).
- **Executor (16.08 ночь):** modules/executor.py — выигранные заказы → задачи агентам коллекции. Каталог: `zarabotok/.opencode/agents_index.json` (184 агента: {file,name,desc} по категориям). `pick_agents(tz)` — подбор по ключевым словам ТЗ (парсер→data-engineer+ai-engineer+backend-architect; ai/видео→ai-engineer+mcp-builder+technical-artist; сайт/tilda→cms+frontend+senior-dev; бот→backend-architect; девопс→devops-automator+sre; fallback=senior-dev+backend+ai). Задачи: state/exec_tasks.json (queued|running|done|failed), артефакты в `pipeline_v3/deliverables/<safe_url>/` c plan.md. API: GET /api/exec, POST /api/order/<url>/execute, автосоздание при status=won (source=auto:status=won, идемпотентно). Кнопка «🚀 Передать агентам» в модалке + секция «Исполнение агентами».
- **API-роутинг с URL заказов (слэши!)**: url в пути API кодируется encodeURIComponent, сервер разбирает urllib.parse.unquote + endswith-суффиксы; НЕ ломать (иначе 404 на t.me/... урл). В onclick НЕ подставлять url напрямую — только `data-u` атрибут + `openOrder(this.dataset.u)`.
- **JS в Python-тройных кавычках**: `\'` превращается Python'ом в `'` и ломает JS-строки — нельзя inline `onclick="f(\'x\')"`, только data-атрибуты или глобальная переменная (CUR). Проверка: извлечь <script> и node --check.
- **Отладка SPA**: headless Chrome (`--remote-debugging-port` + Start-Process, не --dump-dom — тот не ждёт fetch) + node WebSocket-клиент CDP: Runtime.evaluate + Runtime.exceptionThrown/Log.entryAdded. См. `$env:TEMP\opencode\cdp_full4.js` — шаблон. Помогло найти 3 бага v4: рассинхрон ключей API («stats» vs «st» в overview/orders) и onclick без кавычек.
- **POST-body с кириллицей**: PowerShell Invoke-RestMethod и даже python -c ПОРТЯТ русский текст (консоль cp866/cp1251) — для тестов слать UTF-8-клиентом из файла (python/jscript); сервер читает body как UTF-8 и не виноват. Диагностика: socket-echo-сервер.
- **executor**: create_exec_task идемпотентен (существующая активная задача возвращается как есть — tz не обновляется); /api/orders отдаёт {rows, st, unread_total}; после правок modules/* перезапускать dashboard (RULES грузятся при импорте).
- dashboard отдаёт `Cache-Control: no-store` на всё — старый SPA в браузере не залипает.
- watchdog: pid-файл называется `watchdog.pid` (без .py) — dashboard читает его отдельно; дубль watchdog возможен после ручных подъёмов — гасить старые. При ручном старте запускать через launcher.py (пишет pid), иначе Start-Process не обновит watchdog.pid.

## Пользователь (владелец)
- Имя: Александр. Работает с opencode (power user). Требует: полный контроль, всё в рамках проекта, **все действия фиксировать** (память отшибает при перезагрузке ПК), качество > количества. Раздражается на «убогий» UI и незавершённые задачи.
- Цель: автономная система заказов с CRM, двусторонней перепиской, оплатами, агентами (внутренними + opencode-субагентами через LM Studio), дашбордом-контрольной панелью.

## Инвентарь агентов/скиллов на ПК (полный, сессия 16.08 вечер)
- `Downloads\agency-agents-main\agency-agents-main\` — **ОСНОВНОЙ архив**: 168 субагентов в `.opencode\agents\` (формат opencode: name/description/mode: subagent/color), категории: engineering(29), marketing(30), specialized(41), sales(8), testing(8), design(8), game-development(5), finance(5), product(5), support(6), academic(5), paid-media(7), project-management(6), spatial(6), strategy(3), integrations(1). ВСЕГО ~594 md.
- `~/.claude/agents/` — 187 (дубликаты тех же, префиксы engineering-/marketing- и т.д.).
- `~/.config/opencode/agent/` — 49 активных (подмножество тех же).
- `~/.config/opencode/skill/` — 14 скиллов superpowers (установлены).
- `Downloads\skills\skills\` — 37 скиллов НЕ установлены: azure ×26, archon ×6, genkit, webapp-testing, marketing-ideas, js-code-sandbox, find-skills.
- Маркетплейс claude-plugins-official: 243 плагина, 68 агентов, 1699 скиллов (установлен только superpowers 6.1.1).
- `Downloads\superpowers-6.1.0.zip` — тот же superpowers.
- Итог: «~400 агентов» = agency(168) + claude(187) + opencode(49) — дубли одного набора.
- **Консолидация (решение владельца): всё в рамках проекта zarabotok (папки .opencode/ в проекте), индексы и NOTES.md, глобально НЕ крошить.**

## Прочее (обновлено 27.08)
- sing-box: `pipeline\tools\singbox\config.json` (4067) — автозапуск через `autostart.bat` в Startup; http_client._proxy_alive() фолбэк на прямой IP если upstream мёртв (проверено 26.08: General SOCKS failure при открытом порте). Проверка: `python run.py status` (socks OK/DOWN) и `state/last_scan.json`.
- LM Studio: http://127.0.0.1:1234/v1, модели консолидированы на omnicoder-qwen3.5-9b (writer/judge/qa/light единая, без свопов в 8GB VRAM), embed nomic 84M. Требуется CUDA 12 runtime (RTX 3070) + GPU Offload=Max, иначе ~4 tok/s на CPU (было 4.8). Jan backup 1337.
- Восстановление после перезагрузки: autostart.bat (sing-box → lms server start → watchdog) → watchdog поднимает 7 воркеров; pid-файл watchdog правится Get-CimInstance; QR-сессия `telegram_session_sender.json.session` (@aleksandr_kisilev_1999) — НЕ ТРОГАТЬ.
- Дашборд: единственный UI на 8765 (светлая shadcn, канбан, график активности /api/activity_days, SPA без бэкслешей); 8766 редиректит на 8765.
- Kill Switch: POST /api/system/stop → state/KILL_SWITCH → sender стоп; /resume снимает.

---

## Memory audit conclusions (2026-08-31) — обновлено с `memory/memory_audit_summary.md`
- **Audit source:** `memory/memory_audit_summary.md` (StrategicMemoryAuditor, 2026-08-31) — full file read, cross-check with `memory/2026-08-16.md`, `2026-08-17.md`, `2026-08-18.md`, `2026-08-19.md`, `2026-08-20.md`, `2026-08-25.md`, `2026-08-27.md`, `WORKFLOW.md`, 4 audit summaries.
- **Readiness score:** 3/5 — excellent technical architecture, audit culture (4 audit summaries + version tracking + test counts), recovery practices (reboot checklist verified 08-20, 08-25, 08-27); but memory layer incomplete (missing 08-21→08-24, no structured decision/risk/experiment/feedback artifacts, weak backlinks).
- **Highest-return actions completed (this session):**
  1. Close gap 21-24 (`memory/2026-08-21.md` … `2026-08-24.md`) — reconstructed from 20.md morning addendum (line 47-55), 25.md rebuild prerequisites (§1, §8 08:43 first real send), audit gap descriptions (`memory_audit_summary.md` §2.1), `launcher_new.log` metadata (30.08 21:15, 14852 lines), `state/agents_activity.json` (start 27.08). Explicit gap notes included.
  2. Create 4 artifact folders and first entries (`memory/decisions/decision-2026-08-31.md`, `memory/risks/risk-2026-08-31.md`, `memory/experiments/experiment-2026-08-31.md`, `memory/feedback/feedback-2026-08-31.md`).
  3. Enforce daily template (`memory/2026-08-31.md` updated; reconstructed 21-24 include template sections with reconstruction notes).
  4. Update `MEMORY.md` with audit conclusions + link to `memory/full_audit_master.md`; reference reconstructed days, artifact folders, state sync.
  5. Sync `state/agents_activity.json` → `memory/agent_activity_2026-08-31.md`; `MEMORY.md` references sync.
  6. Verify all steps in `memory/memory_completion.md` (dates, links, formats).
- **Link to master audit:** `memory/full_audit_master.md` — all directions (accessibility, workflow, release, code, memory) reconciled.
- **Link to audit sources:** `memory/workflow_audit_summary.md`, `memory/code_audit_summary.md`, `memory/release_audit_summary.md`, `memory/accessibility_audit_summary.md`, `memory/memory_audit_summary.md`.
- **Next recommended action:** Verify `memory/2026-09-01.md` against `template_daily.md`; run first MemoryAudit check (`memory/memory_audit_summary.md` §6.5); confirm `state/agents_activity.json` continuity; maintain 2+ consecutive complete daily notes.

## Memory artifact index (2026-08-31)
- `memory/2026-08-21.md` — RECONSTRUCTED (source: 20.md 47-55 + 25.md §1 + audit)
- `memory/2026-08-22.md` — RECONSTRUCTED (inferred from watchdog patterns + continuous operation)
- `memory/2026-08-23.md` — RECONSTRUCTED (pre-rebuild state from 25.md prerequisites)
- `memory/2026-08-24.md` — RECONSTRUCTED (quiet/preparation day before 25.08 rebuild)
- `memory/decisions/decision-2026-08-31.md` — filled (audit gaps, sequential vs batch, master list created)
- `memory/risks/risk-2026-08-31.md` — filled (medium/high, agent audit + checklists, mitigated)
- `memory/experiments/experiment-2026-08-31.md` — filled (parallel agents, 5 audits/1 session, valid)
- `memory/feedback/feedback-2026-08-31.md` — filled (audit source, worklist implemented, MemoryRecoveryAgent)
- `memory/agent_activity_2026-08-31.md` — sync file referencing `zarabotok/pipeline_v3/state/agents_activity.json`
- `memory/memory_completion.md` — verification file (all created files + date/link/format checks)
- `memory/2026-08-31.md` — session record with M1-M8 execution + template compliance verification

## State sync (M8)
- Source file: `zarabotok/pipeline_v3/state/agents_activity.json` (404 lines; items from 27.08 18:56 through 30.08 21:07: crm, executor, exec_worker actions, pipeline runs, validation/repair cycles, review waits).
- Sync file: `memory/agent_activity_2026-08-31.md` — summarizes key agents (crm: draft→won→reply; executor: task creation; exec_worker: pipeline plan→implement→validate→repair; review wait at 03:43/04:00/21:07).
- Link from MEMORY.md to sync verified; link from 31.md to sync verified.