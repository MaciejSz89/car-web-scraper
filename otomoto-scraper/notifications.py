from __future__ import annotations

import csv
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config import ANALYTICS_DIR, NOTIFICATION_HISTORY_FILE, NOTIFICATION_STATE_FILE, QUERIES
from preferences import get_query_preferences, load_preferences
from storage import read_existing_cars
from utils import safe_int


logger = logging.getLogger(__name__)

DEFAULT_ALLOWED_BUCKETS = {"high-priority"}
DEFAULT_MIN_FINAL_SCORE = 80
SIGNIFICANT_PRICE_DROP_RATIO = 0.03
DEFAULT_BLOCKED_ENRICHMENT_FLAGS = {"damage_declared"}
DEFAULT_BUCKET_UPGRADE_TARGET_BUCKETS = {"high-priority"}
NOTIFICATION_CHANNEL_LOG = "log"
NOTIFICATION_CHANNEL_TELEGRAM = "telegram"

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
    last_notification_event: str
    last_notification_at: str
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
        "last_notification_event",
        "last_notification_at",
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
                last_notification_event=str(row.get("last_notification_event") or "").strip().lower(),
                last_notification_at=str(row.get("last_notification_at") or "").strip(),
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


def _get_notification_channels(preferences: dict[str, Any], query_name: str) -> list[dict[str, Any]]:
    effective_preferences = get_query_preferences(preferences, query_name)
    raw_channels = effective_preferences.get("notification_channels")

    if not isinstance(raw_channels, list) or not raw_channels:
        return [{"type": NOTIFICATION_CHANNEL_LOG}]

    normalized_channels: list[dict[str, Any]] = []
    for item in raw_channels:
        if isinstance(item, str):
            channel_type = item.strip().lower()
            if channel_type:
                normalized_channels.append({"type": channel_type})
            continue

        if not isinstance(item, dict):
            continue

        channel_type = str(item.get("type") or "").strip().lower()
        if not channel_type:
            continue
        normalized_channels.append(dict(item) | {"type": channel_type})

    return normalized_channels or [{"type": NOTIFICATION_CHANNEL_LOG}]


def _parse_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_iso_datetime(value: str | None) -> datetime | None:
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


def _parse_csv_date(value: str | None) -> date | None:
    if not value:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    for pattern in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(normalized, pattern).date()
        except ValueError:
            continue

    return None


def _is_notification_eligible(result: dict[str, Any], row: dict[str, Any], filters: dict[str, Any]) -> bool:
    min_final_score = safe_int(filters.get("min_final_score"))
    if min_final_score is None:
        min_final_score = DEFAULT_MIN_FINAL_SCORE

    allowed_buckets = filters.get("allowed_buckets")
    if isinstance(allowed_buckets, list):
        allowed_bucket_set = {str(value).strip().lower() for value in allowed_buckets if str(value).strip()}
    else:
        allowed_bucket_set = DEFAULT_ALLOWED_BUCKETS

    require_hard_filter_pass = filters.get("require_hard_filter_pass", True)
    exclude_damaged_listings = filters.get("exclude_damaged_listings", True)

    blocked_enrichment_flags_cfg = filters.get("blocked_enrichment_flags")
    if isinstance(blocked_enrichment_flags_cfg, list):
        blocked_enrichment_flags = {
            str(flag).strip().lower() for flag in blocked_enrichment_flags_cfg if str(flag).strip()
        }
    else:
        blocked_enrichment_flags = DEFAULT_BLOCKED_ENRICHMENT_FLAGS

    final_score = safe_int(result.get("final_score")) or 0
    decision_bucket = str(result.get("decision_bucket") or "ignore").strip().lower()
    hard_filter_passed = _parse_bool(result.get("hard_filter_passed"))
    is_damaged = _parse_bool(row.get("is_damaged"))
    enrichment_flags_raw = result.get("enrichment_flags")
    enrichment_flags = {
        str(flag).strip().lower()
        for flag in enrichment_flags_raw
        if isinstance(flag, str) and str(flag).strip()
    } if isinstance(enrichment_flags_raw, list) else set()

    if final_score < min_final_score:
        return False
    if decision_bucket not in allowed_bucket_set:
        return False
    if require_hard_filter_pass and not hard_filter_passed:
        return False
    if exclude_damaged_listings and is_damaged:
        return False
    if blocked_enrichment_flags and enrichment_flags.intersection(blocked_enrichment_flags):
        return False

    return True


def _current_state_from_listing(
    query_name: str,
    row: dict[str, Any],
    analysis_result: dict[str, Any] | None,
    previous_state: NotificationState | None,
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
        notification_eligible = _is_notification_eligible(analysis_result, row, filters)
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
        last_notification_event=(previous_state.last_notification_event if previous_state else ""),
        last_notification_at=(previous_state.last_notification_at if previous_state else ""),
        updated_at=now_iso,
    )


def _bucket_rank(bucket: str) -> int:
    return BUCKET_RANKS.get(str(bucket or "ignore").strip().lower(), 0)


def determine_notification_event(
    current_state: NotificationState,
    previous_state: NotificationState | None,
    *,
    filters: dict[str, Any],
    today: date,
    now_utc: datetime,
) -> str | None:
    if not current_state.is_active or not current_state.notification_eligible:
        return None

    if previous_state is not None and not previous_state.is_active:
        allow_reactivated = bool(filters.get("allow_reactivated", True))
        if not allow_reactivated:
            return None

        min_reactivated_absence_days = safe_int(filters.get("min_reactivated_absence_days")) or 0
        if min_reactivated_absence_days > 0:
            previous_last_seen = _parse_csv_date(previous_state.last_seen_date)
            if previous_last_seen is not None:
                inactive_days = (today - previous_last_seen).days
                if inactive_days < min_reactivated_absence_days:
                    return None
        return "reactivated"

    if current_state.first_seen_date == today.isoformat() and previous_state is None:
        return "new-listing"

    if previous_state is not None and _bucket_rank(current_state.decision_bucket) > _bucket_rank(previous_state.decision_bucket):
        target_buckets_cfg = filters.get("bucket_upgrade_target_buckets")
        if isinstance(target_buckets_cfg, list):
            target_buckets = {
                str(bucket).strip().lower() for bucket in target_buckets_cfg if str(bucket).strip()
            }
        else:
            target_buckets = DEFAULT_BUCKET_UPGRADE_TARGET_BUCKETS

        if target_buckets and current_state.decision_bucket not in target_buckets:
            return None

        suppress_hours = safe_int(filters.get("suppress_bucket_upgrade_after_reactivation_hours")) or 0
        if suppress_hours > 0 and previous_state.last_notification_event == "reactivated":
            last_notification_at = _parse_iso_datetime(previous_state.last_notification_at)
            if last_notification_at is not None:
                hours_since_last_notification = (now_utc - last_notification_at).total_seconds() / 3600
                if hours_since_last_notification < suppress_hours:
                    return None
        return "bucket-upgrade"

    if previous_state is not None and previous_state.price_pln and current_state.price_pln:
        if current_state.price_pln < previous_state.price_pln:
            min_price_drop_ratio = _parse_float(filters.get("min_price_drop_ratio"))
            if min_price_drop_ratio is None:
                min_price_drop_ratio = SIGNIFICANT_PRICE_DROP_RATIO
            drop_ratio = (previous_state.price_pln - current_state.price_pln) / previous_state.price_pln
            if drop_ratio >= min_price_drop_ratio:
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
    channel: str,
    now_iso: str,
) -> NotificationRecord:
    return NotificationRecord(
        listing_id=str(row.get("listing_id") or "").strip(),
        query_name=query_name,
        event_type=event_type,
        notification_channel=channel,
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


def _format_notification_message(record: NotificationRecord) -> str:
    return (
        f"[{record.event_type}] {record.query_name}\n"
        f"{record.title}\n"
        f"Cena: {record.price_pln} PLN | final={record.final_score} | confidence={record.confidence_score}\n"
        f"Bucket: {record.decision_bucket}\n"
        f"Powod: {record.notification_reason_summary}\n"
        f"{record.link}"
    )


def _emit_log_notification(record: NotificationRecord) -> NotificationRecord:
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
    return record


def _resolve_channel_value(channel: dict[str, Any], key: str) -> str:
    direct_value = str(channel.get(key) or "").strip()
    if direct_value:
        return direct_value

    env_key = str(channel.get(f"{key}_env") or "").strip()
    if env_key:
        return str(os.environ.get(env_key) or "").strip()

    return ""


def _emit_telegram_notification(record: NotificationRecord, channel: dict[str, Any]) -> NotificationRecord:
    bot_token = _resolve_channel_value(channel, "bot_token")
    chat_id = _resolve_channel_value(channel, "chat_id")

    if not bot_token or not chat_id:
        logger.warning(
            "Telegram notification skipped for listing_id=%s because bot_token/chat_id are missing.",
            record.listing_id,
        )
        return NotificationRecord(
            **(asdict(record) | {"notification_status": "failed", "notification_decision": "send"})
        )

    payload = {
        "chat_id": chat_id,
        "text": _format_notification_message(record),
        "disable_web_page_preview": bool(channel.get("disable_web_page_preview", False)),
    }
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    request = Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            response.read()
        logger.info(
            "Telegram notification sent for listing_id=%s query=%s event=%s",
            record.listing_id,
            record.query_name,
            record.event_type,
        )
        return record
    except (HTTPError, URLError, OSError) as exc:
        logger.warning(
            "Telegram notification failed for listing_id=%s query=%s event=%s reason=%s",
            record.listing_id,
            record.query_name,
            record.event_type,
            exc,
        )
        return NotificationRecord(
            **(asdict(record) | {"notification_status": "failed", "notification_decision": "send"})
        )


def _emit_notification(record: NotificationRecord, channel: dict[str, Any]) -> NotificationRecord:
    channel_type = str(channel.get("type") or NOTIFICATION_CHANNEL_LOG).strip().lower()
    if channel_type == NOTIFICATION_CHANNEL_TELEGRAM:
        return _emit_telegram_notification(record, channel)
    return _emit_log_notification(record)


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
    now_utc = datetime.now(timezone.utc)
    today = date.today()

    for query in queries:
        query_name = str(query["name"])
        csv_file = str(query["csv_file"])
        analysis_results = load_analysis_results(csv_file)
        rows_by_id = read_existing_cars(csv_file)
        channels = _get_notification_channels(preferences, query_name)
        filters = _get_notification_filters(preferences, query_name)

        for listing_id, row in rows_by_id.items():
            analysis_result = analysis_results.get(listing_id)
            previous_state = previous_states.get(listing_id)
            current_state = _current_state_from_listing(
                query_name=query_name,
                row=row,
                analysis_result=analysis_result,
                previous_state=previous_state,
                preferences=preferences,
                now_iso=now_iso,
            )

            if analysis_result is not None:
                event_type = determine_notification_event(
                    current_state,
                    previous_state,
                    filters=filters,
                    today=today,
                    now_utc=now_utc,
                )
                if event_type is not None:
                    current_state.last_notification_event = event_type
                    current_state.last_notification_at = now_iso
                    for channel in channels:
                        channel_type = str(channel.get("type") or NOTIFICATION_CHANNEL_LOG).strip().lower()
                        record = _build_notification_record(
                            query_name=query_name,
                            row=row,
                            result=analysis_result,
                            event_type=event_type,
                            channel=channel_type,
                            now_iso=now_iso,
                        )
                        sent_records.append(_emit_notification(record, channel))

            next_states[listing_id] = current_state

    save_notification_state(next_states, state_file=state_file)
    append_notification_history(sent_records, history_file=history_file)
    return sent_records