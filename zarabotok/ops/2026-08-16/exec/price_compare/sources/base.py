from dataclasses import dataclass


@dataclass
class ProductMatch:
    upc: str
    source: str
    product_url: str
    title: str
    price: float | None
    raw: dict


class SourceAdapter:
    name = "base"

    def search_by_upc(self, upc: str) -> ProductMatch:
        raise NotImplementedError