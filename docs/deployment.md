# CarWebScraper — Uruchamianie w kontenerze (Docker)

Obraz zawiera wszystko, czego potrzebuje pipeline: Python 3.13, zależności z `uv.lock`, Chromium (Playwright — scraping Otomoto) oraz Camoufox (Firefox — mobile.de i enrichment). Dane, konfiguracja i sekrety są **poza obrazem**.

## Spis treści

- [Model uruchomieniowy](#model-uruchomieniowy)
- [Szybki start (docker compose)](#szybki-start-docker-compose)
- [Zmienne środowiskowe](#zmienne-środowiskowe)
- [Wolumeny i pliki](#wolumeny-i-pliki)
- [Typowe operacje](#typowe-operacje)
- [Obraz z rejestru (GHCR)](#obraz-z-rejestru-ghcr)
- [Kopie zapasowe](#kopie-zapasowe)
- [Rozwiązywanie problemów](#rozwiązywanie-problemów)

---

## Model uruchomieniowy

| Element | W kontenerze | Źródło |
|---|---|---|
| Kod aplikacji | `/app/otomoto-scraper/` | obraz |
| Dane (CSV, kolejki, sidecar JSON, stan sesji przeglądarki) | `/data` | volume / bind mount |
| Konfiguracja (`queries.json`, `preferences.json`) | `/config` (read-only) | bind mount; gdy brak plików → `*.example.json` z obrazu |
| Sekrety (OpenAI, Telegram) | zmienne środowiskowe | `.env` / secret manager |

- `ENTRYPOINT` to `python otomoto-scraper/main.py`. Wszystkie flagi CLI z [usage.md](usage.md) działają bez zmian.
- Domyślne `CMD`: `--run-enrichment --run-notifications --loop` (tryb ciągły, co 30 min).
- Kontener działa jako użytkownik `app` (UID 1000), nie root.
- Przeglądarki zawsze w trybie headless (`CARSCRAPER_HEADLESS=1`).

---

## Szybki start (docker compose)

```powershell
Copy-Item .env.example .env      # uzupełnij OPENAI_API_KEY, tokeny Telegram
docker compose up -d --build     # build + start w tle
docker compose logs -f           # podgląd logów
```

Compose montuje:

- `./data/otomoto` → `/data` (te same dane, których używa uruchomienie lokalne przez `uv run`),
- `./otomoto-scraper` → `/config` (lokalne `queries.json` i `preferences.json`).

Dzięki temu można przełączać się między `uv run` a Dockerem bez migracji danych. **Nie uruchamiaj obu naraz** — CSV nie mają blokad i jednoczesny zapis z dwóch procesów może je uszkodzić.

---

## Zmienne środowiskowe

### Aplikacja

| Zmienna | Domyślnie (lokalnie) | Domyślnie (obraz) | Opis |
|---|---|---|---|
| `CARSCRAPER_DATA_DIR` | `<repo>/data/otomoto` | `/data` | Katalog danych |
| `CARSCRAPER_CONFIG_DIR` | `<repo>/otomoto-scraper` | `/config` | Katalog z `queries.json` i `preferences.json` |
| `CARSCRAPER_HEADLESS` | `0` | `1` | Tryb headless, gdy nie podano `--headless`/`--no-headless` |

### Sekrety

Nazwy zmiennych wskazują pola `*_env` w `preferences.json` — poniżej wartości domyślne z `preferences.example.json`.

| Zmienna | Wymagana gdy |
|---|---|
| `OPENAI_API_KEY` | `--run-llm` lub komentarze LLM w powiadomieniach |
| `OTOMOTO_TELEGRAM_BOT_TOKEN` | kanał Telegram włączony |
| `OTOMOTO_TELEGRAM_CHAT_ID` (`_2`, …) | kanał Telegram włączony |

### Tylko docker compose

| Zmienna | Domyślnie | Opis |
|---|---|---|
| `CARSCRAPER_VERSION` | `latest` / `dev` | Tag obrazu i wersja wpisywana do etykiet |
| `CARSCRAPER_LOOP_INTERVAL` | `1800` | Przerwa między iteracjami w sekundach |
| `CARSCRAPER_HOST_DATA_DIR` | `./data/otomoto` | Katalog danych na hoście |
| `CARSCRAPER_HOST_CONFIG_DIR` | `./otomoto-scraper` | Katalog konfiguracji na hoście |

---

## Wolumeny i pliki

Zawartość `/data` (patrz też [usage.md → Pliki danych](usage.md#pliki-danych)):

| Ścieżka | Uwagi |
|---|---|
| `<model>.csv` | Historia ofert — **dane krytyczne**, obejmij backupem |
| `enrichment_queue.csv`, `notification_state.csv`, `notification_history.csv` | Stan pipeline'u — utrata = ponowne powiadomienia/enrichment |
| `details/`, `analytics/` | Odtwarzalne (sidecar JSON wymaga ponownego pobrania) |
| `.session-state*.json` | Ciasteczka przeglądarki; utrata = nowa sesja (większe ryzyko blokady) |
| `debug-errors/` | Zrzuty HTML przy błędach — można czyścić |

---

## Typowe operacje

```powershell
# Jednorazowy przebieg bez pętli
docker compose run --rm scraper --run-enrichment --run-notifications

# Tylko enrichment + powiadomienia, bez scrapowania
docker compose run --rm scraper --dry-run --run-enrichment --run-notifications

# Pełny pipeline z LLM
docker compose run --rm scraper --run-enrichment --run-llm --run-notifications

# Lokalna analityka CSV
docker compose run --rm --entrypoint python scraper analyze.py

# Wersja obrazu
docker compose run --rm scraper --version

# Aktualizacja po zmianach w kodzie
docker compose up -d --build
```

Zatrzymanie (`docker compose stop`) wysyła SIGTERM; `init: true` dba o poprawne zamknięcie procesów przeglądarek.

---

## Obraz z rejestru (GHCR)

Każdy release (`vX.Y.Z`, patrz [releasing.md](releasing.md)) publikuje obraz:

```
ghcr.io/maciejsz89/car-web-scraper:0.2.0
ghcr.io/maciejsz89/car-web-scraper:0.2
ghcr.io/maciejsz89/car-web-scraper:latest
```

Na serwerze nie trzeba budować obrazu:

```bash
CARSCRAPER_VERSION=0.2.0 docker compose pull
CARSCRAPER_VERSION=0.2.0 docker compose up -d --no-build
```

Jeśli pakiet w GHCR jest prywatny, najpierw `docker login ghcr.io` tokenem z uprawnieniem `read:packages`.

---

## Kopie zapasowe

Minimum: codzienna kopia `CARSCRAPER_HOST_DATA_DIR` bez `debug-errors/`, np.:

```bash
tar --exclude=debug-errors -czf "backup-$(date +%F).tar.gz" -C ./data otomoto
```

W chmurze — kopia do object storage (S3/GCS/Azure Blob) z retencją, patrz [cloud.md](cloud.md).

---

## Rozwiązywanie problemów

| Objaw | Przyczyna / rozwiązanie |
|---|---|
| Chromium pada z `Target crashed` / brak pamięci | Za mały `/dev/shm` — w compose jest `shm_size: 1gb`; przy `docker run` dodaj `--shm-size=1g` |
| 0 ofert dla kwerendy, log o blokadzie | Blokada anty-botowa (Akamai). Oferty nie są dezaktywowane. Odczekaj, nie skracaj interwału; w chmurze patrz [cloud.md → Ryzyka](cloud.md#2-ryzyka) |
| `Permission denied` przy zapisie do `/data` | Katalog na hoście musi być zapisywalny dla UID 1000 (`chown -R 1000:1000 data/otomoto` na Linuksie) |
| Powiadomienia nie wychodzą | Brak zmiennych Telegram w `.env` — sprawdź log `bot_token/chat_id are missing` |
| Kontener używa przykładowych kwerend | Brak `queries.json` w `CARSCRAPER_HOST_CONFIG_DIR` — log startowy pokazuje użyty katalog `config=` |
