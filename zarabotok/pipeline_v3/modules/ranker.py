"""ranker.py — S formula per ТЗ §7.2 / §6.4 + legacy keyword scoring.

S = 100 * (w_sim*sim + w_b*B + w_f*F + w_c*C + w_s*Sigma) - sum(P_k)

Defaults: w_sim=0.40, w_b=0.20, w_f=0.15, w_c=0.15, w_s=0.10
Thresholds: S>=65 matched, 45<=S<65 manual_review, S<45 rejected.
"""
import json
import os
import re
import time
import math

try:
    import yaml
except ImportError:
    yaml = None

from modules import store, config_loader

_MAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w]{2,}")
_TGU = re.compile(r"@([A-Za-z0-9_]{4,32})")

_SKILLS_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "skills.yaml")
_DEFAULTS = {
    "weights": {"sim": 0.40, "budget": 0.20, "freshness": 0.15, "channel": 0.15, "source": 0.10},
    "thresholds": {"matched": 65, "manual_review": 45},
    "freshness_tau_hours": 3.0,
    "risk_penalties": {
        "scam": 100, "prepayment_request": 30, "adult": 100, "gambling": 100,
        "diploma": 100, "bypass_protection": 100, "nda_required": 50,
        "paid_test": 50, "no_contact": 40, "below_min_budget": 50,
    },
    "global_filters": {
        "stop_themes": ["18+", "casino", "betting", "bypass_protection", "hack", "diploma", "financial_schemes"],
        "prepayment_only_threshold_rub": 50000,
        "paid_test_patterns": ["оплатите тестовое", "тестовое задание за \\d+ руб"],
    },
}


def _load_yaml() -> dict:
    if yaml is None:
        return _DEFAULTS
    if not os.path.exists(_SKILLS_PATH):
        return _DEFAULTS
    try:
        with open(_SKILLS_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        out = dict(_DEFAULTS)
        scoring = data.get("scoring") or {}
        for k, v in scoring.items():
            if isinstance(v, dict) and k in out:
                merged = dict(out[k])
                merged.update(v)
                out[k] = merged
            else:
                out[k] = v
        if "global_filters" in data:
            out["global_filters"] = {**(out.get("global_filters") or {}), **data["global_filters"]}
        return out
    except Exception:
        return _DEFAULTS


_CFG = _load_yaml()


def has_contact(job: dict) -> bool:
    """Есть ли прямой контакт заказчика."""
    if job.get("contact") or job.get("contact_email") or job.get("contact_tg"):
        return True
    text = ((job.get("title") or "") + " " + (job.get("description") or "")).lower()
    return bool(_MAIL.search(text)) or bool(_TGU.search(text))


def load_skills() -> list[str]:
    """Legacy: list of skill titles."""
    if yaml is None or not os.path.exists(_SKILLS_PATH):
        return config_loader.get_config().get("skills", [])
    try:
        with open(_SKILLS_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        skills = data.get("skills", [])
        return [s.get("title", "") for s in skills if s.get("title")]
    except Exception:
        return config_loader.get_config().get("skills", [])


def load_skills_struct() -> list[dict]:
    """Full skill dicts from skills.yaml."""
    if yaml is None or not os.path.exists(_SKILLS_PATH):
        return []
    try:
        with open(_SKILLS_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("skills", [])
    except Exception:
        return []


# -------- Legacy keyword scoring (kept for compatibility) --------
def score_job(job: dict, skills: list[str]) -> int:
    text = ((job.get("title") or "") + " " + (job.get("description") or "")).lower()
    score = 0
    for s in skills:
        if s and s.lower() in text:
            score += 1
    return score


# -------- New S formula (ТЗ §7.2) --------
def _sim_to_skill(lead: dict, skill: dict, embed_cache: dict = None) -> float:
    from modules import matcher
    text = (lead.get("title") or "") + " " + (lead.get("description") or "")
    anchors = skill.get("embedding_anchors") or []
    if not anchors:
        return 0.0
    cache = embed_cache if embed_cache is not None else {}
    best = 0.0
    for anchor in anchors[:10]:
        if not anchor:
            continue
        av = cache.get(anchor) or matcher.embed(anchor)
        if av and cache is not None:
            cache[anchor] = av
        if not av:
            continue
        vec = cache.get(text) or matcher.embed(text)
        if not vec:
            continue
        sim = matcher.cosine(vec, av)
        if sim > best:
            best = sim
        if best > 0.9:
            break
    return max(0.0, min(1.0, best))


def _budget_score(lead: dict, skill: dict) -> tuple:
    budget = lead.get("budget") or lead.get("budget_max") or 0
    skill_budget = (skill.get("budget") or {}).get("min", 0)
    if not budget or budget <= 0:
        return (0.4, False)
    if budget >= skill_budget:
        return (1.0, False)
    return (0.0, True)


def _freshness_score(lead: dict, tau_hours: float = 3.0) -> float:
    posted = lead.get("posted_at") or lead.get("captured_at") or 0
    if not posted:
        return 0.5
    try:
        if isinstance(posted, str):
            from datetime import datetime
            posted = datetime.fromisoformat(posted.replace("Z", "+00:00")).timestamp()
        delta_h = max(0.0, (time.time() - posted) / 3600.0)
    except Exception:
        return 0.5
    return math.exp(-delta_h / tau_hours)


def _channel_score(lead: dict) -> float:
    if lead.get("can_submit_auto") is True:
        return 1.0
    if lead.get("contact_email") or lead.get("contact_tg") or has_contact(lead):
        return 0.6
    return 0.0


def _source_score(source: str, replies: int = 0, sent: int = 0) -> float:
    return (replies + 1) / (sent + 5)


def _risk_penalties(lead: dict, skill: dict) -> int:
    penalties = _CFG.get("risk_penalties", _DEFAULTS["risk_penalties"])
    flags = lead.get("risk_flags") or []
    if isinstance(flags, str):
        flags = [flags]
    text = ((lead.get("title") or "") + " " + (lead.get("description") or "")).lower()
    total = 0
    flag_map = {
        "scam": ["scam", "western_union", "moneygram", "fraud"],
        "prepayment_request": ["100% предоплата", "залог", "переведите"],
        "adult": ["18+", "только для совершеннолетних", "nude"],
        "gambling": ["казино", "ставки", "casino", "betting"],
        "diploma": ["диссертация", "курсовая за студента", "academic"],
        "bypass_protection": ["обход блокировки", "взлом", "hack"],
        "nda_required": ["nda", "неразглашение"],
        "paid_test": ["оплатите тестовое", "тестовое задание платное"],
    }
    for flag, patterns in flag_map.items():
        if flag in flags or any(p in text for p in patterns):
            total += penalties.get(flag, 0)
    if not has_contact(lead):
        total += penalties.get("no_contact", 0)
    budget = lead.get("budget") or lead.get("budget_max") or 0
    skill_min = (skill.get("budget") or {}).get("min", 0)
    if budget and budget < skill_min:
        total += penalties.get("below_min_budget", 0)
    return total


def _global_hard_filter(lead: dict) -> tuple:
    text = ((lead.get("title") or "") + " " + (lead.get("description") or "")).lower()
    filters = _CFG.get("global_filters", _DEFAULTS["global_filters"])
    if any(t in text for t in ["18+", "casino", "betting", "bypass_protection", "hack", "diploma"]):
        return (False, "hard_filter:stop_theme")
    if "передача персональных данных" in text or "third party personal" in text:
        return (False, "hard_filter:personal_data")
    if any(t in text for t in ["физическое присутствие", "на территории", "in office", "relocate"]):
        return (False, "hard_filter:physical_presence")
    paid_test_patterns = filters.get("paid_test_patterns", [])
    for p in paid_test_patterns:
        if p and re.search(p, text):
            return (False, "hard_filter:paid_test")
    prepayment_threshold = filters.get("prepayment_only_threshold_rub", 50000)
    budget = lead.get("budget") or lead.get("budget_max") or 0
    if any(p in text for p in ["100% предоплата от исполнителя", "оплата после сдачи без договора"]):
        if budget > prepayment_threshold:
            return (False, "hard_filter:prepayment_only_high_budget")
    return (True, None)


def score(lead: dict, skill: dict, source_stats: dict = None,
         embed_cache: dict = None) -> dict:
    weights = _CFG.get("weights", _DEFAULTS["weights"])
    thresholds = _CFG.get("thresholds", _DEFAULTS["thresholds"])
    tau = _CFG.get("freshness_tau_hours", _DEFAULTS["freshness_tau_hours"])
    sim = _sim_to_skill(lead, skill, embed_cache)
    B, _ = _budget_score(lead, skill)
    F = _freshness_score(lead, tau)
    C = _channel_score(lead)
    source_name = lead.get("source") or lead.get("platform") or "?"
    stats = (source_stats or {}).get(source_name, {"replied": 0, "sent": 0})
    Sigma = _source_score(source_name, stats.get("replied", 0), stats.get("sent", 0))
    P = _risk_penalties(lead, skill)
    S = 100.0 * (
        weights.get("sim", 0.40) * sim +
        weights.get("budget", 0.20) * B +
        weights.get("freshness", 0.15) * F +
        weights.get("channel", 0.15) * C +
        weights.get("source", 0.10) * Sigma
    ) - P
    S = max(0.0, min(100.0, S))
    if S >= thresholds.get("matched", 65):
        decision = "matched"
    elif S >= thresholds.get("manual_review", 45):
        decision = "manual_review"
    else:
        decision = "rejected"
    return {
        "S": round(S, 2),
        "sim": round(sim, 4),
        "B": B,
        "F": round(F, 4),
        "C": C,
        "Sigma": round(Sigma, 4),
        "P": P,
        "decision": decision,
        "skill_id": skill.get("id"),
    }


def rank_and_store(jobs: list[dict], min_score: int = 1, contact_only: bool = True,
                   drop_vacancies: bool = True) -> list[dict]:
    """Backward-compat: rank with simple score, store new jobs."""
    skills_str = load_skills()
    seen = store.load("seen_jobs", {})
    new = []
    updated = 0
    for j in jobs:
        if drop_vacancies and (j.get("kind") or "").lower() == "vacancy":
            continue
        if contact_only and not has_contact(j):
            continue
        s = score_job(j, skills_str)
        if s < min_score:
            continue
        key = j["url"] + (j.get("source") or j.get("platform") or "")
        is_new = key not in seen
        if is_new:
            seen[key] = store.now()
            new.append(j)
        else:
            updated += 1
        j["score"] = score_job(j, skills_str)
        j["source"] = j.get("platform") or j.get("source") or "?"
    store.save("seen_jobs", seen)
    if new:
        prev = store.load("jobs", {"items": []})
        prev.setdefault("items", [])
        prev["items"] = new + prev["items"]
        store.save("jobs", prev)
    return new


def rank_with_formula(leads: list[dict], source_stats: dict = None,
                      embed_cache: dict = None) -> list[dict]:
    """New S-formula based ranking. Picks best skill per lead."""
    skills = load_skills_struct()
    out = []
    for lead in leads:
        passed, reason = _global_hard_filter(lead)
        if not passed:
            out.append({**lead, "decision": "rejected", "reject_reason": reason})
            continue
        best = None
        for skill in skills:
            r = score(lead, skill, source_stats, embed_cache)
            if best is None or r["S"] > best["S"]:
                best = r
        if best is None:
            out.append({**lead, "decision": "rejected", "reject_reason": "no_skill_match"})
        else:
            out.append({**lead, **best})
    return out
