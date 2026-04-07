from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from config import PREFERENCES_EXAMPLE_FILE, PREFERENCES_FILE
from utils import safe_int


JsonDict = dict[str, Any]


def _load_json_dict(file_path: str) -> JsonDict:
    with open(file_path, "r", encoding="utf-8") as file_handle:
        data = json.load(file_handle)

    if not isinstance(data, dict):
        raise ValueError(f"Plik {file_path} musi zawierać obiekt JSON.")

    return data


def _merge_dicts(base: JsonDict, override: JsonDict) -> JsonDict:
    merged = deepcopy(base)

    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = deepcopy(value)

    return merged


def load_preferences() -> JsonDict:
    preferences_source = PREFERENCES_FILE if PREFERENCES_FILE.exists() else PREFERENCES_EXAMPLE_FILE
    return _load_json_dict(str(preferences_source))


def get_query_preferences(preferences: JsonDict, query_name: str) -> JsonDict:
    global_preferences = preferences.get("global", {})
    query_preferences = preferences.get("queries", {}).get(query_name, {})
    if not isinstance(global_preferences, dict) or not isinstance(query_preferences, dict):
        raise ValueError("Nieprawidłowa struktura preferencji globalnych albo preferencji kwerendy.")

    return _merge_dicts(global_preferences, query_preferences)


def evaluate_preferences(car: JsonDict, query_name: str, preferences: JsonDict) -> JsonDict:
    effective_preferences = get_query_preferences(preferences, query_name)
    hard_filters = effective_preferences.get("hard_filters", {})
    soft_preferences = effective_preferences.get("soft_preferences", {})

    reasons: list[str] = []
    hard_filter_passed = True

    price_pln = safe_int(car.get("price_pln"))
    mileage_km = safe_int(car.get("mileage_km"))
    year = safe_int(car.get("year"))
    engine_cm3 = safe_int(car.get("engine_cm3"))
    power_hp = safe_int(car.get("power_hp"))
    fuel_type = car.get("fuel_type")
    gearbox = car.get("gearbox")

    def fail_filter(reason: str) -> None:
        nonlocal hard_filter_passed
        hard_filter_passed = False
        reasons.append(reason)

    max_price_pln = safe_int(hard_filters.get("max_price_pln"))
    if max_price_pln is not None and price_pln is not None and price_pln > max_price_pln:
        fail_filter(f"cena powyzej limitu preferencji ({price_pln} > {max_price_pln})")

    max_mileage_km = safe_int(hard_filters.get("max_mileage_km"))
    if max_mileage_km is not None and mileage_km is not None and mileage_km > max_mileage_km:
        fail_filter(f"przebieg powyzej limitu preferencji ({mileage_km} > {max_mileage_km})")

    min_year = safe_int(hard_filters.get("min_year"))
    if min_year is not None and year is not None and year < min_year:
        fail_filter(f"rocznik ponizej limitu preferencji ({year} < {min_year})")

    min_engine_cm3 = safe_int(hard_filters.get("min_engine_cm3"))
    if min_engine_cm3 is not None and engine_cm3 is not None and engine_cm3 < min_engine_cm3:
        fail_filter(f"pojemnosc ponizej limitu preferencji ({engine_cm3} < {min_engine_cm3})")

    min_power_hp = safe_int(hard_filters.get("min_power_hp"))
    if min_power_hp is not None and power_hp is not None and power_hp < min_power_hp:
        fail_filter(f"moc ponizej limitu preferencji ({power_hp} < {min_power_hp})")

    allowed_fuel_types = hard_filters.get("fuel_types")
    if isinstance(allowed_fuel_types, list) and fuel_type and fuel_type not in allowed_fuel_types:
        fail_filter(f"paliwo poza preferowanym zakresem ({fuel_type})")

    allowed_gearboxes = hard_filters.get("gearboxes")
    if isinstance(allowed_gearboxes, list) and gearbox and gearbox not in allowed_gearboxes:
        fail_filter(f"skrzynia poza preferowanym zakresem ({gearbox})")

    if not hard_filter_passed:
        return {
            "hard_filter_passed": False,
            "preference_score": 0,
            "preference_reasons": reasons,
            "applied_preference_profile": preferences.get("profile_name", "default"),
        }

    score = 50

    preferred_gearboxes = soft_preferences.get("preferred_gearboxes", {})
    if gearbox in preferred_gearboxes:
        delta = safe_int(preferred_gearboxes.get(gearbox)) or 0
        score += delta
        reasons.append(f"preferowana skrzynia: {gearbox} ({delta:+d})")

    preferred_fuel_types = soft_preferences.get("preferred_fuel_types", {})
    if fuel_type in preferred_fuel_types:
        delta = safe_int(preferred_fuel_types.get(fuel_type)) or 0
        score += delta
        reasons.append(f"preferowane paliwo: {fuel_type} ({delta:+d})")

    year_boost = soft_preferences.get("year_boost")
    if isinstance(year_boost, dict):
        year_threshold = safe_int(year_boost.get("min_year"))
        year_score = safe_int(year_boost.get("score")) or 0
        if year_threshold is not None and year is not None and year >= year_threshold:
            score += year_score
            reasons.append(f"premia za rocznik >= {year_threshold} ({year_score:+d})")

    low_mileage_boost = soft_preferences.get("low_mileage_boost")
    if isinstance(low_mileage_boost, dict):
        max_mileage = safe_int(low_mileage_boost.get("max_mileage_km"))
        mileage_score = safe_int(low_mileage_boost.get("score")) or 0
        if max_mileage is not None and mileage_km is not None and mileage_km <= max_mileage:
            score += mileage_score
            reasons.append(f"premia za niski przebieg <= {max_mileage} ({mileage_score:+d})")

    high_mileage_penalty = soft_preferences.get("high_mileage_penalty")
    if isinstance(high_mileage_penalty, dict):
        min_mileage = safe_int(high_mileage_penalty.get("min_mileage_km"))
        mileage_score = safe_int(high_mileage_penalty.get("score")) or 0
        if min_mileage is not None and mileage_km is not None and mileage_km >= min_mileage:
            score += mileage_score
            reasons.append(f"kara za wysoki przebieg >= {min_mileage} ({mileage_score:+d})")

    preferred_engine_ranges = soft_preferences.get("preferred_engine_cm3_ranges")
    if isinstance(preferred_engine_ranges, list) and engine_cm3 is not None:
        for engine_range in preferred_engine_ranges:
            if not isinstance(engine_range, dict):
                continue

            range_min = safe_int(engine_range.get("min"))
            range_max = safe_int(engine_range.get("max"))
            range_score = safe_int(engine_range.get("score")) or 0

            if range_min is None or range_max is None:
                continue

            if range_min <= engine_cm3 <= range_max:
                score += range_score
                reasons.append(f"preferowana pojemnosc {range_min}-{range_max} cm3 ({range_score:+d})")
                break

    return {
        "hard_filter_passed": True,
        "preference_score": max(0, min(100, score)),
        "preference_reasons": reasons,
        "applied_preference_profile": preferences.get("profile_name", "default"),
    }