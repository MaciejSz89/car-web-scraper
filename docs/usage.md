# CarWebScraper — Instrukcja użytkowania

## Wymagania wstępne

- Python ≥ 3.13
- [uv](https://docs.astral.sh/uv/) (zalecany manager środowiska)
- Playwright Chromium: `uv run playwright install chromium`
- OpenAI API key (wymagany tylko gdy używasz `--run-llm`)
- Telegram Bot token + chat ID (wymagany tylko dla kanału Telegram)

---

## Konfiguracja

### Kwerendy: `otomoto-scraper/queries.json`

Definiuje listę modeli do scrapowania. Każda kwerenda ma:

- `name` — nazwa pliku CSV (bez rozszerzenia) i klucz w `preferences.json`
- `source` — `"otomoto"` lub `"mobile_de"`
- `csv_file` — ścieżka do pliku CSV z wynikami
- `max_pages` — limit stron do przescrapowania
- `enabled` — `true`/`false`

Dla Otomoto używaj klucza `otomoto_params` z polami `make`, `model`, `year_from`, `fuel_type`, `mileage_to` itd. Config loader buduje `start_url` automatycznie.
Pole `start_url` działa jako fallback dla wstecznej kompatybilności.

Wzorzec: `queries.example.json`.

### Preferencje: `otomoto-scraper/preferences.json`

Definiuje preferencje użytkownika:

- `hard_filters` — twarde odrzucenie ofert (przebieg, rocznik, cena, paliwo)
- `soft_preferences` — miękkie korekty scoringu (premia za automat, kara za LPG)
- `boost_rules` — premie za szczególnie pożądane konfiguracje
- `notification_filters` — blokowanie powiadomień mimo dobrego score
- `llm` — konfiguracja warstwy LLM (model, limity, klucz API)
- `source_adjustments` — per-źródło `import_cost_pln` i `reliability_score_bonus`

Wzorzec: `preferences.example.json`.

---

## Uruchomienie

### Tylko scraping

```powershell
uv run .\otomoto-scraper\main.py --headless
```

### Scraping + enrichment + LLM + powiadomienia (pełny pipeline)

```powershell
uv run .\otomoto-scraper\main.py --headless --run-enrichment --run-llm --run-notifications
```

### Ograniczenie liczby enrichowanych ofert

Kolejka jest sortowana malejąco po priorytecie — przy limicie zawsze przetwarzane są najpierw najważniejsze oferty.

```powershell
uv run .\otomoto-scraper\main.py --headless --run-enrichment --enrichment-limit 50
```

### Tylko enrichment i powiadomienia (bez ponownego scrapowania)

`--dry-run` pomija pętlę po kwerendach (brak Playwright), ale w pełni wykonuje enrichment i powiadomienia.

```powershell
uv run .\otomoto-scraper\main.py --dry-run --run-enrichment --run-notifications
```

### Ponowienie nieudanych enrichmentów

```powershell
uv run .\otomoto-scraper\main.py --headless --run-enrichment --retry-failed-enrichment
```

### Ponowienie nieudanych powiadomień

```powershell
uv run .\otomoto-scraper\main.py --dry-run --run-notifications --retry-failed-notifications
```

### Tryb ciągłej pracy (loop)

```powershell
uv run .\otomoto-scraper\main.py --headless --run-enrichment --run-notifications --loop --loop-interval 1800
```

Przerwanie przez `Ctrl+C` kończy pracę czysto po zakończeniu bieżącej iteracji.

### Lokalna analityka bez scrapowania

```powershell
uv run .\analyze.py
```

Czyta istniejące pliki CSV i zapisuje JSON z wynikami analityki do `data/otomoto/analytics/`.

### Naprawa flag enrichmentu bez ponownego scrapowania

Jednorazowa migracja — przetwarza istniejące sidecar JSON i nadpisuje flagi CSV z poprawioną logiką.

```powershell
uv run .\otomoto-scraper\main.py --reprocess-details
```

---

## Parametry CLI — skrócona lista

| Parametr                       | Opis                                                         |
| ------------------------------ | ------------------------------------------------------------ |
| `--headless`                   | Uruchamia Playwright w trybie headless                       |
| `--verbose`                    | Bardziej szczegółowe logi                                    |
| `--dry-run`                    | Pomija scraping (zachowuje enrichment i powiadomienia)       |
| `--run-enrichment`             | Uruchamia etap enrichmentu                                   |
| `--run-llm`                    | Uruchamia etap oceny LLM                                     |
| `--run-notifications`          | Uruchamia etap powiadomień                                   |
| `--enrichment-limit N`         | Limit ofert do enrichmentu w jednym przebiegu                |
| `--retry-failed-enrichment`    | Ponawia enrichmenty ze statusem `failed`                     |
| `--retry-failed-notifications` | Ponawia powiadomienia ze statusem `failed`                   |
| `--llm-limit N`                | Limit ofert do oceny LLM w jednym przebiegu                  |
| `--llm-model MODEL`            | Nadpisuje model LLM z `preferences.json`                     |
| `--loop`                       | Tryb ciągłej pracy                                           |
| `--loop-interval SEC`          | Przerwa między iteracjami w trybie loop (domyślnie 1800 s)   |
| `--reprocess-details`          | Przetwarza sidecar JSON i naprawia flagi CSV bez scrapowania |
| `--cooldown-days N`            | Cooldown enrichmentu w dniach (domyślnie 7)                  |

---

## Testy

```powershell
uv run pytest tests/
```

---

## Pliki danych

| Ścieżka                                 | Opis                                                     |
| --------------------------------------- | -------------------------------------------------------- |
| `data/otomoto/<model>.csv`              | Historia ofert per kwerenda                              |
| `data/otomoto/enrichment_queue.csv`     | Kolejka do enrichmentu (samoczyści się po przetworzeniu) |
| `data/otomoto/notification_state.csv`   | Stan deduplikacji powiadomień per listing                |
| `data/otomoto/notification_history.csv` | Historia wysłanych powiadomień                           |
| `data/otomoto/analytics/`               | Pliki JSON z wynikami analityki per kwerenda             |
| `data/otomoto/details/`                 | Sidecar JSON ze szczegółami ofert z detail page          |
