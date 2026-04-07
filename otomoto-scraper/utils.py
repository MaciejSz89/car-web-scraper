import re
from typing import Optional


def clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def to_int(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def safe_int(value: Optional[str | int]) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except ValueError:
        return None


def detect_damage(text: Optional[str]) -> tuple[bool, Optional[str]]:
    """Szybkie wykrywanie słów-kluczy sugerujących uszkodzenie/kolizję.

    Zwraca (is_damaged, note) gdzie note to dopasowane słowo/frasetka.
    Funkcja jest celowo prosta — służy jako szybkie, list-card-level wykrycie.
    """
    if not text:
        return False, None

    lowered = text.lower()
    keywords = [
        "uszk", "bezwypad", "kolizj", "wypadk", "stluczk", "stłuczk", "do poprawek",
        "lekko uszkodzon", "powypadkow", "napraw", "naprawiany", "po kolizji",
    ]

    for kw in keywords:
        if kw in lowered:
            return True, kw

    return False, None