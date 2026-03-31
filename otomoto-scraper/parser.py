import re
from typing import Optional
import json

from bs4 import BeautifulSoup, Tag

from utils import clean_text, to_int


def extract_title_and_link(article: Tag) -> tuple[Optional[str], Optional[str]]:
    link_tag = article.find("a", href=lambda h: h and "/osobowe/oferta/" in h)
    if not link_tag:
        return None, None

    link = link_tag.get("href")

    # 1. tekst linku
    title = clean_text(link_tag.get_text(" ", strip=True))
    if title:
        return title, link

    # 2. aria-label (często najlepsze źródło)
    title = clean_text(link_tag.get("aria-label"))
    if title:
        return title, link

    # 3. SZUKAJ nagłówków w article (to powinno być główne źródło!)
    for tag_name in ("h1", "h2", "h3", "h4"):
        heading = article.find(tag_name)
        if heading:
            title = clean_text(heading.get_text(" ", strip=True))
            if title:
                return title, link

    # 4. title atrybut
    title = clean_text(link_tag.get("title"))
    if title:
        return title, link

    # 5. alt obrazka (ALE tylko jeśli sensowny)
    img_tag = link_tag.find("img")
    if img_tag:
        alt = clean_text(img_tag.get("alt"))
        if alt and alt.lower() != "alt":
            return alt, link

    return None, link


def extract_price(article: Tag) -> tuple[Optional[int], Optional[str]]:
    currency_node = article.find("p", string=lambda s: s and s.strip() == "PLN")
    if not currency_node:
        return None, None

    price_h3 = currency_node.find_previous("h3")
    if not price_h3:
        return None, "PLN"

    return to_int(price_h3.get_text()), "PLN"


def extract_parameter(article: Tag, param_name: str) -> Optional[str]:
    dd = article.find("dd", attrs={"data-parameter": param_name})
    if not dd:
        return None
    return clean_text(dd.get_text(" ", strip=True))


def extract_subtitle(article: Tag) -> Optional[str]:
    subtitle_tag = article.find("p", string=lambda s: s and ("cm3" in s or "KM" in s))
    return clean_text(subtitle_tag.get_text()) if subtitle_tag else None


def extract_engine_and_power(subtitle: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    if not subtitle:
        return None, None

    engine_match = re.search(r"(\d[\d\s]*)\s*cm3", subtitle, re.IGNORECASE)
    power_match = re.search(r"(\d[\d\s]*)\s*KM", subtitle, re.IGNORECASE)

    engine_cm3 = int(engine_match.group(1).replace(" ", "")) if engine_match else None
    power_hp = int(power_match.group(1).replace(" ", "")) if power_match else None

    return engine_cm3, power_hp


def extract_location(article: Tag) -> Optional[str]:
    for p in article.find_all("p"):
        text = clean_text(p.get_text())
        if text and "(" in text and ")" in text:
            return text
    return None


def extract_cars_from_json_ld(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="listing-json-ld")

    if not script or not script.string:
        return []

    try:
        data = json.loads(script.string)
    except Exception:
        return []

    main = data.get("mainEntity", {})
    items = main.get("itemListElement", [])

    cars = []

    for item in items:
        offer = item.get("itemOffered", {})
        price = item.get("priceSpecification", {}).get("price")

        cars.append({
            "listing_id": None,  # brak ID → tylko fallback
            "title": offer.get("name"),
            "price_pln": int(price) if price else None,
            "currency": "PLN",
            "link": None,
            "subtitle": None,
            "engine_cm3": None,
            "power_hp": None,
            "mileage_km": None,
            "fuel_type": offer.get("fuelType"),
            "gearbox": None,
            "year": None,
            "location": None,
        })

    return cars


def parse_car(article: Tag) -> Optional[dict]:
    listing_id = article.get("data-id")
    if not listing_id:
        print("ODRZUT: brak listing_id")
        return None

    title, link = extract_title_and_link(article)
    if not title or not link:
        print(f"ODRZUT {listing_id}: brak title/link | title={title!r} | link={link!r}")
        return None

    price_pln, currency = extract_price(article)
    if price_pln is None:
        print(f"UWAGA {listing_id}: brak ceny")

    subtitle = extract_subtitle(article)
    engine_cm3, power_hp = extract_engine_and_power(subtitle)

    mileage_km = to_int(extract_parameter(article, "mileage"))
    fuel_type = extract_parameter(article, "fuel_type")
    gearbox = extract_parameter(article, "gearbox")
    year = to_int(extract_parameter(article, "year"))
    location = extract_location(article)

    return {
        "listing_id": listing_id,
        "title": title,
        "price_pln": price_pln,
        "currency": currency,
        "link": link,
        "subtitle": subtitle,
        "engine_cm3": engine_cm3,
        "power_hp": power_hp,
        "mileage_km": mileage_km,
        "fuel_type": fuel_type,
        "gearbox": gearbox,
        "year": year,
        "location": location,
    }


def get_cars_from_content(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    cars = []

    articles = soup.find_all("article", attrs={"data-id": True})
    print(f"article[data-id] w HTML: {len(articles)}")

    for article in articles:
        car = parse_car(article)
        if car:
            cars.append(car)

    print(f"HTML cards: {len(cars)}")
    return cars