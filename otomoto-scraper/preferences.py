from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from config import PREFERENCES_EXAMPLE_FILE, PREFERENCES_FILE
from utils import safe_int


JsonDict = dict[str, Any]

# Kody Otomoto (lowercase) dla krajów UE — bez "pl" (obsługiwany osobno).
# Źródło: wartości pola parametersDict.country_origin na stronie Otomoto.
EU_OTOMOTO_CODES: frozenset[str] = frozenset({
    "a",   # Austria
    "b",   # Belgia
    "bg",  # Bułgaria
    "hr",  # Chorwacja
    "cy",  # Cypr
    "cz",  # Czechy
    "dk",  # Dania
    "est", # Estonia
    "fi",  # Finlandia
    "f",   # Francja
    "gr",  # Grecja
    "hu",  # Węgry
    "ie",  # Irlandia
    "i",   # Włochy
    "lv",  # Łotwa
    "lt",  # Litwa
    "lu",  # Luksemburg
    "mt",  # Malta
    "nl",  # Holandia
    "pt",  # Portugalia
    "ro",  # Rumunia
    "sk",  # Słowacja
    "si",  # Słowenia
    "e",   # Hiszpania
    "s",   # Szwecja
})

# Kody ISO-3166-1 alpha-2 (lowercase) dla krajów UE — używane np. przez mobile.de ("DE").
EU_ISO2_CODES: frozenset[str] = frozenset({
    "at", "be", "bg", "hr", "cy", "cz", "dk", "ee", "fi", "fr",
    "de", "gr", "hu", "ie", "it", "lv", "lt", "lu", "mt", "nl",
    "pt", "ro", "sk", "si", "es", "se",
})

# Polskie nazwy krajów UE (lowercase) — do klasyfikacji wartości zwróconych przez LLM.
EU_COUNTRY_POLISH_NAMES: frozenset[str] = frozenset({
    "austria", "belgia", "bułgaria", "chorwacja", "cypr", "czechy",
    "dania", "estonia", "finlandia", "francja", "grecja", "hiszpania",
    "holandia", "niderlandy", "irlandia", "litwa", "luksemburg",
    "łotwa", "malta", "niemcy", "portugalia", "rumunia",
    "słowacja", "słowenia", "szwecja", "węgry", "włochy",
})


def classify_country_origin(country: str) -> str:
    """Klasyfikuje kraj pochodzenia auta.

    Obsługuje kody Otomoto (np. 'pl', 'd', 'usa'), kody ISO-2 (np. 'DE' z mobile.de)
    oraz polskie nazwy krajów (np. 'Niemcy' zwrócone przez LLM).

    Zwraca: 'poland', 'eu', 'non_eu' lub 'unknown' gdy brak danych.
    """
    normalized = country.strip().lower()
    if not normalized:
        return "unknown"
    # Polska — kod Otomoto lub polska nazwa
    if normalized in ("pl", "polska"):
        return "poland"
    # EU — kody Otomoto
    if normalized in EU_OTOMOTO_CODES:
        return "eu"
    # EU — kody ISO-2 (np. "de" z mobile.de)
    if normalized in EU_ISO2_CODES:
        return "eu"
    # EU — polskie nazwy (ekstrakcja LLM)
    if normalized in EU_COUNTRY_POLISH_NAMES:
        return "eu"
    return "non_eu"


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

    # Konfiguracja specyficzna dla źródła danych (np. mobile_de)
    source_adjustments = effective_preferences.get("source_adjustments", {})
    source = str(car.get("source") or "").strip().lower()
    source_config: JsonDict = source_adjustments.get(source, {})
    import_cost_pln = safe_int(source_config.get("import_cost_pln")) or 0

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
    if max_price_pln is not None and price_pln is not None:
        effective_price_pln = price_pln + import_cost_pln
        if effective_price_pln > max_price_pln:
            suffix = f" + {import_cost_pln} import" if import_cost_pln else ""
            fail_filter(f"efektywna cena powyzej limitu preferencji ({price_pln}{suffix} = {effective_price_pln} > {max_price_pln})")

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

    reliability_bonus = safe_int(source_config.get("reliability_score_bonus")) or 0
    if reliability_bonus:
        score += reliability_bonus
        label = f"+{reliability_bonus}" if reliability_bonus > 0 else str(reliability_bonus)
        reasons.append(f"korekta wiarygodnosci zrodla {source}: {label}")

    origin_scoring_cfg = soft_preferences.get("origin_scoring")
    if isinstance(origin_scoring_cfg, dict):
        country_origin = str(car.get("details_country_origin") or "").strip()
        if country_origin:
            origin_tier = classify_country_origin(country_origin)
            if origin_tier == "poland":
                poland_bonus = safe_int(origin_scoring_cfg.get("poland_bonus")) or 0
                if poland_bonus:
                    score += poland_bonus
                    reasons.append(f"premia za polskie pochodzenie: +{poland_bonus}")
                private_poland_bonus = safe_int(origin_scoring_cfg.get("private_poland_bonus")) or 0
                seller_type_raw = str(car.get("seller_type") or "").strip().lower()
                if private_poland_bonus and seller_type_raw == "private":
                    score += private_poland_bonus
                    reasons.append(f"premia za prywatnego sprzedawce z Polski: +{private_poland_bonus}")
            elif origin_tier == "eu":
                eu_penalty = safe_int(origin_scoring_cfg.get("eu_penalty")) or 0
                if eu_penalty:
                    score += eu_penalty
                    reasons.append(f"korekta za auto z UE (nie-PL) ({country_origin}): {eu_penalty:+d}")
            elif origin_tier == "non_eu":
                non_eu_penalty = safe_int(origin_scoring_cfg.get("non_eu_penalty")) or 0
                if non_eu_penalty:
                    score += non_eu_penalty
                    reasons.append(f"kara za auto spoza UE ({country_origin}): {non_eu_penalty:+d}")

    return {
        "hard_filter_passed": True,
        "preference_score": max(0, min(100, score)),
        "preference_reasons": reasons,
        "applied_preference_profile": preferences.get("profile_name", "default"),
    }