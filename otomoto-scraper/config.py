from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict


class QueryConfig(TypedDict):
	name: str
	start_url: str
	csv_file: str
	max_pages: int
	enabled: bool


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRAPER_DIR = PROJECT_ROOT / "otomoto-scraper"
DATA_DIR = PROJECT_ROOT / "data" / "otomoto"
ANALYTICS_DIR = DATA_DIR / "analytics"
NOTIFICATION_HISTORY_FILE = DATA_DIR / "notification_history.csv"
NOTIFICATION_STATE_FILE = DATA_DIR / "notification_state.csv"
QUERIES_FILE = SCRAPER_DIR / "queries.json"
QUERIES_EXAMPLE_FILE = SCRAPER_DIR / "queries.example.json"
PREFERENCES_FILE = SCRAPER_DIR / "preferences.json"
PREFERENCES_EXAMPLE_FILE = SCRAPER_DIR / "preferences.example.json"
SESSION_STATE_FILE = DATA_DIR / ".session-state.json"

HEADLESS = False
WAIT_MS = 3000
MAX_PAGES = 10
MAX_NAVIGATION_RETRIES = 3
NAVIGATION_TIMEOUT_MS = 45000

POST_NAVIGATION_DELAY_RANGE_MS = (2000, 5500)
PAGE_BREAK_DELAY_RANGE_MS = (4000, 8000)
SCROLL_PAUSE_RANGE_MS = (900, 2200)
SCROLL_STEP_RANGE_PX = (1400, 4200)
RETRY_BACKOFF_DELAY_RANGE_MS = (4000, 10000)


def resolve_csv_file(csv_file: str) -> str:
	csv_path = Path(csv_file)
	if not csv_path.is_absolute():
		csv_path = DATA_DIR / csv_path
	return str(csv_path)


def load_queries() -> list[QueryConfig]:
	queries_source = QUERIES_FILE if QUERIES_FILE.exists() else QUERIES_EXAMPLE_FILE

	with open(queries_source, "r", encoding="utf-8") as file_handle:
		raw_queries = json.load(file_handle)

	if not isinstance(raw_queries, list) or not raw_queries:
		raise ValueError(f"Plik {queries_source} musi zawierać niepustą listę kwerend.")

	normalized_queries: list[QueryConfig] = []

	for index, raw_query in enumerate(raw_queries, start=1):
		if not isinstance(raw_query, dict):
			raise ValueError(f"Kwerenda #{index} w {queries_source} musi być obiektem JSON.")

		name = str(raw_query.get("name", "")).strip()
		start_url = str(raw_query.get("start_url", "")).strip()
		csv_file = str(raw_query.get("csv_file", "")).strip()
		max_pages = raw_query.get("max_pages", MAX_PAGES)
		enabled = raw_query.get("enabled", True)

		if not name:
			raise ValueError(f"Kwerenda #{index} w {queries_source} nie ma pola 'name'.")
		if not start_url:
			raise ValueError(f"Kwerenda '{name}' w {queries_source} nie ma pola 'start_url'.")
		if not csv_file:
			raise ValueError(f"Kwerenda '{name}' w {queries_source} nie ma pola 'csv_file'.")
		if not isinstance(enabled, bool):
			raise ValueError(f"Kwerenda '{name}' w {queries_source} ma nieprawidłowe 'enabled': {enabled!r}.")

		try:
			normalized_max_pages = int(max_pages)
		except (TypeError, ValueError) as exc:
			raise ValueError(
				f"Kwerenda '{name}' w {queries_source} ma nieprawidłowe 'max_pages': {max_pages!r}."
			) from exc

		if enabled:
			normalized_queries.append({
				"name": name,
				"start_url": start_url,
				"csv_file": resolve_csv_file(csv_file),
				"max_pages": normalized_max_pages,
				"enabled": enabled,
			})

	return normalized_queries


QUERIES = load_queries()