"""
Freelancer.com API scanner - search projects via official API.
API docs: https://developers.freelancer.com/
"""
import json
import os
import sys
import ssl
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules import http_client as hc


def _load_freelancer_cfg():
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json"), encoding="utf-8") as f:
            cfg = json.load(f) or {}
            return cfg.get("sources", {}).get("freelancer", {})
    except Exception:
        return {}


def _get_access_token():
    """Get access_token from state/freelancer_token.json or config.json"""
    # 1) state/freelancer_token.json
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "freelancer_token.json"), encoding="utf-8") as f:
            data = json.load(f)
            token = data.get("access_token", "").strip()
            if token:
                return token
    except Exception:
        pass
    # 2) config.json
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json"), encoding="utf-8") as f:
            cfg = json.load(f)
            token = (cfg.get("sources", {}).get("freelancer", {}) or {}).get("token", "").strip()
            if token:
                return token
    except Exception:
        pass
    return None


def _ssl_context():
    """SSL context that bypasses cert verification (for local network issues)"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _api_request(endpoint, params=None, method="GET"):
    """Execute request to Freelancer API"""
    token = _get_access_token()
    if not token:
        raise RuntimeError("Freelancer access_token not found. Configure OAuth via modules.freelancer_oauth")

    base_url = "https://www.freelancer.com/api"
    url = base_url + endpoint

    request_data = None
    if params:
        if method == "GET":
            url += "?" + urllib.parse.urlencode(params, doseq=True)
        else:
            request_data = urllib.parse.urlencode(params, doseq=True).encode()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    req = urllib.request.Request(url, data=request_data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        raise RuntimeError(f"Freelancer API {e.code}: {err_body}")
    except Exception as e:
        raise RuntimeError(f"Freelancer API network error: {type(e).__name__}: {e}")


def search_projects(query="", min_budget=0, max_budget=0, skills=None, limit=50, offset=0, project_types=None):
    """
    Search active projects via API.
    Uses endpoint /projects/0.1/projects/active
    query - search text
    skills - list of skills (skill IDs or names, API may ignore names)
    project_types - ["fixed"] for fixed-price only, ["hourly"] for hourly, None for all
    limit - max results (API max 100)
    """
    params = {
        "limit": min(limit, 100),
        "offset": offset,
        "compact": "true",
        "full_description": "true",
        "job_details": "true",
    }

    if query:
        params["query"] = query
    if min_budget > 0:
        params["min_budget"] = min_budget
    if max_budget > 0:
        params["max_budget"] = max_budget
    if skills:
        params["skills[]"] = skills
    if project_types:
        params["project_types[]"] = project_types
    else:
        params["project_types[]"] = "fixed"

    data = _api_request("/projects/0.1/projects/active", params)
    return data


def get_project_details(project_id):
    """Get project details by ID"""
    data = _api_request(f"/projects/0.1/projects/{project_id}", {"full_description": "true", "job_details": "true"})
    return data


def get_project_bids(project_id, limit=20, offset=0):
    """Get list of bids on a project"""
    data = _api_request(f"/projects/0.1/projects/{project_id}/bids/", {"limit": limit, "offset": offset, "compact": "true"})
    return data


def _make_job(project_data) -> dict:
    """Normalize project data to pipeline job format"""
    proj = project_data.get("project", project_data)

    title = proj.get("title", "")
    desc = proj.get("description", "")
    budget = proj.get("budget", {})
    budget_str = ""
    if budget:
        min_b = budget.get("minimum")
        max_b = budget.get("maximum")
        currency = budget.get("currency", {}).get("code", "USD")
        if min_b and max_b:
            budget_str = f"{min_b}-{max_b} {currency}"
        elif min_b:
            budget_str = f"from {min_b} {currency}"
        elif max_b:
            budget_str = f"up to {max_b} {currency}"

    # Skills (jobs array)
    skills = []
    for s in proj.get("jobs", []) or []:
        skills.append(s.get("name", ""))
    skills_str = ", ".join(skills) if skills else ""

    seo_url = proj.get("seo_url", "")
    url = f"https://www.freelancer.com/projects/{seo_url}" if seo_url else f"https://www.freelancer.com/projects/{proj.get('id')}"

    # Owner info
    owner = proj.get("owner", {})
    author = owner.get("username", owner.get("display_name", "freelancer.com"))

    return {
        "platform": "Freelancer.com",
        "kind": "order",
        "job_id": f"freelancer:{proj.get('id')}",
        "url": url,
        "title": title,
        "description": f"{desc}\n\nSkills: {skills_str}" if skills_str else desc,
        "budget": budget_str,
        "author": author,
        "contact": None,
        "scanned_at": __import__("modules.store", fromlist=["now"]).now(),
        "score": 0,
        "metadata": {
            "freelancer_id": proj.get("id"),
            "status": proj.get("status"),
            "currency": budget.get("currency", {}).get("code") if budget else None,
            "skills": skills,
            "bid_stats": proj.get("bid_stats", {}),
            "type": proj.get("type"),
        }
    }


def fetch_jobs(cfg: dict) -> tuple[list[dict], list[str]]:
    """Main entry point for scanner pipeline"""
    jobs = []
    errors = []

    if not cfg or not cfg.get("enabled"):
        return jobs, errors

    try:
        skills = cfg.get("search_skills") or [
            "python", "django", "fastapi", "react", "javascript", "typescript",
            "postgresql", "mongodb", "redis", "docker", "aws", "gcp",
            "ai", "machine learning", "nlp", "chatbot", "llm",
            "web scraping", "automation", "api", "integration"
        ]

        query = cfg.get("search_query", "")
        min_budget = cfg.get("min_budget", 100)
        max_budget = cfg.get("max_budget", 10000)
        limit = cfg.get("max_per_scan", 50)

        data = search_projects(
            query=query,
            min_budget=min_budget,
            max_budget=max_budget,
            skills=skills,
            limit=limit
        )

        projects = data.get("result", {}).get("projects", [])

        for p in projects:
            try:
                job = _make_job(p)
                jobs.append(job)
            except Exception as e:
                errors.append(f"parse error: {e}")

    except Exception as e:
        errors.append(f"freelancer.com API: {type(e).__name__}: {str(e)[:120]}")

    return jobs, errors


if __name__ == "__main__":
    import os
    cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    cfg = {}
    try:
        with open(cfg_path, encoding="utf-8") as f:
            cfg = ((json.load(f) or {}).get("sources") or {}).get("freelancer") or {}
    except Exception:
        pass

    jobs, errs = fetch_jobs(cfg)
    print(f"Found {len(jobs)} projects, errors: {errs}")
    for j in jobs[:5]:
        print(f"  {j['title'][:80]} | {j['budget']} | {j['url']}")