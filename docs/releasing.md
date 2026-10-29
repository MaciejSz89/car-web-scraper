# CarWebScraper — Wersjonowanie i wydania

## Zasady wersjonowania

Projekt stosuje [Semantic Versioning](https://semver.org/lang/pl/) `MAJOR.MINOR.PATCH`:

| Część | Kiedy podbijamy | Przykład |
|---|---|---|
| `MAJOR` | Zmiana niekompatybilna: format CSV/bazy wymagający migracji, usunięte flagi CLI, zmiana struktury `queries.json`/`preferences.json` bez wstecznej zgodności | migracja CSV → SQLite (REQ-059) |
| `MINOR` | Nowa funkcja zgodna wstecz: nowe źródło, nowa flaga, nowe pole w preferencjach z wartością domyślną | nowy scraper, konteneryzacja |
| `PATCH` | Poprawka bez zmiany interfejsu | naprawa selektora paginacji |

Do wersji `1.0.0` (stabilny format danych i konfiguracji) zmiana niekompatybilna może podbijać `MINOR`; musi być jednak opisana w changelogu w sekcji **Zmiany niekompatybilne**.

### Jedno źródło prawdy

Wersja jest zapisana **tylko** w `pyproject.toml` (`[project].version`). Odczytują ją:

- `main.py --version` i log startowy (`config.get_version()`),
- workflow release (porównuje z tagiem),
- etykiety obrazu Docker (`org.opencontainers.image.version`).

---

## Changelog

[`docs/changelog.md`](changelog.md) — najnowsze wpisy na górze. Każde wydanie ma nagłówek:

```markdown
## [0.3.0] — 2026-11-15
```

Zmiany jeszcze niewydane trafiają pod `## [Unreleased]`. Przy wydaniu ta sekcja zmienia nazwę na numer wersji. Workflow release wycina sekcję danej wersji i używa jej jako opisu GitHub Release.

Zalecane podsekcje: **Dodano**, **Zmieniono**, **Naprawiono**, **Usunięto**, **Zmiany niekompatybilne**.

---

## Procedura wydania

1. Upewnij się, że `main` jest zielony w CI.
2. Na gałęzi `release/X.Y.Z` (lub bezpośrednio przez PR):
   - podbij `version` w `pyproject.toml`,
   - `uv lock` (aktualizuje wersję projektu w `uv.lock`),
   - w `docs/changelog.md` zmień `## [Unreleased]` na `## [X.Y.Z] — RRRR-MM-DD`,
   - zaktualizuj statusy w `docs/requirements.md`.
3. Zmerguj do `main`.
4. Utwórz i wypchnij tag:

   ```powershell
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin vX.Y.Z
   ```

5. Workflow [`release.yml`](../.github/workflows/release.yml):
   - sprawdza zgodność tagu z `pyproject.toml` (niezgodność = błąd),
   - uruchamia testy,
   - buduje i publikuje obraz `ghcr.io/maciejsz89/car-web-scraper:{X.Y.Z, X.Y, latest}`,
   - tworzy GitHub Release z sekcją changeloga.

### Hotfix

Poprawka do starszej wersji: gałąź `hotfix/X.Y.(Z+1)` od taga `vX.Y.Z`, ta sama procedura, potem merge do `main`.

---

## CI

[`ci.yml`](../.github/workflows/ci.yml) uruchamia się na każdym pushu do `main` i każdym PR:

- `test` — `uv sync --frozen` + `pytest`,
- `docker` — build obrazu bez publikacji (wykrywa zepsuty `Dockerfile` przed wydaniem).

`--frozen` oznacza, że niezaktualizowany `uv.lock` po zmianie zależności w `pyproject.toml` kończy CI błędem.
