from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import DATA_DIR
from utils import clean_text, safe_int


DETAILS_DIR = DATA_DIR / "details"

POSITIVE_DESCRIPTION_RULES = {
    "bezwypad": (12, "deklaracja bezwypadkowosci", "accident_free_declared"),
    "serwis aso": (10, "wzmianka o serwisie ASO", "aso_service"),
    "pierwszy wlasc": (8, "wzmianka o pierwszym wlascicielu", "first_owner"),
    "pierwszy właśc": (8, "wzmianka o pierwszym wlascicielu", "first_owner"),
    "garazowan": (5, "wzmianka o garazowaniu", "garage_kept"),
    "udokumentowan": (6, "wzmianka o udokumentowanej historii", "documented_history"),
}

NEGATIVE_DESCRIPTION_RULES = {
    "uszkodz": (-18, "wzmianka o uszkodzeniu", "damage_declared"),
    "do poprawek": (-10, "wzmianka o koniecznych poprawkach", "needs_repairs"),
    "po koliz": (-16, "wzmianka o kolizji", "collision_history"),
    "naprawian": (-12, "wzmianka o naprawach blacharskich", "repaired_bodywork"),
    "brak dokument": (-14, "wzmianka o brakach dokumentow", "missing_documents"),
    "sprowadz": (-4, "wzmianka o imporcie pojazdu", "imported_vehicle"),
    "brak przod": (-30, "ciezkie uszkodzenie przodu", "severe_front_damage"),
    "brak tyl": (-28, "ciezkie uszkodzenie tylu", "severe_rear_damage"),
    "wystrzelon": (-35, "wzmianka o wystrzelonych poduszkach", "airbags_deployed"),
    "szkoda calkowita": (-40, "wzmianka o szkodzie calkowitej", "total_loss_declared"),
    "szkoda całkowita": (-40, "wzmianka o szkodzie calkowitej", "total_loss_declared"),
    "do kasacji": (-35, "wzmianka o pojezdzie do kasacji", "scrap_candidate"),
    "na czesci": (-30, "wzmianka o pojezdzie na czesci", "parts_only_vehicle"),
}

EQUIPMENT_RULES = {
    "kamera": (4, "obecnosc kamery", "camera_present"),
    "tempomat": (3, "obecnosc tempomatu", "cruise_control_present"),
    "adaptacyj": (4, "obecnosc funkcji adaptacyjnych", "adaptive_feature_present"),
    "skora": (3, "bogatsze wykonczenie wnetrza", "leather_trim_present"),
    "led": (2, "oswietlenie LED", "led_present"),
    "4x4": (3, "naped 4x4", "awd_present"),
}


@dataclass(slots=True)
class EnrichmentAnalysisResult:
    listing_id: str
    enrichment_score: int
    enrichment_confidence: int
    enrichment_reasons: list[str]
    enrichment_flags: list[str]
    description_signals: list[str]
    equipment_signals: list[str]
    seller_signals: list[str]
    consistency_signals: list[str]


def get_details_file_path(listing_id: str, details_dir: str | Path | None = None) -> Path:
    base_dir = Path(details_dir) if details_dir is not None else DETAILS_DIR
    return base_dir / f"{listing_id}.json"


def load_details_payload(listing_id: str, details_dir: str | Path | None = None) -> dict[str, Any] | None:
    details_file = get_details_file_path(listing_id, details_dir)
    if not details_file.exists():
        return None

    try:
        with open(details_file, "r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)
    except (OSError, json.JSONDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


def _append_unique(target: list[str], value: str) -> None:
    if value not in target:
        target.append(value)


def _score_description(description: str | None) -> tuple[int, list[str], list[str]]:
    if not description:
        return 0, [], []

    lowered = description.lower()
    score = 0
    reasons: list[str] = []
    flags: list[str] = []

    for keyword, (delta, reason, flag) in POSITIVE_DESCRIPTION_RULES.items():
        if keyword in lowered:
            score += delta
            _append_unique(reasons, reason)
            _append_unique(flags, flag)

    for keyword, (delta, reason, flag) in NEGATIVE_DESCRIPTION_RULES.items():
        if keyword in lowered:
            score += delta
            _append_unique(reasons, reason)
            _append_unique(flags, flag)

    return score, reasons, flags


def _score_equipment(equipment: Any) -> tuple[int, list[str], list[str]]:
    if not isinstance(equipment, list):
        return 0, [], []

    flattened = " ".join(str(item).lower() for item in equipment)
    score = 0
    reasons: list[str] = []
    flags: list[str] = []

    for keyword, (delta, reason, flag) in EQUIPMENT_RULES.items():
        if keyword in flattened:
            score += delta
            _append_unique(reasons, reason)
            _append_unique(flags, flag)

    return score, reasons, flags


def _score_seller(seller: Any) -> tuple[int, list[str], list[str]]:
    if not isinstance(seller, dict):
        return 0, [], []

    score = 0
    reasons: list[str] = []
    flags: list[str] = []
    seller_type = str(seller.get("type") or "").strip().lower()

    if seller.get("name"):
        _append_unique(reasons, "dostepna nazwa sprzedawcy")
        _append_unique(flags, "seller_name_present")

    if seller.get("phone_numbers"):
        _append_unique(reasons, "dostepny kontakt telefoniczny")
        _append_unique(flags, "seller_phone_present")

    if seller_type == "private":
        score += 3
        _append_unique(reasons, "detail page potwierdza prywatnego sprzedawce")
        _append_unique(flags, "seller_private_confirmed")
    elif seller_type == "business":
        score -= 1
        _append_unique(reasons, "detail page potwierdza firme")
        _append_unique(flags, "seller_business_confirmed")

    return score, reasons, flags


def _score_consistency(payload: dict[str, Any], listing_row: dict[str, Any] | None) -> tuple[int, list[str], list[str]]:
    if not listing_row:
        return 0, [], []

    score = 0
    reasons: list[str] = []
    flags: list[str] = []

    detail_price_raw = payload.get("price")
    detail_amount = None
    if isinstance(detail_price_raw, dict):
        detail_amount = safe_int(detail_price_raw.get("amount"))
    else:
        detail_amount = safe_int(detail_price_raw)

    listing_price = safe_int(listing_row.get("price_pln"))
    if detail_amount is not None and listing_price is not None:
        if detail_amount != listing_price:
            score -= 14
            _append_unique(reasons, f"niespojnosc ceny listing/detail ({listing_price} vs {detail_amount})")
            _append_unique(flags, "listing_detail_mismatch")
        else:
            _append_unique(reasons, "spojna cena miedzy listingiem i detail page")
            _append_unique(flags, "listing_detail_price_consistent")

    seller = payload.get("seller")
    detail_seller_type = str((seller or {}).get("type") or "").strip().lower() if isinstance(seller, dict) else ""
    listing_seller_type = str(listing_row.get("seller_type") or "").strip().lower()
    if detail_seller_type and listing_seller_type:
        if detail_seller_type != listing_seller_type:
            score -= 10
            _append_unique(reasons, "niespojnosc typu sprzedawcy miedzy listingiem i detail page")
            _append_unique(flags, "seller_type_mismatch")
        else:
            _append_unique(flags, "seller_type_consistent")

    parameters = payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {}
    vin = clean_text(parameters.get("vin") if isinstance(parameters, dict) else None)
    if vin:
        score += 5
        _append_unique(reasons, "obecnosc numeru VIN")
        _append_unique(flags, "vin_present")

    imported = str(parameters.get("is_imported_car") or "").strip().lower() if isinstance(parameters, dict) else ""
    if imported in {"true", "1", "yes", "tak"}:
        score -= 2
        _append_unique(reasons, "detail page wskazuje na import pojazdu")
        _append_unique(flags, "import_flag_present")

    return score, reasons, flags


def _score_parameters(parameters: Any) -> tuple[int, list[str], list[str]]:
    if not isinstance(parameters, dict):
        return 0, [], []

    score = 0
    reasons: list[str] = []
    flags: list[str] = []

    damaged_raw = parameters.get("damaged")
    if damaged_raw not in (None, "", [], {}):
        normalized = str(damaged_raw).strip().lower()
        if normalized not in {"0", "false", "no", "nie"}:
            score -= 25
            _append_unique(reasons, "strukturalna flaga uszkodzenia z detail page")
            _append_unique(flags, "damage_structural")

    no_accident_raw = parameters.get("no_accident")
    if no_accident_raw not in (None, "", [], {}):
        normalized = str(no_accident_raw).strip().lower()
        if normalized not in {"0", "false", "no", "nie"}:
            score += 8
            _append_unique(reasons, "strukturalna flaga bezwypadkowosci z detail page")
            _append_unique(flags, "accident_free_structural")

    return score, reasons, flags


def _calculate_confidence(payload: dict[str, Any], consistency_flags: list[str]) -> int:
    confidence = 20

    if clean_text(payload.get("description")):
        confidence += 25
    if isinstance(payload.get("parameters"), dict) and payload.get("parameters"):
        confidence += 20
    if isinstance(payload.get("equipment"), list) and payload.get("equipment"):
        confidence += 10
    if isinstance(payload.get("seller"), dict) and payload.get("seller"):
        confidence += 10
    if payload.get("price") not in (None, "", {}, []):
        confidence += 10
    if payload.get("structured_data") not in (None, "", {}, []):
        confidence += 5

    if "listing_detail_mismatch" in consistency_flags:
        confidence -= 10

    return max(0, min(100, confidence))


def analyze_detail_payload(
    listing_id: str,
    payload: dict[str, Any],
    *,
    listing_row: dict[str, Any] | None = None,
) -> EnrichmentAnalysisResult:
    description = clean_text(payload.get("description"))
    equipment = payload.get("equipment")
    seller = payload.get("seller")
    parameters = payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {}

    description_score, description_reasons, description_flags = _score_description(description)
    equipment_score, equipment_reasons, equipment_flags = _score_equipment(equipment)
    seller_score, seller_reasons, seller_flags = _score_seller(seller)
    consistency_score, consistency_reasons, consistency_flags = _score_consistency(payload, listing_row)
    parameters_score, parameters_reasons, parameters_flags = _score_parameters(parameters)

    raw_score = 50 + description_score + equipment_score + seller_score + consistency_score + parameters_score
    enrichment_score = max(0, min(100, raw_score))
    enrichment_confidence = _calculate_confidence(payload, consistency_flags)

    enrichment_reasons = description_reasons + equipment_reasons + seller_reasons + consistency_reasons + parameters_reasons
    enrichment_flags = description_flags + equipment_flags + seller_flags + consistency_flags + parameters_flags

    return EnrichmentAnalysisResult(
        listing_id=listing_id,
        enrichment_score=enrichment_score,
        enrichment_confidence=enrichment_confidence,
        enrichment_reasons=enrichment_reasons,
        enrichment_flags=enrichment_flags,
        description_signals=description_flags,
        equipment_signals=equipment_flags,
        seller_signals=seller_flags,
        consistency_signals=consistency_flags + parameters_flags,
    )


def analyze_listing_details(
    listing_id: str,
    *,
    listing_row: dict[str, Any] | None = None,
    details_dir: str | Path | None = None,
) -> EnrichmentAnalysisResult | None:
    payload = load_details_payload(listing_id, details_dir)
    if payload is None:
        return None

    return analyze_detail_payload(listing_id, payload, listing_row=listing_row)