import json
import os
import re

from modules import store

_MAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w]{2,}")
_TGU = re.compile(r"@([A-Za-z0-9_]{4,32})")


def has_contact(job: dict) -> bool:
    """Есть ли прямой контакт заказчика: @ник в тексте или email.
    Только такие заказы система умеет отправлять автономно."""
    if job.get("contact"):
        return True
    text = ((job.get("title") or "") + " " + (job.get("description") or "")).lower()
    return bool(_MAIL.search(text)) or bool(_TGU.search(text))


def load_skills() -> list[str]:
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("skills", [])


def score_job(job: dict, skills: list[str]) -> int:
    text = ((job.get("title") or "") + " " + (job.get("description") or "")).lower()
    score = 0
    for s in skills:
        if s.lower() in text:
            score += 1
    return score


def rank_and_store(jobs: list[dict], min_score: int = 1, contact_only: bool = True,
                   drop_vacancies: bool = True) -> list[dict]:
    """Сохраняем заказы с рейтингом. Обновляем score для всех, храним новые с контактом."""
    skills = load_skills()
    seen = store.load("seen_jobs", {})
    new = []
    updated = 0
    for j in jobs:
        if drop_vacancies and (j.get("kind") or "").lower() == "vacancy":
            continue
        if contact_only and not has_contact(j):
            continue
        s = score_job(j, skills)
        if s < min_score:
            continue
        key = j["url"] + (j.get("source") or j.get("platform") or "")
        is_new = key not in seen
        if is_new:
            seen[key] = store.now()
            new.append(j)
        else:
            updated += 1
        # Всегда обновляем score и source
        j["score"] = score_job(j, load_skills())
        j["source"] = j.get("platform") or j.get("source") or "?"
        if is_new:
            seen[key] = store.now()
    store.save("seen_jobs", seen)
    if new:
        prev = store.load("jobs", {"items": []})
        prev.setdefault("items", [])
        prev["items"] = new + prev["items"]
        store.save("jobs", prev)
    return new