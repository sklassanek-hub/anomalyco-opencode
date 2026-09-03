import os
import time

import requests


class KeepaClient:
    BASE = "https://api.keepa.com"

    def __init__(self):
        self.api_key = os.environ["KEEPA_API_KEY"]
        self.domain = int(os.environ.get("KEEPA_DOMAIN", "1"))
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "price-compare/1.0"})

    def search_upc(self, upc: str) -> str | None:
        resp = self.session.get(
            f"{self.BASE}/search",
            params={
                "key": self.api_key,
                "domain": self.domain,
                "type": "upc",
                "term": upc,
                "buybox": 1,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            raise RuntimeError(data["error"])
        products = data.get("products") or []
        if not products:
            return None
        products.sort(key=lambda p: p.get("buyBoxPrice") or float("inf"))
        return products[0].get("asin")

    def product_price(self, asin: str) -> float | None:
        resp = self.session.get(
            f"{self.BASE}/product",
            params={
                "key": self.api_key,
                "domain": self.domain,
                "asin": asin,
                "range": 24,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            raise RuntimeError(data["error"])
        products = data.get("products") or []
        if not products:
            return None
        product = products[0]
        buybox = product.get("buyBoxPrice")
        if buybox:
            return buybox / 100
        offers = product.get("offerCountFBA") or 0
        if offers:
            return 0.0
        return None