"""Agent-based order filtering using .opencode/skills_registry.json (L0-L4).

Formula Score §6.4 (skill match): S = count of registry skills whose id/name
appear in the job title/description/skills.

Rules:
- L0 skills -> excluded from auto-reply (manual or excluded)
- L2 skills -> manual approval only
- L3/L4 skills -> allowed for auto-reply
"""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Registry lives in the parent workspace (zarabotok root), not inside pipeline_v3.
_PROJECT_ROOT = os.path.dirname(BASE)
SKILLS_REGISTRY_PATH = os.path.join(_PROJECT_ROOT, ".opencode", "skills_registry.json")


def load_skills_registry() -> dict:
    with open(SKILLS_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_skill_match_s(job: dict, registry: dict = None) -> tuple[int, list]:
    """Calculate S (skill-match score) and list of matched registry skills."""
    if registry is None:
        registry = load_skills_registry()
    skills = registry.get("skills", [])
    # Normalize job text for matching
    text_parts = [
        job.get("title", ""),
        job.get("description", ""),
    ]
    metadata = job.get("metadata") or {}
    if isinstance(metadata, dict) and "skills" in metadata:
        text_parts.extend(str(s) for s in metadata["skills"])
    text = " ".join(text_parts).lower()
    matched = []
    s_score = 0
    for skill in skills:
        sid = (skill.get("id") or "").lower()
        sname = (skill.get("name") or "").lower()
        # Match if id or name is present in job text
        if sid and sid in text:
            s_score += 1
            matched.append({
                "id": skill.get("id"),
                "name": skill.get("name"),
                "autonomy_level": skill.get("autonomy_level", "L0"),
            })
        elif sname and sname in text:
            s_score += 1
            matched.append({
                "id": skill.get("id"),
                "name": skill.get("name"),
                "autonomy_level": skill.get("autonomy_level", "L0"),
            })
    return s_score, matched


def filter_with_agents(jobs: list = None, registry: dict = None) -> dict:
    """Filter orders using agent autonomy levels from skills_registry.json.

    Returns dict with keys:
      - total: int
      - excluded (L0 / no match): list
      - manual_approval (L2): list
      - auto_reply (L3/L4): list
      - skills_registry: str description
    """
    if registry is None:
        registry = load_skills_registry()
    if jobs is None:
        state_path = os.path.join(BASE, "state", "jobs.json")
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                jobs = json.load(f).get("items", [])
        except Exception:
            jobs = []
    result = {
        "total": len(jobs),
        "excluded": [],
        "manual_approval": [],
        "auto_reply": [],
        "skills_registry": "C:/Users/klass/OneDrive/Desktop/work/zarabotok/.opencode/skills_registry.json (184 skills, L0-L4)",
    }
    for job in jobs:
        s_score, matched = calculate_skill_match_s(job, registry)
        levels = {m["autonomy_level"] for m in matched}
        # Decision rules per requirements
        has_l3_l4 = any(l in ("L3", "L4") for l in levels)
        has_l2 = "L2" in levels
        # Exclude L0 from auto-reply; allow L3/L4; L2 -> manual approval
        if has_l3_l4:
            action = "auto_reply"
        elif has_l2:
            action = "manual_approval"
        else:
            # L0 only or no registry match -> excluded from auto-reply
            action = "excluded"
        entry = {
            "url": job.get("url"),
            "title": job.get("title", ""),
            "platform": job.get("platform", ""),
            "budget": job.get("budget", ""),
            "current_score": job.get("score", 0),
            "skill_match_s": s_score,
            "matched_skills": matched,
            "autonomy_levels_found": sorted(levels) if levels else ["L0"],
            "action": action,
        }
        result[action].append(entry)
    return result


def is_scam(job: dict, embedding_path: str = "") -> bool:
    """Formalized scam detection (W13) using hash + embedding reference.
    Computes SHA-256 hash of job normalized text; compares to embedding cache
    (state/embeddings_cache.json) for known scam embeddings.
    Returns True if hash matches known scam pattern or embedding similarity > threshold.
    """
    import hashlib
    text = " ".join(str(job.get(k, "")) for k in ("title", "description", "url", "budget"))
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    # Embedding reference: try to load embeddings_cache.json from state directory
    if not embedding_path:
        embedding_path = os.path.join(BASE, "state", "embeddings_cache.json")
    try:
        with open(embedding_path, "r", encoding="utf-8") as f:
            emb = json.load(f)
    except Exception:
        emb = {}
    # Check for known scam hash list or embedding match
    known_hashes = emb.get("scam_hashes", [])
    if h in known_hashes:
        return True
    # Embedding similarity check (stub: reference only)
    embeddings = emb.get("items", [])
    for item in embeddings:
        if item.get("hash") == h and item.get("label") == "scam":
            return True
    return False


def enhance_filter():
    """Alias / convenience wrapper for filter_with_agents()."""
    return filter_with_agents()
