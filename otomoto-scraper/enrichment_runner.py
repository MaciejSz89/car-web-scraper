"""Run enrichment selection across all query CSVs and produce a unified queue.

Usage:
    python enrichment_runner.py
"""
import glob
import os
from enrichment_selector import select_from_csv, write_queue


def find_storage_csvs(data_dir: str):
    pattern = os.path.join(data_dir, "*.csv")
    return glob.glob(pattern)


def run(data_dir: str = None, out_file: str = None, top_per_source: int = 50):
    if data_dir is None:
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "otomoto"))
    if out_file is None:
        out_file = os.path.join(data_dir, "enrichment_queue.csv")

    all_candidates = []
    for csv_file in find_storage_csvs(data_dir):
        candidates = select_from_csv(csv_file, top_n=top_per_source)
        # tag source quickly
        for c in candidates:
            c["source_csv"] = os.path.basename(csv_file)
        all_candidates.extend(candidates)

    # simple dedupe by listing_id, keep highest priority
    by_id = {}
    for c in all_candidates:
        lid = c.get("listing_id")
        if not lid:
            continue
        prev = by_id.get(lid)
        if not prev or int(c.get("priority") or 0) > int(prev.get("priority") or 0):
            by_id[lid] = c

    queue = sorted(by_id.values(), key=lambda r: int(r.get("priority") or 0), reverse=True)

    write_queue(queue, out_file)
    print(f"Wrote {len(queue)} items to {out_file}")


if __name__ == "__main__":
    run()
