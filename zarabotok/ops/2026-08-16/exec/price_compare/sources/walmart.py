import os

import requests

from sources.base import ProductMatch, SourceAdapter


class WalmartAdapter(SourceAdapter):
    name = "walmart"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "application/json, text/html, */*",
        })
        self.proxy = os.environ.get("HTTP_PROXY", "")
        if self.proxy:
            self.session.proxies = {"http": self.proxy, "https": self.proxy}

    def search_by_upc(self, upc: str) -> ProductMatch | None:
        try:
            resp = self.session.get(
                "https://www.walmart.com/graphql/repSearchItems",
                params={"query": upc},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            return ProductMatch(upc, self.name, "", f"error: {e}", None, {"error": str(e)})

        items = data.get("data", {}).get("search", {}).get("searchResult", {}).get("itemStacks", [])
        for stack in items:
            for item in stack.get("items", []):
                price_raw = item.get("priceInfo", {}).get("currentPrice", {}).get("price")
                try:
                    price = float(price_raw) if price_raw is not None else None
                except (TypeError, ValueError):
                    price = None
                return ProductMatch(
                    upc,
                    self.name,
                    "https://www.walmart.com/ip/" + str(item.get("usItemId", "")),
                    item.get("name", ""),
                    price,
                    item,
                )
        return ProductMatch(upc, self.name, "", "", None, {"empty": True})