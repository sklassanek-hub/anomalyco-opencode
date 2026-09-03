# Pipeline v3 — статус

**Дата:** 2026-08-16 ~22:15 (вечер, MVP-сессия)

## Дашборд v4 SPA — ГОТОВ (все 7 шагов MVP закрыты)

- **API** (JSON): GET /api/overview | orders | order/<url> | chat/<url> | finance | agents | settings; POST /api/scan, /api/chat/<url>/reply|read, /api/order/<url>/status|meta|approve|regen|dismiss|edit|read, /api/settings.
- **Фронт**: SPA vanilla JS — меню (Обзор/Заказы/Переписка/Платежи/Агенты/Настройки), модалка-карточка заказа (CRM-статус, оплата, переписка 2-сторонняя с reply, черновик + action'ы, файлы, лог агентов), badge непрочитанных.
- Старые POST-роуты v3 работают; старая страница — `/legacy`. QR-вход на месте.
- **Тесты**: все эндпоинты зелёные (reply → чат, статус туда-обратно, edit→revert, URL с слэшами t.me/..., 404). JS проверен node --check. py_compile OK.
- Воркеры: 1×watchdog + 5 (scanner/orchestrator/sender/listener/dashboard) — все живы; прокси 4067, LM Studio qwen2.5-omni-3b на 1234.
- Состояние: jobs 188, drafts ~115, contacts 11, approved=0, won=1 (тест u1, 15000 ₽, оплачен).

**Уроки:** url заказов кодировать encodeURIComponent (слэши в пути); в Python-тройных кавычках `\'` ломает JS — только data-атрибуты/CUR; state-файлы править ТОЛЬКО Python'ом (PowerShell портит кодировку и пишет BOM); pid-файл watchdog = `watchdog.pid` без .py.

---

**Дата:** 2026-08-16 ~18:20 (вторая половина сессии)

## Консолидация агентов/скиллов в рамках проекта (сделано)

- **184 субагента** скопированы из `Downloads/agency-agents-main/agency-agents-main/.opencode/agents/` в `zarabotok/.opencode/agents/` (BOM убран у 169 файлов — критично для парсинга frontmatter).
- **37 скиллов** (azure, archon, genkit, webapp-testing, marketing-ideas...) из `Downloads/skills/` → `zarabotok/.opencode/skills/`.
- **Индекс**: `zarabotok/.opencode/AGENTS.md` (264 строки, категории: Инженерия 90, Продажи 23, Маркетинг 23, QA 13, Дизайн 9 и т.д.) + `agents_index.json` (генерируется `gen_agents_index.py`).
- **Дубль для runtime** (рабочая директория opencode = `work\`): `work/.opencode/agents/` (184) + `skills/` + `AGENTS.md`.
- Глобальные каталоги НЕ тронуты (`.config/opencode/agent` — 49 активных, `.claude/agents` — 187 бэкап-дублей).
- **Восстановление после перезагрузки ПК**: Watchdog умер (pid 7240 ложный/мёртв) — поднят новый (15556), все 6 воркеров перезапущены, dashboard 200 OK (274 КБ). Из важного: watchdog.pid был перезаписан вручную, и если dashboard не отвечает — проверять именно watchdog процесс.

## Состояние на 18:20

- outbox: 102 черновика, 8 с контактом (все скам-посты: криптообмен/казино/реклама-GG — заблокированы стоп-словами), approved=0, sent=0.
- 6 воркеров живы: watchdog 15556, scanner 11904, orchestrator 13032, sender 15944, listener 13508, dashboard 14272.
- Дальше по плану: полный дизайн SPA-дашборда v4 (утверждён: CRM-карточки, двусторонняя переписка, материалы, платежи, агенты, настройки, режимы) — в процессе проектирования, НЕ начат.

---

# История (ранее в сессии)

**Дата:** 2026-08-16 ~16:50

## Что сделано в этой сессии

1. **Сканер TG через API (Telethon)** — новый `modules/tg_scrape.py`:
   - `contact_of()` — умное определение контакта: берёт только @ник/почту из предложений с ask-словами, отбрасывает рекламные маркеры и посты-резюме.
   - Каналы: `freelancechoice`, `Koteyka_Freelancer`, `freelance_chat_ru` в `TG_API_CHANNELS`.
   - Один Telethon-клиент на всех каналов (прошлые SOCKS-ошибки устранены паузами/ретраями).

2. **Исправлена гонка записи outbox** (критично): sender каждые 60 с перезаписывал свою устаревшую копию и затирал новые черновики с контактами (89 → 74). Причина — кэш в `store.py` + load→save без блокировки. Решение:
   - `store.py`: убран `_cache`, добавлен кросспроцессный `msvcrt`-лок и атомарный `store.mutate(name, fn)`.
   - `proposals.build_outbox`, `sender.run_cycle`, `dashboard.edit_item` переведены на `mutate`.
   - Проверено: 2 процесса по 60 записей → 120/120 без потерь.

3. **Защита от скама в автоотправке**:
   - В `auto_approve` стоп-слова проверяются по title + text (раньше только title).
   - config `sender.stopwords` расширен: вложени/криптообмен/anydesk/нейросети-схемы/«в день» и т.п.
   - Итог: из 5 черновиков с контактами все были скам-постами — ни один не одобрен, не ушёл. approved=0, sent=0 — ожидаемо и правильно.

## Текущее состояние

- 6 воркеров живы (watchdog 7240, scanner 2276, orchestrator 9724, sender 20840, listener 17004, dashboard 14656).
- Дашборд: HTTP 200, ~206 КБ (переписан: тёмная тема, статистика, воркеры, черновики, настройки GSM/Gmail).
- jobs: 136 заказов в скане (FL 30, Habr 30, freelance.ru 21, TG-API 15, остальные TG-веб), errors=0.
- outbox: 89 черновиков, из них 5 с контактом (все скам → заблокированы), approved=0, sent=0.
- Gmail подключён (smtp/imap aprenkavuj@gmail.com, app-пароль в settings), tg_poll=True.

## Заметки

- Перезапуск воркера: наблюдаем и держим watchdog. При правке `.py` — убить pid, watchdog поднимет.
- Известная слабость: веб-каналы t.me/s часто дают SOCKS-ошибки, API-каналы стабильны → приоритет расширять TG_API_CHANNELS.
- На будущее: кандидаты в TG_API_CHANNELS — digitalrabota, llm_jobs (проверены, дают контакты), farpost-like, fl_cat_channels.

## Executor (16.08 ночь) — выигранный заказ → агенты коллекции
- modules/executor.py: каталог = zarabotok/.opencode/agents_index.json (184 агента, {file,name,desc}); pick_agents(tz) по ключам; задачи state/exec_tasks.json; артефакты deliverables/<safe_url>/plan.md.
- Dashboard: GET /api/exec, POST /api/order/<url>/execute; автосоздание при status=won; модалка: секция «Исполнение агентами» + кнопка «🚀 Передать агентам» (disabled при queued/running).
- Тесты зелёные (API + CDP-браузер), тестовые следы откачены. Индекс содержит 184 агентов (не 400: 400 = сумма дублей agency+claude+opencode — см. MEMORY.md «Инвентарь»).
- TODO: реальное исполнение queued-задач (TDD + субагенты), интеграция в обмен с заказчиком (результат → клиенту), тайм-ауты/ретраи задач.