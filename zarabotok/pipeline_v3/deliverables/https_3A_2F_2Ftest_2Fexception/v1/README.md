# Проект по заказу

- заказ: https%3A%2F%2Ftest%2Fexception
- версия: v1

| файл | статус | ошибки |
|---|---|---|
| bot.py | ok | — |
| handlers/exceptions.py | ok | — |
| config/settings.py | ТРЕБУЕТ ВНИМАНИЯ |   File "C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline_v3\deliverables\https_3A_2F_2Ftest_2Fexception\v1\config\settings.py", line 110
    DB_TYPE: str = os.getenv("DB_TYPE", "sqlite")
     |
| utils/logger.py | ТРЕБУЕТ ВНИМАНИЯ | runtime smoke (exit -1): sandbox: запуск разрешён только внутри workspace/ (текущий: C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline_v3\deliverables\https_3A_2F_2Ftest_2Fexception\v1\utils\log |
| models/error_types.py | ТРЕБУЕТ ВНИМАНИЯ | генерация не удалась |
| main.py | ТРЕБУЕТ ВНИМАНИЯ | генерация не удалась |

## Как запустить

```bash
# установите зависимости (если есть requirements.txt)
pip install -r requirements.txt
# запустите основной файл
```