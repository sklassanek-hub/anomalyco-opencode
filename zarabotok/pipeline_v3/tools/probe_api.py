"""Разведка каналов через Telethon API: читает публичные каналы/супергруппы, ищет посты с контактами."""
import asyncio
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

from modules import tg_scrape

CANDIDATES = [
    # чаты/группы (через веб t.me/s не читаются!)
    "freelancetavern", "frilans_chat", "freelance_chat_ru", "zakazy_freelance_chat",
    "fl_chat_freelance", "free_lance_chat", "orders_freelance_chat", "freelance_jobs_chat",
    "digital_freelance", "digitalrabota", "zakaz_chat", "freelance_tg_chat",
    # каналы
    "freelancechoice", "Koteyka_Freelancer", "llm_jobs", "findwork",
    "freelance_orders", "frilans", "vorkzavr", "workayte", "freelancersu",
    # ниши
    "python_freelance", "ai_freelance", "gpt_orders", "нейро_заказы",
    "parser_pro_orders", "web_orders_ru",
]


def main():
    t0 = time.time()
    results = []
    for i, ch in enumerate(CANDIDATES):
        r = asyncio.run(tg_scrape.probe_channel(ch, limit=20))
        results.append(r)
        ok = r.get("alive") and r.get("posts", 0)
        hit = ok and r.get("tg_contact", 0) >= 3
        flag = "HIT " if hit else ("live" if ok else "dead")
        print(f"[{i+1}/{len(CANDIDATES)}] {flag} {ch}: posts={r.get('posts')} tg={r.get('tg_contact')} new={r.get('newest')} users={r.get('users')} | {str(r.get('sample'))[:60]} | {r.get('reason', '')}", flush=True)
        time.sleep(1.0)
    print(f"\nвремя: {round(time.time()-t0)} сек")


if __name__ == "__main__":
    main()