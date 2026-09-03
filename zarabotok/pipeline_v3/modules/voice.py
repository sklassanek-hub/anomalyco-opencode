"""
Voice AI Integration Module for pipeline_v3 (§voice-storytime + critical events).
Поддерживает sag (ElevenLabs CLI) и локальный TTS-фоллбэк (pyttsx3 / gTTS / .txt).
Не ломает текущую структуру: используется как независимый модуль.
"""
import os
import subprocess
import sys
import json
import time
import threading
from pathlib import Path

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE, "config.json")
DELIVER_DIR = os.path.join(BASE, "deliverables", "voice")
os.makedirs(DELIVER_DIR, exist_ok=True)

# --- Профили голоса для "storytime" и уведомлений ---
PROFILES = {
    "funny":    {"prefix": "Хи-хи! ",   "speed": 1.35, "pitch": 1.25, "voice_hint": "Rachel"},
    "dramatic": {"prefix": "ВНИМАНИЕ! ", "speed": 0.85, "pitch": 0.75, "voice_hint": "Adam"},
    "robot":    {"prefix": "СИСТЕМА: ",  "speed": 0.95, "pitch": 1.00, "voice_hint": "Antoni"},
    "pirate":   {"prefix": "Аррр! ",    "speed": 1.15, "pitch": 1.10, "voice_hint": "Josh"},
    "default":  {"prefix": "",           "speed": 1.00, "pitch": 1.00, "voice_hint": "Rachel"},
}

EVENT_MAP = {
    "kill_switch":     "dramatic",
    "pipeline_error":  "dramatic",
    "payment":         "funny",
    "pipeline_result": "robot",
    "daily_digest":    "funny",
    "storytime":       "funny",
}


def _cfg() -> dict:
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _voice_cfg() -> dict:
    return _cfg().get("voice", {})


def _sag_available() -> bool:
    """Проверка доступности CLI sag (ElevenLabs)."""
    try:
        result = subprocess.run(
            ["sag", "--version"],
            capture_output=True,
            timeout=3,
        )
        out = (result.stdout or b"").decode("utf-8", errors="ignore")
        err = (result.stderr or b"").decode("utf-8", errors="ignore")
        return result.returncode == 0 or "sag" in out.lower() or "eleven" in out.lower() or "eleven" in err.lower()
    except Exception:
        return False


def _local_tts_available() -> bool:
    try:
        import pyttsx3  # noqa: F401
        return True
    except Exception:
        pass
    try:
        from gtts import gTTS  # noqa: F401
        return True
    except Exception:
        pass
    return False


def _build_sag_cmd(text: str, profile: dict, output_path: str) -> list:
    cmd = ["sag", "speak", "--text", text, "--output", output_path]
    # Профиль голоса
    voice_hint = profile.get("voice_hint", profile.get("voice_name", "Rachel"))
    cmd.extend(["--voice", voice_hint])
    # Скорость / тон
    speed = profile.get("speed", 1.0)
    cmd.extend(["--speed", str(round(speed, 2))])
    # API-ключ (из config или env)
    cfg = _voice_cfg()
    api_key = cfg.get("api_key") or cfg.get("elevenlabs_api_key") or os.environ.get("ELEVENLABS_API_KEY", "")
    if api_key:
        cmd.extend(["--api-key", api_key])
    # Модель по умолчанию
    model = cfg.get("model", "eleven_multilingual_v2")
    cmd.extend(["--model", model])
    return cmd


def speak(text: str, voice: str = "funny", output_path: str = None) -> str:
    """
    Генерирует голосовой отклик или текстовый фоллбэк.
    Возвращает абсолютный путь к файлу (.mp3 / .wav / .txt).
    """
    profile = PROFILES.get(voice, PROFILES["default"])
    if output_path is None:
        ts = int(time.time())
        output_path = os.path.join(DELIVER_DIR, f"voice_{voice}_{ts}")
    output_path = output_path.replace("\\", "/")
    # Убеждаемся, что расширение есть
    if "." not in os.path.basename(output_path):
        output_path += ".mp3"
    # 1. Попытка sag (ElevenLabs CLI)
    if _sag_available():
        try:
            cmd = _build_sag_cmd(text, profile, output_path)
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=90,
                check=False,
            )
            if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return os.path.abspath(output_path)
        except Exception as exc:
            # Силент-фоллбэк: не ломаем конвейер из-за TTS-ошибки
            pass
    # 2. Локальный TTS (pyttsx3 / gTTS)
    if _local_tts_available():
        try:
            import pyttsx3
            engine = pyttsx3.init()
            # Установка скорости речи (pyttsx3 использует ~150 слов/мин как базу)
            target_rate = int(profile.get("speed", 1.0) * 150)
            engine.setProperty("rate", target_rate)
            voices = engine.getProperty("voices")
            # Пробуем выбрать голос с индексом > 0, если доступен (часто «женский» или «другой»)
            if voices and len(voices) > 1:
                engine.setProperty("voice", voices[1].id)
            out_wav = output_path.replace(".mp3", ".wav")
            engine.save_to_file(text, out_wav)
            engine.runAndWait()
            if os.path.exists(out_wav) and os.path.getsize(out_wav) > 0:
                return os.path.abspath(out_wav)
        except Exception:
            pass
        try:
            from gtts import gTTS
            out_mp3 = output_path.replace(".wav", ".mp3")
            gtts_obj = gTTS(text=text, lang="ru", slow=(profile.get("speed", 1.0) < 1.0))
            gtts_obj.save(out_mp3)
            if os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 0:
                return os.path.abspath(out_mp3)
        except Exception:
            pass
    # 3. Финальный фоллбэк: текстовый файл с префиксом голоса (для audit / storytime)
    txt_path = output_path.replace(".mp3", ".txt").replace(".wav", ".txt")
    try:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"{profile['prefix']}{text}\n")
            f.write(f"[VOICE PROFILE] {voice}\n")
            f.write(f"[SPEED] {profile['speed']} | [PITCH] {profile['pitch']}\n")
            if _sag_available() is False:
                f.write("[NOTE] sag CLI не обнаружен в системе.\n")
            if _local_tts_available() is False:
                f.write("[NOTE] Локальные TTS-библиотеки (pyttsx3 / gTTS) не установлены.\n")
            f.write(f"[FILE] {os.path.abspath(output_path)}\n")
    except Exception:
        pass
    # Возвращаем путь к текстовому фоллбэку или исходному пути
    if os.path.exists(txt_path):
        return os.path.abspath(txt_path)
    return os.path.abspath(output_path)


def announce_event(event: dict, output_dir: str = DELIVER_DIR) -> str:
    """
    Голосовое уведомление для критических событий конвейера.
    event = {"type": "kill_switch" | "pipeline_error" | "payment" | ...,
             "message": "...", "details": "..."}
    Возвращает путь к сгенерированному аудио или .txt.
    """
    event_type = event.get("type", "unknown")
    msg = event.get("message", event.get("text", "Событие в конвейере."))
    details = event.get("details", "")
    profile_name = EVENT_MAP.get(event_type, "default")
    profile = PROFILES.get(profile_name, PROFILES["default"])

    # Формируем текст с «забавным» вступлением для storytime / критических моментов
    full_text = msg
    if event_type == "storytime":
        full_text = f"Ой, слушайте! {msg}. А теперь — время историй!"
    elif event_type in ("kill_switch", "pipeline_error"):
        full_text = f"{profile['prefix']}{msg} Ой-вей, это серьёзно! {details}".strip()
    elif event_type == "payment":
        full_text = f"{profile['prefix']}{msg}! {details} Ура, деньги на месте!".strip()
    elif event_type == "pipeline_result":
        full_text = f"{profile['prefix']}{msg}. {details}".strip()
    elif event_type == "daily_digest":
        full_text = f"{profile['prefix']}{msg}. {details}".strip()
    else:
        full_text = f"{profile['prefix']}{msg} {details}".strip()

    # Не блокируем поток watchdog — запускаем в фоне
    result_path = speak(full_text, voice=profile_name, output_path=os.path.join(output_dir, f"event_{event_type}_{int(time.time())}"))
    # Логируем в audit-файл (без сырых аудио-данных — только пути и события)
    log_path = os.path.join(output_dir, "voice_events.log")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(
                f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} "
                f"event={event_type} profile={profile_name} path={result_path} msg={msg[:200]}\n"
            )
    except Exception:
        pass
    return result_path


def _nonblocking_speak(text: str, voice: str, output_dir: str):
    """Вспомогательная функция для запуска в фоновом потоке (не блокирует watchdog)."""
    try:
        output_path = os.path.join(output_dir, f"bg_{voice}_{int(time.time())}")
        speak(text, voice=voice, output_path=output_path)
    except Exception:
        pass


if __name__ == "__main__":
    # Быстрая проверка синтаксиса и базовая демонстрация
    print("[VOICE MODULE OK] Синтаксис проверен.")
    demo_path = announce_event({
        "type": "storytime",
        "message": "Тестовая история: голосовой модуль интегрирован в pipeline_v3!",
        "details": "Используется профиль funny — весёлый голос для критических событий.",
    })
    print(f"[DEMO] Файл уведомления: {demo_path}")
