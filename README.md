# car-web-scraper

[![CI](https://github.com/MaciejSz89/car-web-scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/MaciejSz89/car-web-scraper/actions/workflows/ci.yml)

Scraper ogłoszeń samochodowych z **Otomoto** i **mobile.de** z warstwą analityczną, selektywnym enrichmentem, oceną LLM i powiadomieniami Telegram.

Aktualna wersja: zobacz `pyproject.toml` lub `main.py --version`. Historia zmian: [docs/changelog.md](docs/changelog.md).

## Funkcje

- Scraping list ogłoszeń dla dowolnych kwerend (model/rok/filtr), wiele źródeł (Otomoto, mobile.de)
- Zapis historii ofert do CSV — aktywność, daty, zmiany cen
- Analityka rynkowa: scoring ofert na tle segmentu porównywalnych pojazdów, z uwzględnieniem kosztów importu
- Selektywny enrichment: pobieranie szczegółów tylko dla wybranych, wysoko ocenionych ofert
- Warstwa LLM (OpenAI): ocena jakościowa kandydatów z komentarzem dołączanym do powiadomień
- Warstwa preferencji użytkownika (twarde filtry, miękkie korekty rankingu, kraj pochodzenia)
- Powiadomienia o nowych okazjach z deduplikacją (log, Telegram)

## Pipeline

```
scrapers/ + parsers/ → storage.py → analytics.py → enrichment_* → llm_worker.py → notifications.py
```

## Szybki start

### Docker (zalecane do pracy ciągłej)

```powershell
Copy-Item .env.example .env      # uzupełnij OPENAI_API_KEY i tokeny Telegram
docker compose up -d --build
docker compose logs -f
```

Szczegóły: [docs/deployment.md](docs/deployment.md).

### Lokalnie (uv)

Wymagania: Python ≥ 3.13, [uv](https://docs.astral.sh/uv/).

```powershell
uv sync
uv run playwright install chromium
uv run python -m camoufox fetch
uv run .\otomoto-scraper\main.py --headless --run-enrichment --run-notifications
```

Pełna lista flag CLI i scenariuszy: [docs/usage.md](docs/usage.md).

## Konfiguracja

| Co | Gdzie | Wzorzec |
|---|---|---|
| Kwerendy | `otomoto-scraper/queries.json` | `queries.example.json` |
| Preferencje, LLM, kanały powiadomień | `otomoto-scraper/preferences.json` | `preferences.example.json` |
| Sekrety | zmienne środowiskowe / `.env` | `.env.example` |
| Ścieżki danych i konfiguracji, headless | `CARSCRAPER_DATA_DIR`, `CARSCRAPER_CONFIG_DIR`, `CARSCRAPER_HEADLESS` | [docs/usage.md](docs/usage.md#zmienne-środowiskowe) |

`queries.json`, `preferences.json` i `.env` są prywatne (`.gitignore`). Gdy plików JSON brak, aplikacja używa wzorców `*.example.json`.

## Struktura projektu

```
otomoto-scraper/
  main.py                  # punkt wejścia CLI, orkiestracja pipeline'u
  config.py                # ścieżki (env), stałe, ładowanie queries, wersja
  scraper.py, scrapers/    # Playwright / Camoufox — listy ogłoszeń z paginacją
  parser.py, parsers/      # parsery kart ofert per źródło
  storage.py               # CSV storage + enrichment_queue
  analytics.py             # scoring rynkowy i segmentacja porównawcza
  enrichment_selector.py / enrichment_runner.py  # selekcja kandydatów do enrichmentu
  enrichment_worker.py     # pobieranie detail page
  enrichment_analysis.py   # sygnały jakościowe z detail page
  llm_worker.py            # ocena OpenAI: batch + on-demand dla powiadomień
  notifications.py         # eventy, deduplikacja, Telegram
  preferences.py           # warstwa preferencji użytkownika
tests/                     # pytest
docs/                      # dokumentacja (patrz niżej)
Dockerfile, compose.yaml   # konteneryzacja
.github/workflows/         # CI i release
data/otomoto/              # dane runtime (poza git)
```

## Testy

```powershell
uv sync
uv run pytest
```

CI uruchamia testy i build obrazu na każdym pushu do `main` i każdym PR.

## Wersjonowanie i wydania

[SemVer](https://semver.org/lang/pl/), jedyne źródło wersji to `pyproject.toml`. Wydanie powstaje po wypchnięciu taga `vX.Y.Z`: CI publikuje obraz `ghcr.io/maciejsz89/car-web-scraper:X.Y.Z` i tworzy GitHub Release. Procedura: [docs/releasing.md](docs/releasing.md).

## Dokumentacja

| Plik | Zawartość |
|---|---|
| [`REQUIREMENTS.md`](REQUIREMENTS.md) | Indeks wymagań ze statusami |
| [`docs/requirements.md`](docs/requirements.md) | Pełna tabela wymagań (REQ-001 … REQ-071) |
| [`docs/architecture.md`](docs/architecture.md) | Reguły projektowe, kontrakty danych, scoring, enrichment, LLM, powiadomienia |
| [`docs/usage.md`](docs/usage.md) | Instrukcja użytkowania, parametry CLI, zmienne środowiskowe |
| [`docs/deployment.md`](docs/deployment.md) | Docker / compose: wolumeny, sekrety, operacje, backup, troubleshooting |
| [`docs/releasing.md`](docs/releasing.md) | Wersjonowanie, changelog, procedura wydania, CI/CD |
| [`docs/cloud.md`](docs/cloud.md) | Analiza i plan migracji do chmury |
| [`docs/changelog.md`](docs/changelog.md) | Dziennik zmian według wersji |
