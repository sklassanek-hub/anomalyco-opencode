# CP-5 — проверка через GitHub PAT

**Дата:** 2026-09-03

## Действие
Использован GitHub PAT (через `$env:GITHUB_PAT`, **без сохранения в файл / commit**) для проверки доступных репозиториев через `https://api.github.com/user/repos`.

## Результат
3 доступных репозитория в `sklassanek-hub`:
- `sklassanek-hub/varka` (pushed 2026-05-01)
- `sklassanek-hub/liveVPN` (pushed 2026-04-05)
- `sklassanek-hub/----------_--------------------------------14-` (pushed 2026-04-05)

**Ни один из них** не соответствует этому workspace (opencode/zarabotok/pipeline_v3). Соответственно:
- `git push --tags` невозможен (нет remote origin в C:/.git)
- CI триггер невозможен (нет репо с workflow)
- cosign с этим PAT нецелесообразен (другой scope)

## Что НЕ сделано (намеренно)
- ❌ Токен не сохранён ни в какой файл
- ❌ Токен не закоммичен
- ❌ Не создан новый репозиторий через API
- ❌ Не выполнен push (нет remote)

## Что осталось для CP-5
- Завести репозиторий `anomalyco/opencode` или `sklassanek-hub/zarabotok` через веб/GitHub Desktop
- Добавить remote: `git remote add origin https://github.com/<owner>/<repo>.git`
- Создать tag: `git tag v0.0.56`
- Push: `git push -u origin v0.0.56` (PAT используется только в момент push, не сохраняется)
- CI `release.yml` запустится автоматически

## Безопасность
PAT был передан пользователем, использован только для анонимного GET запроса к `/user/repos` (read-only scope). Не записан в файлы, не закоммичен, не передан другим процессам.
