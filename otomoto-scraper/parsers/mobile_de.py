"""Parser mobile.de — REQ-063.

Eksponuje `get_cars_from_content(html) -> list[dict]` o strukturze dict
identycznej z output parsers/otomoto / parser.py.

Strategia parsowania:
1. Wyciąga `window.__STATE__` z HTML (rich JSON z API mobile.de).
2. Dla każdej oferty w `srp.data.ads` buduje ustandaryzowany dict.
3. Fallback (jeśli JSON niedostępny): parsowanie HTML artykułów przez BeautifulSoup.

Kurs EUR→PLN: stały przybliżony kurs (4.25), konfigurowalny przez zmienną modułową.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

from bs4 import BeautifulSoup, Tag

from utils import clean_text, to_int, detect_damage

logger = logging.getLogger(__name__)

# Stały kurs EUR→PLN. Docelowo można zastąpić dynamicznym kursem NBP.
EUR_TO_PLN_RATE: float = 4.25

MOBILE_DE_BASE = "https://suchen.mobile.de"

# Mapowanie kodów paliwa mobile.de → ustandaryzowane wartości
FUEL_TYPE_MAP: dict[str, str] = {
    "Benzin": "petrol",
    "Diesel": "diesel",
    "Elektro": "electric",
    "Hybrid (Benzin/Elektro)": "hybrid",
    "Hybrid (Diesel/Elektro)": "hybrid",
    "Mild-Hybrid (Benzin)": "hybrid",
    "Mild-Hybrid (Diesel)": "hybrid",
    "Plug-in-Hybrid (Benzin)": "plugin_hybrid",
    "Plug-in-Hybrid (Diesel)": "plugin_hybrid",
    "Erdgas (CNG)": "cng",
    "Flüssiggas (LPG)": "lpg",
    "Wasserstoff": "hydrogen",
}

GEARBOX_MAP: dict[str, str] = {
    "Automatik": "automatic",
    "Schaltgetriebe": "manual",
    "Halbautomatik": "semi-automatic",
}


def _extract_state_json(html: str) -> Optional[dict]:
    """Wyciąga obiekt window.__INITIAL_STATE__ z HTML."""
    match = re.search(
        r'window\.__INITIAL_STATE__\s*=\s*(\{.+?)(?=\n\s*window\.|\Z)',
        html,
        re.DOTALL,
    )
    if not match:
        return None
    raw = match.group(1).strip().rstrip(';')
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Szukamy do ostatniego pasującego }
        depth = 0
        end = 0
        for i, ch in enumerate(raw):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        try:
            return json.loads(raw[:end])
        except Exception:
            return None


def _eur_to_pln(eur_amount: Optional[float | int]) -> Optional[int]:
    if eur_amount is None:
        return None
    return int(round(eur_amount * EUR_TO_PLN_RATE))


def _parse_ez_year(fr: Optional[str]) -> Optional[int]:
    """Parsuje 'EZ MM/YYYY' lub 'MM/YYYY' → rok."""
    if not fr:
        return None
    m = re.search(r'(\d{4})', str(fr))
    return int(m.group(1)) if m else None


def _parse_mileage(ml: Optional[str]) -> Optional[int]:
    """Parsuje '102.120 km' → 102120."""
    if not ml:
        return None
    return to_int(str(ml))


def _parse_power_kw(pw: Optional[str]) -> Optional[int]:
    """Parsuje '130 kW (177 PS)' → 177 (PS/HP)."""
    if not pw:
        return None
    m = re.search(r'\((\d+)\s*PS\)', str(pw))
    if m:
        return int(m.group(1))
    # Fallback: kW → HP
    m2 = re.search(r'(\d+)\s*kW', str(pw))
    if m2:
        return int(round(int(m2.group(1)) * 1.341))
    return None


def _parse_engine_cc(cc: Optional[str]) -> Optional[int]:
    """Parsuje '1.591 cm³' lub '1591 cm³' → 1591."""
    if not cc:
        return None
    # Usuń separatory tysięcy (.) i cm³
    cleaned = re.sub(r'[^\d]', '', str(cc))
    return int(cleaned) if cleaned else None


def _map_fuel_type(ft: Optional[str]) -> Optional[str]:
    if not ft:
        return None
    return FUEL_TYPE_MAP.get(str(ft), str(ft).lower())


def _map_gearbox(tr: Optional[str]) -> Optional[str]:
    if not tr:
        return None
    return GEARBOX_MAP.get(str(tr), str(tr).lower())


def _map_seller_type(seller_type_str: Optional[str]) -> Optional[str]:
    if not seller_type_str:
        return None
    s = str(seller_type_str).upper()
    if s == "DEALER":
        return "business"
    if s == "PRIVATE":
        return "private"
    return None


def _is_accident_free(attributes: list) -> Optional[bool]:
    """Sprawdza czy w attributes[0] jest wpis {"value": "Unfallfrei", "bold": true}."""
    if not attributes or not isinstance(attributes, list):
        return None
    first_group = attributes[0] if attributes else []
    if not isinstance(first_group, list):
        return None
    for item in first_group:
        if isinstance(item, dict) and item.get("bold") and "unfallfrei" in str(item.get("value", "")).lower():
            return True
    return None


def _make_full_link(relative_url: str) -> str:
    if relative_url.startswith("http"):
        # Zachowaj tylko id z URL
        m = re.search(r'(https?://[^?]+\?id=(\d+))', relative_url)
        return m.group(1) if m else relative_url
    # Usuń zbędne query params śledzące — zachowaj tylko id
    parsed = re.match(r'(/fahrzeuge/details\.html\?id=(\d+))', relative_url)
    if parsed:
        return MOBILE_DE_BASE + parsed.group(1)
    return MOBILE_DE_BASE + relative_url


def _car_from_state_entry(entry: dict) -> Optional[dict]:
    """Buduje ustandaryzowany dict oferty z jednego wpisu z window.__STATE__.ads."""
    if entry.get("type") in ("inlineAdvertising", "eyecatcherAd"):
        return None

    listing_id = str(entry.get("id", "")).strip()
    if not listing_id:
        return None

    short_title = entry.get("shortTitle") or ""
    sub_title = entry.get("subTitle") or ""
    full_title = f"{short_title} {sub_title}".strip() if sub_title else short_title
    if not full_title:
        return None

    relative_url = entry.get("relativeUrl", "")
    link = _make_full_link(relative_url) if relative_url else None

    # Cena
    price_data = entry.get("price") or {}
    gross_eur = price_data.get("grossAmount")
    price_pln = _eur_to_pln(gross_eur)

    # Atrybuty techniczne ze słownika attr
    attr: dict = entry.get("attr") or {}
    year = _parse_ez_year(attr.get("fr"))
    mileage_km = _parse_mileage(attr.get("ml"))
    power_hp = _parse_power_kw(attr.get("pw"))
    engine_cm3 = _parse_engine_cc(attr.get("cc"))
    fuel_type = _map_fuel_type(attr.get("ft"))
    gearbox = _map_gearbox(attr.get("tr"))
    location_raw = attr.get("loc")
    zip_code = attr.get("z")
    location = f"{location_raw} ({zip_code})" if location_raw and zip_code else location_raw or zip_code or None

    # Sprzedawca
    contact_info: dict = entry.get("contactInfo") or {}
    seller_type = _map_seller_type(contact_info.get("sellerType"))
    seller_location = contact_info.get("location")
    if seller_location and not location:
        location = seller_location

    # Uszkodzenia
    accident_free = _is_accident_free(entry.get("attributes"))
    combined_text = f"{full_title} {entry.get('highlights', [])}"
    text_damaged, condition_note = detect_damage(combined_text)

    if accident_free:
        is_damaged = 0
        condition_note = condition_note or ""
    else:
        is_damaged = 1 if text_damaged else 0
        condition_note = condition_note or ""

    return {
        "listing_id": listing_id,
        "title": full_title,
        "price_pln": price_pln,
        "currency": "EUR",
        "link": link,
        "subtitle": sub_title or None,
        "engine_cm3": engine_cm3,
        "power_hp": power_hp,
        "mileage_km": mileage_km,
        "fuel_type": fuel_type,
        "gearbox": gearbox,
        "year": year,
        "location": location,
        "seller_type": seller_type,
        "is_damaged": is_damaged,
        "condition_note": condition_note,
        "source": "mobile_de",
    }


# ---------------------------------------------------------------------------
# Fallback: parsowanie HTML artykułów (gdy __STATE__ niedostępny)
# ---------------------------------------------------------------------------

def _parse_article_html(article: Tag) -> Optional[dict]:
    """Fallback parser HTML dla pojedynczego artykułu mobile.de."""
    link_tag = article.find("a", href=lambda h: h and "/fahrzeuge/details" in h)
    if not link_tag:
        return None

    href = link_tag.get("href", "")
    m = re.search(r'\?id=(\d+)', href)
    if not m:
        return None
    listing_id = m.group(1)

    # Tytuł z h2
    h2 = article.find("h2")
    title = clean_text(h2.get_text(" ", strip=True)) if h2 else None
    # Usuń badge "Gesponsert" / "Top" z tytułu
    if title:
        title = re.sub(r'^(Top|Gesponsert)\s*', '', title, flags=re.IGNORECASE).strip()
    if not title:
        return None

    link = _make_full_link(href)

    # Cena
    price_pln = None
    price_span = article.find("span", attrs={"data-testid": "price-label"})
    if price_span:
        raw_price = price_span.get_text(strip=True)
        # "34.800 €" → 34800
        price_digits = re.sub(r'[^\d]', '', raw_price.split('€')[0])
        if price_digits:
            try:
                price_pln = _eur_to_pln(int(price_digits))
            except ValueError:
                pass

    # Atrybuty techniczne z `data-testid="listing-details-attributes"`
    year = mileage_km = power_hp = fuel_type = None
    details_div = article.find(attrs={"data-testid": "listing-details-attributes"})
    if details_div:
        details_text = details_div.get_text(" ", strip=True)
        # Format: "EZ 05/2025 • 20.249 km • 158 kW (215 PS) • Hybrid (Benzin/Elektro)"
        year = _parse_ez_year(details_text)
        m_mileage = re.search(r'([\d.]+)\s*km', details_text)
        mileage_km = to_int(m_mileage.group(1)) if m_mileage else None
        power_hp = _parse_power_kw(details_text)
        for fuel_de, fuel_en in FUEL_TYPE_MAP.items():
            if fuel_de.lower() in details_text.lower():
                fuel_type = fuel_en
                break

    # Lokalizacja ze sprzedawcy
    seller_div = article.find(attrs={"data-testid": "seller-info"})
    location = None
    seller_type = None
    if seller_div:
        texts = [t.strip() for t in seller_div.stripped_strings]
        # Ostatni element to lokalizacja (format "PLZ Ort")
        for t in reversed(texts):
            if re.match(r'^\d{5}\s+\w', t):
                location = t
                break
        # Sprawdź czy sprzedawca to firma (obecność logo) vs prywatny
        logo_img = seller_div.find("img", class_=lambda c: c and "p7NSE" in c)
        seller_type = "business" if logo_img else None

    combined_text = title or ""
    text_damaged, condition_note = detect_damage(combined_text)

    return {
        "listing_id": listing_id,
        "title": title,
        "price_pln": price_pln,
        "currency": "EUR",
        "link": link,
        "subtitle": None,
        "engine_cm3": None,
        "power_hp": power_hp,
        "mileage_km": mileage_km,
        "fuel_type": fuel_type,
        "gearbox": None,
        "year": year,
        "location": location,
        "seller_type": seller_type,
        "is_damaged": 1 if text_damaged else 0,
        "condition_note": condition_note or "",
        "source": "mobile_de",
    }


# ---------------------------------------------------------------------------
# Publiczne API
# ---------------------------------------------------------------------------

def get_cars_from_content(html: str) -> list[dict]:
    """Parsuje HTML strony wynikowej mobile.de.

    Zwraca listę dicts o tej samej strukturze co parser Otomoto.
    Błędne karty są pomijane z logiem ostrzeżenia.
    """
    # Próba 1: wyciągnij dane ze struktury __STATE__
    state = _extract_state_json(html)
    if state:
        ads = None
        try:
            ads = state["search"]["srp"]["data"]["searchResults"]["items"]
        except (KeyError, TypeError):
            pass

        if ads:
            cars = []
            for entry in ads:
                try:
                    car = _car_from_state_entry(entry)
                    if car:
                        cars.append(car)
                except Exception as exc:
                    logger.warning("mobile.de parser: błąd dla wpisu id=%s: %s", entry.get("id"), exc)
            logger.info("mobile.de __INITIAL_STATE__: sparsowano %d ofert", len(cars))
            return cars

    # Fallback: parsowanie HTML artykułów
    logger.info("mobile.de: __STATE__ niedostępny, używam fallback HTML parser")
    soup = BeautifulSoup(html, "html.parser")
    articles = [
        a for a in soup.find_all("article")
        if a.find("a", href=lambda h: h and "/fahrzeuge/details" in h)
    ]
    logger.info("mobile.de HTML fallback: znaleziono %d artykułów", len(articles))

    cars = []
    for article in articles:
        try:
            car = _parse_article_html(article)
            if car:
                cars.append(car)
        except Exception as exc:
            logger.warning("mobile.de HTML parser: błąd artykułu: %s", exc)

    logger.info("mobile.de HTML fallback: sparsowano %d ofert", len(cars))
    return cars
