---
name: Voice Integration (TTS / Storytime / Critical Events)
description: >
  Интеграция голосового интерфейса в pipeline_v3 и .opencode-экосистему.
  Поддерживает sag (ElevenLabs CLI) и локальный TTS-фоллбэк (pyttsx3 / gTTS / .txt).
  Фокус: "storytime" (весёлые/забавные голоса) и голосовые уведомления
  для критических событий — Kill Switch, доставка результата, оплата, ошибка конвейера.
mode: subagent
color: '#8B5CF6'
---

# Voice Integration Skill — `pipeline_v3` / `.opencode`

## 🎯 Цель

Добавить голосовой отклик (TTS) в `pipeline_v3` без разрушения текущей структуры. Голосовые уведомления для критических событий + "storytime" с весёлыми голосами.

## 🧩 Изменённые / добавленные модули

| Модуль | Тип | Описание |
|---|---|---|
| `zarabotok/pipeline_v3/modules/voice.py` | **Новый** | TTS-движок (`sag` / локальный фоллбэк) с профилями `funny`, `dramatic`, `robot`, `pirate` |
| `zarabotok/pipeline_v3/watchdog.py` | **Модифицирован** | Неблокирующие голосовые вызовы (`_voice_bg`) для `kill_switch`, `pipeline_error`, `daily_digest`, `payment` |
| `zarabotok/pipeline_v3/modules/billing_service.py` | **Модифицирован** | Голосовое уведомление при успешной записи платежа (`announce_event`) |
| `.opencode/skills/voice-integration.md` | **Новый** | Этот скилл (документация + архитектура) |

## 🏗 Архитектура

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│  watchdog.py        │────▶│  modules/voice.py    │────▶│  deliverables/voice │
│  (kill_switch,      │     │  (sag / local TTS)   │     │  .mp3 / .txt / log │
│   error, digest)    │     │  announce_event()    │     │                    │
└─────────────────────┘     └──────────────────────┘     └─────────────────────┘
         │                           │
         ▼                           ▼
┌─────────────────────┐     ┌──────────────────────┐
│ billing_service.py  │────▶│  voice_events.log    │
│ (payment event)     │     │  (audit без PII)     │
└─────────────────────┘     └──────────────────────┘
```

### Ключевые правила (из AGENTS.md / Voice AI Integration Engineer)

- **Никогда не ломать конвейер** — `voice` оборачивается в `try/except`; ошибка TTS не влияет на `watchdog` или биллинг.
- **Никогда не логировать сырое аудио** — в `watchdog.log` и `voice_events.log` записываются только пути, тип события и короткий текст.
- **Всегда сохранять timestamps** — каждый `announce_event` пишет `ts` в `.txt` / `.log`.
- **Весёлые голоса для storytime** — профиль `funny` используется для `storytime`, `daily_digest`, `payment`.
- **Драматичные голоса для критических событий** — профиль `dramatic` для `kill_switch` и `pipeline_error`.

## 🛠 Установка / проверка

```bash
# Проверка синтаксиса модуля
python -m py_compile zarabotok/pipeline_v3/modules/voice.py

# Быстрая демонстрация (создаёт deliverables/voice/)
python -c "
import sys
sys.path.insert(0, 'zarabotok/pipeline_v3')
from modules import voice
path = voice.announce_event({
    'type': 'storytime',
    'message': 'Голосовой модуль интегрирован!',
    'details': 'Профиль funny — весёлый голос для критических событий.'
})
print('Output:', path)
"
```

## 📋 Конфигурация (`config.json` или env)

```json
{
  "voice": {
    "api_key": "<ELEVENLABS_API_KEY>",
    "model": "eleven_multilingual_v2",
    "enabled": true
  }
}
```

- `ELEVENLABS_API_KEY` — переменная окружения для `sag` CLI (если `sag` установлен).
- Если `sag` отсутствует и `pyttsx3` / `gTTS` не установлены — модуль автоматически падает на `.txt` с префиксом (`Хи-хи! ` / `ВНИМАНИЕ! ` / `Ой-вей, это серьёзно!`), сохраняя аудит.

## 🔊 Профили голосов

| Профиль | Скорость | Тон | Префикс | Применение |
|---|---|---|---|---|
| `funny` | 1.35x | 1.25x | `Хи-хи! ` | `storytime`, `daily_digest`, `payment` |
| `dramatic` | 0.85x | 0.75x | `ВНИМАНИЕ! ` | `kill_switch`, `pipeline_error` |
| `robot` | 0.95x | 1.00x | `СИСТЕМА: ` | `pipeline_result` |
| `pirate` | 1.15x | 1.10x | `Аррр! ` | Дополнительно (не используется по умолчанию) |

## ⚡ Интеграция с `watchdog`

В `watchdog.py` добавлен `_voice_bg()` — неблокирующий вызов через `threading.Thread`:

- `kill_active` → `dramatic` (`"Kill Switch активен — пропуск запуска воркера ... Ой-вей, это серьёзно!"`)
- `down` → `dramatic` (`"Воркеры неактивны, перезапущены: ... Ой-вей, это серьёзно!"`)
- `storage.get("ok") == False` → `dramatic`
- `_maybe_send_daily_digest()` → `funny` (`"Ежедневная сводка готова! ... Storytime: сегодня всё работает как нужно."`)
- `_billing.check_yoomoney_payments()` / `usdt` → `funny` (`"ЮMoney: платёж подтверждён! Ура, деньги на месте! Storytime: оплата прошла успешно."`)

## 💰 Интеграция с биллингом (`billing_service.py`)

При успешной записи платежа (`recorded == True`) запускается фоновый поток `voice.announce_event({"type": "payment", ...})`. Это не блокирует webhook-ответ ЮMoney (`process_notification`).

## ✅ Проверка синтаксиса / работоспособности

- `python -m py_compile modules/voice.py` — **ОК**
- `python modules/voice.py` — демонстрация (`DEMO`) — **ОК**
- Модуль возвращает абсолютный путь (`str`) — `.mp3`, `.wav` или `.txt` в зависимости от доступности `sag` / локального TTS.
- `watchdog.py` и `billing_service.py` модифицированы с защитой `try/except` + `threading.Thread` — **не ломают текущий конвейер**.

## 🔒 Приватность и безопасность

- Никаких сырых аудио-данных или неотредактированных текстов транскриптов в `watchdog.log` или `voice_events.log`.
- Только пути, типы событий и короткие строки (`msg[:200]`).
- `deliverables/voice/` изолирован и подчиняется политике хранения (`retention`) проекта.

---
*Скилл сгенерирован: Voice AI Integration Engineer (`@voice-ai-integration-engineer`).*
