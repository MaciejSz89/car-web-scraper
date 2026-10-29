# CarWebScraper — Wymagania (indeks)

Plik REQUIREMENTS.md jest indeksem i tabelą statusów wymagań.
Szczegółowe reguły i opisy znajdują się w katalogu [`docs/`](docs/).

## Dokumentacja

| Plik | Zawartość |
|---|---|
| [`docs/requirements.md`](docs/requirements.md) | Pełna tabela wymagań (REQ-001 … REQ-071) ze statusami i uwagami |
| [`docs/architecture.md`](docs/architecture.md) | Reguły projektowe, kontrakty danych, reguły segmentacji, deal_score, enrichmentu, LLM i powiadomień |
| [`docs/usage.md`](docs/usage.md) | Instrukcja użytkowania: konfiguracja, parametry CLI, uruchamianie, testy |
| [`docs/deployment.md`](docs/deployment.md) | Uruchamianie w Dockerze: obraz, compose, zmienne środowiskowe, wolumeny, backup |
| [`docs/releasing.md`](docs/releasing.md) | Wersjonowanie SemVer, procedura wydania, CI/CD |
| [`docs/cloud.md`](docs/cloud.md) | Analiza i plan migracji do chmury |
| [`docs/changelog.md`](docs/changelog.md) | Dziennik zmian według wersji |

## Szybki status (aktywne obszary)

| Obszar | Zakończone | Zaplanowane |
|---|---|---|
| Scraping | REQ-001, 050, 056, 061–065 | — |
| Storage | REQ-002, 042 | REQ-059 (SQLite) |
| Analytics | REQ-003–004, 008–012, 017–026, 040–041, 047–048, 066 | — |
| Enrichment | REQ-005, 013–014, 027–030, 046, 049, 051, 054, 057, 060, 064 | — |
| LLM | REQ-006, 015, 031–033, 058 | — |
| Notifications | REQ-007, 016, 034–036, 055 | — |
| Preferences | REQ-037–039 | — |
| Parsing | REQ-043, 045, 063 | — |
| Tooling | REQ-044, 056, 068 | REQ-071 (sygnalizacja porażki) |
| Deployment | REQ-067, 069 | REQ-070 (chmura) |

## Zasady aktualizacji

- Każde wymaganie ma stałe ID (np. `REQ-067`).
- Zmieniamy status istniejącego wpisu zamiast tworzyć duplikat.
- Istotne zmiany dopisujemy do [`docs/changelog.md`](docs/changelog.md).
- Szczegółowe reguły nowych obszarów dodajemy do [`docs/architecture.md`](docs/architecture.md).
