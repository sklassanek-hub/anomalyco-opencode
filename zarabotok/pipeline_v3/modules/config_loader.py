"""Config loader: merges config.json with .env environment variables."""
import json
import os
from pathlib import Path
from typing import Any, Dict

BASE = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE / "config.json"
ENV_PATH = BASE / ".env"

_dotenv_loaded = False

def load_dotenv():
    """Load .env file into os.environ."""
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    if ENV_PATH.exists():
        with open(ENV_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())
    _dotenv_loaded = True


def _replace_env_placeholders(obj: Any) -> Any:
    """Recursively replace __FROM_ENV__ values with environment variables."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if v == "__FROM_ENV__":
                env_key = k.upper()
                # Try to find matching env var
                for env_k, env_v in os.environ.items():
                    if env_k.lower() == k.lower() or env_k.lower().endswith(f"_{k.lower()}"):
                        result[k] = env_v
                        break
                else:
                    result[k] = v
            elif isinstance(v, (dict, list)):
                result[k] = _replace_env_placeholders(v)
            else:
                result[k] = v
        return result
    elif isinstance(obj, list):
        return [_replace_env_placeholders(item) for item in obj]
    return obj


def load_config() -> Dict:
    """Load config.json with .env overrides."""
    load_dotenv()
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = json.load(f)
    return _replace_env_placeholders(config)


def get_config() -> Dict:
    """Cached config getter."""
    if not hasattr(get_config, "_cache"):
        get_config._cache = load_config()
    return get_config._cache


def reload_config():
    """Force reload config."""
    if hasattr(get_config, "_cache"):
        delattr(get_config, "_cache")
    return get_config()


if __name__ == "__main__":
    cfg = load_config()
    print(json.dumps(cfg, ensure_ascii=False, indent=2)[:2000])