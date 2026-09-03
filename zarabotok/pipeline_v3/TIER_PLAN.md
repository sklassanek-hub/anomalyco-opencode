# Соответствие ТЗ «Автономный фриланс-конвейер» — план приведения pipeline_v3

Статус этапов: [ ] не начат, [~] в работе, [x] готово.

## Этап A. Слой данных (PostgreSQL)
- [x] A1. Запуск чистого инстанса PostgreSQL (порт 5433, БД `pipeline`, роль pipeline/pipeline). datadir: `C:\Users\klass\OneDrive\Desktop\work\zarabotok\pgdata`.
- [x] A2. Драйвер psycopg (psycopg[binary] 3.3.4) — `modules/storage.py`: тот же интерфейс, что у store.py (load/save/mutate/append/now/_path), коллекции = таблицы `kv` (jsonb) + `events` (append-лог).
- [x] A3. Авто-импорт существующих state/*.json в PG при первом старте (идемпотентно; 20/20 коллекций совпали).
- [x] A4. Переключение store.py на storage (флаг `storage.type: "postgres"` в config.json, фолбэк JSON при недоступности).
- [x] A5. Верификация: funnel/status на живых данных, перезапуск воркеров (14:22 19.08).

## Этап B. Конфиг + логи + мониторинг (из ТЗ п.3)
- [x] B1. Единый config.json — единственный источник истины; dashboard-настройки (tg_poll, show_vacancies, auto_reply) теперь в config.dashboard, store.load("settings") мерджит legacy (27.08, modules/store.py _dashboard_cfg/_persist_dashboard_to_cfg).
- [x] B2. Структурированные JSON-логи: `modules/logger.py` (logs/YYYY-MM-DD.jsonl + события в events).
- [x] B3. health-check: dashboard :8765/health (все воркеры, PG, LM Studio, IMAP/SMTP, socks), watchdog пишет метрики в metrics.
- [x] B4. Алерты: при падении воркера/PG — событие warning в events (watchdog).

## Этап C. Очереди и надёжность (ТЗ п.3: RabbitMQ/Redis — заменяем на PG-очередь, без Docker)
- [x] C1. Retry с экспоненциальной задержкой (base 30с, кап 3600с, max 4 попытки) + DLQ: `outbox_dead` с причиной (sender.py).
- [x] C2. Идемпотентность: проверка sent_log перед отправкой (tg/email по {url,channel,dest} за час, FL за 2ч) — защита от двойной отправки.

## Этап D. Агенты и оркестрация (ТЗ п.2 «Агенты-исполнители», Multica-подобный)
- [x] D1. Менеджер задач: статусы queued → running → done/failed, таймауты (шаг 600с, задача 1800с), отмена (cancel_task, requeue не воскрешает отменённое).
- [x] D2. Параллельный запуск агентов (ThreadPoolExecutor, 2 задачи), логирование каждого шага агента (agents_log).
- [x] D3. Валидация результатов (файл существует и непустой), версионирование deliverables/<id>/v<N>/.

## Этап E. Финансы (ТЗ п.2 «Финансовый модуль»)
- [x] E1. Настройки: валюта (RUB), налог (6%), шаблоны (default/ip) в config payment (billing.py).
- [x] E2. ЮMoney OAuth + авто-проверка оплат: `modules/yoomoney.py` (exchange_code → access_token → state/yoomoney_token.json + mirror в config, operation-history с Bearer, сверка label==invoice.no, HMAC не требуется — токен проверяется сервером), `tools/yoomoney_auth.py` (CLI обмен code→token), `billing.check_yoomoney_payments()` + Quickpay-ссылка с label в render(), watchdog опрос каждые 20с. Кошелёк 4100119458306656. Годен к работе — требуется одноразовый code (27.08).
- [x] E3. История оплат (payments через store) + idempotent mark_paid + валидация методов оплаты.

## Этап F. Отчёты и аналитика (ТЗ п.7)
- [x] F1. Дашборд: воронка заказы→отклики→won→paid, конверсии, среднее время реакции (/funnel, /reports/daily).
- [x] F2. Ежедневная сводка: /reports/daily готов; доставка в TG при 09:00 via watchdog._maybe_send_daily_digest() → sender.send_telegram("me") (27.08, modules/report.py).

## Этап G. UI (ТЗ п.3: React/Vue)
- [x] G1. API-слой: `workers/api.py` v1.0 :8766 — 24 эндпоинта (orders/deals/replies/filter/agents/tasks/invoices/payments/metrics/logs/health/funnel/events/settings) + write: filter decision, PATCH deal (статус/заметка/агент/счёт), invoice resend/mark-paid, task cancel/reassign.
- [x] G2. React+TS панель (Vite+Router+React Query, ui/dist): 12 маршрутов, 8 разделов (Overview/Pipeline/Orders/LLM&Filter/CRM/Agents/Billing/Monitoring), канбан с drag-drop и подтверждением Won/Paid, DealDrawer с вкладками, quality gate задач, журнал событий, роли operator/reviewer/admin, тёмная тема, polling 10-30с.
- [x] G3. Инлайн-правки/предпросмотр: решения фильтра, статусы, заметки, назначение агентов, счета, отмена/реассайн задач — работают через API. «Approve & send to client» подключено: dashboard /api/order/.../approve теперь вызывает sender.approve_and_send (27.08). LLM-настройки read-only (модели в config.models) — редактирование через config, роли localStorage.

## Этап H. Коммуникации (достройка, ТЗ п.2)
- [x] H1. Несколько ящиков email (конфиг-массив email_accounts, sender._email_accounts() + poll_email() итерирует все; dashboard показывает первый).
- [x] H2. Восстановление TG-туннеля: watchdog._check_tunnel() каждые 60с — socks 4067 + LM Studio + storage → events warning; http_client._proxy_alive() fallback на прямой IP.
- [x] H3. Классификация входящих: autoreply.classify_message + check_agreement + entity-извлечение (бюджет/дедлайн) — полный цикл; cooldown и QA-фильтры (27.08).

Порядок исполнения: A → B → C → F (быстрые победы), затем D, E, G, H по сессиям.
Осталось: E2 токен ЮMoney (ждём от владельца), полировка UI/роли (опционально). Все критические этапы A–H закрыты на 27.08.