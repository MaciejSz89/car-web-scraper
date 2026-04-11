import json
import sys
from pathlib import Path
import pytest

# ensure otomoto-scraper dir is on path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "otomoto-scraper"))

import analytics


def test_percentile_25_basic():
    prices = [100, 200, 300, 400]
    p25 = analytics._percentile_25(prices)
    # sorted [100,200,300,400], index = int((4-1)*0.25)=0 -> 100
    assert p25 == 100


def test_calculate_market_score_small_group():
    target = {"price_pln": 100, "days_on_site": 1, "initial_price_pln": 120, "price_change_count": 0, "seller_type": "private", "year": 2018, "mileage_km": 50000, "fuel_type": "petrol", "gearbox": "manual"}
    group = [
        {"price_pln": 110},
        {"price_pln": None},
    ]
    score, reasons = analytics._calculate_market_score(target, group, fallback_level=0)
    # group has less than MIN_LOW_CONFIDENCE_GROUP_SIZE -> returns 20
    assert score == 20
    assert any("zbyt mala grupa" in r for r in reasons)


def test_apply_enrichment_adjustment_does_not_promote_weak_market_offer():
    enrichment_result = analytics.EnrichmentAnalysisResult(
        listing_id="A",
        enrichment_score=95,
        enrichment_confidence=100,
        enrichment_reasons=["positive"],
        enrichment_flags=["vin_present"],
        description_signals=["accident_free_declared"],
        equipment_signals=[],
        seller_signals=[],
        consistency_signals=[],
    )

    adjusted = analytics._apply_enrichment_adjustment(30, 30, enrichment_result)
    assert adjusted == 30


def test_analyze_query_csv_end_to_end(tmp_path, monkeypatch):
    # create minimal CSV with two active cars
    csv_path = tmp_path / "cars.csv"
    header = [
        "listing_id","title","price_pln","currency","link","subtitle","engine_cm3","power_hp",
        "mileage_km","fuel_type","gearbox","year","location","seller_type","details_status",
        "details_priority","details_fetched_at","is_damaged","condition_note","first_seen_date",
        "last_seen_date","days_on_site","is_active","removed_date","initial_price_pln","lowest_price_pln",
        "price_change_count","last_price_change_date",
    ]

    rows = [
        {"listing_id": "A", "title": "A", "price_pln": "10000", "currency": "PLN", "link": "l", "subtitle": "", "engine_cm3": "1600", "power_hp": "120", "mileage_km": "50000", "fuel_type": "petrol", "gearbox": "manual", "year": "2018", "location": "x", "seller_type": "private", "is_damaged": "0", "first_seen_date": "2026-04-01", "last_seen_date": "2026-04-01", "days_on_site": "0", "is_active": "1", "initial_price_pln": "10000", "lowest_price_pln": "10000", "price_change_count": "0", "last_price_change_date": ""},
        {"listing_id": "B", "title": "B", "price_pln": "12000", "currency": "PLN", "link": "l2", "subtitle": "", "engine_cm3": "1600", "power_hp": "120", "mileage_km": "55000", "fuel_type": "petrol", "gearbox": "manual", "year": "2017", "location": "x", "seller_type": "business", "is_damaged": "0", "first_seen_date": "2026-04-01", "last_seen_date": "2026-04-01", "days_on_site": "0", "is_active": "1", "initial_price_pln": "12000", "lowest_price_pln": "12000", "price_change_count": "0", "last_price_change_date": ""},
    ]

    with open(csv_path, "w", encoding="utf-8") as f:
        import csv
        writer = csv.DictWriter(f, fieldnames=header, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    # monkeypatch load_preferences to return minimal prefs
    monkeypatch.setattr(analytics, "load_preferences", lambda: {"global":{}, "queries":{}, "profile_name":"test"})
    monkeypatch.setattr(
        analytics,
        "analyze_listing_details",
        lambda listing_id, listing_row=None: analytics.EnrichmentAnalysisResult(
            listing_id=listing_id,
            enrichment_score=80 if listing_id == "A" else 20,
            enrichment_confidence=100,
            enrichment_reasons=["test enrichment"],
            enrichment_flags=["vin_present"],
            description_signals=["vin_present"],
            equipment_signals=[],
            seller_signals=[],
            consistency_signals=[],
        ),
    )

    results = analytics.analyze_query_csv("test", str(csv_path))
    assert isinstance(results, list)
    assert all(hasattr(r, "listing_id") for r in results)
    assert all(hasattr(r, "enrichment_score") for r in results)
    assert results[0].enrichment_reasons
    # results sorted by final_score desc
    assert results[0].final_score >= results[-1].final_score
