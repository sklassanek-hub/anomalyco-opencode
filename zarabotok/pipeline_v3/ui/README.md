# Zarabotok — панель (этап G)

React-панель (Vite) поверх REST API из `workers/api.py`.

## Запуск

1. Собрать статику (один раз, после изменений в `src/`):

   ```
   cd ui
   npm install
   npm run build
   ```

2. Поднять API + панель (порт из `config.json` `ui.panel_port`, по умолчанию 8766):

   ```
   python workers/api.py
   ```

3. Открыть http://127.0.0.1:8766

Сервер отдаёт `ui/dist` (React-сборку); если сборки нет — ванильный `ui/index.html`
(фоллбэк без сборки), а без него — JSON со списком эндпоинтов.

## API (только чтение)

- `GET /api/orders` — заказы из orders_meta + messages/invoices/exec_tasks
- `GET /api/funnel` — воронка по статусам + конверсии
- `GET /api/events?limit=50` — журнал (activity + events)
- `GET /api/invoices` — счета
- `GET /api/payments` — платежи
- `GET /api/settings` — config.json без секретов (***)

Роли admin/user — в шапке панели (user не видит «Платежи» и «Настройки»).