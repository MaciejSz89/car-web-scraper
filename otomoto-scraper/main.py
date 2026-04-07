from __future__ import annotations

from analytics import save_query_analysis
from scraper import get_html_pages
from parser import get_cars_from_content
from storage import upsert_cars_to_csv
from config import (
    QUERIES,
    HEADLESS,
    WAIT_MS,
    MAX_NAVIGATION_RETRIES,
    POST_NAVIGATION_DELAY_RANGE_MS,
    PAGE_BREAK_DELAY_RANGE_MS,
    SCROLL_PAUSE_RANGE_MS,
    SCROLL_STEP_RANGE_PX,
    RETRY_BACKOFF_DELAY_RANGE_MS,
    SESSION_STATE_FILE,
)

def process_query(query: dict[str, str | int]) -> None:
    query_name = str(query["name"])
    start_url = str(query["start_url"])
    csv_file = str(query["csv_file"])
    max_pages = int(query["max_pages"])

    print(f"\n=== Kwerenda: {query_name} ===")

    html_pages = get_html_pages(
        start_url=start_url,
        headless=HEADLESS,
        wait_ms=WAIT_MS,
        max_pages=max_pages,
        post_navigation_delay_range_ms=POST_NAVIGATION_DELAY_RANGE_MS,
        page_break_delay_range_ms=PAGE_BREAK_DELAY_RANGE_MS,
        scroll_pause_range_ms=SCROLL_PAUSE_RANGE_MS,
        scroll_step_range_px=SCROLL_STEP_RANGE_PX,
        retry_backoff_delay_range_ms=RETRY_BACKOFF_DELAY_RANGE_MS,
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
    failed_queries: list[str] = []

    for query in QUERIES:
        try:
            process_query(query)
        except Exception as exc:
            query_name = str(query["name"])
            failed_queries.append(query_name)
            print(f"Błąd w kwerendzie '{query_name}': {exc}")

    print(f"\nZakończono przetwarzanie kwerend: {len(QUERIES) - len(failed_queries)}/{len(QUERIES)} sukcesów.")

    if failed_queries:
        print("Nieudane kwerendy:")
        for query_name in failed_queries:
            print(f"- {query_name}")


if __name__ == "__main__":
    main()