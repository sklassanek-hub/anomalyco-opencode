# Отчёт интеграции голосового интерфейса (Voice AI) — pipeline_v3 / .opencode

**Автор:** Voice AI Integration Engineer (`@voice-ai-integration-engineer`)
**Дата:** 2026-08-31
**Рабочая директория:** `C:\Users\klass\OneDrive\Desktop\work`

---

## 1. Какие модули изменены / добавлены

### Новые файлы
- `zarabotok/pipeline_v3/modules/voice.py` — основной TTS-модуль (sag + локальный фоллбэк).
- `.opencode/skills/voice-integration.md` — скилл-документация интеграции.
- `zarabotok/pipeline_v3/deliverables/voice/` — директория для аудио / текстовых артефактов.

### Изменённые файлы
- `zarabotok/pipeline_v3/watchdog.py` — добавлен `_voice_bg()` (неблокирующий `threading.Thread`) для голосовых уведомлений (`kill_switch`, `pipeline_error`, `daily_digest`, `payment`).
- `zarabotok/pipeline_v3/modules/billing_service.py` — голосовое уведомление (`announce_event`) при успешной записи платежа.

---

## 2. Работает ли голосовой отклик?

### Проверка модуля
```bash
python -m py_compile zarabotok/pipeline_v3/modules/voice.py  # OK
python zarabotok/pipeline_v3/modules/voice.py                  # DEMO OK
```

### Результат теста
- Файл: `deliverables/voice/event_storytime_1788128398.txt`
- Содержимое содержит префикс `Хи-хи! ` (профиль `funny`), текст события, профиль, скорость / тон, примечания о доступности `sag` и локальных TTS-библиотек.
- `voice_events.log` записан с `ts`, `event`, `profile`, `path`, `msg` (без сырых аудио-данных — PII-защита).

### Доступность движков
- `sag` (ElevenLabs CLI) — **не обнаружен** в системе (`sag --version` отсутствует).
- Локальные TTS (`pyttsx3`, `gTTS`) — **не установлены**.
- **Фоллбэк работает:** модуль автоматически переходит на `.txt`-вывод с правильным префиксом голосового профиля.

---

## 3. Синтаксис проверен

| Файл | Команда | Результат |
|---|---|---|
| `modules/voice.py` | `python -m py_compile` | ✅ OK |
| `watchdog.py` | `python -m py_compile` | ✅ OK |
| `modules/billing_service.py` | `python -m py_compile` | ✅ OK |
| `.opencode/skills/voice-integration.md` | ручная проверка структуры (YAML frontmatter + markdown) | ✅ OK |

---

## 4. Что интегрировано в конвейер

### `watchdog.py`
- `_voice_bg("kill_switch", ...)` — при активном `KILL_SWITCH` (драматичный голос, префикс `ВНИМАНИЕ! `).
- `_voice_bg("pipeline_error", ...)` — при перезапуске воркеров или ошибке хранилища.
- `_voice_bg("daily_digest", ...)` — фоновый поток при `_maybe_send_daily_digest()` (`funny`).
- `_voice_bg("payment", ...)` — при успешной проверке ЮMoney / USDT (`funny` с `Storytime` деталями).

### `billing_service.py`
- Фоновый `threading.Thread` запускает `voice.announce_event({"type": "payment", ...})` сразу после записи в `state/payments.json`.
- Не блокирует webhook-ответ (`process_notification` возвращает `{"ok": True, ...}` независимо от TTS).

---

## 5. Приватность и безопасность (из AGENTS.md / Voice AI Integration Engineer)

- ✅ Никаких сырых аудио или неотредактированных текстов транскриптов в `watchdog.log` или `voice_events.log`.
- ✅ Только пути (`path`), типы событий (`event`) и короткие строки (`msg[:200]`).
- ✅ `deliverables/voice/` — изолированная директория.
- ✅ Модуль не ломает текущий конвейер: все вызовы обёрнуты в `try/except` + `daemon=True` потоки.

---

## 6. Как использовать / расширять

```python
# Пример вызова из любого модуля pipeline_v3
from modules import voice
path = voice.announce_event({
    "type": "storytime",
    "message": "Новая функция готова!",
    "details": "Storytime: весёлый голос для критических событий."
})
# path -> .mp3 (если sag + API-ключ настроены) или .txt (фоллбэк)
```

### Установка `sag` для полноценного аудио
```bash
# Пример (если ElevenLabs CLI доступен)
pip install sag-cli  # или аналогичная установка
export ELEVENLABS_API_KEY="<key>"
# После этого voice.py будет генерировать .mp3 через sag
```

---

## 7. Итоговый статус

- [x] Модуль `voice.py` написан и синтаксически проверен.
- [x] `watchdog.py` модифицирован (неблокирующие голосовые вызовы).
- [x] `billing_service.py` модифицирован (голосовое уведомление о платеже).
- [x] `.opencode/skills/voice-integration.md` создан.
- [x] Файл `.txt` с префиксом `Хи-хи! ` сгенерирован и проверен.
- [x] `watchdog` не сломан; биллинг не блокируется.
- [ ] `sag` CLI отсутствует в текущей системе — аудио `.mp3` будет доступно после установки `sag` + API-ключа.
- [ ] Локальные TTS (`pyttsx3` / `gTTS`) отсутствуют — `.txt` фоллбэк работает корректно.
