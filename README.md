# car-web-scraper

Scraper ogłoszeń samochodowych z Otomoto z warstwą analityczną, enrichmentem i powiadomieniami.

## Funkcje

- Scraping list ogłoszeń dla dowolnych kwerend (model/rok/filtr)
- Zapis historii ofert do CSV — aktywność, daty, zmiany cen
- Analityka rynkowa: scoring ofert na tle segmentu porównywalnych pojazdów
- Selektywny enrichment: pobieranie szczegółów tylko dla wybranych, wysokoscorowanych ofert
- Warstwa LLM (OpenAI): ocena jakościowa kandydatów z automatycznym komentarzem dołączanym do powiadomień
- Warstwa preferencji użytkownika (twarde filtry + miękkie korekty rankingu)
- Powiadomienia o nowych okazjach z deduplikacją (log, Telegram)

## Struktura projektu

```
otomoto-scraper/
  main.py              # punkt wejścia CLI
  scraper.py           # Playwright scraper list ogłoszeń z paginacją
  parser.py            # parser kart ofert HTML
  storage.py           # CSV storage + zarządzanie enrichment_queue
  analytics.py         # scoring rynkowy i segmentacja porównawcza
  enrichment_worker.py # worker pobierający szczegóły wybranych ofert
  enrichment_selector.py / enrichment_runner.py  # selekcja kandydatów do enrichmentu
  enrichment_analysis.py  # analiza sygnałów jakościowych z detail page
  notifications.py     # pipeline powiadomień (eventy, deduplikacja, Telegram, LLM on-demand)
  llm_worker.py        # ocena ofert przez OpenAI: batch run + on-demand dla powiadomień
  preferences.py       # warstwa preferencji użytkownika
  config.py            # stałe konfiguracyjne i ładowanie queries/preferences
  utils.py             # narzędzia pomocnicze (clean_text, detect_damage, …)
  queries.json         # definicje kwerend scrapowania
  preferences.json     # preferencje użytkownika
data/otomoto/
  <model>.csv          # historia ofert per kwerenda
  enrichment_queue.csv # kolejka do enrichmentu (samo się czyści po przetworzeniu)
  analytics/           # JSON z wynikami analityki per kwerenda
  details/             # sidecar JSON ze szczegółami ofert
```

## Wymagania

- Python ≥ 3.13
- [uv](https://docs.astral.sh/uv/) (zalecany manager)
- Playwright Chromium: `uv run playwright install chromium`

## Uruchomienie

### Tylko scraping

```powershell
uv run .\otomoto-scraper\main.py --headless
```

### Scraping + enrichment + powiadomienia

```powershell
uv run .\otomoto-scraper\main.py --headless --run-enrichment --run-notifications
```

### Ograniczenie liczby enrichowanych ofert w jednym przebiegu

Kolejka jest sortowana malejąco po priorytecie — przy limicie zawsze przetwarzane są najpierw najważniejsze oferty.

```powershell
uv run .\otomoto-scraper\main.py --headless --run-enrichment --enrichment-limit 50
```

### Tylko enrichment i powiadomienia (bez ponownego scrapowania stron)

`--dry-run` pomija pętlę po kwerendach (brak Playwright), ale w pełni wykonuje enrichment i powiadomienia.

```powershell
uv run .\otomoto-scraper\main.py --dry-run --run-enrichment --run-notifications
```

### Ponowienie nieudanych enrichmentów

```powershell
uv run .\otomoto-scraper\main.py --headless --run-enrichment --retry-failed-enrichment
```

### Lokalna analityka bez scrapowania

```powershell
uv run .\analyze.py
```

## Konfiguracja

- **`otomoto-scraper/queries.json`** — lista kwerend (nazwa, `otomoto_params` z polami `make`/`model`/`year_from`/`fuel_type`/`mileage_to`, plik CSV, max stron); config loader buduje `start_url` z parametrów w czasie ładowania
- **`otomoto-scraper/preferences.json`** — preferencje użytkownika: twarde filtry (przebieg, rok, paliwo) i miękkie korekty scoringu, ustawienia powiadomień (kanał, próg score, Telegram token/chat)

Wzorce plików konfiguracyjnych: `queries.example.json`, `preferences.example.json`.

## Testy

```powershell
uv run pytest tests/
```

## Dokumentacja

| Plik                                           | Zawartość                                                          |
| ---------------------------------------------- | ------------------------------------------------------------------ |
| [`REQUIREMENTS.md`](REQUIREMENTS.md)           | Indeks wymagań ze statusami i linkami                              |
| [`docs/requirements.md`](docs/requirements.md) | Pełna tabela wymagań (REQ-001 … REQ-066)                           |
| [`docs/architecture.md`](docs/architecture.md) | Reguły projektowe, kontrakty danych, reguły scoringu i enrichmentu |
| [`docs/usage.md`](docs/usage.md)               | Pełna instrukcja użytkowania i opis parametrów CLI                 |
| [`docs/changelog.md`](docs/changelog.md)       | Chronologiczny dziennik zmian                                      |
