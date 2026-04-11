import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "otomoto-scraper"))

import enrichment_worker


DETAIL_HTML = """
<html>
  <head>
    <title>Oferta testowa</title>
    <meta name="description" content="Opis testowej oferty" />
    <script type="application/ld+json">{"@type": "Car", "name": "Test Car"}</script>
        <script id="__NEXT_DATA__" type="application/json">
            {
                "props": {
                    "pageProps": {
                        "advert": {
                            "description": "  Bardzo zadbany egzemplarz.  ",
                            "equipment": [
                                {"label": "Klimatyzacja"},
                                {"label": "Tempomat"}
                            ],
                            "parametersDict": {
                                "vin": "VIN123",
                                "fuel_type": {"value": "Benzyna"},
                                "gearbox": {"label": "Automatyczna"}
                            },
                            "seller": {
                                "name": "Jan Kowalski",
                                "type": "private"
                            },
                            "price": {
                                "amount": 10000,
                                "currency": "PLN"
                            },
                            "adFeatures": [
                                {"name": "Zarejestrowany w Polsce"}
                            ],
                            "mainFeatures": [
                                {"value": "Serwisowany"}
                            ]
                        }
                    }
                },
                "buildId": "build-123"
            }
        </script>
  </head>
    <body>
        <h1>Test</h1>
        <div data-testid="advert-description">Opis z DOM</div>
    </body>
</html>
"""


def _write_storage_csv(csv_path: Path, listing_id: str = "123") -> None:
    header = [
        "listing_id","title","price_pln","currency","link","subtitle","engine_cm3","power_hp",
        "mileage_km","fuel_type","gearbox","year","location","seller_type","details_status",
        "details_priority","details_fetched_at","details_based_on_price_pln","details_based_on_last_seen_date",
        "details_based_on_decision_bucket","details_fields_present","details_description_excerpt","details_seller_name",
        "details_vin","details_country_origin","details_no_accident_flag","details_service_record_flag",
        "details_imported_flag","details_enrichment_score","details_enrichment_confidence","details_enrichment_flags",
        "is_damaged","condition_note","first_seen_date",
        "last_seen_date","days_on_site","is_active","removed_date","initial_price_pln","lowest_price_pln",
        "price_change_count","last_price_change_date",
    ]
    rows = [{
        "listing_id": listing_id,
        "title": "Car",
        "price_pln": "10000",
        "currency": "PLN",
        "link": "https://example.com/oferta",
        "subtitle": "",
        "engine_cm3": "1600",
        "power_hp": "120",
        "mileage_km": "50000",
        "fuel_type": "petrol",
        "gearbox": "manual",
        "year": "2019",
        "location": "Warsaw",
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
        "first_seen_date": "2026-04-01",
        "last_seen_date": "2026-04-01",
        "days_on_site": "1",
        "is_active": "1",
        "removed_date": "",
        "initial_price_pln": "10000",
        "lowest_price_pln": "10000",
        "price_change_count": "0",
        "last_price_change_date": "",
    }]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=header, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def test_extract_detail_payload():
    payload = enrichment_worker.extract_detail_payload(DETAIL_HTML, "https://example.com/oferta")
    assert payload["url"] == "https://example.com/oferta"
    assert payload["page_title"] == "Oferta testowa"
    assert payload["meta_description"] == "Opis testowej oferty"
    assert payload["json_ld_count"] == 1
    assert payload["structured_data"][0]["name"] == "Test Car"
    assert payload["description"] == "Bardzo zadbany egzemplarz."
    assert payload["seller"]["name"] == "Jan Kowalski"
    assert payload["price"]["amount"] == 10000
    assert payload["equipment"] == ["Klimatyzacja", "Tempomat"]
    assert payload["parameters"]["vin"] == "VIN123"
    assert payload["fields_present"]


def test_process_queue_item_writes_json_and_updates_csv(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    details_dir = data_dir / "details"
    csv_file = data_dir / "cars.csv"
    _write_storage_csv(csv_file)

    item = {
        "listing_id": "123",
        "link": "https://example.com/oferta",
        "priority": "77",
        "source_csv": "cars.csv",
    }

    result = enrichment_worker.process_queue_item(
        item,
        data_dir=str(data_dir),
        details_dir=str(details_dir),
        fetch_html=lambda url: DETAIL_HTML,
    )

    assert result["status"] == "fetched"
    detail_file = details_dir / "123.json"
    assert detail_file.exists()

    payload = json.loads(detail_file.read_text(encoding="utf-8"))
    assert payload["page_title"] == "Oferta testowa"

    with open(csv_file, "r", newline="", encoding="utf-8-sig") as file_handle:
        rows = list(csv.DictReader(file_handle, delimiter=";"))
    assert rows[0]["details_status"] == "fetched"
    assert rows[0]["details_priority"] == "77"
    assert rows[0]["details_fetched_at"]
    assert rows[0]["details_based_on_price_pln"] == "10000"
    assert rows[0]["details_based_on_last_seen_date"] == "2026-04-01"
    assert rows[0]["details_fields_present"]
    assert rows[0]["details_description_excerpt"] == "Bardzo zadbany egzemplarz."
    assert rows[0]["details_seller_name"] == "Jan Kowalski"
    assert rows[0]["details_vin"] == "VIN123"
    assert rows[0]["details_enrichment_score"]
    assert "seller_private_confirmed" in rows[0]["details_enrichment_flags"]


def test_run_processes_queue(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    csv_file = data_dir / "cars.csv"
    queue_file = data_dir / "enrichment_queue.csv"
    _write_storage_csv(csv_file, listing_id="ABC")

    with open(queue_file, "w", newline="", encoding="utf-8-sig") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=["listing_id", "link", "priority", "reason", "selected_at", "source_csv"],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerow({
            "listing_id": "ABC",
            "link": "https://example.com/oferta",
            "priority": "50",
            "reason": "new",
            "selected_at": "2026-04-11T10:00:00+00:00",
            "source_csv": "cars.csv",
        })

    results = enrichment_worker.run(
        queue_file=str(queue_file),
        data_dir=str(data_dir),
        details_dir=str(data_dir / "details"),
        fetch_html=lambda url: DETAIL_HTML,
    )

    assert len(results) == 1
    assert results[0]["status"] == "fetched"


def test_parse_args_supports_cli_flags(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "enrichment_worker.py",
            "--queue-file",
            "queue.csv",
            "--data-dir",
            "data-dir",
            "--details-dir",
            "details-dir",
            "--limit",
            "3",
            "--cooldown-days",
            "14",
            "--retry-failed",
        ],
    )

    args = enrichment_worker.parse_args()

    assert args.queue_file == "queue.csv"
    assert args.data_dir == "data-dir"
    assert args.details_dir == "details-dir"
    assert args.limit == 3
    assert args.cooldown_days == 14
    assert args.retry_failed is True


def test_is_in_cooldown_true_and_false_cases():
    now = datetime(2026, 4, 11, 12, 0, tzinfo=timezone.utc)
    fresh = (now - timedelta(days=2)).isoformat()
    stale = (now - timedelta(days=10)).isoformat()

    assert enrichment_worker.is_in_cooldown(fresh, cooldown_days=7, now=now) is True
    assert enrichment_worker.is_in_cooldown(stale, cooldown_days=7, now=now) is False
    assert enrichment_worker.is_in_cooldown("", cooldown_days=7, now=now) is False


def test_run_skips_failed_without_retry_and_processes_with_retry(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    csv_file = data_dir / "cars.csv"
    queue_file = data_dir / "enrichment_queue.csv"
    _write_storage_csv(csv_file, listing_id="FAILED1")

    with open(csv_file, "r", newline="", encoding="utf-8-sig") as file_handle:
        rows = list(csv.DictReader(file_handle, delimiter=";"))
    rows[0]["details_status"] = "failed"
    with open(csv_file, "w", newline="", encoding="utf-8-sig") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=list(rows[0].keys()), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    with open(queue_file, "w", newline="", encoding="utf-8-sig") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=["listing_id", "link", "priority", "reason", "selected_at", "source_csv"],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerow({
            "listing_id": "FAILED1",
            "link": "https://example.com/oferta",
            "priority": "50",
            "reason": "new",
            "selected_at": "2026-04-11T10:00:00+00:00",
            "source_csv": "cars.csv",
        })

    results_without_retry = enrichment_worker.run(
        queue_file=str(queue_file),
        data_dir=str(data_dir),
        details_dir=str(data_dir / "details"),
        retry_failed=False,
        fetch_html=lambda url: DETAIL_HTML,
    )
    assert results_without_retry == []

    results_with_retry = enrichment_worker.run(
        queue_file=str(queue_file),
        data_dir=str(data_dir),
        details_dir=str(data_dir / "details"),
        retry_failed=True,
        fetch_html=lambda url: DETAIL_HTML,
    )
    assert len(results_with_retry) == 1
    assert results_with_retry[0]["status"] == "fetched"


def test_run_skips_recently_fetched_within_cooldown(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    csv_file = data_dir / "cars.csv"
    queue_file = data_dir / "enrichment_queue.csv"
    _write_storage_csv(csv_file, listing_id="RECENT1")

    with open(csv_file, "r", newline="", encoding="utf-8-sig") as file_handle:
        rows = list(csv.DictReader(file_handle, delimiter=";"))
    rows[0]["details_status"] = "fetched"
    rows[0]["details_fetched_at"] = datetime.now(timezone.utc).isoformat()
    with open(csv_file, "w", newline="", encoding="utf-8-sig") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=list(rows[0].keys()), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    with open(queue_file, "w", newline="", encoding="utf-8-sig") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=["listing_id", "link", "priority", "reason", "selected_at", "source_csv"],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerow({
            "listing_id": "RECENT1",
            "link": "https://example.com/oferta",
            "priority": "50",
            "reason": "new",
            "selected_at": "2026-04-11T10:00:00+00:00",
            "source_csv": "cars.csv",
        })

    results = enrichment_worker.run(
        queue_file=str(queue_file),
        data_dir=str(data_dir),
        details_dir=str(data_dir / "details"),
        cooldown_days=7,
        fetch_html=lambda url: DETAIL_HTML,
    )

    assert results == []


def test_run_reprocesses_fetched_after_cooldown_expires(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    csv_file = data_dir / "cars.csv"
    queue_file = data_dir / "enrichment_queue.csv"
    _write_storage_csv(csv_file, listing_id="STALE1")

    with open(csv_file, "r", newline="", encoding="utf-8-sig") as file_handle:
        rows = list(csv.DictReader(file_handle, delimiter=";"))
    rows[0]["details_status"] = "fetched"
    rows[0]["details_fetched_at"] = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    with open(csv_file, "w", newline="", encoding="utf-8-sig") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=list(rows[0].keys()), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    with open(queue_file, "w", newline="", encoding="utf-8-sig") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=["listing_id", "link", "priority", "reason", "selected_at", "source_csv"],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerow({
            "listing_id": "STALE1",
            "link": "https://example.com/oferta",
            "priority": "50",
            "reason": "refresh",
            "selected_at": "2026-04-11T10:00:00+00:00",
            "source_csv": "cars.csv",
        })

    results = enrichment_worker.run(
        queue_file=str(queue_file),
        data_dir=str(data_dir),
        details_dir=str(data_dir / "details"),
        cooldown_days=7,
        fetch_html=lambda url: DETAIL_HTML,
    )

    assert len(results) == 1
    assert results[0]["status"] == "fetched"


def test_should_bypass_cooldown_for_price_change_and_bucket_promotion():
    assert enrichment_worker.should_bypass_cooldown(
        {
            "price_pln": "12000",
            "details_based_on_price_pln": "10000",
            "details_based_on_decision_bucket": "watch",
        },
        current_decision_bucket="watch",
    ) is True

    assert enrichment_worker.should_bypass_cooldown(
        {
            "price_pln": "10000",
            "details_based_on_price_pln": "10000",
            "details_based_on_decision_bucket": "watch",
        },
        current_decision_bucket="candidate",
    ) is True

    assert enrichment_worker.should_bypass_cooldown(
        {
            "price_pln": "10000",
            "details_based_on_price_pln": "10000",
            "details_based_on_decision_bucket": "candidate",
        },
        current_decision_bucket="watch",
    ) is False


def test_run_reprocesses_recent_listing_when_price_changed(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    csv_file = data_dir / "cars.csv"
    queue_file = data_dir / "enrichment_queue.csv"
    _write_storage_csv(csv_file, listing_id="PRICE1")

    with open(csv_file, "r", newline="", encoding="utf-8-sig") as file_handle:
        rows = list(csv.DictReader(file_handle, delimiter=";"))
    rows[0]["details_status"] = "fetched"
    rows[0]["details_fetched_at"] = datetime.now(timezone.utc).isoformat()
    rows[0]["details_based_on_price_pln"] = "9000"
    with open(csv_file, "w", newline="", encoding="utf-8-sig") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=list(rows[0].keys()), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    with open(queue_file, "w", newline="", encoding="utf-8-sig") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=["listing_id", "link", "priority", "reason", "selected_at", "source_csv"],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerow({
            "listing_id": "PRICE1",
            "link": "https://example.com/oferta",
            "priority": "50",
            "reason": "price-change",
            "selected_at": "2026-04-11T10:00:00+00:00",
            "source_csv": "cars.csv",
        })

    results = enrichment_worker.run(
        queue_file=str(queue_file),
        data_dir=str(data_dir),
        details_dir=str(data_dir / "details"),
        cooldown_days=7,
        fetch_html=lambda url: DETAIL_HTML,
    )

    assert len(results) == 1
    assert results[0]["status"] == "fetched"


def test_run_reprocesses_recent_listing_when_bucket_promoted(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    analytics_dir = data_dir / "analytics"
    analytics_dir.mkdir()
    csv_file = data_dir / "cars.csv"
    queue_file = data_dir / "enrichment_queue.csv"
    _write_storage_csv(csv_file, listing_id="BUCKET1")

    with open(csv_file, "r", newline="", encoding="utf-8-sig") as file_handle:
        rows = list(csv.DictReader(file_handle, delimiter=";"))
    rows[0]["details_status"] = "fetched"
    rows[0]["details_fetched_at"] = datetime.now(timezone.utc).isoformat()
    rows[0]["details_based_on_price_pln"] = "10000"
    rows[0]["details_based_on_decision_bucket"] = "watch"
    with open(csv_file, "w", newline="", encoding="utf-8-sig") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=list(rows[0].keys()), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    (analytics_dir / "cars-analysis.json").write_text(
        json.dumps([
            {
                "listing_id": "BUCKET1",
                "decision_bucket": "candidate",
            }
        ]),
        encoding="utf-8",
    )

    with open(queue_file, "w", newline="", encoding="utf-8-sig") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=["listing_id", "link", "priority", "reason", "selected_at", "source_csv"],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerow({
            "listing_id": "BUCKET1",
            "link": "https://example.com/oferta",
            "priority": "50",
            "reason": "bucket-promotion",
            "selected_at": "2026-04-11T10:00:00+00:00",
            "source_csv": "cars.csv",
        })

    results = enrichment_worker.run(
        queue_file=str(queue_file),
        data_dir=str(data_dir),
        details_dir=str(data_dir / "details"),
        cooldown_days=7,
        fetch_html=lambda url: DETAIL_HTML,
    )

    assert len(results) == 1
    assert results[0]["status"] == "fetched"

    with open(csv_file, "r", newline="", encoding="utf-8-sig") as file_handle:
        refreshed_rows = list(csv.DictReader(file_handle, delimiter=";"))
    assert refreshed_rows[0]["details_based_on_decision_bucket"] == "candidate"
