import csv
import os
from datetime import date, datetime


from utils import safe_int


def read_existing_cars(csv_file: str) -> dict[str, dict]:
    """
    Zwraca słownik:
    {
        listing_id: row_dict
    }

    Obsługuje także starsze wersje CSV, które nie mają jeszcze nowych kolumn.
    """
    if not os.path.exists(csv_file):
        return {}

    cars_by_id = {}

    with open(csv_file, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            listing_id = row.get("listing_id")
            if not listing_id:
                continue

            current_price = safe_int(row.get("price_pln"))

            if not row.get("initial_price_pln"):
                row["initial_price_pln"] = current_price

            if not row.get("lowest_price_pln"):
                row["lowest_price_pln"] = current_price

            if not row.get("price_change_count"):
                row["price_change_count"] = 0

            if "last_price_change_date" not in row:
                row["last_price_change_date"] = ""

            if "is_active" not in row or row.get("is_active") in (None, ""):
                row["is_active"] = 1

            if "removed_date" not in row:
                row["removed_date"] = ""

            if "is_damaged" not in row:
                row["is_damaged"] = 0

            if "condition_note" not in row:
                row["condition_note"] = ""

            cars_by_id[listing_id] = row

    return cars_by_id


def calculate_days_on_site(first_seen_date_str: str, last_seen_date_str: str) -> int:
    first_seen = datetime.strptime(first_seen_date_str, "%Y-%m-%d").date()
    last_seen = datetime.strptime(last_seen_date_str, "%Y-%m-%d").date()
    return (last_seen - first_seen).days


def upsert_cars_to_csv(cars: list[dict], csv_file: str) -> tuple[int, int]:
    today = date.today().isoformat()

    fieldnames = [
        "listing_id",
        "title",
        "price_pln",
        "currency",
        "link",
        "subtitle",
        "engine_cm3",
        "power_hp",
        "mileage_km",
        "fuel_type",
        "gearbox",
        "year",
        "location",
        "is_damaged",
        "condition_note",
        "first_seen_date",
        "last_seen_date",
        "days_on_site",
        "is_active",
        "removed_date",
        "initial_price_pln",
        "lowest_price_pln",
        "price_change_count",
        "last_price_change_date",
    ]

    existing = read_existing_cars(csv_file)

    print(f"CSV file: {os.path.abspath(csv_file)}")
    print(f"Ile rekordów już w CSV: {len(existing)}")
    print(f"Ile ofert znaleziono teraz: {len(cars)}")

    new_count = 0
    updated_count = 0
    new_items = []

    for row in existing.values():
        row["is_active"] = 0

    for car in cars:
        listing_id = car["listing_id"]
        current_price = car["price_pln"]

        if listing_id in existing:
            row = existing[listing_id]

            old_price = safe_int(row.get("price_pln"))
            lowest_price = safe_int(row.get("lowest_price_pln"))
            price_change_count = safe_int(row.get("price_change_count")) or 0

            row["title"] = car["title"]
            row["price_pln"] = current_price
            row["currency"] = car["currency"]
            row["link"] = car["link"]
            row["subtitle"] = car["subtitle"]
            row["engine_cm3"] = car["engine_cm3"]
            row["power_hp"] = car["power_hp"]
            row["mileage_km"] = car["mileage_km"]
            row["fuel_type"] = car["fuel_type"]
            row["gearbox"] = car["gearbox"]
            row["year"] = car["year"]
            row["location"] = car["location"]
            # aktualizuj informacje o stanie/uszkodzeniu
            row["is_damaged"] = 1 if car.get("is_damaged") else 0
            row["condition_note"] = car.get("condition_note") or ""
            row["last_seen_date"] = today
            row["days_on_site"] = calculate_days_on_site(row["first_seen_date"], today)

            row["is_active"] = 1
            row["removed_date"] = ""

            if not row.get("initial_price_pln"):
                row["initial_price_pln"] = current_price

            if lowest_price is None:
                row["lowest_price_pln"] = current_price
                lowest_price = current_price

            if old_price is not None and current_price is not None and old_price != current_price:
                row["price_change_count"] = price_change_count + 1
                row["last_price_change_date"] = today

                if lowest_price is None or current_price < lowest_price:
                    row["lowest_price_pln"] = current_price
            else:
                if row.get("price_change_count") in (None, ""):
                    row["price_change_count"] = price_change_count

                if row.get("last_price_change_date") is None:
                    row["last_price_change_date"] = ""

                if lowest_price is None and current_price is not None:
                    row["lowest_price_pln"] = current_price

            updated_count += 1

        else:
            car["first_seen_date"] = today
            car["last_seen_date"] = today
            car["days_on_site"] = 0
            car["is_active"] = 1
            car["removed_date"] = ""
            car["initial_price_pln"] = current_price
            car["lowest_price_pln"] = current_price
            car["price_change_count"] = 0
            car["last_price_change_date"] = ""
            # uzupełnij pola uszkodzenia dla nowych rekordów
            car["is_damaged"] = 1 if car.get("is_damaged") else 0
            car["condition_note"] = car.get("condition_note") or ""

            existing[listing_id] = car
            new_count += 1

            new_items.append({
                "listing_id": listing_id,
                "title": car["title"],
                "link": car["link"],
            })

    for row in existing.values():
        if str(row.get("is_active")) == "0" and not row.get("removed_date"):
            row["removed_date"] = today

    rows = list(existing.values())

    with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            delimiter=";",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Nowe ogłoszenia: {new_count}")
    print(f"Zaktualizowane ogłoszenia: {updated_count}")

    if new_items:
        print("\nLista nowych ogłoszeń:")
        for item in new_items:
            print(f'- {item["listing_id"]} | {item["title"]} | {item["link"]}')
    else:
        print("\nBrak nowych ogłoszeń.")

    return new_count, updated_count