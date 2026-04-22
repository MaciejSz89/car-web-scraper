from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Any

from config import ANALYTICS_DIR
from enrichment_analysis import EnrichmentAnalysisResult, analyze_listing_details
from preferences import evaluate_preferences, get_query_preferences, load_preferences
from utils import safe_int


MIN_COMPARISON_GROUP_SIZE = 5
MIN_LOW_CONFIDENCE_GROUP_SIZE = 3
DAMAGE_PENALTY = 30
PRIVATE_SELLER_BONUS = 5
BUSINESS_SELLER_PENALTY = 2

SEGMENT_RULES = [
    {"year": 1, "mileage": 20_000, "power": 15, "engine": 200, "allow_gearbox_mismatch": False, "allow_engine_mismatch": False},
    {"year": 2, "mileage": 20_000, "power": 15, "engine": 200, "allow_gearbox_mismatch": False, "allow_engine_mismatch": False},
    {"year": 2, "mileage": 30_000, "power": 25, "engine": 300, "allow_gearbox_mismatch": False, "allow_engine_mismatch": False},
    {"year": 2, "mileage": 30_000, "power": 25, "engine": 300, "allow_gearbox_mismatch": True, "allow_engine_mismatch": False},
    {"year": 2, "mileage": 30_000, "power": 25, "engine": 300, "allow_gearbox_mismatch": True, "allow_engine_mismatch": True},
]


@dataclass(slots=True)
class AnalyticsResult:
    listing_id: str
    query_name: str
    title: str | None
    link: str | None
    price_pln: int | None
    seller_type: str | None
    market_score: int
    confidence_score: int
    preference_score: int
    final_score: int
    decision_bucket: str
    hard_filter_passed: bool
    comparison_group_size: int
    fallback_level: int
    market_reasons: list[str]
    preference_reasons: list[str]
    enrichment_score: int | None
    enrichment_confidence: int
    enrichment_reasons: list[str]
    enrichment_flags: list[str]


def _read_active_cars(csv_file: str) -> list[dict[str, Any]]:
    cars: list[dict[str, Any]] = []

    with open(csv_file, "r", newline="", encoding="utf-8-sig") as file_handle:
        reader = csv.DictReader(file_handle, delimiter=";")
        for row in reader:
            if str(row.get("is_active")) != "1":
                continue

            cars.append({
                **row,
                "price_pln": safe_int(row.get("price_pln")),
                "engine_cm3": safe_int(row.get("engine_cm3")),
                "power_hp": safe_int(row.get("power_hp")),
                "mileage_km": safe_int(row.get("mileage_km")),
                "year": safe_int(row.get("year")),
                "days_on_site": safe_int(row.get("days_on_site")),
                "initial_price_pln": safe_int(row.get("initial_price_pln")),
                "lowest_price_pln": safe_int(row.get("lowest_price_pln")),
                "price_change_count": safe_int(row.get("price_change_count")) or 0,
                "seller_type": (row.get("seller_type") or "").strip() or None,
                "is_damaged": str(row.get("is_damaged")).lower() in ("1", "true", "yes"),
                "condition_note": row.get("condition_note") or None,
            })

    return cars


def _matches_segment(target: dict[str, Any], candidate: dict[str, Any], rule: dict[str, Any]) -> bool:
    if target["listing_id"] == candidate["listing_id"]:
        return False

    target_fuel = target.get("fuel_type")
    candidate_fuel = candidate.get("fuel_type")
    if target_fuel and candidate_fuel and target_fuel != candidate_fuel:
        return False

    if not rule["allow_gearbox_mismatch"]:
        target_gearbox = target.get("gearbox")
        candidate_gearbox = candidate.get("gearbox")
        if target_gearbox and candidate_gearbox and target_gearbox != candidate_gearbox:
            return False

    target_year = target.get("year")
    candidate_year = candidate.get("year")
    if target_year is not None and candidate_year is not None and abs(target_year - candidate_year) > rule["year"]:
        return False

    target_mileage = target.get("mileage_km")
    candidate_mileage = candidate.get("mileage_km")
    if target_mileage is not None and candidate_mileage is not None and abs(target_mileage - candidate_mileage) > rule["mileage"]:
        return False

    target_power = target.get("power_hp")
    candidate_power = candidate.get("power_hp")
    if target_power is not None and candidate_power is not None:
        if abs(target_power - candidate_power) > rule["power"] and not rule["allow_engine_mismatch"]:
            return False
        return True

    target_engine = target.get("engine_cm3")
    candidate_engine = candidate.get("engine_cm3")
    if target_engine is not None and candidate_engine is not None:
        if abs(target_engine - candidate_engine) > rule["engine"] and not rule["allow_engine_mismatch"]:
            return False

    return True


def _build_comparison_group(target: dict[str, Any], cars: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    fallback_level = len(SEGMENT_RULES) - 1
    group: list[dict[str, Any]] = []

    for index, rule in enumerate(SEGMENT_RULES):
        current_group = [candidate for candidate in cars if _matches_segment(target, candidate, rule)]
        group = current_group
        fallback_level = index
        if len(current_group) >= MIN_COMPARISON_GROUP_SIZE:
            break

    return group, fallback_level


def _percentile_25(prices: list[int]) -> int:
    sorted_prices = sorted(prices)
    if not sorted_prices:
        raise ValueError("Lista cen nie moze byc pusta.")
    index = max(0, int((len(sorted_prices) - 1) * 0.25))
    return sorted_prices[index]


def _calculate_market_score(target: dict[str, Any], group: list[dict[str, Any]], fallback_level: int, import_cost_pln: int = 0) -> tuple[int, list[str]]:
    reasons: list[str] = []
    price_pln = target.get("price_pln")
    if price_pln is None:
        return 0, ["brak ceny oferty"]

    effective_price = price_pln + import_cost_pln
    if import_cost_pln:
        reasons.append(f"korekta o koszty importu: +{import_cost_pln} PLN (efektywna cena: {effective_price} PLN)")

    prices = [candidate["price_pln"] for candidate in group if candidate.get("price_pln") is not None]
    if len(prices) < MIN_LOW_CONFIDENCE_GROUP_SIZE:
        return 20, reasons + ["zbyt mala grupa porownawcza do wyceny rynku"]

    median_price = round(median(prices))
    p25_price = _percentile_25(prices)
    price_advantage_ratio = (median_price - effective_price) / median_price if median_price else 0.0

    score = 50 + int(price_advantage_ratio * 250)
    reasons.append(f"pozycja ceny vs mediana segmentu: {effective_price} vs {median_price}")

    if effective_price <= p25_price:
        score += 10
        reasons.append(f"cena w dolnym kwartylu segmentu ({p25_price})")

    days_on_site = target.get("days_on_site")
    if days_on_site is not None:
        if days_on_site <= 2:
            score += 12
            reasons.append("swieza oferta")
        elif days_on_site <= 7:
            score += 6
            reasons.append("relatywnie swieza oferta")

    initial_price = target.get("initial_price_pln")
    if initial_price and price_pln < initial_price:
        drop_ratio = (initial_price - price_pln) / initial_price
        drop_bonus = min(15, int(drop_ratio * 100))
        score += drop_bonus
        reasons.append(f"spadek ceny od pierwszej obserwacji: {drop_ratio:.0%}")

    price_change_count = target.get("price_change_count") or 0
    if price_change_count <= 1:
        score += 4
        reasons.append("niewiele zmian ceny")

    seller_type = target.get("seller_type")
    if seller_type == "private":
        score += PRIVATE_SELLER_BONUS
        reasons.append(f"premia za prywatnego sprzedawce: +{PRIVATE_SELLER_BONUS}")
    elif seller_type == "business":
        score -= BUSINESS_SELLER_PENALTY
        reasons.append(f"lekka kara za oferte firmowa: -{BUSINESS_SELLER_PENALTY}")

    missing_fields = sum(
        value in (None, "")
        for value in [
            target.get("year"),
            target.get("mileage_km"),
            target.get("fuel_type"),
            target.get("gearbox"),
            target.get("power_hp") or target.get("engine_cm3"),
        ]
    )
    if missing_fields:
        penalty = missing_fields * 6
        score -= penalty
        reasons.append(f"kara za braki danych: -{penalty}")

    if fallback_level:
        penalty = fallback_level * 5
        score -= penalty
        reasons.append(f"kara za fallback segmentacji: -{penalty}")

    # kara za wykryte uszkodzenie (informacja z list-card / CSV)
    if target.get("is_damaged"):
        score -= DAMAGE_PENALTY
        reasons.append(f"znaleziono informacje o uszkodzeniu oferty: -{DAMAGE_PENALTY}")

    return max(0, min(100, score)), reasons


def _calculate_confidence_score(target: dict[str, Any], group_size: int, fallback_level: int) -> tuple[int, list[str]]:
    score = 100
    reasons: list[str] = []

    if group_size < MIN_COMPARISON_GROUP_SIZE:
        penalty = (MIN_COMPARISON_GROUP_SIZE - group_size) * 12
        score -= penalty
        reasons.append(f"mala grupa porownawcza: -{penalty}")

    if fallback_level:
        base_penalty = fallback_level * 12
        # Duza grupa porownawcza niweluje nieufnosc do fallbacku:
        # przy group_size >= MIN + 30 kara spada do 20% wartosci bazowej.
        size_factor = max(0.2, 1.0 - (group_size - MIN_COMPARISON_GROUP_SIZE) / 30)
        penalty = round(base_penalty * size_factor)
        score -= penalty
        reasons.append(f"nizsze zaufanie przez fallback: -{penalty}")

    missing_fields = sum(
        value in (None, "")
        for value in [
            target.get("year"),
            target.get("mileage_km"),
            target.get("fuel_type"),
            target.get("gearbox"),
            target.get("power_hp") or target.get("engine_cm3"),
        ]
    )
    if missing_fields:
        penalty = missing_fields * 8
        score -= penalty
        reasons.append(f"braki danych do porownania: -{penalty}")

    return max(0, min(100, score)), reasons


def _decision_bucket(final_score: int, hard_filter_passed: bool) -> str:
    if not hard_filter_passed:
        return "ignore"
    if final_score >= 80:
        return "high-priority"
    if final_score >= 60:
        return "candidate"
    if final_score >= 40:
        return "watch"
    return "ignore"


def _apply_enrichment_adjustment(
    base_final_score: int,
    market_score: int,
    enrichment_result: EnrichmentAnalysisResult | None,
) -> int:
    if enrichment_result is None:
        return base_final_score

    delta_from_neutral = enrichment_result.enrichment_score - 50
    scaled_adjustment = round(delta_from_neutral * 0.2 * (enrichment_result.enrichment_confidence / 100))

    # Detail-page signals can penalize weak-quality offers strongly enough to demote them,
    # but they cannot create a top opportunity on their own when market pricing is weak.
    if market_score < 40 and scaled_adjustment > 0:
        scaled_adjustment = 0

    return max(0, min(100, base_final_score + scaled_adjustment))


def analyze_query_csv(query_name: str, csv_file: str) -> list[AnalyticsResult]:
    cars = _read_active_cars(csv_file)
    preferences = load_preferences()
    effective_prefs = get_query_preferences(preferences, query_name)
    source_adjustments = effective_prefs.get("source_adjustments", {})
    results: list[AnalyticsResult] = []

    for car in cars:
        source = str(car.get("source") or "").strip().lower()
        source_config = source_adjustments.get(source, {})
        import_cost_pln = safe_int(source_config.get("import_cost_pln")) or 0
        comparison_group, fallback_level = _build_comparison_group(car, cars)
        market_score, market_reasons = _calculate_market_score(car, comparison_group, fallback_level, import_cost_pln=import_cost_pln)
        confidence_score, confidence_reasons = _calculate_confidence_score(car, len(comparison_group), fallback_level)
        enrichment_result = analyze_listing_details(str(car["listing_id"]), listing_row=car)

        preference_result = evaluate_preferences(car, query_name, preferences)
        hard_filter_passed = bool(preference_result["hard_filter_passed"])
        preference_score = int(preference_result["preference_score"])

        final_score = 0
        if hard_filter_passed:
            base_final_score = round(market_score * 0.7 + preference_score * 0.3)
            final_score = _apply_enrichment_adjustment(base_final_score, market_score, enrichment_result)

        decision_bucket = _decision_bucket(final_score, hard_filter_passed)

        results.append(AnalyticsResult(
            listing_id=str(car["listing_id"]),
            query_name=query_name,
            title=car.get("title"),
            link=car.get("link"),
            price_pln=car.get("price_pln"),
            seller_type=car.get("seller_type"),
            market_score=market_score,
            confidence_score=confidence_score,
            preference_score=preference_score,
            final_score=max(0, min(100, final_score)),
            decision_bucket=decision_bucket,
            hard_filter_passed=hard_filter_passed,
            comparison_group_size=len(comparison_group),
            fallback_level=fallback_level,
            market_reasons=market_reasons + confidence_reasons,
            preference_reasons=list(preference_result["preference_reasons"]),
            enrichment_score=enrichment_result.enrichment_score if enrichment_result else None,
            enrichment_confidence=enrichment_result.enrichment_confidence if enrichment_result else 0,
            enrichment_reasons=list(enrichment_result.enrichment_reasons) if enrichment_result else [],
            enrichment_flags=list(enrichment_result.enrichment_flags) if enrichment_result else [],
        ))

    return sorted(results, key=lambda result: result.final_score, reverse=True)


def save_query_analysis(query_name: str, csv_file: str) -> tuple[str, list[AnalyticsResult]]:
    results = analyze_query_csv(query_name, csv_file)
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

    output_path = ANALYTICS_DIR / f"{Path(csv_file).stem}-analysis.json"
    serialized_results = [asdict(result) for result in results]

    with open(output_path, "w", encoding="utf-8") as file_handle:
        json.dump(serialized_results, file_handle, ensure_ascii=False, indent=2)

    return str(output_path), results