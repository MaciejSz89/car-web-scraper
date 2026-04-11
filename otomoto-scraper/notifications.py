from __future__ import annotations

import csv
import json
import logging
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from config import ANALYTICS_DIR, NOTIFICATION_HISTORY_FILE, NOTIFICATION_STATE_FILE, QUERIES
from preferences import get_query_preferences, load_preferences
from storage import read_existing_cars
from utils import safe_int


logger = logging.getLogger(__name__)

DEFAULT_ALLOWED_BUCKETS = {"high-priority"}
DEFAULT_MIN_FINAL_SCORE = 80
SIGNIFICANT_PRICE_DROP_RATIO = 0.03
NOTIFICATION_CHANNEL_LOG = "log"

BUCKET_RANKS = {
    "ignore": 0,
    "watch": 1,
    "candidate": 2,
    "high-priority": 3,
}


@dataclass(slots=True)
class NotificationState:
    listing_id: str
    query_name: str
    price_pln: int | None
    final_score: int
    decision_bucket: str
    is_active: bool
    hard_filter_passed: bool
    notification_eligible: bool
    first_seen_date: str
    last_seen_date: str
    updated_at: str


@dataclass(slots=True)
class NotificationRecord:
    listing_id: str
    query_name: str
    event_type: str
    notification_channel: str
    notification_decision: str
    notification_sent_at: str
    notification_status: str
    notification_reason_summary: str
    title: str
    link: str
    price_pln: int | None
    final_score: int
    confidence_score: int
    decision_bucket: str


def _parse_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def _notification_state_fieldnames() -> list[str]:
    return [
        "listing_id",
        "query_name",
        "price_pln",
        "final_score",
        "decision_bucket",
        "is_active",
        "hard_filter_passed",
        "notification_eligible",
        "first_seen_date",
        "last_seen_date",
        "updated_at",
    ]


def _notification_history_fieldnames() -> list[str]:
    return [
        "listing_id",
        "query_name",
        "event_type",
        "notification_channel",
        "notification_decision",
        "notification_sent_at",
        "notification_status",
        "notification_reason_summary",
        "title",
        "link",
        "price_pln",
        "final_score",
        "confidence_score",
        "decision_bucket",
    ]


def load_notification_state(state_file: Path = NOTIFICATION_STATE_FILE) -> dict[str, NotificationState]:
    if not state_file.exists():
        return {}

    states: dict[str, NotificationState] = {}
    with open(state_file, "r", newline="", encoding="utf-8-sig") as file_handle:
        reader = csv.DictReader(file_handle, delimiter=";")
        for row in reader:
            listing_id = str(row.get("listing_id") or "").strip()
            if not listing_id:
                continue

            states[listing_id] = NotificationState(
                listing_id=listing_id,
                query_name=str(row.get("query_name") or "").strip(),
                price_pln=safe_int(row.get("price_pln")),
                final_score=safe_int(row.get("final_score")) or 0,
                decision_bucket=str(row.get("decision_bucket") or "ignore").strip().lower(),
                is_active=_parse_bool(row.get("is_active")),
                hard_filter_passed=_parse_bool(row.get("hard_filter_passed")),
                notification_eligible=_parse_bool(row.get("notification_eligible")),
                first_seen_date=str(row.get("first_seen_date") or "").strip(),
                last_seen_date=str(row.get("last_seen_date") or "").strip(),
                updated_at=str(row.get("updated_at") or "").strip(),
            )

    return states


def save_notification_state(
    states: dict[str, NotificationState],
    state_file: Path = NOTIFICATION_STATE_FILE,
) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, "w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=_notification_state_fieldnames(), delimiter=";")
        writer.writeheader()
        for listing_id in sorted(states):
            writer.writerow(asdict(states[listing_id]))


def append_notification_history(
    records: list[NotificationRecord],
    history_file: Path = NOTIFICATION_HISTORY_FILE,
) -> None:
    if not records:
        return

    history_file.parent.mkdir(parents=True, exist_ok=True)
    file_exists = history_file.exists()
    with open(history_file, "a", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=_notification_history_fieldnames(), delimiter=";")
        if not file_exists:
            writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))


def _analysis_path_for_csv(csv_file: str) -> Path:
    return ANALYTICS_DIR / f"{Path(csv_file).stem}-analysis.json"


def load_analysis_results(csv_file: str) -> dict[str, dict[str, Any]]:
    analysis_path = _analysis_path_for_csv(csv_file)
    if not analysis_path.exists():
        return {}

    with open(analysis_path, "r", encoding="utf-8") as file_handle:
        data = json.load(file_handle)

    results: dict[str, dict[str, Any]] = {}
    if not isinstance(data, list):
        return results

    for item in data:
        if not isinstance(item, dict):
            continue
        listing_id = str(item.get("listing_id") or "").strip()
        if listing_id:
            results[listing_id] = item

    return results


def _get_notification_filters(preferences: dict[str, Any], query_name: str) -> dict[str, Any]:
    effective_preferences = get_query_preferences(preferences, query_name)
    filters = effective_preferences.get("notification_filters", {})
    return filters if isinstance(filters, dict) else {}


def _is_notification_eligible(result: dict[str, Any], filters: dict[str, Any]) -> bool:
    min_final_score = safe_int(filters.get("min_final_score"))
    if min_final_score is None:
        min_final_score = DEFAULT_MIN_FINAL_SCORE

    allowed_buckets = filters.get("allowed_buckets")
    if isinstance(allowed_buckets, list):
        allowed_bucket_set = {str(value).strip().lower() for value in allowed_buckets if str(value).strip()}
    else:
        allowed_bucket_set = DEFAULT_ALLOWED_BUCKETS

    require_hard_filter_pass = filters.get("require_hard_filter_pass", True)

    final_score = safe_int(result.get("final_score")) or 0
    decision_bucket = str(result.get("decision_bucket") or "ignore").strip().lower()
    hard_filter_passed = _parse_bool(result.get("hard_filter_passed"))

    if final_score < min_final_score:
        return False
    if decision_bucket not in allowed_bucket_set:
        return False
    if require_hard_filter_pass and not hard_filter_passed:
        return False

    return True


def _current_state_from_listing(
    query_name: str,
    row: dict[str, Any],
    analysis_result: dict[str, Any] | None,
    preferences: dict[str, Any],
    now_iso: str,
) -> NotificationState:
    filters = _get_notification_filters(preferences, query_name)
    is_active = _parse_bool(row.get("is_active"))

    notification_eligible = False
    final_score = 0
    decision_bucket = "ignore"
    hard_filter_passed = False

    if analysis_result is not None and is_active:
        notification_eligible = _is_notification_eligible(analysis_result, filters)
        final_score = safe_int(analysis_result.get("final_score")) or 0
        decision_bucket = str(analysis_result.get("decision_bucket") or "ignore").strip().lower()
        hard_filter_passed = _parse_bool(analysis_result.get("hard_filter_passed"))

    return NotificationState(
        listing_id=str(row.get("listing_id") or "").strip(),
        query_name=query_name,
        price_pln=safe_int(row.get("price_pln")),
        final_score=final_score,
        decision_bucket=decision_bucket,
        is_active=is_active,
        hard_filter_passed=hard_filter_passed,
        notification_eligible=notification_eligible,
        first_seen_date=str(row.get("first_seen_date") or "").strip(),
        last_seen_date=str(row.get("last_seen_date") or "").strip(),
        updated_at=now_iso,
    )


def _bucket_rank(bucket: str) -> int:
    return BUCKET_RANKS.get(str(bucket or "ignore").strip().lower(), 0)


def determine_notification_event(
    current_state: NotificationState,
    previous_state: NotificationState | None,
    today: date,
) -> str | None:
    if not current_state.is_active or not current_state.notification_eligible:
        return None

    if previous_state is not None and not previous_state.is_active:
        return "reactivated"

    if current_state.first_seen_date == today.isoformat() and previous_state is None:
        return "new-listing"

    if previous_state is not None and _bucket_rank(current_state.decision_bucket) > _bucket_rank(previous_state.decision_bucket):
        return "bucket-upgrade"

    if previous_state is not None and previous_state.price_pln and current_state.price_pln:
        if current_state.price_pln < previous_state.price_pln:
            drop_ratio = (previous_state.price_pln - current_state.price_pln) / previous_state.price_pln
            if drop_ratio >= SIGNIFICANT_PRICE_DROP_RATIO:
                return "price-drop"

    return None


def _build_reason_summary(event_type: str, result: dict[str, Any], row: dict[str, Any]) -> str:
    final_score = safe_int(result.get("final_score")) or 0
    confidence_score = safe_int(result.get("confidence_score")) or 0
    price_pln = safe_int(row.get("price_pln"))
    decision_bucket = str(result.get("decision_bucket") or "ignore").strip().lower()
    market_reasons = result.get("market_reasons") or []
    enrichment_flags = result.get("enrichment_flags") or []

    fragments = [
        f"event={event_type}",
        f"bucket={decision_bucket}",
        f"final={final_score}",
        f"confidence={confidence_score}",
    ]

    if price_pln is not None:
        fragments.append(f"price={price_pln}")

    short_reasons: list[str] = []
    if isinstance(market_reasons, list):
        short_reasons.extend(str(reason) for reason in market_reasons[:2])
    if isinstance(enrichment_flags, list):
        short_reasons.extend(str(flag) for flag in enrichment_flags[:2])

    if short_reasons:
        fragments.append("signals=" + ", ".join(short_reasons))

    return " | ".join(fragments)


def _build_notification_record(
    query_name: str,
    row: dict[str, Any],
    result: dict[str, Any],
    event_type: str,
    now_iso: str,
) -> NotificationRecord:
    return NotificationRecord(
        listing_id=str(row.get("listing_id") or "").strip(),
        query_name=query_name,
        event_type=event_type,
        notification_channel=NOTIFICATION_CHANNEL_LOG,
        notification_decision="send",
        notification_sent_at=now_iso,
        notification_status="sent",
        notification_reason_summary=_build_reason_summary(event_type, result, row),
        title=str(row.get("title") or "").strip(),
        link=str(row.get("link") or "").strip(),
        price_pln=safe_int(row.get("price_pln")),
        final_score=safe_int(result.get("final_score")) or 0,
        confidence_score=safe_int(result.get("confidence_score")) or 0,
        decision_bucket=str(result.get("decision_bucket") or "ignore").strip().lower(),
    )


def _emit_notification(record: NotificationRecord) -> None:
    logger.info(
        "POWIADOMIENIE [%s] %s | %s | %s | cena=%s | final=%s | %s",
        record.event_type,
        record.query_name,
        record.listing_id,
        record.title,
        record.price_pln,
        record.final_score,
        record.link,
    )


def run(
    queries: list[dict[str, Any]] | None = None,
    state_file: Path = NOTIFICATION_STATE_FILE,
    history_file: Path = NOTIFICATION_HISTORY_FILE,
) -> list[NotificationRecord]:
    if queries is None:
        queries = QUERIES

    preferences = load_preferences()
    previous_states = load_notification_state(state_file)
    next_states: dict[str, NotificationState] = dict(previous_states)
    sent_records: list[NotificationRecord] = []
    now_iso = datetime.now(timezone.utc).isoformat()
    today = date.today()

    for query in queries:
        query_name = str(query["name"])
        csv_file = str(query["csv_file"])
        analysis_results = load_analysis_results(csv_file)
        rows_by_id = read_existing_cars(csv_file)

        for listing_id, row in rows_by_id.items():
            analysis_result = analysis_results.get(listing_id)
            current_state = _current_state_from_listing(
                query_name=query_name,
                row=row,
                analysis_result=analysis_result,
                preferences=preferences,
                now_iso=now_iso,
            )
            previous_state = previous_states.get(listing_id)

            if analysis_result is not None:
                event_type = determine_notification_event(current_state, previous_state, today)
                if event_type is not None:
                    record = _build_notification_record(
                        query_name=query_name,
                        row=row,
                        result=analysis_result,
                        event_type=event_type,
                        now_iso=now_iso,
                    )
                    _emit_notification(record)
                    sent_records.append(record)

            next_states[listing_id] = current_state

    save_notification_state(next_states, state_file=state_file)
    append_notification_history(sent_records, history_file=history_file)
    return sent_records