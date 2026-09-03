"""Матчинг заказа к навыкам через эмбеддинги LM Studio (nomic) + косинус.

Кэш на диск (state/embeddings_cache.json), чтобы не гонять одну и ту же строку.
LLM недоступен / пустой ответ -> skill_boost=0.0 (деградация без падения).
"""
import hashlib
import json
import math
import os
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CACHE_PATH = os.path.join(BASE, "state", "embeddings_cache.json")
_EMBED_MODEL = "text-embedding-nomic-embed-text-v1.5"
_URL = "http://127.0.0.1:1234/v1/embeddings"


def _cache() -> dict:
    try:
        with open(_CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(c: dict):
    try:
        # хранить максимум ~4000 векторов
        if len(c) > 4000:
            c = dict(list(c.items())[-2000:])
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(c, f)
    except Exception:
        pass


def _h(text: str) -> str:
    return hashlib.sha1(text[:1500].encode("utf-8", "replace")).hexdigest()


def cosine(a: list, b: list) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(y * y for y in b)) or 1e-9
    return dot / (na * nb)


def embed(text: str, timeout: int = 20) -> list | None:
    """Вектор строки через локальный embeddings-endpoint; None при ошибке."""
    if not text:
        return None
    key = _h(text)
    c = _cache()
    if key in c:
        return c[key]
    try:
        body = json.dumps({"model": _EMBED_MODEL, "input": text[:1500]}).encode()
        req = urllib.request.Request(_URL, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
        vec = (data.get("data") or [{}])[0].get("embedding")
        if isinstance(vec, list) and vec:
            c[key] = vec
            _save_cache(c)
            return vec
    except Exception:
        return None
    return None


def skill_boost(text: str, skills: list[str], anchors_cache: dict | None = None) -> float:
    """0..N: максимум косинуса текста заказа к якорям навыков.

    Якоря — сами строки навыков из config (кэшируются). Умножай на вес снаружи."""
    vec = embed(text)
    if not vec or not skills:
        return 0.0
    cache = anchors_cache if anchors_cache is not None else {}
    best = 0.0
    for s in skills[:120]:
        sv = cache.get(s) or embed(s)
        if anchors_cache is not None and s not in cache and sv:
            cache[s] = sv
        if not sv:
            continue
        best = max(best, cosine(vec, sv))
        if best > 0.9:
            break
    return round(max(0.0, best), 4)
