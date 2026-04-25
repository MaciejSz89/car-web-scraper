# CarWebScraper — Instrukcje dla Copilota

## Nawigacja po kodzie

Przed czytaniem kodu sprawdź dokumentację w `docs/`:

- `docs/architecture.md` — reguły projektowe, kontrakty danych, zasady działania każdej warstwy
- `docs/requirements.md` — tabela wymagań ze statusami (czytaj tylko gdy szukasz konkretnego REQ-ID)
- `docs/usage.md` — parametry CLI i konfiguracja
- `docs/changelog.md` — ostatnie zmiany (czytaj gdy potrzebujesz kontekstu historycznego)

**Nie czytaj całej tabeli wymagań** — jest obszerna. Szukaj konkretnego REQ-ID lub obszaru gdy naprawdę potrzebujesz.

## Struktura projektu

Cały kod aplikacji jest w `otomoto-scraper/`. Pipeline przebiega w kolejności:

```
scrapers/ + parsers/   →  storage.py  →  analytics.py  →  enrichment_*  →  llm_worker.py  →  notifications.py
```

Kluczowe pliki:

- `main.py` — punkt wejścia CLI, orkiestracja pipeline'u
- `scraper.py` — Playwright, paginacja Otomoto
- `parser.py` — deleguje do `parsers/otomoto.py` lub `parsers/mobile_de.py`
- `storage.py` — CSV storage, upsert ofert, zarządzanie `enrichment_queue.csv`
- `analytics.py` — market scoring, segmentacja porównawcza, `deal_score`/`confidence_score`
- `enrichment_worker.py` — pobieranie detail page, normalizacja `parametersDict`
- `enrichment_analysis.py` — deterministyczna analiza sygnałów jakościowych
- `llm_worker.py` — ocena OpenAI: batch + `OnDemandSession` / `review_single()` dla powiadomień
- `notifications.py` — event engine, deduplikacja, kanał log/Telegram
- `preferences.py` — twarde filtry + miękkie preferencje + `source_adjustments`
- `config.py` — ładowanie `queries.json` i `preferences.json`

## Zasady projektowe (kluczowe)

- `market_score` jest liczony bez udziału preferencji użytkownika — preferencje działają jako osobna warstwa.
- Enrichment jest selektywny — pobierane są tylko oferty spełniające reguły z `enrichment_selector.py`.
- LLM jest **tylko komentatorem** — nie blokuje ani nie generuje eventów powiadomień.
- Każde źródło danych (`otomoto`, `mobile_de`) ma własną parę scraper+parser; warstwy storage/analytics/notifications są wspólne.
- Oferty `source=mobile_de` są pomijane przez `enrichment_worker.py` (brak sidecar JSON nie blokuje scoringu).

## Kontrakty danych

Pola CSV storage per oferta (kluczowe):
`listing_id`, `title`, `price_pln`, `year`, `mileage_km`, `fuel_type`, `gearbox`, `power_hp`, `seller_type`,
`is_damaged`, `is_active`, `source`, `decision_bucket`, `final_score`, `confidence_score`,
`details_status`, `details_damaged_flag`, `details_imported_flag`,
`llm_verdict`, `llm_risk_level`, `llm_summary`

Szczegółowy kontrakt: `docs/architecture.md` → sekcja "Kontrakt danych analityki i enrichmentu".

## Testy

```powershell
uv run pytest tests/
```

Testy są w `tests/`. Nazwy plików: `test_<moduł>.py`. Nie ma fixtures globalnych — każdy test mockuje po swojemu.

## Konfiguracja

- `otomoto-scraper/queries.json` — kwerendy (wzorzec: `queries.example.json`)
- `otomoto-scraper/preferences.json` — preferencje użytkownika (wzorzec: `preferences.example.json`)
- Dane: `data/otomoto/` — CSV, kolejka enrichmentu, state powiadomień, analytics JSON, sidecar JSON

## Minimalizacja czytania tokenów

1. Czytaj tylko jeden plik na raz, zaczynając od tego, który dotyczy konkretnego zadania.
2. Nie czytaj `docs/requirements.md` o ile nie jesteś wprost poproszony o aktualizację wymagań.
3. Przed modyfikacją modułu X sprawdź `docs/architecture.md` → odpowiednią sekcję zamiast czytać kod innych modułów.
4. Zmienne konfiguracyjne — sprawdź w `config.py` i `preferences.py`, nie w `main.py`.
