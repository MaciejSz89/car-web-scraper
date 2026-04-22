# Otomoto scraper — re-exports from the top-level scraper module.
# This module exists so that main.py can dispatch uniformly via
#   from scrapers.otomoto import get_html_pages
# without duplicating code.
from scraper import get_html_pages  # noqa: F401

__all__ = ["get_html_pages"]
