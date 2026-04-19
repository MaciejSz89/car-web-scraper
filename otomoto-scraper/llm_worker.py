from __future__ import annotations

import argparse
import csv
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from bs4 import BeautifulSoup
from openai import OpenAI, RateLimitError

from config import DATA_DIR
from preferences import load_preferences
from utils import clean_text, safe_int


DEFAULT_LLM_MODEL = "gpt-4o-mini"
DEFAULT_MAX_TOKENS = 800
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_CANDIDATES_PER_RUN = 5
DEFAULT_LLM_COOLDOWN_DAYS = 30
DEFAULT_MIN_FINAL_SCORE = 60
DEFAULT_ALLOWED_BUCKETS = {"high-priority", "candidate"}

# Bezwzględny limit — nie może być przekroczony niezależnie od konfiguracji
HARD_MAX_CANDIDATES = 20

LLM_CSV_FIELDS = [
    "llm_verdict",
    "llm_risk_level",
    "llm_confidence",
    "llm_summary",
    "llm_reasons",
    "llm_reviewed_at",
]

logger = logging.getLogger(__name__)


# ── CLI ──────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LLM review on enriched listings.")
    parser.add_argument("--data-dir", default=None, help="Directory with storage CSVs.")
    parser.add_argument("--details-dir", default=None, help="Directory with sidecar JSON files.")
    parser.add_argument(
        "--model",
        default=None,
        help="OpenAI model name (overrides preferences).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max candidates to review per run (overrides preferences).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show candidates without calling the LLM API.",
    )
    return parser.parse_args()


# ── Config ───────────────────────────────────────────────────────────────────


def load_llm_config(preferences: dict[str, Any]) -> dict[str, Any]:
    raw = preferences.get("llm")
    return raw if isinstance(raw, dict) else {}


def resolve_openai_client(llm_config: dict[str, Any]) -> OpenAI:
    api_key_env = str(llm_config.get("api_key_env") or "OPENAI_API_KEY")
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise EnvironmentError(
            f"Brak klucza API OpenAI. Ustaw zmienną środowiskową '{api_key_env}'."
        )
    return OpenAI(api_key=api_key)


# ── CSV helpers ──────────────────────────────────────────────────────────────


def _read_csv_rows(csv_file: str) -> tuple[list[str], list[dict[str, str]]]:
    with open(csv_file, "r", newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    return fieldnames, rows


def _write_csv_rows(csv_file: str, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with open(csv_file, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)


def update_listing_llm_result(
    csv_file: str,
    listing_id: str,
    *,
    verdict: str,
    risk_level: str,
    confidence: int,
    summary: str,
    reasons: list[str],
    reviewed_at: str,
) -> bool:
    if not os.path.exists(csv_file):
        return False

    fieldnames, rows = _read_csv_rows(csv_file)
    for field in LLM_CSV_FIELDS:
        if field not in fieldnames:
            fieldnames.append(field)

    updated = False
    for row in rows:
        if row.get("listing_id") != listing_id:
            continue
        row["llm_verdict"] = verdict
        row["llm_risk_level"] = risk_level
        row["llm_confidence"] = str(confidence)
        row["llm_summary"] = summary
        row["llm_reasons"] = "|".join(reasons)
        row["llm_reviewed_at"] = reviewed_at
        updated = True
        break

    if updated:
        _write_csv_rows(csv_file, fieldnames, rows)

    return updated


# ── Analytics index ──────────────────────────────────────────────────────────


def _load_analytics_index(analytics_dir: str, source_csv: str) -> dict[str, dict[str, Any]]:
    stem, _ = os.path.splitext(source_csv)
    analytics_file = os.path.join(analytics_dir, f"{stem}-analysis.json")
    if not os.path.exists(analytics_file):
        return {}
    try:
        with open(analytics_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, list):
        return {}
    return {
        str(item.get("listing_id") or ""): item
        for item in data
        if isinstance(item, dict) and item.get("listing_id")
    }


def _parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


# ── Candidate selection ──────────────────────────────────────────────────────


def _load_detail_payload(details_dir: str, listing_id: str) -> dict[str, Any] | None:
    path = os.path.join(details_dir, f"{listing_id}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def select_candidates(
    data_dir: str,
    details_dir: str,
    *,
    allowed_buckets: set[str],
    min_final_score: int = DEFAULT_MIN_FINAL_SCORE,
    cooldown_days: int = DEFAULT_LLM_COOLDOWN_DAYS,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    analytics_dir = os.path.join(data_dir, "analytics")
    candidates: list[dict[str, Any]] = []

    for file_name in os.listdir(data_dir):
        if not file_name.endswith(".csv") or file_name == "enrichment_queue.csv":
            continue
        csv_file = os.path.join(data_dir, file_name)
        try:
            _, rows = _read_csv_rows(csv_file)
        except Exception:
            continue

        analytics_index = _load_analytics_index(analytics_dir, file_name)

        for row in rows:
            if (row.get("details_status") or "").strip().lower() != "fetched":
                continue
            if (row.get("llm_verdict") or "").strip():
                continue  # already reviewed

            listing_id = str(row.get("listing_id") or "").strip()
            if not listing_id:
                continue

            analytics = analytics_index.get(listing_id) or {}
            bucket = str(analytics.get("decision_bucket") or "").strip().lower()
            if bucket not in allowed_buckets:
                continue

            detail_payload = _load_detail_payload(details_dir, listing_id)
            if detail_payload is None:
                continue

            final_score = safe_int(str(analytics.get("final_score") or 0)) or 0
            if final_score < min_final_score:
                continue

            reviewed_at_raw = row.get("llm_reviewed_at")
            if reviewed_at_raw and cooldown_days > 0:
                reviewed_ts = _parse_iso_timestamp(reviewed_at_raw)
                if reviewed_ts and datetime.now(timezone.utc) - reviewed_ts < timedelta(days=cooldown_days):
                    continue

            candidates.append({
                "listing_id": listing_id,
                "csv_file": csv_file,
                "source_csv": file_name,
                "listing_row": row,
                "analytics": analytics,
                "detail_payload": detail_payload,
            })

    candidates.sort(
        key=lambda c: safe_int(str(c["analytics"].get("final_score") or 0)) or 0,
        reverse=True,
    )

    if limit is not None:
        candidates = candidates[:limit]

    return candidates


# ── Prompt builder ────────────────────────────────────────────────────────────


def _strip_html(html: str | None) -> str:
    if not html:
        return ""
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return clean_text(text) or ""


def _truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."


def build_prompt(
    listing_row: dict[str, str],
    detail_payload: dict[str, Any] | None,
    analytics: dict[str, Any],
) -> str:
    detail = detail_payload or {}
    equipment: list[str] = detail.get("equipment") if isinstance(detail.get("equipment"), list) else []
    description = _truncate(_strip_html(detail.get("description")), 1000)
    equipment_text = ", ".join(equipment[:30]) if equipment else "brak danych"

    enrichment_flags = str(listing_row.get("details_enrichment_flags") or "brak")

    # --- damage ---
    is_damaged_raw = str(listing_row.get("is_damaged") or "0").strip()
    details_damaged_flag = str(listing_row.get("details_damaged_flag") or "").strip()
    # also read directly from sidecar payload (handles stale CSV from pre-REQ-054 enrichments)
    payload_params = detail.get("parameters") if isinstance(detail.get("parameters"), dict) else {}
    payload_damaged_raw = payload_params.get("damaged")
    payload_damaged_truthy = (
        payload_damaged_raw not in (None, "", [], {})
        and str(payload_damaged_raw).strip().lower() not in {"0", "false", "no", "nie"}
    )
    damage_status = "brak sygnałów uszkodzenia"
    if is_damaged_raw in ("1", "true") or details_damaged_flag.lower() in ("true", "1", "yes") or payload_damaged_truthy:
        damage_status = "UWAGA: oferta oznaczona jako uszkodzona (oceń czy uszkodzenie jest drobne/naprawialne czy dyskwalifikujące)"

    # --- import / country of origin ---
    imported_flag_raw = str(listing_row.get("details_imported_flag") or "0").strip()
    country_origin_val = str(listing_row.get("details_country_origin") or "").strip()
    # also read directly from sidecar payload
    payload_imported_raw = payload_params.get("is_imported_car")
    payload_imported_truthy = (
        payload_imported_raw not in (None, "", [], {})
        and str(payload_imported_raw).strip().lower() not in {"0", "false", "no", "nie"}
    )
    if not country_origin_val:
        payload_country = str(payload_params.get("country_origin") or "").strip()
        if payload_country and payload_country.lower() != "country_origin":
            country_origin_val = payload_country
    if imported_flag_raw in ("1", "true") or payload_imported_truthy or country_origin_val:
        import_parts = ["pojazd importowany"]
        if country_origin_val:
            import_parts.append(f"kraj: {country_origin_val}")
        import_status = "UWAGA: " + "; ".join(import_parts)
        import_status += " — zweryfikuj homologację na rynek UE, historię pojazdu, rzeczywisty przebieg (przeliczenie mil→km) i potencjalne koszty celne/napraw"
    else:
        import_status = "brak flag importu"

    market_reasons_raw = analytics.get("market_reasons") or []
    if isinstance(market_reasons_raw, list):
        market_reasons = "; ".join(str(r) for r in market_reasons_raw[:8])
    else:
        market_reasons = str(market_reasons_raw)

    enrichment_reasons_raw = analytics.get("enrichment_reasons") or []
    if isinstance(enrichment_reasons_raw, list):
        enrichment_reasons = "; ".join(str(r) for r in enrichment_reasons_raw[:8])
    else:
        enrichment_reasons = str(enrichment_reasons_raw)

    lines = [
        "Oceń ogłoszenie sprzedaży samochodu w Polsce. Identyfikuj sygnały ryzyka i sygnały pozytywne.",
        "",
        "## Dane ogłoszenia",
        f"- Tytuł: {listing_row.get('title') or 'brak'}",
        f"- Cena: {listing_row.get('price_pln') or 'brak'} PLN",
        f"- Rocznik: {listing_row.get('year') or 'brak'}",
        f"- Przebieg: {listing_row.get('mileage_km') or 'brak'} km",
        f"- Paliwo: {listing_row.get('fuel_type') or 'brak'}",
        f"- Skrzynia: {listing_row.get('gearbox') or 'brak'}",
        f"- Moc: {listing_row.get('power_hp') or 'brak'} KM",
        f"- Typ sprzedawcy: {listing_row.get('seller_type') or 'brak'}",
        "",
        "## Wynik analityczny",
        f"- Score końcowy: {analytics.get('final_score') or 'brak'}/100",
        f"- Bucket decyzyjny: {analytics.get('decision_bucket') or 'brak'}",
        f"- Score rynkowy: {analytics.get('market_score') or 'brak'}/100",
        f"- Powody rynkowe: {market_reasons or 'brak'}",
        f"- Powody enrichment: {enrichment_reasons or 'brak'}",
        "",
        "## Flagi automatyczne (wykryte regułami)",
        enrichment_flags,
        "",
        f"## Stan uszkodzenia",
        damage_status,
        "",
        "## Import i kraj pochodzenia",
        import_status,
        "",
        "## Opis ogłoszenia",
        description or "brak opisu",
        "",
        "## Wyposażenie",
        equipment_text,
        "",
        "Odpowiedz WYŁĄCZNIE poprawnym obiektem JSON (bez markdown, bez żadnych dodatkowych znaków).",
        "Format odpowiedzi:",
        '{"verdict":"approve|review|reject","risk_level":"low|medium|high","confidence":<0-100>,"summary":"jedno zdanie po polsku z najważniejszym wnioskiem","reasons":["powód 1","powód 2"]}',
        "",
        "Zasady:",
        '- "approve": solidne sygnały pozytywne, brak istotnych ryzyk',
        '- "review": wymaga weryfikacji (oględziny, sprawdzenie historii)',
        '- "reject": istotne ryzyka, mylące ogłoszenie lub deklarowane uszkodzenia',
        "- Nie awansuj do approve wyłącznie ze względu na korzystną cenę",
        "- Bądź zwięzły i konkretny w reasons (max 5 powodów)",
    ]

    return "\n".join(lines)


# ── LLM call ─────────────────────────────────────────────────────────────────


def call_llm(
    prompt: str,
    *,
    client: OpenAI,
    model: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
) -> dict[str, Any]:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Jesteś asystentem analizującym ogłoszenia sprzedaży samochodów w Polsce. "
                    "Odpowiadasz WYŁĄCZNIE poprawnym obiektem JSON bez żadnych dodatkowych znaków."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or "{}"
    return json.loads(raw)


def _parse_llm_response(raw: dict[str, Any]) -> tuple[str, str, int, str, list[str]]:
    verdict = str(raw.get("verdict") or "review").strip().lower()
    if verdict not in {"approve", "review", "reject"}:
        verdict = "review"

    risk_level = str(raw.get("risk_level") or "medium").strip().lower()
    if risk_level not in {"low", "medium", "high"}:
        risk_level = "medium"

    confidence = safe_int(str(raw.get("confidence") or 50)) or 50
    confidence = max(0, min(100, confidence))

    summary = clean_text(str(raw.get("summary") or "")) or ""

    raw_reasons = raw.get("reasons") or []
    reasons: list[str] = []
    if isinstance(raw_reasons, list):
        for r in raw_reasons:
            cleaned = clean_text(str(r)) if r else None
            if cleaned:
                reasons.append(cleaned)

    return verdict, risk_level, confidence, summary, reasons


# ── Main run ──────────────────────────────────────────────────────────────────


def run(
    data_dir: str | None = None,
    details_dir: str | None = None,
    *,
    model: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    preferences: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    resolved_data_dir = data_dir or str(DATA_DIR)
    resolved_details_dir = details_dir or os.path.join(resolved_data_dir, "details")

    prefs = preferences or load_preferences()
    llm_config = load_llm_config(prefs)

    resolved_model = model or str(llm_config.get("model") or DEFAULT_LLM_MODEL)
    max_tokens = safe_int(str(llm_config.get("max_tokens") or DEFAULT_MAX_TOKENS)) or DEFAULT_MAX_TOKENS
    temperature = float(llm_config.get("temperature") or DEFAULT_TEMPERATURE)
    config_limit = safe_int(str(llm_config.get("max_candidates_per_run") or DEFAULT_MAX_CANDIDATES_PER_RUN))
    resolved_limit = limit if limit is not None else config_limit
    if resolved_limit is None or resolved_limit > HARD_MAX_CANDIDATES:
        if resolved_limit is not None and resolved_limit > HARD_MAX_CANDIDATES:
            logger.warning(
                "LLM: limit %d przekracza hard cap %d; ograniczono do %d.",
                resolved_limit,
                HARD_MAX_CANDIDATES,
                HARD_MAX_CANDIDATES,
            )
        resolved_limit = HARD_MAX_CANDIDATES

    min_final_score = safe_int(str(llm_config.get("min_final_score") or DEFAULT_MIN_FINAL_SCORE)) or DEFAULT_MIN_FINAL_SCORE
    cooldown_days = safe_int(str(llm_config.get("llm_cooldown_days") or DEFAULT_LLM_COOLDOWN_DAYS)) or DEFAULT_LLM_COOLDOWN_DAYS

    allowed_buckets_raw: list[str] = llm_config.get("allowed_buckets") or list(DEFAULT_ALLOWED_BUCKETS)
    allowed_buckets = {b.lower() for b in allowed_buckets_raw}

    candidates = select_candidates(
        resolved_data_dir,
        resolved_details_dir,
        allowed_buckets=allowed_buckets,
        min_final_score=min_final_score,
        cooldown_days=cooldown_days,
        limit=resolved_limit,
    )

    logger.info("LLM: %d kandydatów do oceny (model=%s).", len(candidates), resolved_model)

    if not candidates:
        print("LLM review: brak kandydatów do oceny.")
        return []

    if dry_run:
        print(f"LLM review [dry-run]: {len(candidates)} kandydatów")
        for c in candidates:
            row = c["listing_row"]
            analytics = c["analytics"]
            print(
                f"  - {c['listing_id']} | {row.get('title') or ''} | "
                f"score={analytics.get('final_score')} | bucket={analytics.get('decision_bucket')}"
            )
        return []

    client = resolve_openai_client(llm_config)

    results: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates, start=1):
        listing_id = candidate["listing_id"]
        csv_file = candidate["csv_file"]
        listing_row = candidate["listing_row"]
        analytics = candidate["analytics"]
        detail_payload = candidate["detail_payload"]
        reviewed_at = datetime.now(timezone.utc).isoformat()

        logger.info("LLM [%d/%d] listing_id=%s", index, len(candidates), listing_id)

        try:
            prompt = build_prompt(listing_row, detail_payload, analytics)
            raw_response = call_llm(
                prompt,
                client=client,
                model=resolved_model,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            verdict, risk_level, confidence, summary, reasons = _parse_llm_response(raw_response)
            update_listing_llm_result(
                csv_file,
                listing_id,
                verdict=verdict,
                risk_level=risk_level,
                confidence=confidence,
                summary=summary,
                reasons=reasons,
                reviewed_at=reviewed_at,
            )
            results.append({
                "listing_id": listing_id,
                "status": "reviewed",
                "verdict": verdict,
                "risk_level": risk_level,
                "confidence": confidence,
                "source_csv": candidate["source_csv"],
            })
            logger.info(
                "LLM result: listing_id=%s verdict=%s risk=%s confidence=%d",
                listing_id,
                verdict,
                risk_level,
                confidence,
            )
        except RateLimitError as exc:
            logger.error(
                "LLM: rate limit API — przerywam przebieg. Szczegóły: %s", exc
            )
            results.append({
                "listing_id": listing_id,
                "status": "aborted",
                "reason": f"rate_limit: {exc}",
            })
            break
        except json.JSONDecodeError as exc:
            logger.error(
                "LLM: niepoprawny JSON w odpowiedzi dla listing_id=%s: %s",
                listing_id,
                exc,
            )
            results.append({
                "listing_id": listing_id,
                "status": "failed",
                "reason": f"json_decode_error: {exc}",
            })
        except Exception as exc:
            logger.error("LLM: błąd dla listing_id=%s: %s", listing_id, exc)
            results.append({
                "listing_id": listing_id,
                "status": "failed",
                "reason": str(exc),
            })

    reviewed = sum(r.get("status") == "reviewed" for r in results)
    failed = sum(r.get("status") == "failed" for r in results)
    aborted = sum(r.get("status") == "aborted" for r in results)
    print(f"LLM review processed {len(results)} items: {reviewed} reviewed, {failed} failed, {aborted} aborted.")

    return results


# ── On-demand single review ───────────────────────────────────────────────────


@dataclass(slots=True)
class OnDemandSession:
    """Shared LLM client + counter for on-demand reviews within one pipeline run."""

    client: OpenAI
    model: str
    max_tokens: int
    temperature: float
    limit: int
    calls_made: int = 0

    @property
    def budget_exhausted(self) -> bool:
        return self.calls_made >= self.limit


def create_on_demand_session(llm_config: dict[str, Any], *, limit: int) -> OnDemandSession:
    """Build an ``OnDemandSession`` from a loaded llm_config dict."""
    client = resolve_openai_client(llm_config)
    model = str(llm_config.get("model") or DEFAULT_LLM_MODEL)
    max_tokens = safe_int(str(llm_config.get("max_tokens") or DEFAULT_MAX_TOKENS)) or DEFAULT_MAX_TOKENS
    temperature = float(llm_config.get("temperature") or DEFAULT_TEMPERATURE)
    return OnDemandSession(
        client=client,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        limit=limit,
    )


def review_single(
    listing_id: str,
    csv_file: str,
    listing_row: dict[str, Any],
    analytics: dict[str, Any],
    detail_payload: dict[str, Any],
    session: OnDemandSession,
) -> dict[str, Any] | None:
    """Review a single listing on-demand and persist the result to *csv_file*.

    Returns a dict with LLM result fields on success, or ``None`` when skipped
    (budget exhausted, rate-limited, or any error).

    Mutates ``session.calls_made`` on success.
    """
    if session.budget_exhausted:
        logger.debug(
            "LLM on-demand: limit %d osiągnięty, pomijam listing_id=%s",
            session.limit,
            listing_id,
        )
        return None

    reviewed_at = datetime.now(timezone.utc).isoformat()
    try:
        prompt = build_prompt(listing_row, detail_payload, analytics)
        raw_response = call_llm(
            prompt,
            client=session.client,
            model=session.model,
            max_tokens=session.max_tokens,
            temperature=session.temperature,
        )
        verdict, risk_level, confidence, summary, reasons = _parse_llm_response(raw_response)
    except RateLimitError as exc:
        logger.warning(
            "LLM on-demand: rate limit — wyłączam dalsze próby: %s", exc
        )
        session.limit = 0  # exhaust budget to skip remaining candidates
        return None
    except json.JSONDecodeError as exc:
        logger.warning(
            "LLM on-demand: niepoprawny JSON dla listing_id=%s: %s", listing_id, exc
        )
        return None
    except Exception as exc:
        logger.warning(
            "LLM on-demand: błąd dla listing_id=%s: %s", listing_id, exc
        )
        return None

    update_listing_llm_result(
        csv_file,
        listing_id,
        verdict=verdict,
        risk_level=risk_level,
        confidence=confidence,
        summary=summary,
        reasons=reasons,
        reviewed_at=reviewed_at,
    )
    session.calls_made += 1
    logger.info(
        "LLM on-demand: listing_id=%s verdict=%s risk=%s confidence=%d (%d/%d)",
        listing_id,
        verdict,
        risk_level,
        confidence,
        session.calls_made,
        session.limit,
    )
    return {
        "llm_verdict": verdict,
        "llm_risk_level": risk_level,
        "llm_confidence": str(confidence),
        "llm_summary": summary,
        "llm_reasons": "|".join(reasons),
        "llm_reviewed_at": reviewed_at,
    }


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run(
        data_dir=args.data_dir,
        details_dir=args.details_dir,
        model=args.model,
        limit=args.limit,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
