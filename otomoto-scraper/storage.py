import csv
import os
from datetime import date, datetime
from datetime import timezone


from utils import safe_int


def parse_csv_date(value: str) -> date:
    for date_format in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue

    raise ValueError(f"Unsupported date format: {value}")


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

            if "seller_type" not in row:
                row["seller_type"] = ""

            # enrichment fields (can be absent in older CSVs)
            if "details_status" not in row:
                row["details_status"] = ""  # e.g. pending,fetched,failed

            if "details_priority" not in row:
                row["details_priority"] = ""  # integer-like priority

            if "details_fetched_at" not in row:
                row["details_fetched_at"] = ""

            if "details_based_on_price_pln" not in row:
                row["details_based_on_price_pln"] = ""

            if "details_based_on_last_seen_date" not in row:
                row["details_based_on_last_seen_date"] = ""

            if "details_based_on_decision_bucket" not in row:
                row["details_based_on_decision_bucket"] = ""

            if "details_fields_present" not in row:
                row["details_fields_present"] = ""

            if "details_description_excerpt" not in row:
                row["details_description_excerpt"] = ""

            if "details_seller_name" not in row:
                row["details_seller_name"] = ""

            if "details_vin" not in row:
                row["details_vin"] = ""

            if "details_country_origin" not in row:
                row["details_country_origin"] = ""

            if "details_no_accident_flag" not in row:
                row["details_no_accident_flag"] = ""

            if "details_service_record_flag" not in row:
                row["details_service_record_flag"] = ""

            if "details_imported_flag" not in row:
                row["details_imported_flag"] = ""

            if "details_enrichment_score" not in row:
                row["details_enrichment_score"] = ""

            if "details_enrichment_confidence" not in row:
                row["details_enrichment_confidence"] = ""

            if "details_enrichment_flags" not in row:
                row["details_enrichment_flags"] = ""

            cars_by_id[listing_id] = row

    return cars_by_id


def calculate_days_on_site(first_seen_date_str: str, last_seen_date_str: str) -> int:
    first_seen = parse_csv_date(first_seen_date_str)
    last_seen = parse_csv_date(last_seen_date_str)
    return (last_seen - first_seen).days


def upsert_cars_to_csv(cars: list[dict], csv_file: str) -> tuple[int, int]:
    today = date.today().isoformat()

    _baseline_fieldnames = [
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
        "seller_type",
        "details_status",
        "details_priority",
        "details_fetched_at",
        "details_based_on_price_pln",
        "details_based_on_last_seen_date",
        "details_based_on_decision_bucket",
        "details_fields_present",
        "details_description_excerpt",
        "details_seller_name",
        "details_vin",
        "details_country_origin",
        "details_no_accident_flag",
        "details_damaged_flag",
        "details_service_record_flag",
        "details_imported_flag",
        "details_enrichment_score",
        "details_enrichment_confidence",
        "details_enrichment_flags",
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

    # Merge baseline with any extra columns already present in the existing CSV
    # (e.g. fields added by enrichment_worker or llm_worker after initial creation).
    existing_csv_fieldnames: list[str] = []
    if os.path.exists(csv_file):
        try:
            with open(csv_file, "r", newline="", encoding="utf-8-sig") as _fh:
                _reader = csv.DictReader(_fh, delimiter=";")
                existing_csv_fieldnames = list(_reader.fieldnames or [])
        except Exception:
            pass

    baseline_set = set(_baseline_fieldnames)
    fieldnames = list(_baseline_fieldnames)
    for col in existing_csv_fieldnames:
        if col not in baseline_set:
            fieldnames.append(col)
            baseline_set.add(col)

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
            row["seller_type"] = car.get("seller_type") or ""
            row["details_status"] = row.get("details_status") or ""
            row["details_priority"] = row.get("details_priority") or ""
            row["details_fetched_at"] = row.get("details_fetched_at") or ""
            row["details_based_on_price_pln"] = row.get("details_based_on_price_pln") or ""
            row["details_based_on_last_seen_date"] = row.get("details_based_on_last_seen_date") or ""
            row["details_based_on_decision_bucket"] = row.get("details_based_on_decision_bucket") or ""
            row["details_fields_present"] = row.get("details_fields_present") or ""
            row["details_description_excerpt"] = row.get("details_description_excerpt") or ""
            row["details_seller_name"] = row.get("details_seller_name") or ""
            row["details_vin"] = row.get("details_vin") or ""
            row["details_country_origin"] = row.get("details_country_origin") or ""
            row["details_no_accident_flag"] = row.get("details_no_accident_flag") or ""
            row["details_service_record_flag"] = row.get("details_service_record_flag") or ""
            row["details_imported_flag"] = row.get("details_imported_flag") or ""
            row["details_enrichment_score"] = row.get("details_enrichment_score") or ""
            row["details_enrichment_confidence"] = row.get("details_enrichment_confidence") or ""
            row["details_enrichment_flags"] = row.get("details_enrichment_flags") or ""
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
            car["seller_type"] = car.get("seller_type") or ""
            car["details_status"] = car.get("details_status") or ""
            car["details_priority"] = car.get("details_priority") or ""
            car["details_fetched_at"] = car.get("details_fetched_at") or ""
            car["details_based_on_price_pln"] = car.get("details_based_on_price_pln") or ""
            car["details_based_on_last_seen_date"] = car.get("details_based_on_last_seen_date") or ""
            car["details_based_on_decision_bucket"] = car.get("details_based_on_decision_bucket") or ""
            car["details_fields_present"] = car.get("details_fields_present") or ""
            car["details_description_excerpt"] = car.get("details_description_excerpt") or ""
            car["details_seller_name"] = car.get("details_seller_name") or ""
            car["details_vin"] = car.get("details_vin") or ""
            car["details_country_origin"] = car.get("details_country_origin") or ""
            car["details_no_accident_flag"] = car.get("details_no_accident_flag") or ""
            car["details_service_record_flag"] = car.get("details_service_record_flag") or ""
            car["details_imported_flag"] = car.get("details_imported_flag") or ""
            car["details_enrichment_score"] = car.get("details_enrichment_score") or ""
            car["details_enrichment_confidence"] = car.get("details_enrichment_confidence") or ""
            car["details_enrichment_flags"] = car.get("details_enrichment_flags") or ""
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
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Nowe ogłoszenia: {new_count}")
    print(f"Zaktualizowane ogłoszenia: {updated_count}")

    if new_items:
        print("\nLista nowych ogłoszeń:")
        for item in new_items:
            print(f'- {item["listing_id"]} | {item["title"]} | {item["link"]}')
        # Dodaj nowe oferty do pliku kolejki wzbogacania (enrichment_queue.csv)
        try:
            queue_file = os.path.join(os.path.dirname(csv_file), "enrichment_queue.csv")
            # wczytaj istniejące listing_id z kolejki, by uniknąć duplikatów
            existing_ids = set()
            if os.path.exists(queue_file):
                try:
                    with open(queue_file, "r", newline="", encoding="utf-8-sig") as qf:
                        qreader = csv.DictReader(qf, delimiter=";")
                        for qrow in qreader:
                            lid = qrow.get("listing_id")
                            if lid:
                                existing_ids.add(lid)
                except Exception:
                    # jeśli nie uda się odczytać, kontynuujemy i nadpiszemy
                    existing_ids = set()

            source_csv_name = os.path.basename(csv_file)
            to_append = []
            for item in new_items:
                lid = item.get("listing_id")
                if not lid or lid in existing_ids:
                    continue
                to_append.append({
                    "listing_id": lid,
                    "link": item.get("link", ""),
                    "priority": 50,
                    "reason": "new",
                    "selected_at": datetime.now(timezone.utc).isoformat(),
                    "source_csv": source_csv_name,
                })

            if to_append:
                write_header = not os.path.exists(queue_file)
                os.makedirs(os.path.dirname(queue_file), exist_ok=True)
                with open(queue_file, "a", newline="", encoding="utf-8-sig") as qf:
                    fieldnames_q = ["listing_id", "link", "priority", "reason", "selected_at", "source_csv"]
                    writer = csv.DictWriter(qf, fieldnames=fieldnames_q, delimiter=";", quoting=csv.QUOTE_MINIMAL)
                    if write_header:
                        writer.writeheader()
                    for row in to_append:
                        writer.writerow(row)
                print(f"Dodano {len(to_append)} pozycji do kolejki wzbogacania: {queue_file}")
        except Exception as e:
            print(f"Nie udało się zapisać do enrichment_queue: {e}")
    else:
        print("\nBrak nowych ogłoszeń.")

    return new_count, updated_count