import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "otomoto-scraper"))

import enrichment_analysis


def test_analyze_detail_payload_detects_positive_negative_and_consistency_signals():
    payload = {
        "description": "Bezwypadkowy, serwis ASO, ale auto po kolizji i do poprawek.",
        "equipment": ["Kamera cofania", "Tempomat", "LED"],
        "seller": {"type": "private", "name": "Jan", "phone_numbers": ["123"]},
        "price": {"amount": 10000, "currency": "PLN"},
        "parameters": {"vin": "VIN123", "is_imported_car": "false"},
        "structured_data": [{"@type": "Car"}],
    }
    listing_row = {"price_pln": "10000", "seller_type": "private"}

    result = enrichment_analysis.analyze_detail_payload("123", payload, listing_row=listing_row)

    assert result.listing_id == "123"
    assert result.enrichment_confidence > 0
    assert "accident_free_declared" in result.enrichment_flags
    assert "collision_history" in result.enrichment_flags
    assert "vin_present" in result.enrichment_flags
    assert "listing_detail_price_consistent" in result.enrichment_flags
    assert any("ASO" in reason or "aso" in reason.lower() for reason in result.enrichment_reasons)


def test_load_and_analyze_listing_details_from_sidecar(tmp_path):
    details_dir = tmp_path / "details"
    details_dir.mkdir()
    payload = {
        "description": "Pierwszy właściciel, garażowany.",
        "equipment": ["Skora"],
        "seller": {"type": "business", "name": "Komis"},
        "price": {"amount": 9000},
        "parameters": {},
    }
    (details_dir / "ABC.json").write_text(json.dumps(payload), encoding="utf-8")

    result = enrichment_analysis.analyze_listing_details(
        "ABC",
        listing_row={"price_pln": "9000", "seller_type": "business"},
        details_dir=details_dir,
    )

    assert result is not None
    assert result.listing_id == "ABC"
    assert result.enrichment_score >= 50
    assert "seller_business_confirmed" in result.enrichment_flags


def test_import_flag_detected_for_otomoto_checkbox_pattern():
    """is_imported_car with value equal to its key (otomoto checkbox) must trigger import_flag_present."""
    payload = {
        "description": "Samochód w dobrym stanie.",
        "parameters": {"is_imported_car": "is_imported_car", "vin": "VIN999"},
        "price": {"amount": 30000},
        "seller": {"type": "private"},
    }
    listing_row = {"price_pln": "30000", "seller_type": "private"}
    result = enrichment_analysis.analyze_detail_payload("X1", payload, listing_row=listing_row)
    assert "import_flag_present" in result.enrichment_flags


def test_overseas_import_flag_for_usa():
    """country_origin containing known overseas keyword must trigger overseas_import flag and penalty."""
    payload = {
        "description": "Samochód sprowadzony.",
        "parameters": {"country_origin": "Stany Zjednoczone"},
        "price": {"amount": 40000},
        "seller": {"type": "private"},
    }
    listing_row = {"price_pln": "40000", "seller_type": "private"}
    result = enrichment_analysis.analyze_detail_payload("X2", payload, listing_row=listing_row)
    assert "overseas_import" in result.enrichment_flags
    # score should be below neutral 50 due to overseas penalty
    assert result.enrichment_score < 50