import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "otomoto-scraper"))

from utils import clean_text, to_int, safe_int, detect_damage


def test_clean_text_none_and_spaces():
    assert clean_text(None) is None
    assert clean_text("  foo   bar \n") == "foo bar"


def test_to_int_and_safe_int():
    assert to_int("12 345 PLN") == 12345
    assert to_int(None) is None
    assert safe_int(None) is None
    assert safe_int(123) == 123
    assert safe_int("456") == 456
    assert safe_int("notanumber") is None


def test_detect_damage_keywords():
    assert detect_damage(None) == (False, None)
    assert detect_damage(" samochód bezwypadkowy ") == (True, "bezwypad")
    assert detect_damage("do poprawek, drobne") == (True, "do poprawek")
    assert detect_damage("normal listing") == (False, None)
