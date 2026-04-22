from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import random
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from config import DATA_DIR, HEADLESS, SESSION_STATE_FILE_MOBILE_DE
from enrichment_analysis import analyze_detail_payload
from utils import clean_text, safe_int


DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_FETCH_COOLDOWN_DAYS = 7
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/135.0.0.0 Safari/537.36"
)

BUCKET_RANKS = {
    "ignore": 0,
    "watch": 1,
    "candidate": 2,
    "high-priority": 3,
}

logger = logging.getLogger(__name__)


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
    parser.add_argument(
        "--cooldown-days",
        type=int,
        default=DEFAULT_FETCH_COOLDOWN_DAYS,
        help="Skip re-fetching listings enriched within the last N days.",
    )
    return parser.parse_args()


def load_queue(queue_file: str) -> list[dict[str, str]]:
    if not os.path.exists(queue_file):
        return []

    with open(queue_file, "r", newline="", encoding="utf-8-sig") as file_handle:
        reader = csv.DictReader(file_handle, delimiter=";")
        return [dict(row) for row in reader if row.get("listing_id") and row.get("link")]


def flush_completed_from_queue(
    queue_file: str,
    processed_ids: set[str],
) -> int:
    """Remove from queue_file all entries whose listing_id is in processed_ids.

    Returns the number of rows removed.
    """
    if not os.path.exists(queue_file) or not processed_ids:
        return 0

    with open(queue_file, "r", newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    remaining = [r for r in rows if r.get("listing_id") not in processed_ids]
    removed = len(rows) - len(remaining)

    if removed == 0:
        return 0

    with open(queue_file, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(remaining)

    logger.info("Enrichment queue: usunięto %d przetworzonych wpisów, pozostało %d.", removed, len(remaining))
    return removed


def fetch_listing_html(url: str, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    request = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    with urlopen(request, timeout=timeout_seconds) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


class MobileDeHtmlFetcher:
    """Camoufox-based fetcher for mobile.de detail pages.

    Maintains a single browser session to avoid repeated Akamai challenges.
    Lazy initialization — the browser starts on the first __call__.
    """

    _HOME = "https://www.mobile.de/"
    _CHALLENGE_SEL = "#sec-if-cpt-container, #sec-bc-tile-container"

    def __init__(self, *, headless: bool = True, session_state_file: Path | None = None) -> None:
        self._headless = headless
        self._session_state_file = session_state_file
        self._camoufox: Any = None
        self._browser: Any = None
        self._ctx: Any = None
        self._page: Any = None
        self._homepage_visited = False

    def _ensure_browser(self) -> None:
        if self._page is not None:
            return
        from camoufox.sync_api import Camoufox  # lazy import — only when actually used
        self._camoufox = Camoufox(headless=self._headless, humanize=True, os="windows", geoip=True)
        self._browser = self._camoufox.__enter__()
        ctx_kwargs: dict[str, Any] = {}
        if self._session_state_file and self._session_state_file.exists():
            ctx_kwargs["storage_state"] = str(self._session_state_file)
        self._ctx = self._browser.new_context(**ctx_kwargs)
        self._page = self._ctx.new_page()

    def _wait_for_akamai(self, max_attempts: int = 15) -> None:
        for _ in range(max_attempts):
            if self._page.locator(self._CHALLENGE_SEL).count() > 0:
                self._page.wait_for_timeout(3000)
            else:
                break

    def _accept_cookies(self) -> None:
        for sel in (
            "button.mde-consent-accept-btn",
            "button:has-text('Einverstanden')",
            "button:has-text('Alle akzeptieren')",
        ):
            try:
                btn = self._page.locator(sel).first
                if btn.count() > 0:
                    btn.click(timeout=3000)
                    self._page.wait_for_timeout(1500)
                    return
            except Exception:
                pass

    def _visit_homepage(self) -> None:
        self._page.goto(self._HOME, wait_until="domcontentloaded", timeout=60_000)
        self._page.wait_for_timeout(2000)
        self._wait_for_akamai()
        self._accept_cookies()
        self._page.wait_for_timeout(1500)
        logger.info("MobileDeHtmlFetcher: homepage załadowana: %s", self._page.title())
        self._save_session()

    def _save_session(self) -> None:
        if self._session_state_file and self._ctx is not None:
            try:
                self._ctx.storage_state(path=str(self._session_state_file))
            except Exception:
                pass

    def __call__(self, url: str) -> str:
        self._ensure_browser()
        if not self._homepage_visited:
            self._visit_homepage()
            self._homepage_visited = True
        self._page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        self._wait_for_akamai()
        self._page.wait_for_timeout(2000)
        html = self._page.content()
        self._save_session()
        return html

    def close(self) -> None:
        if self._camoufox is not None:
            try:
                self._camoufox.__exit__(None, None, None)
            except Exception:
                pass
            self._camoufox = None
            self._browser = None
            self._ctx = None
            self._page = None

    def __enter__(self) -> "MobileDeHtmlFetcher":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


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


def _extract_next_data(soup: BeautifulSoup) -> dict[str, Any] | None:
    script = soup.find("script", attrs={"id": "__NEXT_DATA__", "type": "application/json"})
    if not script:
        return None

    raw = script.string or script.get_text(strip=True)
    if not raw:
        return None

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None

    return payload if isinstance(payload, dict) else None


def _find_nested_key(payload: Any, target_key: str) -> Any:
    if isinstance(payload, dict):
        if target_key in payload:
            return payload[target_key]
        for value in payload.values():
            found = _find_nested_key(value, target_key)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_nested_key(item, target_key)
            if found is not None:
                return found
    return None


def _extract_advert(next_data: dict[str, Any] | None) -> dict[str, Any]:
    if not next_data:
        return {}

    advert = _find_nested_key(next_data, "advert")
    return advert if isinstance(advert, dict) else {}


def _normalize_text_list(values: Any) -> list[str]:
    normalized: list[str] = []
    items = values if isinstance(values, list) else []
    for item in items:
        if isinstance(item, str):
            text = clean_text(item)
            if text:
                normalized.append(text)
            continue

        if not isinstance(item, dict):
            continue

        for key in ("label", "name", "value", "text"):
            text = clean_text(item.get(key))
            if text:
                normalized.append(text)
                break

    return normalized


def _normalize_parameters(parameters: Any) -> dict[str, Any]:
    if not isinstance(parameters, dict):
        return {}

    normalized: dict[str, Any] = {}
    for key, value in parameters.items():
        if isinstance(value, dict):
            # Otomoto format: {"label": "<key>", "values": [{"value": "...", "label": "..."}, ...]}
            values_list = value.get("values")
            if isinstance(values_list, list) and values_list:
                extracted = [
                    item.get("value") if isinstance(item, dict) else item
                    for item in values_list
                    if (item.get("value") if isinstance(item, dict) else item) not in (None, "")
                ]
                if len(extracted) == 1:
                    normalized[key] = extracted[0]
                elif len(extracted) > 1:
                    normalized[key] = extracted
                continue

            # Legacy format: {"value": "...", "label": "..."}
            candidate = value.get("value")
            if candidate is None:
                candidate = value.get("label")
            if candidate is None:
                candidate = value.get("name")
            if candidate is not None:
                normalized[key] = candidate
                continue

        if isinstance(value, list):
            list_values: list[Any] = []
            for item in value:
                if isinstance(item, dict):
                    candidate = item.get("value")
                    if candidate is None:
                        candidate = item.get("label")
                    if candidate is None:
                        candidate = item.get("name")
                    list_values.append(candidate)
                else:
                    list_values.append(item)
            normalized[key] = [item for item in list_values if item not in (None, "")]
            continue

        normalized[key] = value

    return normalized


def _extract_dom_description(soup: BeautifulSoup) -> str | None:
    for selector in (
        '[data-testid*="description"]',
        '[class*="description"]',
    ):
        node = soup.select_one(selector)
        if not node:
            continue
        text = clean_text(node.get_text(" ", strip=True))
        if text:
            return text
    return None


def _extract_seller_summary(advert: dict[str, Any], soup: BeautifulSoup) -> dict[str, Any]:
    seller = advert.get("seller")
    summary: dict[str, Any] = {}
    if isinstance(seller, dict):
        for source_key, target_key in (
            ("name", "name"),
            ("type", "type"),
            ("id", "id"),
            ("slug", "slug"),
        ):
            value = seller.get(source_key)
            if value not in (None, ""):
                summary[target_key] = value

        phone_numbers = seller.get("phoneNumbers") or advert.get("phoneNumbers")
        if isinstance(phone_numbers, list) and phone_numbers:
            summary["phone_numbers"] = [str(number) for number in phone_numbers if number not in (None, "")]

    if summary:
        return summary

    seller_node = soup.select_one('[data-testid*="seller"]')
    if not seller_node:
        return {}

    text = clean_text(seller_node.get_text(" ", strip=True))
    return {"display_text": text} if text else {}


def _collect_fields_present(payload: dict[str, Any]) -> list[str]:
    fields: list[str] = []
    for field in (
        "page_title",
        "meta_description",
        "description",
        "seller",
        "price",
        "equipment",
        "parameters",
        "ad_features",
        "main_features",
        "structured_data",
        "next_data",
    ):
        value = payload.get(field)
        if value in (None, "", [], {}):
            continue
        fields.append(field)
    return fields


def _stringify_bool(value: bool | None) -> str:
    if value is None:
        return ""
    return "1" if value else "0"


def _build_description_excerpt(description: str | None, max_length: int = 400) -> str:
    if not description:
        return ""

    plain_text = clean_text(BeautifulSoup(description, "html.parser").get_text(" ", strip=True))
    if not plain_text:
        return ""
    if len(plain_text) <= max_length:
        return plain_text
    return plain_text[: max_length - 3].rstrip() + "..."


def _parameter_value(parameters: dict[str, Any], key: str) -> str:
    raw_value = clean_text(parameters.get(key))
    if not raw_value:
        return ""

    lowered = raw_value.lower()
    if lowered == key.lower():
        return ""
    return raw_value


def _parameter_flag(parameters: dict[str, Any], key: str) -> bool | None:
    raw_value = parameters.get(key)
    if raw_value in (None, "", [], {}):
        return None

    normalized = str(raw_value).strip().lower()
    if normalized == key.lower():  # key==value means unresolved (legacy/broken normalization)
        return None
    if normalized in {"0", "false", "no", "nie"}:
        return False
    return True


def build_csv_detail_summary(payload: dict[str, Any], listing_row: dict[str, str]) -> dict[str, str]:
    analysis_result = analyze_detail_payload(str(listing_row.get("listing_id") or ""), payload, listing_row=listing_row)
    parameters = payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {}
    seller = payload.get("seller") if isinstance(payload.get("seller"), dict) else {}

    no_accident_flag = (
        "accident_free_declared" in analysis_result.enrichment_flags
        or "accident_free_structural" in analysis_result.enrichment_flags
        or _parameter_flag(parameters, "no_accident") is True
    )
    damaged_flag = (
        "damage_declared" in analysis_result.enrichment_flags
        or "damage_structural" in analysis_result.enrichment_flags
        or _parameter_flag(parameters, "damaged") is True
    )
    service_record_flag = (
        "aso_service" in analysis_result.enrichment_flags
        or "documented_history" in analysis_result.enrichment_flags
        or _parameter_flag(parameters, "service_record") is True
    )
    imported_flag = (
        "import_flag_present" in analysis_result.enrichment_flags
        or _parameter_flag(parameters, "is_imported_car") is True
    )

    return {
        "description_excerpt": _build_description_excerpt(payload.get("description")),
        "seller_name": clean_text(seller.get("name")) or "",
        "vin": _parameter_value(parameters, "vin"),
        "country_origin": _parameter_value(parameters, "country_origin"),
        "no_accident_flag": _stringify_bool(no_accident_flag),
        "damaged_flag": _stringify_bool(damaged_flag),
        "service_record_flag": _stringify_bool(service_record_flag),
        "imported_flag": _stringify_bool(imported_flag),
        "enrichment_score": str(analysis_result.enrichment_score),
        "enrichment_confidence": str(analysis_result.enrichment_confidence),
        "enrichment_flags": ",".join(analysis_result.enrichment_flags),
    }


def extract_detail_payload(html: str, url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    page_title = soup.title.get_text(" ", strip=True) if soup.title else None

    meta_description = None
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag:
        meta_description = meta_tag.get("content")

    json_ld_payloads = _extract_json_ld(soup)
    next_data = _extract_next_data(soup)
    advert = _extract_advert(next_data)
    description = clean_text(advert.get("description")) or _extract_dom_description(soup)
    parameters = _normalize_parameters(advert.get("parametersDict"))
    equipment = _normalize_text_list(advert.get("equipment"))
    ad_features = _normalize_text_list(advert.get("adFeatures"))
    main_features = _normalize_text_list(advert.get("mainFeatures"))
    seller = _extract_seller_summary(advert, soup)

    advert_price = advert.get("price")
    if isinstance(advert_price, dict):
        normalized_price: Any = {
            key: value
            for key, value in advert_price.items()
            if value not in (None, "", [], {})
        }
    else:
        normalized_price = advert_price

    payload = {
        "url": url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "page_title": page_title,
        "meta_description": meta_description,
        "json_ld_count": len(json_ld_payloads),
        "structured_data": json_ld_payloads,
        "description": description,
        "seller": seller,
        "price": normalized_price,
        "equipment": equipment,
        "parameters": parameters,
        "ad_features": ad_features,
        "main_features": main_features,
        "source": {
            "next_data_present": bool(next_data),
            "advert_keys": sorted(advert.keys()) if advert else [],
        },
    }

    if next_data is not None:
        build_id = next_data.get("buildId")
        next_data_summary = {"buildId": build_id} if build_id else {"present": True}
        payload["next_data"] = next_data_summary

    payload["fields_present"] = _collect_fields_present(payload)

    return payload


def extract_detail_payload_mobile_de(html: str, url: str) -> dict[str, Any]:
    """Parse a mobile.de VIP (detail) page HTML and return a payload matching
    the schema used by build_csv_detail_summary / analyze_detail_payload.

    Data comes from ``window.__INITIAL_STATE__`` embedded in the page:
      search.vip.ads.<id>.data.ad → attributes (list), features, htmlDescription,
      contactInfo, price, highlights.
    """
    soup = BeautifulSoup(html, "html.parser")
    page_title = soup.title.get_text(" ", strip=True) if soup.title else None

    # Extract window.__INITIAL_STATE__ JSON blob
    initial_state: dict[str, Any] = {}
    for script in soup.find_all("script"):
        raw = script.string or ""
        if "window.__INITIAL_STATE__" not in raw:
            continue
        m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.+\})\s*;?\s*$", raw, re.DOTALL)
        if m:
            try:
                initial_state = json.loads(m.group(1))
            except (json.JSONDecodeError, ValueError):
                pass
        break

    # Navigate to the ad object: search.vip.ads.<id>.data.ad
    ad: dict[str, Any] = {}
    vip_ads = (initial_state.get("search") or {}).get("vip", {}).get("ads", {})
    for wrapper in vip_ads.values():
        candidate = (wrapper.get("data") or {}).get("ad")
        if isinstance(candidate, dict):
            ad = candidate
            break

    # Attributes list → flat dict keyed by tag
    attr_map: dict[str, Any] = {}
    for attr in (ad.get("attributes") or []):
        if isinstance(attr, dict) and attr.get("tag"):
            attr_map[attr["tag"]] = attr.get("value")

    # Equipment / features (list of plain strings)
    features: list[str] = [str(f) for f in (ad.get("features") or []) if f]

    # Description: mobile.de provides htmlDescription
    description: str | None = None
    html_desc = ad.get("htmlDescription")
    if html_desc:
        description = clean_text(
            BeautifulSoup(html_desc, "html.parser").get_text(" ", strip=True)
        )

    # Seller
    contact: dict[str, Any] = ad.get("contactInfo") or {}
    seller: dict[str, Any] = {}
    if contact.get("name"):
        seller["name"] = contact["name"]
    if contact.get("sellerType"):
        seller["type"] = contact["sellerType"].lower()
    if contact.get("country"):
        seller["country"] = contact["country"]

    # Price
    price_raw = ad.get("price") or {}
    price: dict[str, Any] = {}
    if isinstance(price_raw, dict):
        if price_raw.get("grossAmount") is not None:
            price["amount"] = price_raw["grossAmount"]
        if price_raw.get("grossCurrency"):
            price["currency"] = price_raw["grossCurrency"]

    # Parameters — map mobile.de attributes to normalized keys understood by
    # build_csv_detail_summary / analyze_detail_payload
    parameters: dict[str, Any] = {}

    # Accident / damage: damageCondition = "Unfallfahrzeug"
    damage_cond = str(attr_map.get("damageCondition") or "").lower()
    if "unfallfahrzeug" in damage_cond:
        parameters["damaged"] = True

    # Country of origin: seller's country (always "DE" for German listings)
    seller_country = str(contact.get("country") or "").upper()
    if seller_country:
        parameters["country_origin"] = seller_country

    # Service record: check features list and description for German keywords
    service_keywords = {"scheckheft", "serviceheft", "scheckheftgepflegt"}
    if {f.lower() for f in features} & service_keywords:
        parameters["service_record"] = True
    elif description and any(kw in description.lower() for kw in service_keywords):
        parameters["service_record"] = True

    # Highlights → ad_features (e.g. "nationale Auslieferung")
    highlights: list[str] = [str(h) for h in (ad.get("highlights") or []) if h]

    json_ld_payloads = _extract_json_ld(soup)

    payload: dict[str, Any] = {
        "url": url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "page_title": page_title,
        "meta_description": None,
        "json_ld_count": len(json_ld_payloads),
        "structured_data": json_ld_payloads,
        "description": description,
        "seller": seller,
        "price": price or None,
        "equipment": features,
        "parameters": parameters,
        "ad_features": highlights,
        "main_features": [],
        "source": {
            "initial_state_present": bool(initial_state),
            "ad_keys": sorted(ad.keys()) if ad else [],
        },
    }
    payload["fields_present"] = _collect_fields_present(payload)
    return payload


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


def get_listing_row(csv_file: str, listing_id: str) -> dict[str, str] | None:
    if not os.path.exists(csv_file):
        return None

    _, rows = _read_csv_rows(csv_file)
    for row in rows:
        if row.get("listing_id") == listing_id:
            return row

    return None


def parse_enrichment_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def is_in_cooldown(
    fetched_at: str | None,
    *,
    cooldown_days: int,
    now: datetime | None = None,
) -> bool:
    if cooldown_days <= 0:
        return False

    parsed = parse_enrichment_timestamp(fetched_at)
    if parsed is None:
        return False

    current_time = now or datetime.now(timezone.utc)
    return current_time - parsed < timedelta(days=cooldown_days)


def update_listing_enrichment_status(
    csv_file: str,
    listing_id: str,
    *,
    status: str,
    fetched_at: str,
    priority: str | int | None = None,
    based_on_price_pln: str | int | None = None,
    based_on_last_seen_date: str | None = None,
    based_on_decision_bucket: str | None = None,
    fields_present: list[str] | None = None,
    detail_summary: dict[str, str] | None = None,
    active: bool | None = None,
) -> bool:
    if not os.path.exists(csv_file):
        return False

    fieldnames, rows = _read_csv_rows(csv_file)
    required_fields = [
        "details_status",
        "details_priority",
        "details_fetched_at",
        "details_based_on_price_pln",
        "details_based_on_last_seen_date",
        "details_based_on_decision_bucket",
        "details_fields_present",
        "details_description_excerpt",
        "details_seller_name",
        "details_vin",
        "details_country_origin",
        "details_no_accident_flag",
        "details_damaged_flag",
        "details_service_record_flag",
        "details_imported_flag",
        "details_enrichment_score",
        "details_enrichment_confidence",
        "details_enrichment_flags",
        "is_active",
    ]
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
        if based_on_price_pln is not None:
            row["details_based_on_price_pln"] = str(based_on_price_pln)
        if based_on_last_seen_date is not None:
            row["details_based_on_last_seen_date"] = based_on_last_seen_date
        if based_on_decision_bucket is not None:
            row["details_based_on_decision_bucket"] = based_on_decision_bucket
        if fields_present is not None:
            row["details_fields_present"] = ",".join(fields_present)
        if detail_summary is not None:
            row["details_description_excerpt"] = detail_summary.get("description_excerpt", "")
            row["details_seller_name"] = detail_summary.get("seller_name", "")
            row["details_vin"] = detail_summary.get("vin", "")
            row["details_country_origin"] = detail_summary.get("country_origin", "")
            row["details_no_accident_flag"] = detail_summary.get("no_accident_flag", "")
            row["details_damaged_flag"] = detail_summary.get("damaged_flag", "")
            row["details_service_record_flag"] = detail_summary.get("service_record_flag", "")
            row["details_imported_flag"] = detail_summary.get("imported_flag", "")
            row["details_enrichment_score"] = detail_summary.get("enrichment_score", "")
            row["details_enrichment_confidence"] = detail_summary.get("enrichment_confidence", "")
            row["details_enrichment_flags"] = detail_summary.get("enrichment_flags", "")
        if active is not None:
            row["is_active"] = "1" if active else "0"
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


def get_analytics_file_path(data_dir: str, source_csv: str | None) -> str | None:
    if not source_csv:
        return None

    stem, _ = os.path.splitext(source_csv)
    analytics_file = os.path.join(data_dir, "analytics", f"{stem}-analysis.json")
    return analytics_file if os.path.exists(analytics_file) else None


def load_analytics_index(data_dir: str, source_csv: str | None) -> dict[str, dict[str, Any]]:
    analytics_file = get_analytics_file_path(data_dir, source_csv)
    if not analytics_file:
        return {}

    try:
        with open(analytics_file, "r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(payload, list):
        return {}

    index: dict[str, dict[str, Any]] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        listing_id = str(item.get("listing_id") or "").strip()
        if listing_id:
            index[listing_id] = item
    return index


def get_current_decision_bucket(
    data_dir: str,
    source_csv: str | None,
    listing_id: str,
    analytics_cache: dict[str, dict[str, dict[str, Any]]],
) -> str:
    cache_key = source_csv or ""
    if cache_key not in analytics_cache:
        analytics_cache[cache_key] = load_analytics_index(data_dir, source_csv)

    listing = analytics_cache[cache_key].get(listing_id) or {}
    return str(listing.get("decision_bucket") or "").strip().lower()


def should_bypass_cooldown(
    row: dict[str, str] | None,
    *,
    current_decision_bucket: str,
) -> bool:
    if not row:
        return False

    current_price = safe_int(row.get("price_pln"))
    previous_price = safe_int(row.get("details_based_on_price_pln"))
    if current_price is not None and previous_price is not None and current_price != previous_price:
        return True

    previous_bucket = str(row.get("details_based_on_decision_bucket") or "").strip().lower()
    if not previous_bucket or not current_decision_bucket:
        return False

    return BUCKET_RANKS.get(current_decision_bucket, -1) > BUCKET_RANKS.get(previous_bucket, -1)


def process_queue_item(
    item: dict[str, str],
    *,
    data_dir: str,
    details_dir: str,
    analytics_cache: dict[str, dict[str, dict[str, Any]]] | None = None,
    fetch_html: Callable[[str], str] = fetch_listing_html,
    fetch_html_mobile_de: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    listing_id = str(item.get("listing_id") or "").strip()
    link = str(item.get("link") or "").strip()
    priority = item.get("priority") or ""
    source_csv = item.get("source_csv") or None
    processed_at = datetime.now(timezone.utc).isoformat()

    if not listing_id or not link:
        return {
            "listing_id": listing_id,
            "status": "skipped",
            "reason": "missing listing_id or link",
            "source_csv": source_csv,
            "link": link,
        }

    item_source = _get_item_source(item)
    if item_source == "mobile_de" and fetch_html_mobile_de is None:
        logger.info("Enrichment: pomijam %s (source=mobile_de, brak fetchera Camoufox)", listing_id)
        return {
            "listing_id": listing_id,
            "status": "skipped",
            "reason": "source=mobile_de: fetcher not configured",
            "source_csv": source_csv,
            "link": link,
        }

    csv_file = find_listing_csv(data_dir, listing_id, source_csv)
    if not csv_file:
        return {
            "listing_id": listing_id,
            "status": "failed",
            "reason": "listing not found in storage csv",
            "source_csv": source_csv,
            "link": link,
        }

    current_row = get_listing_row(csv_file, listing_id) or {}
    cache = analytics_cache if analytics_cache is not None else {}
    current_decision_bucket = get_current_decision_bucket(data_dir, source_csv, listing_id, cache)

    try:
        if item_source == "mobile_de":
            html = fetch_html_mobile_de(link)  # type: ignore[misc]
            payload = extract_detail_payload_mobile_de(html, link)
        else:
            html = fetch_html(link)
            payload = extract_detail_payload(html, link)
        output_path = write_detail_json(details_dir, listing_id, payload)
        detail_summary = build_csv_detail_summary(payload, current_row)
        update_listing_enrichment_status(
            csv_file,
            listing_id,
            status="fetched",
            fetched_at=processed_at,
            priority=priority,
            based_on_price_pln=current_row.get("price_pln") or "",
            based_on_last_seen_date=current_row.get("last_seen_date") or "",
            based_on_decision_bucket=current_decision_bucket,
            fields_present=payload.get("fields_present") or [],
            detail_summary=detail_summary,
        )
        return {
            "listing_id": listing_id,
            "status": "fetched",
            "details_file": output_path,
            "csv_file": csv_file,
            "decision_bucket": current_decision_bucket,
            "source_csv": source_csv,
            "link": link,
        }
    except (OSError, URLError, ValueError) as exc:
        is_gone = isinstance(exc, HTTPError) and exc.code == 410
        new_status = "gone" if is_gone else "failed"
        update_listing_enrichment_status(
            csv_file,
            listing_id,
            status=new_status,
            fetched_at=processed_at,
            priority=priority,
            based_on_price_pln=current_row.get("price_pln") or "",
            based_on_last_seen_date=current_row.get("last_seen_date") or "",
            based_on_decision_bucket=current_decision_bucket,
            active=False if is_gone else None,
        )
        return {
            "listing_id": listing_id,
            "status": new_status,
            "csv_file": csv_file,
            "reason": str(exc),
            "source_csv": source_csv,
            "link": link,
        }
    except Exception as exc:
        # Catch non-standard exceptions (e.g. Playwright errors from mobile.de fetcher)
        logger.exception("Enrichment: nieoczekiwany błąd dla %s (%s)", listing_id, item_source)
        update_listing_enrichment_status(
            csv_file,
            listing_id,
            status="failed",
            fetched_at=processed_at,
            priority=priority,
            based_on_price_pln=current_row.get("price_pln") or "",
            based_on_last_seen_date=current_row.get("last_seen_date") or "",
            based_on_decision_bucket=current_decision_bucket,
        )
        return {
            "listing_id": listing_id,
            "status": "failed",
            "csv_file": csv_file,
            "reason": f"{type(exc).__name__}: {exc}",
            "source_csv": source_csv,
            "link": link,
        }


DEFAULT_FETCH_DELAY_RANGE_SECONDS: tuple[float, float] = (1.5, 4.0)


def _get_item_source(item: dict[str, str]) -> str:
    """Return the canonical source identifier for a queue item.

    Prefers the explicit ``source`` field; falls back to inferring from
    ``source_csv`` filename so that older queue entries (written before the
    source field was propagated) are still handled correctly.
    """
    src = str(item.get("source") or "").strip().lower()
    if src:
        return src
    source_csv_name = str(item.get("source_csv") or "").lower()
    if "mobile-de" in source_csv_name or "mobile_de" in source_csv_name:
        return "mobile_de"
    return ""


def run(
    queue_file: str | None = None,
    *,
    data_dir: str | None = None,
    details_dir: str | None = None,
    limit: int | None = None,
    retry_failed: bool = False,
    cooldown_days: int = DEFAULT_FETCH_COOLDOWN_DAYS,
    allowed_buckets: frozenset[str] | None = None,
    fetch_delay_range_seconds: tuple[float, float] = DEFAULT_FETCH_DELAY_RANGE_SECONDS,
    fetch_html: Callable[[str], str] = fetch_listing_html,
) -> list[dict[str, Any]]:
    resolved_data_dir = data_dir or str(DATA_DIR)
    resolved_queue_file = queue_file or os.path.join(resolved_data_dir, "enrichment_queue.csv")
    resolved_details_dir = details_dir or os.path.join(resolved_data_dir, "details")

    raw_queue = load_queue(resolved_queue_file)
    queue: list[dict[str, str]] = []
    cooldown_ids: set[str] = set()   # fetched + in cooldown → safe to remove from queue
    analytics_cache: dict[str, dict[str, dict[str, Any]]] = {}

    # Build an in-memory index of all storage CSVs once — avoids O(n×m) disk reads
    # when filtering the queue.  Index: listing_id → (csv_file_path, row_dict)
    storage_index: dict[str, tuple[str, dict[str, str]]] = {}
    for file_name in os.listdir(resolved_data_dir):
        if not file_name.endswith(".csv") or file_name == "enrichment_queue.csv":
            continue
        full_path = os.path.join(resolved_data_dir, file_name)
        try:
            _, rows = _read_csv_rows(full_path)
            for row in rows:
                lid = row.get("listing_id")
                if lid and lid not in storage_index:
                    storage_index[lid] = (full_path, row)
        except Exception:
            pass
    logger.info("Enrichment: zaindeksowano %d ofert z plików CSV.", len(storage_index))

    for item in raw_queue:
        listing_id = str(item.get("listing_id") or "").strip()
        source_csv = item.get("source_csv") or None

        csv_file: str | None = None
        current_row: dict[str, str] | None = None
        if listing_id in storage_index:
            csv_file, current_row = storage_index[listing_id]

        if csv_file:
            current_status_val = (current_row or {}).get("details_status") or ""
            current_status = str(current_status_val).strip().lower()
            if current_status == "fetched":
                fetched_at = (current_row or {}).get("details_fetched_at")
                current_bucket = get_current_decision_bucket(
                    resolved_data_dir,
                    source_csv,
                    listing_id,
                    analytics_cache,
                )
                if is_in_cooldown(fetched_at, cooldown_days=cooldown_days) and not should_bypass_cooldown(
                    current_row,
                    current_decision_bucket=current_bucket,
                ):
                    if listing_id:
                        cooldown_ids.add(listing_id)
                    continue
            if current_status == "gone":
                if listing_id:
                    cooldown_ids.add(listing_id)
                continue
            if current_status == "failed" and not retry_failed:
                continue

        # Skip listings outside the allowed analytics buckets.
        # Items with no bucket data yet (new, analytics not run) get the benefit of the doubt.
        # Items that are skipped stay in the queue so they can be picked up if their bucket improves.
        if allowed_buckets is not None:
            item_bucket = get_current_decision_bucket(
                resolved_data_dir,
                source_csv,
                listing_id,
                analytics_cache,
            )
            if item_bucket and item_bucket not in allowed_buckets:
                continue

        queue.append(item)

    if cooldown_ids:
        logger.info("Enrichment queue: %d wpisów jest w cooldownie i zostanie usuniętych.", len(cooldown_ids))
        flush_completed_from_queue(resolved_queue_file, cooldown_ids)

    # Sort highest-priority items first so the most valuable listings are always
    # processed even when a --enrichment-limit is used.
    queue.sort(key=lambda item: int(item.get("priority") or 0), reverse=True)

    if limit is not None:
        queue = queue[:limit]

    total = len(queue)
    logger.info("Enrichment: %d pozycji do przetworzenia.", total)

    # Create a Camoufox-based fetcher for mobile.de items if any are in the queue
    mobile_de_count = sum(
        1 for item in queue
        if _get_item_source(item) == "mobile_de"
    )
    mobile_de_fetcher: MobileDeHtmlFetcher | None = None
    if mobile_de_count:
        logger.info("Enrichment: %d ofert mobile.de — uruchamiam MobileDeHtmlFetcher.", mobile_de_count)
        mobile_de_fetcher = MobileDeHtmlFetcher(
            headless=HEADLESS,
            session_state_file=SESSION_STATE_FILE_MOBILE_DE,
        )

    results: list[dict[str, Any]] = []
    try:
        for index, item in enumerate(queue, start=1):
            result = process_queue_item(
                item,
                data_dir=resolved_data_dir,
                details_dir=resolved_details_dir,
                analytics_cache=analytics_cache,
                fetch_html=fetch_html,
                fetch_html_mobile_de=mobile_de_fetcher,
            )
            results.append(result)
            logger.info(
                "Enrichment [%d/%d] listing_id=%s status=%s",
                index,
                total,
                result.get("listing_id") or "",
                result.get("status") or "",
            )
            if result.get("status") in ("fetched", "failed") and index < total:
                delay = random.uniform(*fetch_delay_range_seconds)
                time.sleep(delay)
    finally:
        if mobile_de_fetcher is not None:
            mobile_de_fetcher.close()
            logger.info("Enrichment: MobileDeHtmlFetcher zamknięty.")

    fetched = sum(result.get("status") == "fetched" for result in results)
    failed = sum(result.get("status") == "failed" for result in results)
    skipped = sum(result.get("status") == "skipped" for result in results)
    gone = sum(result.get("status") == "gone" for result in results)
    for result in results:
        if result.get("status") != "failed":
            continue
        logger.warning(
            "Enrichment failed for listing_id=%s source_csv=%s csv_file=%s reason=%s link=%s",
            result.get("listing_id") or "",
            result.get("source_csv") or "",
            result.get("csv_file") or "",
            result.get("reason") or "",
            result.get("link") or "",
        )
    print(
        f"Enrichment processed {len(results)} items: "
        f"{fetched} fetched, {failed} failed, {skipped} skipped, {gone} gone."
    )

    # Usuń z kolejki wpisy które zostały pomyślnie pobrane lub nie mogły być
    # znalezione (listing_not_found / missing data) — nie ma sensu próbować ich ponownie.
    ids_to_flush = {
        r["listing_id"]
        for r in results
        if r.get("status") in ("fetched", "skipped", "gone")
        and r.get("listing_id")
    }
    flush_completed_from_queue(resolved_queue_file, ids_to_flush)

    return results


# ── Migration: reprocess existing sidecar JSONs ───────────────────────────────


def reprocess_details_flags(
    data_dir: str | None = None,
    details_dir: str | None = None,
) -> dict[str, int]:
    """Re-read existing sidecar JSON files and rewrite CSV detail flags using fixed normalization.

    This migration fixes rows that were enriched before the parametersDict normalization bug
    was corrected (all boolean flags like damaged/imported were always set to True).

    Returns a dict with counts: updated, skipped, missing_json, errors.
    """
    resolved_data_dir = data_dir or str(DATA_DIR)
    resolved_details_dir = details_dir or os.path.join(resolved_data_dir, "details")

    counts: dict[str, int] = {"updated": 0, "skipped": 0, "missing_json": 0, "errors": 0}

    _EXCLUDED_CSVS = {"enrichment_queue.csv", "notification_history.csv", "notification_state.csv"}

    for file_name in os.listdir(resolved_data_dir):
        if not file_name.endswith(".csv") or file_name in _EXCLUDED_CSVS:
            continue

        csv_file = os.path.join(resolved_data_dir, file_name)
        try:
            fieldnames, rows = _read_csv_rows(csv_file)
        except Exception:
            logger.exception("reprocess_details_flags: nie można odczytać %s", csv_file)
            counts["errors"] += 1
            continue

        changed = False
        for row in rows:
            if (row.get("details_status") or "").strip().lower() != "fetched":
                counts["skipped"] += 1
                continue

            listing_id = str(row.get("listing_id") or "").strip()
            if not listing_id:
                counts["skipped"] += 1
                continue

            json_path = os.path.join(resolved_details_dir, f"{listing_id}.json")
            if not os.path.exists(json_path):
                counts["missing_json"] += 1
                continue

            try:
                with open(json_path, "r", encoding="utf-8") as fh:
                    payload = json.load(fh)
            except (OSError, json.JSONDecodeError):
                logger.warning("reprocess_details_flags: nie można odczytać %s", json_path)
                counts["errors"] += 1
                continue

            try:
                summary = build_csv_detail_summary(payload, row)
            except Exception:
                logger.exception("reprocess_details_flags: build_csv_detail_summary failed dla %s", listing_id)
                counts["errors"] += 1
                continue

            row["details_damaged_flag"] = summary.get("damaged_flag", "")
            row["details_imported_flag"] = summary.get("imported_flag", "")
            row["details_no_accident_flag"] = summary.get("no_accident_flag", "")
            row["details_service_record_flag"] = summary.get("service_record_flag", "")
            row["details_enrichment_score"] = summary.get("enrichment_score", "")
            row["details_enrichment_confidence"] = summary.get("enrichment_confidence", "")
            row["details_enrichment_flags"] = summary.get("enrichment_flags", "")
            row["details_description_excerpt"] = summary.get("description_excerpt", row.get("details_description_excerpt", ""))
            row["details_vin"] = summary.get("vin", row.get("details_vin", ""))
            row["details_country_origin"] = summary.get("country_origin", row.get("details_country_origin", ""))
            row["details_seller_name"] = summary.get("seller_name", row.get("details_seller_name", ""))

            changed = True
            counts["updated"] += 1

        if changed:
            try:
                _write_csv_rows(csv_file, fieldnames, rows)
                logger.info("reprocess_details_flags: zapisano %s", file_name)
            except Exception:
                logger.exception("reprocess_details_flags: nie można zapisać %s", csv_file)
                counts["errors"] += 1

    return counts


def main() -> None:
    args = parse_args()
    run(
        queue_file=args.queue_file,
        data_dir=args.data_dir,
        details_dir=args.details_dir,
        limit=args.limit,
        retry_failed=args.retry_failed,
        cooldown_days=args.cooldown_days,
    )


if __name__ == "__main__":
    main()
