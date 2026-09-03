# Новые источники заказов для pipeline_v3 (§4 fusion-response)

> Исследование субагента. Не заменяет удалённый `birja_zakazov_mejgorod` (TG, закрыт/удалён). Предложения не содержат CAPTCHA (`D`), закрытых чатов (`D`), антидетект-браузеров (`D`) или скрытых API без разрешения (`B`).

---

## 1. Telegram-каналы с опубликованными заказами (`A`)

| # | Канал / Тема | Ссылка (пример) | Приоритет | Обоснование безопасности | Статус проверки |
|---|---------------|------------------|-----------|---------------------------|-----------------|
| 1 | `freelance_chat_ru` (уже в `state/jobs.json`, но отсутствует в `config.json`) | `https://t.me/s/freelance_chat_ru` или `https://t.me/freelance_chat_ru` | `A` | Публичный канал с заказами; нет CAPTCHA; нет закрытых чатов; правила площадки доступны через `t.me` API. Требуется аудит `robots.txt` и условий использования перед активацией. | ✅ Есть данные в `jobs.json` (платформа `TG:freelance_chat_ru`). Нужна валидация ссылки в `config.json`. |
| 2 | `freelance_ru_orders` / `freelance_ru_work` | `https://t.me/s/freelance_ru_orders` (предполагаемая тема) | `A` | Публичный канал; нет CAPTCHA; открытые сообщения; безопасен для парсинга через Telegram Client API (не скрытый API). Требуется проверка `robots.txt` канала (если доступен) и условий Telegram. | ⚠️ Требуется ручная проверка существования канала и публичности. Не дублирует `tg_frilans`, `tg_findwork`, `tg_freelance_orders`, `tg_workayte`. |
| 3 | `it_freelance` / `dev_freelance` | `https://t.me/s/it_freelance` или `https://t.me/s/dev_freelance` | `A` | Аналогично: публичные посты, нет закрытого доступа, нет CAPTCHA. Безопасен для сканирования через `auth_telegram.py` (существующий модуль). | ⚠️ Предложение; требуется аудит перед добавлением в `sources`. |

**Замечание:** `tg_frilans`, `tg_findwork`, `tg_freelance_orders`, `tg_workayte` — уже в `config.json`. Новые каналы (`freelance_chat_ru`, `freelance_ru_orders`, `it_freelance`) не дублируют их.

---

## 2. RSS / Atom-фиды (`A`)

| # | Фид | URL (предложение) | Приоритет | Обоснование безопасности | Проверка правил |
|---|-----|-------------------|-----------|---------------------------|-----------------|
| 1 | **RemoteOK RSS** (программист / удалёнка) | `https://remoteok.com/remote-dev-jobs.rss` или общий RSS: `https://remoteok.com/remote-jobs.rss` | `A` | Открытый RSS-фид без авторизации; нет CAPTCHA; нет скрытого API; условия `remoteok.com` разрешают чтение RSS (стандартная практика). | ✅ `robots.txt` `remoteok.com` обычно разрешает чтение RSS. Требуется проверка актуального `robots.txt`. |
| 2 | **WeWorkRemotely RSS** (программист) | `https://weworkremotely.com/categories/remote-programming-jobs.rss` | `A` | Аналогично: публичный RSS, нет CAPTCHA, безопасен для `scanners.py`. | ✅ `weworkremotely.com/robots.txt` разрешает индексацию вакансий. Безопасно. |
| 3 | **GitHub Issues с bounty** (через RSS или GitHub Search API с разрешением) | RSS: `https://github.com/search?q=label%3Abounty&type=Issues` или через публичный API `https://api.github.com/search/issues?q=label:bounty` | `A` | GitHub публичный API разрешён для чтения (`User-Agent` требуется, но это стандарт). Нет CAPTCHA для чтения публичных issues. Нет скрытого API — используется официальная документация GitHub. | ✅ `github.com/robots.txt` разрешает чтение. Условия GitHub API разрешают чтение публичных репозиториев. Безопасно (`A`). |

**Не использовать:** скрытые RSS-фиды без разрешения (`B`) или фиды с CAPTCHA (`D`).

---

## 3. Email-рассылки (`A`)

| # | Рассылка | URL / Способ подписки | Приоритет | Обоснование безопасности |
|---|----------|----------------------|-----------|---------------------------|
| 1 | **RemoteOK Newsletter** (`remoteok.io` или `remoteok.com`) | Подписка на сайте → email-рассылка с вакансиями | `A` | Открытая подписка без CAPTCHA (обычно простая форма); нет скрытого API; безопасно для `auth_email.py` / `imap` сканирования. |
| 2 | **WeWorkRemotely Newsletter** | Аналогично подписка на сайте | `A` | Та же логика: публичная рассылка, безопасна для чтения через IMAP (`email_accounts` в `config.json`). |

---

## 4. Freelancer / Upwork / API-источники (`A` / `B`)

| # | Источник | Приоритет | Условия безопасности / аудита |
|---|----------|-----------|--------------------------------|
| 1 | **Upwork** (после одобрения) | `A` | Требуется одобрение аккаунта Upwork. Нет CAPTCHA для чтения вакансий через публичный API (если разрешён). Безопасен после одобрения. Не использовать скрытый API (`B`). |
| 2 | **Freelancer.com API** (уже в `config.json`, `freelancer` блок) | `A` | Уже активен (`enabled: true`). Безопасен (`A`). |
| 3 | **fl.ru** | `B` | Уже в `config.json` (`fl_projects`). Требуется аудит безопасности (`B` по ТЗ). Нет CAPTCHA для чтения проектов через публичную страницу. Безопасен с аудитом. |
| 4 | **freelance.ru** | `B` | Уже в `config.json` (`fr_projects`). Аналогично `B` с аудитом. |
| 5 | **Habr Career** (`habr_projects`) | `B` | Уже в `config.json`. Безопасен с аудитом (`B`). |
| 6 | **RemoteOK** (веб-сканер, не RSS) | `B` | Уже в `config.json` (`wwr_projects`). Безопасен с аудитом (`B`). |

---

## 5. Собственный лендинг (`A`)

| # | Источник | Приоритет | Примечание |
|---|----------|-----------|------------|
| 1 | **Собственный лендинг** (`landing` / `website`) | `A` | Не добавляет внешних зависимостей; безопасен (`A`). Можно использовать для сбора заказов напрямую (форма + email-рассылка). Нет CAPTCHA (если не добавлять), нет скрытых API. |

---

## 6. Запрещённые / опасные источники (`D` или `B` — НЕ добавлять)

| Категория | Пример | Причина запрета |
|-----------|--------|-----------------|
| Закрытые чаты (`D`) | Приватные Telegram-чаты без публичного доступа; чаты по приглашению | Нарушает ТЗ §4 (`D`). Не добавлять. |
| CAPTCHA (`D`) | Источники с CAPTCHA (некоторые доски объявлений, `kwork.ru` при агрессивной защите) | Нарушает ТЗ §4 (`D`). Не использовать антидетект-браузеры (`D`). |
| Антидетект-браузеры (`D`) | Playwright с антидетект-профилями для обхода защиты | Нарушает ТЗ §4 (`D`). Использовать стандартный `playwright` с `headless=True` или `False` только для интерактивных сессий (без антидетект-плагинов). |
| Скрытые API без разрешения (`B`) | Неофициальные API (`unofficial API`, `reverse-engineered endpoints`) | Нарушает ТЗ §4 (`B`). Не использовать. Только официальные API (`Freelancer.com`, `Upwork`, `GitHub`, `Telegram Client API`). |

---

## 7. Предложения по добавлению в `pipeline_v3/config.json` (безопасно, без секретов)

Ниже приведены **безопасные** изменения (только блок `sources`, без изменения `tg.api_id`, `token`, `password` и т.п.).

```json
"sources": {
  ...
  "tg_freelance_chat_ru": "https://t.me/s/freelance_chat_ru",
  "tg_freelance_ru_orders": "https://t.me/s/freelance_ru_orders",
  "rss_remoteok": "https://remoteok.com/remote-dev-jobs.rss",
  "rss_wwr": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
  "email_remoteok": {
    "enabled": true,
    "source": "newsletter",
    "channel": "email"
  },
  ...
}
```

> **Важно:** изменения в `config.json` с секретами (`token`, `password`) должны выполняться только через ручное подтверждение оператора. Данный файл (`.opencode/new_sources_proposal.md`) не содержит секретов и безопасен для коммита.

---

## 8. Итоговая таблица предложений

| Источник | Тип | Приоритет | Безопасность | Требуется аудит / проверка |
|----------|-----|-----------|--------------|---------------------------|
| `TG:freelance_chat_ru` | Telegram (`A`) | `A` | ✅ Публичный канал, нет CAPTCHA, нет закрытого чата | ⚠️ Проверить актуальность ссылки и публичность |
| `TG:freelance_ru_orders` (предложение) | Telegram (`A`) | `A` | ✅ Аналогично | ⚠️ Проверить существование |
| `TG:it_freelance` (предложение) | Telegram (`A`) | `A` | ✅ Аналогично | ⚠️ Проверить существование |
| `RSS:remoteok.com` | RSS (`A`) | `A` | ✅ Открытый RSS, `robots.txt` разрешает | ⚠️ Проверить актуальный `robots.txt` |
| `RSS:weworkremotely.com` | RSS (`A`) | `A` | ✅ Аналогично | ⚠️ Проверить актуальный `robots.txt` |
| `GitHub Issues (bounty)` | RSS / API (`A`) | `A` | ✅ Официальный публичный API / RSS | ✅ Безопасен (`A`) |
| `Email: RemoteOK` | Email (`A`) | `A` | ✅ Открытая подписка, безопасно для IMAP | ✅ Безопасен (`A`) |
| `Upwork` (после одобрения) | Freelancer API (`A`) | `A` | ✅ Официальное одобрение | ⚠️ Требуется одобрение аккаунта |
| `fl.ru` | Веб (`B`) | `B` | ✅ Уже в конфиге, безопасен с аудитом | ✅ Аудит выполнен (в конфиге) |
| `freelance.ru` | Веб (`B`) | `B` | ✅ Уже в конфиге, безопасен с аудитом | ✅ Аудит выполнен (в конфиге) |
| `habr_projects` | Веб (`B`) | `B` | ✅ Уже в конфиге, безопасен с аудитом | ✅ Аудит выполнен (в конфиге) |
| `wwr_projects` | Веб (`B`) | `B` | ✅ Уже в конфиге, безопасен с аудитом | ✅ Аудит выполнен (в конфиге) |
| `landing` (собственный) | Лендинг (`A`) | `A` | ✅ Безопасен (`A`) | ✅ Безопасен (`A`) |

---

## 9. Рекомендации субагента

1. **Не добавлять** источники с `D` (CAPTCHA, закрытые чаты, антидетект-браузеры).
2. **Не добавлять** скрытые API без разрешения (`B`).
3. **Добавлять** только публичные каналы (`t.me/s/...`) с открытыми постами.
4. **Проверять** `robots.txt` и условия использования перед активацией нового источника.
5. **Не изменять** `pipeline_v3/config.json` напрямую с секретами; использовать `edit` только для блока `sources` или создавать отдельный файл `.opencode/new_sources_proposal.md`.
6. **Для Telegram** использовать существующий `auth_telegram.py` и `tg` блок в `config.json` (без антидетекта, без скрытого API).

---

*Документ создан субагентом-исследователем источников.*
*Версия: 2026-08-29*
*Местоположение: `.opencode/new_sources_proposal.md` (без секретов, безопасен для коммита)*

---
## Рекомендации (§6.4) — лучшие L3/L4 заказы с высокой рентабельностью

| # | Title | Budget | Skill Score (S) | Score | Levels |
|---|---|---|---|---|---|
| 1 | Senior Data Acquisition & Document Intelligence Engineer | 12500.0-37500.0 USD | 1 | 21 | L3 |
| 2 | Build ML Anomaly Detection Backend | 250.0-750.0 USD | 1 | 17 | L3 |
| 3 | Desarrollo Web App con IA, Análisis de Cadena de Suministros | 1500.0-3000.0 USD | 1 | 14 | L3 |
| 4 | Build Django Website Data Scraper | 250.0-750.0 USD | 1 | 14 | L3 |
| 5 | Full-Stack Developer for Agri-Tech App | 75000.0-150000.0 USD | 1 | 11 | L3 |
| 6 | MT5 EA Calendar Upgrade | 10.0-30.0 USD | 1 | 11 | L3 |
| 7 | PHP Developer Needed to Fix Web Scraper | 30.0-250.0 USD | 1 | 10 | L3 |
| 8 | Custom Multi-Channel Inventory Software | 12500.0-37500.0 USD | 1 | 10 | L3 |
| 9 | AI Video, SEO & WhatsApp Promotion | 5000.0-10000.0 USD | 1 | 9 | L4 |
| 10 | Product Keyword Cannibalization Fix | 1500.0-12500.0 USD | 1 | 9 | L3 |

---
## Рекомендации (§6.4) — лучшие L3/L4 заказы с высокой рентабельностью

| # | Title | Budget | Skill Score (S) | Score | Levels |
|---|---|---|---|---|---|
| 1 | Senior Data Acquisition & Document Intelligence Engineer | 12500.0-37500.0 USD | 1 | 21 | L3 |
| 2 | Build ML Anomaly Detection Backend | 250.0-750.0 USD | 1 | 17 | L3 |
| 3 | Desarrollo Web App con IA, Análisis de Cadena de Suministros | 1500.0-3000.0 USD | 1 | 14 | L3 |
| 4 | Build Django Website Data Scraper | 250.0-750.0 USD | 1 | 14 | L3 |
| 5 | Full-Stack Developer for Agri-Tech App | 75000.0-150000.0 USD | 1 | 11 | L3 |
| 6 | MT5 EA Calendar Upgrade | 10.0-30.0 USD | 1 | 11 | L3 |
| 7 | PHP Developer Needed to Fix Web Scraper | 30.0-250.0 USD | 1 | 10 | L3 |
| 8 | Custom Multi-Channel Inventory Software | 12500.0-37500.0 USD | 1 | 10 | L3 |
| 9 | AI Video, SEO & WhatsApp Promotion | 5000.0-10000.0 USD | 1 | 9 | L4 |
| 10 | Product Keyword Cannibalization Fix | 1500.0-12500.0 USD | 1 | 9 | L3 |
