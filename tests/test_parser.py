import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "otomoto-scraper"))

from bs4 import BeautifulSoup
import parser as p


def make_article_html(listing_id: str, title_text: str, price: str, seller_label: str = "Prywatny sprzedawca") -> str:
    return f"""
<article data-id="{listing_id}">
  <a href="/osobowe/oferta/{listing_id}" aria-label="{title_text}">{title_text}</a>
  <h3>{price}</h3>
  <p>PLN</p>
  <p>przebieg</p>
  <dd data-parameter="mileage">50 000 km</dd>
  <p>{seller_label} • dodatkowe</p>
  <p>1598 cm3 • 120 KM</p>
  <p>(Warszawa)</p>
</article>
"""


def test_extract_title_and_price_and_seller():
    html = make_article_html("ID1", "Tytuł auta", "10 000")
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article")

    title, link = p.extract_title_and_link(article)
    assert title == "Tytuł auta"
    assert "/osobowe/oferta/ID1" in link

    price, currency = p.extract_price(article)
    assert price == 10000
    assert currency == "PLN"

    seller = p.extract_seller_type(article)
    assert seller == "private"


def test_extract_engine_and_power_and_location_and_params():
    html = make_article_html("ID2", "Auto 2", "12 345", seller_label="Firma")
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article")

    engine, power = p.extract_engine_and_power(p.extract_subtitle(article))
    assert engine == 1598
    assert power == 120

    location = p.extract_location(article)
    assert "(" in location

    mileage = p.extract_parameter(article, "mileage")
    assert "50 000" in mileage


def test_parse_car_and_get_cars_from_content():
    html = make_article_html("ID3", "Auto 3", "9000")
    content = f"<html><body>{html}</body></html>"
    cars = p.get_cars_from_content(content)
    assert isinstance(cars, list)
    assert len(cars) == 1
    car = cars[0]
    assert car["listing_id"] == "ID3"
    assert car["price_pln"] == 9000
    assert car["seller_type"] == "private"
