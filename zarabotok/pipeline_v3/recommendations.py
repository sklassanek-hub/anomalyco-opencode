"""Recommendations engine: L3/L4 orders with high Score (§6.4)."""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from modules import filter


def build_recommendations() -> dict:
    result = filter.filter_with_agents()
    auto_reply = result.get("auto_reply", [])
    # Sort by skill_match_s + score + budget presence
    def sort_key(item):
        s = item.get("skill_match_s", 0)
        budget = item.get("budget", "")
        budget_score = 2 if any(ch.isdigit() for ch in str(budget)) else 0
        return s + budget_score + item.get("current_score", 0)

    best = sorted(auto_reply, key=sort_key, reverse=True)[:10]
    lines = []
    lines.append("| # | Title | Budget | Skill Score (S) | Score | Levels |")
    lines.append("|---|---|---|---|---|---|")
    for idx, item in enumerate(best, 1):
        title = (item.get("title", "") or "")[:60]
        budget = item.get("budget", "")
        s_score = item.get("skill_match_s", 0)
        score = item.get("current_score", 0)
        levels = ",".join(item.get("autonomy_levels_found", ["L0"]))
        lines.append(f"| {idx} | {title} | {budget} | {s_score} | {score} | {levels} |")
    table_text = "\n".join(lines)
    # Update docs file
    doc_path = os.path.join(BASE, "docs", "recommendations.md")
    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("{{ best_orders_table }}", table_text)
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(content)
    # Update proposal
    proposal_path = os.path.join(BASE, ".opencode", "new_sources_proposal.md")
    if os.path.exists(proposal_path):
        with open(proposal_path, "r", encoding="utf-8") as f:
            prop_content = f.read()
        prop_content += f"\n---\n## Рекомендации (§6.4) — лучшие L3/L4 заказы с высокой рентабельностью\n\n{table_text}\n"
        with open(proposal_path, "w", encoding="utf-8") as f:
            f.write(prop_content)
    else:
        # If proposal file is outside pipeline_v3, try parent
        parent_prop = os.path.join(os.path.dirname(BASE), ".opencode", "new_sources_proposal.md")
        if os.path.exists(parent_prop):
            with open(parent_prop, "r", encoding="utf-8") as f:
                prop_content = f.read()
            prop_content += f"\n---\n## Рекомендации (§6.4) — лучшие L3/L4 заказы с высокой рентабельностью\n\n{table_text}\n"
            with open(parent_prop, "w", encoding="utf-8") as f:
                f.write(prop_content)
    return {
        "total": result.get("total", 0),
        "auto_reply": len(auto_reply),
        "best_count": len(best),
        "best_orders": best,
        "table_text": table_text,
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    res = build_recommendations()
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
