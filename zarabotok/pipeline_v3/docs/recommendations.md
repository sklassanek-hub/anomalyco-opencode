# Рекомендации заказов (§6.4 Score + фильтр L3/L4)

Генерируется автоматически из `skills_registry.json` и `state/jobs.json`.

## Формула Score (§6.4)

S = skill-match count (из registry) + рентабельность (budget) + текущий score.

- **L3/L4** — авто-отклик разрешён (высокая автономия).
- **L2** — ручное одобрение.
- **L0** — исключён из авто-ответа.

## Лучшие заказы (L3/L4) с высокой рентабельностью

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

## Методика

1. Загружается `.opencode/skills_registry.json`.
2. Применяется `modules.filter.filter_with_agents()`.
3. Для `auto_reply` выбираются записи с максимальным `skill_match_s` и положительным `budget`.
4. Формируется `docs/recommendations.md` + `.opencode/new_sources_proposal.md`.

*Создано субагентом-исследователем. Версия: 2026-08-29.*
