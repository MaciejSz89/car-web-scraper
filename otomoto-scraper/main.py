from __future__ import annotations

import argparse
import logging

from analytics import save_query_analysis
from notifications import run as run_notifications_pipeline
from enrichment_worker import run as run_enrichment_worker
from scraper import get_html_pages
from parser import get_cars_from_content
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

    print(f"\n=== Kwerenda: {query_name} ===")

    html_pages = get_html_pages(
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
        session_state_file=SESSION_STATE_FILE,
    )

    cars_by_id: dict[str, dict] = {}
    pages_with_results = 0

    for page_number, html in enumerate(html_pages, start=1):
        print(f"\nParsuję stronę {page_number}/{len(html_pages)}")
        page_cars = get_cars_from_content(html)

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
        "--run-notifications",
        action="store_true",
        help="Po zakończeniu analityki uruchom warstwę powiadomień i zapisz eventy.",
    )

    args = parser.parse_args()

    # configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    chosen_headless = args.headless if args.headless is not None else HEADLESS

    failed_queries: list[str] = []

    if args.dry_run:
        logging.info("DRY RUN: nie będą pobierane strony, tylko pokazany plan kwerend")
        for query in QUERIES:
            logging.info("Kwerenda: %s -> %s (max_pages=%s)", query.get("name"), query.get("start_url"), query.get("max_pages"))
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

    if args.run_enrichment:
        try:
            enrichment_results = run_enrichment_worker(
                retry_failed=args.retry_failed_enrichment,
                limit=args.enrichment_limit,
            )
            logging.info(
                "Enrichment worker zakończył się przetworzeniem %d wpisów.",
                len(enrichment_results),
            )
            rerun_analytics_for_all_queries()
        except Exception:
            logging.exception("Enrichment worker nie powiódł się")

    if args.run_notifications:
        try:
            notification_results = run_notifications_pipeline()
            logging.info(
                "Warstwa powiadomien zapisala %d eventow.",
                len(notification_results),
            )
        except Exception:
            logging.exception("Warstwa powiadomien nie powiodla sie")


if __name__ == "__main__":
    main()