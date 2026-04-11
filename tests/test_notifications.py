import csv
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "otomoto-scraper"))

import notifications


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def _write_analysis(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file_handle:
        json.dump(rows, file_handle, ensure_ascii=False, indent=2)


def _base_csv_row(today: str) -> dict[str, str]:
    return {
        "listing_id": "A",
        "title": "Oferta testowa",
        "price_pln": "50000",
        "currency": "PLN",
        "link": "https://example.test/oferta/A",
        "subtitle": "",
        "engine_cm3": "1600",
        "power_hp": "150",
        "mileage_km": "80000",
        "fuel_type": "Benzyna",
        "gearbox": "Automatyczna",
        "year": "2020",
        "location": "Warszawa",
        "seller_type": "private",
        "details_status": "",
        "details_priority": "",
        "details_fetched_at": "",
        "details_based_on_price_pln": "",
        "details_based_on_last_seen_date": "",
        "details_based_on_decision_bucket": "",
        "details_fields_present": "",
        "details_description_excerpt": "",
        "details_seller_name": "",
        "details_vin": "",
        "details_country_origin": "",
        "details_no_accident_flag": "",
        "details_service_record_flag": "",
        "details_imported_flag": "",
        "details_enrichment_score": "",
        "details_enrichment_confidence": "",
        "details_enrichment_flags": "",
        "is_damaged": "0",
        "condition_note": "",
        "first_seen_date": today,
        "last_seen_date": today,
        "days_on_site": "0",
        "is_active": "1",
        "removed_date": "",
        "initial_price_pln": "50000",
        "lowest_price_pln": "50000",
        "price_change_count": "0",
        "last_price_change_date": "",
    }


def _base_analysis_row() -> dict[str, object]:
    return {
        "listing_id": "A",
        "query_name": "Test Query",
        "title": "Oferta testowa",
        "link": "https://example.test/oferta/A",
        "price_pln": 50000,
        "seller_type": "private",
        "market_score": 90,
        "confidence_score": 88,
        "preference_score": 75,
        "final_score": 86,
        "decision_bucket": "high-priority",
        "hard_filter_passed": True,
        "comparison_group_size": 10,
        "fallback_level": 0,
        "market_reasons": ["pozycja ceny vs mediana segmentu"],
        "preference_reasons": ["preferowana skrzynia"],
        "enrichment_score": 70,
        "enrichment_confidence": 100,
        "enrichment_reasons": ["seller_name_present"],
        "enrichment_flags": ["vin_present"],
    }


def test_notifications_emit_new_listing_once(tmp_path, monkeypatch):
    today = date.today().isoformat()
    csv_path = tmp_path / "cars.csv"
    analytics_path = tmp_path / "analytics" / "cars-analysis.json"
    state_path = tmp_path / "notification_state.csv"
    history_path = tmp_path / "notification_history.csv"

    _write_csv(csv_path, notifications._notification_state_fieldnames() if False else list(_base_csv_row(today).keys()), [_base_csv_row(today)])
    _write_analysis(analytics_path, [_base_analysis_row()])

    monkeypatch.setattr(notifications, "ANALYTICS_DIR", tmp_path / "analytics")
    monkeypatch.setattr(notifications, "load_preferences", lambda: {
        "profile_name": "test",
        "global": {
            "notification_filters": {
                "min_final_score": 65,
                "require_hard_filter_pass": True,
                "allowed_buckets": ["candidate", "high-priority"],
            }
        },
        "queries": {},
    })

    records = notifications.run(
        queries=[{"name": "Test Query", "csv_file": str(csv_path)}],
        state_file=state_path,
        history_file=history_path,
    )

    assert len(records) == 1
    assert records[0].event_type == "new-listing"
    assert history_path.exists()
    assert state_path.exists()

    records_second_run = notifications.run(
        queries=[{"name": "Test Query", "csv_file": str(csv_path)}],
        state_file=state_path,
        history_file=history_path,
    )
    assert records_second_run == []


def test_notifications_emit_price_drop_after_previous_state(tmp_path, monkeypatch):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    today = date.today().isoformat()
    csv_path = tmp_path / "cars.csv"
    analytics_path = tmp_path / "analytics" / "cars-analysis.json"
    state_path = tmp_path / "notification_state.csv"
    history_path = tmp_path / "notification_history.csv"

    row = _base_csv_row(yesterday)
    row["last_seen_date"] = today
    row["days_on_site"] = "1"
    _write_csv(csv_path, list(row.keys()), [row])
    _write_analysis(analytics_path, [{**_base_analysis_row(), "decision_bucket": "candidate", "final_score": 72}])

    monkeypatch.setattr(notifications, "ANALYTICS_DIR", tmp_path / "analytics")
    monkeypatch.setattr(notifications, "load_preferences", lambda: {
        "profile_name": "test",
        "global": {
            "notification_filters": {
                "min_final_score": 65,
                "require_hard_filter_pass": True,
                "allowed_buckets": ["candidate", "high-priority"],
            }
        },
        "queries": {},
    })

    first_run = notifications.run(
        queries=[{"name": "Test Query", "csv_file": str(csv_path)}],
        state_file=state_path,
        history_file=history_path,
    )
    assert first_run == []

    dropped_row = dict(row)
    dropped_row["price_pln"] = "47000"
    dropped_row["lowest_price_pln"] = "47000"
    dropped_row["price_change_count"] = "1"
    dropped_row["last_price_change_date"] = today
    _write_csv(csv_path, list(dropped_row.keys()), [dropped_row])
    _write_analysis(analytics_path, [{**_base_analysis_row(), "price_pln": 47000, "decision_bucket": "candidate", "final_score": 74}])

    second_run = notifications.run(
        queries=[{"name": "Test Query", "csv_file": str(csv_path)}],
        state_file=state_path,
        history_file=history_path,
    )
    assert len(second_run) == 1
    assert second_run[0].event_type == "price-drop"


def test_notifications_emit_bucket_upgrade(tmp_path, monkeypatch):
    yesterday = (date.today() - timedelta(days=2)).isoformat()
    today = date.today().isoformat()
    csv_path = tmp_path / "cars.csv"
    analytics_path = tmp_path / "analytics" / "cars-analysis.json"
    state_path = tmp_path / "notification_state.csv"
    history_path = tmp_path / "notification_history.csv"

    row = _base_csv_row(yesterday)
    row["last_seen_date"] = today
    row["days_on_site"] = "2"
    _write_csv(csv_path, list(row.keys()), [row])
    _write_analysis(analytics_path, [{**_base_analysis_row(), "decision_bucket": "candidate", "final_score": 70}])

    monkeypatch.setattr(notifications, "ANALYTICS_DIR", tmp_path / "analytics")
    monkeypatch.setattr(notifications, "load_preferences", lambda: {
        "profile_name": "test",
        "global": {
            "notification_filters": {
                "min_final_score": 65,
                "require_hard_filter_pass": True,
                "allowed_buckets": ["candidate", "high-priority"],
            }
        },
        "queries": {},
    })

    assert notifications.run(
        queries=[{"name": "Test Query", "csv_file": str(csv_path)}],
        state_file=state_path,
        history_file=history_path,
    ) == []

    _write_analysis(analytics_path, [{**_base_analysis_row(), "decision_bucket": "high-priority", "final_score": 85}])
    records = notifications.run(
        queries=[{"name": "Test Query", "csv_file": str(csv_path)}],
        state_file=state_path,
        history_file=history_path,
    )

    assert len(records) == 1
    assert records[0].event_type == "bucket-upgrade"


def test_notifications_send_to_telegram_channel(tmp_path, monkeypatch):
    today = date.today().isoformat()
    csv_path = tmp_path / "cars.csv"
    analytics_path = tmp_path / "analytics" / "cars-analysis.json"
    state_path = tmp_path / "notification_state.csv"
    history_path = tmp_path / "notification_history.csv"

    _write_csv(csv_path, list(_base_csv_row(today).keys()), [_base_csv_row(today)])
    _write_analysis(analytics_path, [_base_analysis_row()])

    monkeypatch.setattr(notifications, "ANALYTICS_DIR", tmp_path / "analytics")
    monkeypatch.setattr(notifications, "load_preferences", lambda: {
        "profile_name": "test",
        "global": {
            "notification_filters": {
                "min_final_score": 65,
                "require_hard_filter_pass": True,
                "allowed_buckets": ["candidate", "high-priority"],
            },
            "notification_channels": [
                {
                    "type": "telegram",
                    "bot_token": "token-123",
                    "chat_id": "chat-456",
                    "disable_web_page_preview": True,
                }
            ],
        },
        "queries": {},
    })

    captured: dict[str, object] = {}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"ok": true}'

    def _fake_urlopen(request, timeout=0):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _Response()

    monkeypatch.setattr(notifications, "urlopen", _fake_urlopen)

    records = notifications.run(
        queries=[{"name": "Test Query", "csv_file": str(csv_path)}],
        state_file=state_path,
        history_file=history_path,
    )

    assert len(records) == 1
    assert records[0].notification_channel == "telegram"
    assert records[0].notification_status == "sent"
    assert captured["url"] == "https://api.telegram.org/bottoken-123/sendMessage"
    assert captured["timeout"] == 10
    assert captured["body"] == {
        "chat_id": "chat-456",
        "text": notifications._format_notification_message(records[0]),
        "disable_web_page_preview": True,
    }
