from __future__ import annotations

import argparse
import logging
import time

from analytics import save_query_analysis
from notifications import run as run_notifications_pipeline, retry_failed_notifications
from enrichment_worker import run as run_enrichment_worker, reprocess_details_flags
from llm_worker import run as run_llm_worker
from preferences import load_preferences
from scraper import get_html_pages
from parser import get_cars_from_content
from scrapers.mobile_de import get_html_pages as get_html_pages_mobile_de
from parsers.mobile_de import get_cars_from_content as get_cars_from_content_mobile_de
from storage import upsert_cars_to_csv
from config import (
    QUERIES,
    HEADLESS,
    WAIT_MS,
    NAVIGATION_TIMEOUT_MS,
    MAX_NAVIGATION_RETRIES,
    POST_NAVIGATION_DELAY_RANGE_MS,
    PAGE_BREAK_DELAY_RANGE_MS,
    SCROLL_PAUSE_RANGE_MS,
    SCROLL_STEP_RANGE_PX,
    RETRY_BACKOFF_DELAY_RANGE_MS,
    SESSION_STATE_FILE,
    SESSION_STATE_FILE_MOBILE_DE,
)


def rerun_analytics_for_all_queries() -> None:
    for query in QUERIES:
        query_name = str(query["name"])
        csv_file = str(query["csv_file"])
        try:
            save_query_analysis(query_name, csv_file)
            logging.info("Odswiezono analityke po enrichment dla kwerendy '%s'.", query_name)
        except Exception:
            logging.exception("Ponowna analiza po enrichment nie powiodla sie dla '%s'", query_name)

def process_query(query: dict[str, str | int], headless: bool = HEADLESS) -> None:
    query_name = str(query["name"])
    start_url = str(query["start_url"])
    csv_file = str(query["csv_file"])
    max_pages = int(query["max_pages"])
    source = str(query.get("source", "otomoto"))

    print(f"\n=== Kwerenda: {query_name} ===\n(source={source})")

    if source == "mobile_de":
        _get_pages = get_html_pages_mobile_de
        _parse_cars = get_cars_from_content_mobile_de
        _session_file = SESSION_STATE_FILE_MOBILE_DE
    else:
        _get_pages = get_html_pages
        _parse_cars = get_cars_from_content
        _session_file = SESSION_STATE_FILE

    html_pages = _get_pages(
        start_url=start_url,
        headless=headless,
        wait_ms=WAIT_MS,
        max_pages=max_pages,
        post_navigation_delay_range_ms=POST_NAVIGATION_DELAY_RANGE_MS,
        page_break_delay_range_ms=PAGE_BREAK_DELAY_RANGE_MS,
        scroll_pause_range_ms=SCROLL_PAUSE_RANGE_MS,
        scroll_step_range_px=SCROLL_STEP_RANGE_PX,
        retry_backoff_delay_range_ms=RETRY_BACKOFF_DELAY_RANGE_MS,
        navigation_timeout_ms=NAVIGATION_TIMEOUT_MS,
        max_navigation_retries=MAX_NAVIGATION_RETRIES,
        session_state_file=_session_file,
    )

    cars_by_id: dict[str, dict] = {}
    pages_with_results = 0

    for page_number, html in enumerate(html_pages, start=1):
        print(f"\nParsuję stronę {page_number}/{len(html_pages)}")
        page_cars = _parse_cars(html)

        if page_cars:
            pages_with_results += 1

        for car in page_cars:
            listing_id = car.get("listing_id")
            if listing_id:
                cars_by_id[listing_id] = car

    cars = list(cars_by_id.values())
    new_count, updated_count = upsert_cars_to_csv(cars, csv_file)

    print(f"Kwerenda: {query_name}")
    print(f"Przejrzane strony z wynikami: {pages_with_results}")
    print(f"Unikalne oferty ze wszystkich stron: {len(cars)}")
    print(f"Nowe ogłoszenia: {new_count}")
    print(f"Zaktualizowane ogłoszenia: {updated_count}")
    print(f"Zapisano do pliku: {csv_file}")

    try:
        analysis_path, analysis_results = save_query_analysis(query_name, csv_file)
        top_results = [result for result in analysis_results if result.decision_bucket in {"candidate", "high-priority"}][:3]

        print(f"Zapisano analizę do pliku: {analysis_path}")
        print(f"Oferty oznaczone jako candidate/high-priority: {sum(result.decision_bucket in {'candidate', 'high-priority'} for result in analysis_results)}")

        if top_results:
            print("Top oferty wg analityki:")
            for result in top_results:
                print(
                    f"- {result.listing_id} | final={result.final_score} | market={result.market_score} | "
                    f"confidence={result.confidence_score} | {result.title}"
                )
    except Exception as exc:
        print(f"Analiza kwerendy '{query_name}' nie powiodła się: {exc}")


def _run_once(args: argparse.Namespace, chosen_headless: bool) -> None:
    failed_queries: list[str] = []

    if args.dry_run:
        logging.info("DRY RUN: nie będą pobierane strony, tylko pokazany plan kwerend")
        for query in QUERIES:
            logging.info("Kwerenda: %s -> %s (max_pages=%s)", query.get("name"), query.get("start_url"), query.get("max_pages"))
    elif args.skip_scraping or args.reprocess_details:
        logging.info("--skip-scraping / --reprocess-details: pomijam scraping i enrichment.")
    else:
        for query in QUERIES:
            try:
                process_query(query, headless=chosen_headless)
            except Exception as exc:
                query_name = str(query["name"])
                failed_queries.append(query_name)
                logging.exception("Błąd w kwerendzie '%s'", query_name)

        logging.info(
            "Zakończono przetwarzanie kwerend: %d/%d sukcesów.",
            len(QUERIES) - len(failed_queries),
            len(QUERIES),
        )

        if failed_queries:
            logging.warning("Nieudane kwerendy:")
            for query_name in failed_queries:
                logging.warning("- %s", query_name)

    if args.run_enrichment and not args.dry_run and not args.skip_scraping:
        try:
            _prefs = load_preferences()
            _enrichment_cfg = _prefs.get("enrichment") or {}
            _allowed_raw = _enrichment_cfg.get("allowed_buckets")
            _allowed_buckets: frozenset[str] | None = (
                frozenset(str(b).strip().lower() for b in _allowed_raw if b)
                if isinstance(_allowed_raw, list)
                else None
            )
            enrichment_results = run_enrichment_worker(
                retry_failed=args.retry_failed_enrichment,
                limit=args.enrichment_limit,
                allowed_buckets=_allowed_buckets,
            )
            logging.info(
                "Enrichment worker zakończył się przetworzeniem %d wpisów.",
                len(enrichment_results),
            )
            rerun_analytics_for_all_queries()
        except Exception:
            logging.exception("Enrichment worker nie powiódł się")

    if args.run_llm and not args.dry_run:
        try:
            llm_results = run_llm_worker(
                model=args.llm_model,
                limit=args.llm_limit,
            )
            logging.info(
                "LLM review zakończył się oceną %d ofert.",
                len(llm_results),
            )
        except Exception:
            logging.exception("LLM review nie powiodło się")

    if args.run_notifications and not args.dry_run:
        try:
            notification_results = run_notifications_pipeline()
            logging.info(
                "Warstwa powiadomien zapisala %d eventow.",
                len(notification_results),
            )
        except Exception:
            logging.exception("Warstwa powiadomien nie powiodla sie")

    if args.retry_failed_notifications:
        try:
            retry_results = retry_failed_notifications()
            logging.info(
                "Retry powiadomień: %d wpisów przetworzonych.",
                len(retry_results),
            )
        except Exception:
            logging.exception("Retry powiadomień nie powiódł się")

    if args.reprocess_details:
        try:
            counts = reprocess_details_flags()
            logging.info(
                "reprocess-details: zaktualizowano %d wierszy, pominięto %d, brak JSON %d, błędy %d.",
                counts["updated"], counts["skipped"], counts["missing_json"], counts["errors"],
            )
            print(
                f"reprocess-details: updated={counts['updated']}, skipped={counts['skipped']}, "
                f"missing_json={counts['missing_json']}, errors={counts['errors']}"
            )
            rerun_analytics_for_all_queries()
        except Exception:
            logging.exception("reprocess-details nie powiodło się")


def main() -> None:
    parser = argparse.ArgumentParser(description="Otomoto scraper")
    parser.add_argument(
        "--headless",
        dest="headless",
        action="store_true",
        help="Uruchom przeglądarkę w trybie headless (nadpisuje config).",
    )
    parser.add_argument(
        "--no-headless",
        dest="headless",
        action="store_false",
        help="Uruchom przeglądarkę w trybie okienkowym (nadpisuje config).",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Włącz verbose logging (DEBUG)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Wyświetl plan kwerend bez pobierania stron ani zapisu.",
    )
    parser.add_argument(
        "--skip-scraping",
        action="store_true",
        help="Pomiń scraping i enrichment; uruchom tylko dalsze etapy (LLM, notyfikacje).",
    )
    parser.add_argument(
        "--run-enrichment",
        action="store_true",
        help="Po zakończeniu scrapingu uruchom enrichment worker dla kolejki ofert.",
    )
    parser.add_argument(
        "--retry-failed-enrichment",
        action="store_true",
        help="Przy --run-enrichment ponów także wpisy wcześniej oznaczone jako failed.",
    )
    parser.add_argument(
        "--enrichment-limit",
        type=int,
        default=None,
        metavar="N",
        help="Ogranicz liczbę pozycji przetwarzanych przez enrichment worker w jednym uruchomieniu.",
    )
    parser.add_argument(
        "--run-llm",
        action="store_true",
        help="Po enrichmencie uruchom warstwę LLM review dla wybranych kandydatów.",
    )
    parser.add_argument(
        "--llm-limit",
        type=int,
        default=None,
        metavar="N",
        help="Ogranicz liczbę ofert wysyłanych do LLM w jednym uruchomieniu.",
    )
    parser.add_argument(
        "--llm-model",
        default=None,
        help="Model OpenAI (nadpisuje wartość z preferences).",
    )
    parser.add_argument(
        "--run-notifications",
        action="store_true",
        help="Po zakończeniu analityki uruchom warstwę powiadomień i zapisz eventy.",
    )
    parser.add_argument(
        "--retry-failed-notifications",
        action="store_true",
        help="Ponowić wysyłkę powiadomień oznaczonych jako failed w notification_history.csv.",
    )
    parser.add_argument(
        "--reprocess-details",
        action="store_true",
        help="Przetworz ponownie istniejące pliki JSON z dysku i popraw flagi damaged/imported w CSV (bez pobierania).",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Uruchamiaj cykl scrapowania w pętli do czasu przerwania przez Ctrl+C.",
    )
    parser.add_argument(
        "--loop-interval",
        type=int,
        default=1800,
        metavar="SEC",
        help="Przerwa między iteracjami pętli w sekundach (domyślnie: 1800 = 30 min).",
    )

    args = parser.parse_args()

    # configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    chosen_headless = args.headless if args.headless is not None else HEADLESS

    if args.loop:
        logging.info("Tryb pętli: interwał %d s. Przerwij Ctrl+C aby zatrzymać.", args.loop_interval)
        iteration = 0
        while True:
            iteration += 1
            logging.info("--- Pętla: iteracja %d ---", iteration)
            try:
                _run_once(args, chosen_headless)
            except KeyboardInterrupt:
                raise
            except Exception:
                logging.exception("Nieoczekiwany błąd w iteracji %d, kontynuuję pętlę.", iteration)
            logging.info("Następna iteracja za %d s. Ctrl+C aby przerwać.", args.loop_interval)
            try:
                time.sleep(args.loop_interval)
            except KeyboardInterrupt:
                raise
    else:
        _run_once(args, chosen_headless)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Przerwano przez użytkownika (Ctrl+C).")
