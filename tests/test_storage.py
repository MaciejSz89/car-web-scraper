import csv
import os
import sys
from pathlib import Path
import pytest

# ensure otomoto-scraper dir is on path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "otomoto-scraper"))

from storage import (
    parse_csv_date,
    calculate_days_on_site,
    read_existing_cars,
    upsert_cars_to_csv,
)


def make_sample_car(listing_id: str, price: int) -> dict:
    return {
        "listing_id": listing_id,
        "title": "Test Car",
        "price_pln": price,
        "currency": "PLN",
        "link": "https://example.com/1",
        "subtitle": "",
        "engine_cm3": 1600,
        "power_hp": 120,
        "mileage_km": 50000,
        "fuel_type": "petrol",
        "gearbox": "manual",
        "year": 2018,
        "location": "Warsaw",
        "seller_type": "private",
    }


def test_parse_csv_date_iso_and_dot():
    assert parse_csv_date("2026-04-09").isoformat() == "2026-04-09"
    assert parse_csv_date("09.04.2026").isoformat() == "2026-04-09"
    with pytest.raises(ValueError):
        parse_csv_date("04/09/2026")


def test_calculate_days_on_site():
    days = calculate_days_on_site("2026-04-01", "2026-04-09")
    assert days == 8


def test_read_existing_cars_returns_empty_for_missing(tmp_path):
    p = tmp_path / "no-such.csv"
    assert not p.exists()
    res = read_existing_cars(str(p))
    assert res == {}


def test_upsert_creates_and_updates(tmp_path):
    csv_file = str(tmp_path / "cars.csv")

    car1 = make_sample_car("ID1", 10000)
    new_count, updated_count = upsert_cars_to_csv([car1], csv_file)
    assert new_count == 1
    assert updated_count == 0
    assert os.path.exists(csv_file)

    # read back and assert values
    with open(csv_file, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["listing_id"] == "ID1"
    assert rows[0]["price_pln"] in ("10000", 10000)

    # update price -> should increment updated_count and price_change_count
    car1_updated = make_sample_car("ID1", 9000)
    new_count2, updated_count2 = upsert_cars_to_csv([car1_updated], csv_file)
    assert new_count2 == 0
    assert updated_count2 == 1

    # check price_change_count is >=1
    with open(csv_file, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        rows = list(reader)
    assert rows[0]["listing_id"] == "ID1"
    assert int(rows[0]["price_change_count"]) >= 1
