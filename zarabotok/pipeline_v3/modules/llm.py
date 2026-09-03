"""Единая точка конфигурации LLM: ninm executors.lmstudio (config.json)."""
import json
import os

CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")


def model_cfg() -> dict:
    """{model, url, temperature, max_tokens} из config.json executors.lmstudio."""
    default = {
        "model": "qwen2.5-omni-3b",
        "url": "http://127.0.0.1:1234/v1/chat/completions",
        "temperature": 0.3,
        "max_tokens": 1500,
        "timeout": 180,
    }
    try:
        with open(CONFIG, encoding="utf-8") as f:
            lm = json.load(f).get("executors", {}).get("lmstudio", {})
        if not lm:
            return default
        return {
            "model": lm.get("model") or default["model"],
            "url": lm.get("url") or default["url"],
            "temperature": float(lm.get("temperature", default["temperature"])),
            "max_tokens": int(lm.get("max_tokens", default["max_tokens"])),
            "timeout": int(lm.get("timeout", default["timeout"])),
        }
    except (OSError, ValueError):
        return default