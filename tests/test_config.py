import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "otomoto-scraper"))

from config import build_otomoto_url, load_queries


# ---------------------------------------------------------------------------
# build_otomoto_url
# ---------------------------------------------------------------------------

def test_build_otomoto_url_full_params():
    url = build_otomoto_url({
        "make": "kia",
        "model": "sportage",
        "year_from": 2016,
        "fuel_type": "petrol",
        "mileage_to": 180000,
    })
    assert url.startswith("https://www.otomoto.pl/osobowe/kia/sportage/od-2016")
    assert "filter_enum_fuel_type%5D=petrol" in url
    assert "filter_float_mileage%3Ato%5D=180000" in url


def test_build_otomoto_url_no_year():
    url = build_otomoto_url({"make": "honda", "model": "jazz", "fuel_type": "petrol"})
    assert "https://www.otomoto.pl/osobowe/honda/jazz?" in url
    assert "/od-" not in url


def test_build_otomoto_url_no_filters():
    url = build_otomoto_url({"make": "toyota", "model": "yaris", "year_from": 2018})
    assert url == "https://www.otomoto.pl/osobowe/toyota/yaris/od-2018"


def test_build_otomoto_url_optional_price_to():
    url = build_otomoto_url({
        "make": "skoda",
        "model": "octavia",
        "year_from": 2017,
        "fuel_type": "diesel",
        "mileage_to": 120000,
        "price_to": 60000,
    })
    assert "filter_float_price%3Ato%5D=60000" in url


def test_build_otomoto_url_missing_make_raises():
    import pytest
    with pytest.raises(ValueError, match="make"):
        build_otomoto_url({"model": "sportage"})


def test_build_otomoto_url_missing_model_raises():
    import pytest
    with pytest.raises(ValueError, match="model"):
        build_otomoto_url({"make": "kia"})


def test_build_otomoto_url_makes_slug_lowercase():
    url = build_otomoto_url({"make": "KIA", "model": "SPORTAGE"})
    assert "/osobowe/kia/sportage" in url


# ---------------------------------------------------------------------------
# load_queries with otomoto_params
# ---------------------------------------------------------------------------

def _write_temp_queries(data: list) -> Path:
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(data, tmp)
    tmp.close()
    return Path(tmp.name)


def test_load_queries_builds_url_from_otomoto_params(monkeypatch, tmp_path):
    queries_file = tmp_path / "queries.json"
    queries_file.write_text(json.dumps([
        {
            "name": "Test Query",
            "otomoto_params": {
                "make": "ford",
                "model": "focus",
                "year_from": 2018,
                "fuel_type": "petrol",
                "mileage_to": 100000,
            },
            "csv_file": "test.csv",
            "max_pages": 5,
            "enabled": True,
        }
    ]), encoding="utf-8")

    import config
    monkeypatch.setattr(config, "QUERIES_FILE", queries_file)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    result = load_queries()
    assert len(result) == 1
    assert result[0]["name"] == "Test Query"
    assert "ford/focus/od-2018" in result[0]["start_url"]
    assert "petrol" in result[0]["start_url"]


def test_load_queries_fallback_to_start_url(monkeypatch, tmp_path):
    queries_file = tmp_path / "queries.json"
    queries_file.write_text(json.dumps([
        {
            "name": "Legacy Query",
            "start_url": "https://www.otomoto.pl/osobowe/seat/leon/od-2015",
            "csv_file": "test.csv",
            "max_pages": 3,
            "enabled": True,
        }
    ]), encoding="utf-8")

    import config
    monkeypatch.setattr(config, "QUERIES_FILE", queries_file)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    result = load_queries()
    assert result[0]["start_url"] == "https://www.otomoto.pl/osobowe/seat/leon/od-2015"


def test_load_queries_otomoto_params_takes_precedence_over_start_url(monkeypatch, tmp_path):
    queries_file = tmp_path / "queries.json"
    queries_file.write_text(json.dumps([
        {
            "name": "Mixed Query",
            "start_url": "https://www.otomoto.pl/osobowe/old/url",
            "otomoto_params": {"make": "bmw", "model": "x3", "year_from": 2019},
            "csv_file": "test.csv",
            "max_pages": 5,
            "enabled": True,
        }
    ]), encoding="utf-8")

    import config
    monkeypatch.setattr(config, "QUERIES_FILE", queries_file)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    result = load_queries()
    assert "bmw/x3/od-2019" in result[0]["start_url"]
    assert "old/url" not in result[0]["start_url"]


def test_load_queries_no_url_nor_params_raises(monkeypatch, tmp_path):
    queries_file = tmp_path / "queries.json"
    queries_file.write_text(json.dumps([
        {
            "name": "Bad Query",
            "csv_file": "test.csv",
            "max_pages": 5,
            "enabled": True,
        }
    ]), encoding="utf-8")

    import config, pytest
    monkeypatch.setattr(config, "QUERIES_FILE", queries_file)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    with pytest.raises(ValueError, match="start_url.*otomoto_params"):
        load_queries()
