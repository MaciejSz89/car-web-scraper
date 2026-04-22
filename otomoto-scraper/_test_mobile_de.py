"""Skrypt testowy mobile.de — weryfikuje scraper + parser end-to-end.

Użycie:
    uv run otomoto-scraper/_test_mobile_de.py [--headless]

Pobiera 1 stronę wyników dla Kia Sportage, parsuje oferty
i drukuje podsumowanie. Nie zapisuje niczego do CSV.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Dodaj katalog scrapera do sys.path (tak samo jak main.py)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scrapers.mobile_de import get_html_pages
from parsers.mobile_de import get_cars_from_content, EUR_TO_PLN_RATE
from config import (
    DATA_DIR,
    SESSION_STATE_FILE_MOBILE_DE,
    WAIT_MS,
    POST_NAVIGATION_DELAY_RANGE_MS,
    PAGE_BREAK_DELAY_RANGE_MS,
    SCROLL_PAUSE_RANGE_MS,
    SCROLL_STEP_RANGE_PX,
    RETRY_BACKOFF_DELAY_RANGE_MS,
    NAVIGATION_TIMEOUT_MS,
    MAX_NAVIGATION_RETRIES,
)

TEST_URL = (
    "https://suchen.mobile.de/fahrzeuge/search.html"
    "?dam=false&fr=2016%3A&isSearchRequest=true&ml=%3A180000"
    "&ms=13200%3B25%3B%3B&od=up&s=Car&sb=rel&vc=Car"
)


def main() -> None:
    headless = "--headless" in sys.argv
    print(f"=== Test mobile.de scraper + parser ===")
    print(f"headless={headless}, kurs EUR→PLN={EUR_TO_PLN_RATE}")
    print(f"URL: {TEST_URL}\n")

    print("Krok 1: Pobieranie HTML (max 1 strona)...")
    pages = get_html_pages(
        start_url=TEST_URL,
        headless=headless,
        wait_ms=WAIT_MS,
        max_pages=1,
        post_navigation_delay_range_ms=POST_NAVIGATION_DELAY_RANGE_MS,
        page_break_delay_range_ms=PAGE_BREAK_DELAY_RANGE_MS,
        scroll_pause_range_ms=SCROLL_PAUSE_RANGE_MS,
        scroll_step_range_px=SCROLL_STEP_RANGE_PX,
        retry_backoff_delay_range_ms=RETRY_BACKOFF_DELAY_RANGE_MS,
        navigation_timeout_ms=NAVIGATION_TIMEOUT_MS,
        max_navigation_retries=MAX_NAVIGATION_RETRIES,
        session_state_file=SESSION_STATE_FILE_MOBILE_DE,
    )

    print(f"Pobrano stron: {len(pages)}")
    if not pages:
        # Zapisz HTML debug z homepage — sprawdź co mobile.de zwraca
        debug_path = DATA_DIR / "_debug-mobile-de-homepage.html"
        print(f"BŁĄD: Brak stron HTML — scraper nie zwrócił wyników.")
        print(f"Sprawdź: {debug_path} (jeśli istnieje) oraz debug-errors/")
        sys.exit(1)

    print(f"Rozmiar HTML strony 1: {len(pages[0])} znaków\n")

    print("Krok 2: Parsowanie ofert...")
    cars = get_cars_from_content(pages[0])
    print(f"Sparsowano ofert: {len(cars)}\n")

    if not cars:
        print("BŁĄD: Parser nie zwrócił żadnych ofert.")
        # Zapisz HTML do debugowania
        debug_path = DATA_DIR / "_debug-mobile-de-test.html"
        debug_path.write_text(pages[0], encoding="utf-8")
        print(f"HTML zapisany do: {debug_path}")
        sys.exit(1)

    # Wydrukuj pierwsze 5 ofert
    print("=== Przykładowe oferty (pierwsze 5) ===")
    for i, car in enumerate(cars[:5], 1):
        price_eur = int(car["price_pln"] / EUR_TO_PLN_RATE) if car.get("price_pln") else None
        print(
            f"{i:2}. [{car['listing_id']}] {car['title']}\n"
            f"    cena: {car.get('price_pln')} PLN ({price_eur} EUR) | "
            f"rok: {car.get('year')} | "
            f"km: {car.get('mileage_km')} | "
            f"moc: {car.get('power_hp')} HP | "
            f"paliwo: {car.get('fuel_type')} | "
            f"skrzynia: {car.get('gearbox')}\n"
            f"    lokalizacja: {car.get('location')} | "
            f"sprzedawca: {car.get('seller_type')} | "
            f"uszkodzony: {car.get('is_damaged')}\n"
            f"    link: {car.get('link')}\n"
        )

    # Statystyki
    with_price = [c for c in cars if c.get("price_pln")]
    with_year = [c for c in cars if c.get("year")]
    with_mileage = [c for c in cars if c.get("mileage_km")]
    with_fuel = [c for c in cars if c.get("fuel_type")]
    with_gearbox = [c for c in cars if c.get("gearbox")]

    print("=== Statystyki kompletności danych ===")
    print(f"  z ceną:         {len(with_price)}/{len(cars)}")
    print(f"  z rokiem:       {len(with_year)}/{len(cars)}")
    print(f"  z przebiegiem:  {len(with_mileage)}/{len(cars)}")
    print(f"  z paliwem:      {len(with_fuel)}/{len(cars)}")
    print(f"  ze skrzynią:    {len(with_gearbox)}/{len(cars)}")
    print(f"  uszkodzonych:   {sum(1 for c in cars if c.get('is_damaged'))}/{len(cars)}")

    print("\nTest zakończony pomyślnie.")


if __name__ == "__main__":
    main()
