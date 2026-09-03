from dataclasses import dataclass


@dataclass
class CompareRow:
    upc: str
    title: str
    walmart_price: float | None
    walmart_url: str
    amazon_price: float | None
    diff: float | None
    roi_pct: float | None
    note: str


def compare(match, amazon_price: float | None, amazon_asin: str) -> CompareRow:
    wp = match.price
    if wp is None:
        return CompareRow(
            match.upc, match.title, None, match.product_url, amazon_price, None, None,
            "walmart: no price",
        )
    if amazon_price is None:
        return CompareRow(
            match.upc, match.title, wp, match.product_url, None, None, None,
            f"amazon: not found (asin={amazon_asin or 'n/a'})",
        )
    diff = round(amazon_price - wp, 2)
    roi = round(diff / wp * 100, 2) if wp else None
    return CompareRow(
        match.upc, match.title, wp, match.product_url, amazon_price, diff, roi, "ok"
    )