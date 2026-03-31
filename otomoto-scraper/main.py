from __future__ import annotations

from typing import Optional
from scraper import get_html
from parser import get_cars_from_content
from storage import upsert_cars_to_csv
from config import URL, CSV_FILE, HEADLESS, WAIT_MS

def main() -> None:
    html = get_html(URL, headless=HEADLESS, wait_ms=WAIT_MS)
    cars = get_cars_from_content(html)
    new_count, updated_count = upsert_cars_to_csv(cars, CSV_FILE)

    print(f"Znaleziono ofert na stronie: {len(cars)}")
    print(f"Nowe ogłoszenia: {new_count}")
    print(f"Zaktualizowane ogłoszenia: {updated_count}")
    print(f"Zapisano do pliku: {CSV_FILE}")


if __name__ == "__main__":
    main()