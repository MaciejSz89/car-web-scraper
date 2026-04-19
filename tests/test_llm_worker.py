import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "otomoto-scraper"))

import llm_worker


def _base_listing_row(**overrides) -> dict:
    row = {
        "title": "Test Car",
        "price_pln": "30000",
        "year": "2020",
        "mileage_km": "80000",
        "fuel_type": "petrol",
        "gearbox": "manual",
        "power_hp": "100",
        "seller_type": "private",
        "is_damaged": "0",
        "details_damaged_flag": "0",
        "details_imported_flag": "0",
        "details_country_origin": "",
        "details_enrichment_flags": "",
    }
    row.update(overrides)
    return row


def _base_analytics() -> dict:
    return {
        "final_score": 70,
        "decision_bucket": "candidate",
        "market_score": 65,
        "market_reasons": [],
        "enrichment_reasons": [],
    }


def test_build_prompt_no_damage_no_import():
    listing_row = _base_listing_row()
    detail_payload = {"description": "Dobry stan.", "equipment": [], "parameters": {}}
    prompt = llm_worker.build_prompt(listing_row, detail_payload, _base_analytics())
    assert "brak sygnałów uszkodzenia" in prompt
    assert "brak flag importu" in prompt


def test_build_prompt_damage_from_csv_flag():
    listing_row = _base_listing_row(details_damaged_flag="1")
    detail_payload = {"description": "Opis.", "equipment": [], "parameters": {}}
    prompt = llm_worker.build_prompt(listing_row, detail_payload, _base_analytics())
    assert "UWAGA" in prompt
    assert "uszkodzona" in prompt


def test_build_prompt_damage_from_sidecar_when_csv_stale():
    """LLM prompt must pick up damage from sidecar JSON even when CSV details_damaged_flag=0 (stale enrichment)."""
    listing_row = _base_listing_row(details_damaged_flag="0", is_damaged="0")
    detail_payload = {
        "description": "Opis.",
        "equipment": [],
        "parameters": {"damaged": "damaged"},  # otomoto checkbox pattern
    }
    prompt = llm_worker.build_prompt(listing_row, detail_payload, _base_analytics())
    assert "UWAGA" in prompt
    assert "uszkodzona" in prompt


def test_build_prompt_import_from_sidecar_when_csv_stale():
    """LLM prompt must pick up import flag from sidecar JSON when CSV details_imported_flag=0."""
    listing_row = _base_listing_row(details_imported_flag="0", details_country_origin="")
    detail_payload = {
        "description": "Opis.",
        "equipment": [],
        "parameters": {"is_imported_car": "is_imported_car"},  # otomoto checkbox pattern
    }
    prompt = llm_worker.build_prompt(listing_row, detail_payload, _base_analytics())
    assert "UWAGA" in prompt
    assert "importowany" in prompt


def test_build_prompt_overseas_country_from_sidecar():
    """country_origin from sidecar must appear in the import section."""
    listing_row = _base_listing_row(details_imported_flag="0", details_country_origin="")
    detail_payload = {
        "description": "Opis.",
        "equipment": [],
        "parameters": {"country_origin": "Stany Zjednoczone"},
    }
    prompt = llm_worker.build_prompt(listing_row, detail_payload, _base_analytics())
    assert "Stany Zjednoczone" in prompt
    assert "UWAGA" in prompt
