from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from config import DATA_DIR


DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/135.0.0.0 Safari/537.36"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process enrichment queue and fetch listing details.")
    parser.add_argument(
        "--queue-file",
        default=None,
        help="Path to enrichment_queue.csv. Defaults to data_dir/enrichment_queue.csv.",
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Directory containing storage CSV files. Defaults to config.DATA_DIR.",
    )
    parser.add_argument(
        "--details-dir",
        default=None,
        help="Directory for sidecar JSON details. Defaults to data_dir/details.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of queue items to process.",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Re-process listings previously marked as failed.",
    )
    return parser.parse_args()


def load_queue(queue_file: str) -> list[dict[str, str]]:
    if not os.path.exists(queue_file):
        return []

    with open(queue_file, "r", newline="", encoding="utf-8-sig") as file_handle:
        reader = csv.DictReader(file_handle, delimiter=";")
        return [dict(row) for row in reader if row.get("listing_id") and row.get("link")]


def fetch_listing_html(url: str, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    request = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    with urlopen(request, timeout=timeout_seconds) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _extract_json_ld(soup: BeautifulSoup) -> list[Any]:
    payloads: list[Any] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text(strip=True)
        if not raw:
            continue
        try:
            payloads.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return payloads


def extract_detail_payload(html: str, url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    page_title = soup.title.get_text(" ", strip=True) if soup.title else None

    meta_description = None
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag:
        meta_description = meta_tag.get("content")

    json_ld_payloads = _extract_json_ld(soup)

    return {
        "url": url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "page_title": page_title,
        "meta_description": meta_description,
        "json_ld_count": len(json_ld_payloads),
        "structured_data": json_ld_payloads,
    }


def write_detail_json(details_dir: str, listing_id: str, payload: dict[str, Any]) -> str:
    os.makedirs(details_dir, exist_ok=True)
    output_path = os.path.join(details_dir, f"{listing_id}.json")
    with open(output_path, "w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, ensure_ascii=False, indent=2)
    return output_path


def _read_csv_rows(csv_file: str) -> tuple[list[str], list[dict[str, str]]]:
    with open(csv_file, "r", newline="", encoding="utf-8-sig") as file_handle:
        reader = csv.DictReader(file_handle, delimiter=";")
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    return fieldnames, rows


def _write_csv_rows(csv_file: str, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with open(csv_file, "w", newline="", encoding="utf-8-sig") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)


def get_listing_enrichment_status(csv_file: str, listing_id: str) -> str | None:
    if not os.path.exists(csv_file):
        return None

    _, rows = _read_csv_rows(csv_file)
    for row in rows:
        if row.get("listing_id") == listing_id:
            status = (row.get("details_status") or "").strip().lower()
            return status or None

    return None


def update_listing_enrichment_status(
    csv_file: str,
    listing_id: str,
    *,
    status: str,
    fetched_at: str,
    priority: str | int | None = None,
) -> bool:
    if not os.path.exists(csv_file):
        return False

    fieldnames, rows = _read_csv_rows(csv_file)
    required_fields = ["details_status", "details_priority", "details_fetched_at"]
    for field in required_fields:
        if field not in fieldnames:
            fieldnames.append(field)

    updated = False
    for row in rows:
        if row.get("listing_id") != listing_id:
            continue
        row["details_status"] = status
        row["details_fetched_at"] = fetched_at
        if priority is not None:
            row["details_priority"] = str(priority)
        updated = True
        break

    if updated:
        _write_csv_rows(csv_file, fieldnames, rows)

    return updated


def find_listing_csv(data_dir: str, listing_id: str, source_csv: str | None = None) -> str | None:
    candidate_files: list[str] = []
    if source_csv:
        candidate_files.append(os.path.join(data_dir, source_csv))

    for file_name in os.listdir(data_dir):
        if not file_name.endswith(".csv"):
            continue
        if file_name == "enrichment_queue.csv":
            continue
        full_path = os.path.join(data_dir, file_name)
        if full_path not in candidate_files:
            candidate_files.append(full_path)

    for csv_file in candidate_files:
        if not os.path.exists(csv_file):
            continue
        _, rows = _read_csv_rows(csv_file)
        if any(row.get("listing_id") == listing_id for row in rows):
            return csv_file

    return None


def process_queue_item(
    item: dict[str, str],
    *,
    data_dir: str,
    details_dir: str,
    fetch_html: Callable[[str], str] = fetch_listing_html,
) -> dict[str, Any]:
    listing_id = str(item.get("listing_id") or "").strip()
    link = str(item.get("link") or "").strip()
    priority = item.get("priority") or ""
    source_csv = item.get("source_csv") or None
    processed_at = datetime.now(timezone.utc).isoformat()

    if not listing_id or not link:
        return {"listing_id": listing_id, "status": "skipped", "reason": "missing listing_id or link"}

    csv_file = find_listing_csv(data_dir, listing_id, source_csv)
    if not csv_file:
        return {"listing_id": listing_id, "status": "failed", "reason": "listing not found in storage csv"}

    try:
        html = fetch_html(link)
        payload = extract_detail_payload(html, link)
        output_path = write_detail_json(details_dir, listing_id, payload)
        update_listing_enrichment_status(
            csv_file,
            listing_id,
            status="fetched",
            fetched_at=processed_at,
            priority=priority,
        )
        return {
            "listing_id": listing_id,
            "status": "fetched",
            "details_file": output_path,
            "csv_file": csv_file,
        }
    except (OSError, URLError, ValueError) as exc:
        update_listing_enrichment_status(
            csv_file,
            listing_id,
            status="failed",
            fetched_at=processed_at,
            priority=priority,
        )
        return {
            "listing_id": listing_id,
            "status": "failed",
            "csv_file": csv_file,
            "reason": str(exc),
        }


def run(
    queue_file: str | None = None,
    *,
    data_dir: str | None = None,
    details_dir: str | None = None,
    limit: int | None = None,
    retry_failed: bool = False,
    fetch_html: Callable[[str], str] = fetch_listing_html,
) -> list[dict[str, Any]]:
    resolved_data_dir = data_dir or str(DATA_DIR)
    resolved_queue_file = queue_file or os.path.join(resolved_data_dir, "enrichment_queue.csv")
    resolved_details_dir = details_dir or os.path.join(resolved_data_dir, "details")

    raw_queue = load_queue(resolved_queue_file)
    queue: list[dict[str, str]] = []

    for item in raw_queue:
        listing_id = str(item.get("listing_id") or "").strip()
        source_csv = item.get("source_csv") or None
        csv_file = find_listing_csv(resolved_data_dir, listing_id, source_csv)

        if csv_file:
            current_status = get_listing_enrichment_status(csv_file, listing_id)
            if current_status == "fetched":
                continue
            if current_status == "failed" and not retry_failed:
                continue

        queue.append(item)

    if limit is not None:
        queue = queue[:limit]

    results: list[dict[str, Any]] = []
    for item in queue:
        results.append(
            process_queue_item(
                item,
                data_dir=resolved_data_dir,
                details_dir=resolved_details_dir,
                fetch_html=fetch_html,
            )
        )

    fetched = sum(result.get("status") == "fetched" for result in results)
    failed = sum(result.get("status") == "failed" for result in results)
    skipped = sum(result.get("status") == "skipped" for result in results)
    print(
        f"Enrichment processed {len(results)} items: "
        f"{fetched} fetched, {failed} failed, {skipped} skipped."
    )
    return results


def main() -> None:
    args = parse_args()
    run(
        queue_file=args.queue_file,
        data_dir=args.data_dir,
        details_dir=args.details_dir,
        limit=args.limit,
        retry_failed=args.retry_failed,
    )


if __name__ == "__main__":
    main()
