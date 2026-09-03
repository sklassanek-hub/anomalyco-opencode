import csv


def export_report(rows, out_path: str) -> None:
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "UPC", "Title", "WalmartPriceUSD", "WalmartURL",
            "AmazonPriceUSD", "DiffUSD", "ROI%", "Note",
        ])
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "UPC": r.upc,
                "Title": r.title,
                "WalmartPriceUSD": r.walmart_price if r.walmart_price is not None else "",
                "WalmartURL": r.walmart_url,
                "AmazonPriceUSD": r.amazon_price if r.amazon_price is not None else "",
                "DiffUSD": r.diff if r.diff is not None else "",
                "ROI%": r.roi_pct if r.roi_pct is not None else "",
                "Note": r.note,
            })