"""Price comparison CLI: input CSV (UPC/EAN/GTIN) -> report CSV (Walmart vs Amazon)."""
import argparse
import csv
import sys
import time

from compare import compare
from keepa_client import KeepaClient
from report import export_report
from sources.walmart import WalmartAdapter

UPC_ALIASES = ("upc", "ean", "gtin", "barcode", "sku")
MIN_PAUSE_SEC = 2.0


def load_orders(path: str) -> list[tuple[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit(f"input {path}: no header row")
        aliases = {h.lower() for h in reader.fieldnames}
        col = next((c for c in reader.fieldnames if c.lower() in UPC_ALIASES), None)
        if col is None:
            raise SystemExit(f"input {path}: no UPC/EAN/GTIN column found in {reader.fieldnames}")
        title_col = next(
            (c for c in reader.fieldnames if c.lower() in ("title", "name", "product")),
            None,
        )
        rows = []
        for i, r in enumerate(reader, start=2):
            upc = (r.get(col) or "").strip()
            if not upc:
                continue
            if not (upc.isdigit() and len(upc) in (8, 12, 13, 14)):
                raise SystemExit(f"input {path}: row {i}: bad barcode {upc!r}")
            title = (r.get(title_col) or "").strip() if title_col else ""
            rows.append((upc, title))
    return rows


def run(orders, walmart, keepa, delay) -> list:
    rows = []
    total = len(orders)
    for idx, (upc, title) in enumerate(orders, start=1):
        print(f"[{idx}/{total}] {upc}", flush=True)
        match = walmart.search_by_upc(upc)
        amazon_asin = None
        amazon_price = None
        try:
            amazon_asin = keepa.search_upc(upc)
            if amazon_asin:
                amazon_price = keepa.product_price(amazon_asin)
        except Exception as e:
            print(f"    keepa error: {e}", flush=True)
        row = compare(match, amazon_price, amazon_asin)
        if not row.title and title:
            row.title = title
        rows.append(row)
        if idx != total:
            time.sleep(delay)
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Walmart vs Amazon price comparison")
    parser.add_argument("input", help="input CSV with UPC/EAN/GTIN column")
    parser.add_argument("output", nargs="?", default="report.csv", help="output CSV path")
    parser.add_argument("--delay", type=float, default=MIN_PAUSE_SEC, help="pause between items, sec")
    args = parser.parse_args(argv)

    orders = load_orders(args.input)
    if not orders:
        raise SystemExit("input: no rows")

    walmart = WalmartAdapter()
    keepa = KeepaClient()

    rows = run(orders, walmart, keepa, args.delay)
    export_report(rows, args.output)

    ok = [r for r in rows if r.diff is not None]
    print(f"\ndone: {len(ok)}/{len(rows)} matched")
    for r in sorted(ok, key=lambda r: r.roi_pct or 0, reverse=True)[:5]:
        print(f"  {r.upc}: w=${r.walmart_price} a=${r.amazon_price} diff=${r.diff} roi={r.roi_pct}%")
    print(f"report: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())