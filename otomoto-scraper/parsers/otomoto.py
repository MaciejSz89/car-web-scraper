# Otomoto parser — re-exports from the top-level parser module.
# This module exists so that main.py can dispatch uniformly via
#   from parsers.otomoto import get_cars_from_content
# without duplicating code.
from parser import get_cars_from_content  # noqa: F401

__all__ = ["get_cars_from_content"]
