#!/usr/bin/env python3
"""Генерирует AGENTS.md каталог из agents_index.json (внутри проекта zarabotok)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CATS = json.load(open(os.path.join(HERE, "agents_index.json"), encoding="utf-8"))

LINES = [
    "# Каталог агентов проекта (184 субагента)",
    "",
    "Сгенерировано: 2026-08-16. Источник: agency-agents (Downloads), формат opencode.",
    "",
    "## Назначение",
    "",
    "- Все агенты лежат в `.opencode/agents/*.md` внутри проекта zarabotok (в рамках проекта, по требованию владельца).",
    "- Дубликат для runtime: `C:/Users/klass/OneDrive/Desktop/work/.opencode/agents/` (рабочая директория opencode).",
    "- Индекс JSON: `.opencode/agents_index.json`.",
    "- Скиллы: `.opencode/skills/` (37).",
    "",
]
for cat, ags in sorted(CATS.items(), key=lambda x: -len(x[1])):
    LINES.append(f"## {cat} ({len(ags)})")
    LINES.append("")
    for a in sorted(ags, key=lambda x: x["file"]):
        LINES.append(f"- **{a['name']}** (`{a['file']}`) — {a['desc'][:110]}")
    LINES.append("")

OUT = os.path.join(HERE, "AGENTS.md")
with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(LINES))
print(f"AGENTS.md сгенерирован: {len(LINES)} строк -> {OUT}")