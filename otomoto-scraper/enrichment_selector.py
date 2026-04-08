import csv
import os
from datetime import datetime

from utils import safe_int


def _parse_int(value):
    try:
        return safe_int(value)
    except Exception:
        try:
            return int(value)
        except Exception:
            return None


def score_candidate(row: dict) -> int:
    """Simple heuristic score for enrichment priority (higher = more important)."""
    score = 0

    # fresh listings
    try:
        days = int(row.get("days_on_site") or 0)
    except Exception:
        days = 9999

    if days < 7:
        score += 30
    elif days < 30:
        score += 10

    # price changes
    if _parse_int(row.get("price_change_count") or 0) > 0:
        score += 30

    # private sellers slightly prioritized
    if (row.get("seller_type") or "").lower() == "private":
        score += 10

    # prefer active listings
    if str(row.get("is_active")) in ("1", "True", "true"):
        score += 5

    # price drop from initial
    init = _parse_int(row.get("initial_price_pln"))
    curr = _parse_int(row.get("price_pln"))
    lowest = _parse_int(row.get("lowest_price_pln"))
    if init and curr and curr < init:
        # relative discount
        try:
            rel = (init - curr) / max(1, init)
            score += int(min(20, rel * 100))
        except Exception:
            score += 5

    if lowest and init and lowest < init:
        score += 5

    return score


def select_from_csv(csv_file: str, top_n: int = 100) -> list[dict]:
    """Read storage CSV and return top_n candidates for enrichment.

    Output items contain: listing_id, link, priority (1-100), reason
    """
    if not os.path.exists(csv_file):
        return []

    rows = []
    with open(csv_file, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            # skip already fetched details
            if (row.get("details_status") or "").lower() == "fetched":
                continue

            # only active listings
            if str(row.get("is_active")) not in ("1", "True", "true"):
                continue

            sc = score_candidate(row)
            rows.append((sc, row))

    rows.sort(key=lambda x: x[0], reverse=True)

    out = []
    for sc, row in rows[:top_n]:
        priority = max(1, min(100, sc))
        reasons = []
        if int(row.get("days_on_site") or 0) < 7:
            reasons.append("fresh")
        if int(row.get("price_change_count") or 0) > 0:
            reasons.append("price_change")
        if (row.get("seller_type") or "").lower() == "private":
            reasons.append("private_seller")

        out.append({
            "listing_id": row.get("listing_id"),
            "link": row.get("link"),
            "priority": priority,
            "reason": ",".join(reasons) if reasons else "",
            "selected_at": datetime.utcnow().isoformat(),
        })

    return out


def write_queue(queue: list[dict], out_file: str):
    # determine fieldnames from queue plus defaults
    default = ["listing_id", "link", "priority", "reason", "selected_at"]
    extra = []
    if queue:
        keys = set()
        for item in queue:
            keys.update(item.keys())
        extra = [k for k in keys if k not in default]

    fieldnames = default + sorted(extra)
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(queue)


if __name__ == "__main__":
    # basic CLI for one CSV
    import sys
    if len(sys.argv) < 2:
        print("Usage: enrichment_selector.py <storage_csv> [top_n]")
        raise SystemExit(1)

    csv_file = sys.argv[1]
    top_n = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    q = select_from_csv(csv_file, top_n=top_n)
    out = os.path.join(os.path.dirname(csv_file), "enrichment_queue.csv")
    write_queue(q, out)
    print(f"Wrote {len(q)} candidates to {out}")
