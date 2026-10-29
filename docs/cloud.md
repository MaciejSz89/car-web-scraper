# CarWebScraper — Migracja do chmury (analiza i plan)

Status: **propozycja do decyzji** (REQ-070). Dokument opisuje, co przenosimy, gdzie są ryzyka i w jakiej kolejności to robić. Ceny są orientacyjne i przed decyzją trzeba je sprawdzić w cennikach dostawców.

## Spis treści

- [1. Charakterystyka obciążenia](#1-charakterystyka-obciążenia)
- [2. Ryzyka](#2-ryzyka)
- [3. Opcje docelowe](#3-opcje-docelowe)
- [4. Rekomendacja](#4-rekomendacja)
- [5. Plan etapowy](#5-plan-etapowy)
- [6. Pilot — kryteria sukcesu](#6-pilot--kryteria-sukcesu)
- [7. Bezpieczeństwo i sekrety](#7-bezpieczeństwo-i-sekrety)
- [8. Decyzje do podjęcia](#8-decyzje-do-podjęcia)

---

## 1. Charakterystyka obciążenia

| Cecha | Stan obecny | Konsekwencja dla chmury |
|---|---|---|
| Wzorzec pracy | Batch co 30 min (`--loop`), każda iteracja to kilka–kilkanaście minut | Pasuje zarówno do stałej maszyny, jak i do zadań planowanych (scheduled jobs) |
| Zasoby | 2 przeglądarki headless (Chromium + Camoufox/Firefox), sekwencyjnie | ~1,5–2 GB RAM w szczycie, 1–2 vCPU; `/dev/shm` ≥ 1 GB |
| Stan | Pliki CSV + sidecar JSON + stan sesji przeglądarki (~141 MB, rośnie) | Wymaga trwałego dysku; brak transakcji i blokad, więc może działać **tylko jedna instancja** |
| Ruch wychodzący | otomoto.pl, mobile.de (ochrona Akamai), OpenAI API, Telegram API | Reputacja adresu IP jest kluczowa (patrz ryzyka) |
| Ruch przychodzący | brak | Nie ma potrzeby wystawiać portów, load balancera ani domeny |
| Sekrety | `OPENAI_API_KEY`, tokeny Telegram (zmienne środowiskowe) | Gotowe do podpięcia pod secret manager |

Aplikacja jest już przygotowana na kontener: dane i konfigurację wskazują zmienne `CARSCRAPER_DATA_DIR` i `CARSCRAPER_CONFIG_DIR`, a obraz trafia do GHCR (patrz [deployment.md](deployment.md)).

---

## 2. Ryzyka

### R1. Blokady anty-botowe z adresów IP centrów danych — **krytyczne**

Najważniejsze pytanie migracji nie dotyczy technologii, tylko tego, czy otomoto.pl i mobile.de wpuszczą ruch z chmury. Pule adresów AWS, GCP, Azure i Hetznera są powszechnie znane i systemy typu Akamai traktują je ostrzej niż łącza domowe. Projekt już raz trafił na blokadę Akamai (commit `4e441e1`: scraper zwracał 0 ofert).

Ograniczanie ryzyka:
- **Pilot przed migracją** (sekcja 6): tydzień pracy z wybranego dostawcy i regionu, pomiar odsetka pustych lub zablokowanych stron.
- Region w Polsce lub w Niemczech, żeby IP było spójne z językiem i strefą czasową przeglądarki (Camoufox `geoip=True` dopasowuje je do IP).
- Zachowanie obecnego throttlingu i interwału; żadnego równoległego scrapowania.
- Wyjścia awaryjne: proxy rezydencyjne (dodatkowy koszt zależny od transferu, a Playwright pobiera też obrazki) albo **hybryda**: scraping na domowym urządzeniu z IP domowym, reszta pipeline'u w chmurze.

### R2. Stan w plikach CSV — **wysokie przy serverless, niskie na VM**

CSV są przepisywane w całości i nie mają blokad. Na VM z dyskiem lokalnym działa to tak samo jak dziś. W modelu serverless (efemeryczny dysk) trzeba albo montować sieciowy system plików (wolne przepisywanie, brak blokad), albo najpierw zrealizować REQ-059 (SQLite), a później ewentualnie przejść na zarządzanego Postgresa.

### R3. Brak sygnalizacji porażki — **średnie**

`main.py` kończy się kodem 0 nawet wtedy, gdy wszystkie kwerendy zawiodły. Scheduler w chmurze nie odróżni wtedy porażki od sukcesu, a blokada może trwać dniami niezauważona. Potrzebne są: niezerowy kod wyjścia w trybie jednorazowym i alert Telegram przy N kolejnych pustych przebiegach (REQ-071).

### R4. Regulaminy serwisów — **do weryfikacji**

Scraping z infrastruktury komercyjnej może być oceniany inaczej niż użycie prywatne. Przed migracją warto przeczytać regulaminy otomoto.pl i mobile.de i utrzymać niskie obciążenie.

---

## 3. Opcje docelowe

| | A. Pojedynczy VM + docker compose | B. Zadanie kontenerowe na harmonogram (serverless) | C. Kubernetes | D. Hybryda |
|---|---|---|---|---|
| Przykłady | Hetzner Cloud CX22/CPX21, GCP e2-medium, Azure B2s, AWS t4g/t3.small | GCP Cloud Run Jobs + Cloud Scheduler, Azure Container Apps Jobs, AWS ECS Fargate scheduled task | GKE / AKS / EKS / k3s | Scraper na domowym mini-PC, w chmurze enrichment, LLM, powiadomienia i backup |
| Zmiany w kodzie | **Brak** — ten sam `compose.yaml` | Tryb jednorazowy (bez `--loop`), stan poza kontenerem (REQ-059), kody wyjścia (REQ-071) | Jak B + manifesty | Podział pipeline'u, synchronizacja stanu |
| Stan | Dysk VM + backup do object storage | Sieciowy system plików albo baza | PersistentVolume | Dwa miejsca, synchronizacja |
| Koszt / mies. (orientacyjnie) | ~5–10 € (Hetzner), ~25–35 USD (hyperscalerzy) | ~0–35 USD zależnie od długości przebiegu i darmowego limitu dostawcy | Najwyższy (płatny control plane i węzły) | Prąd + mały VM |
| Operacje | Aktualizacje OS, Docker, backup — po naszej stronie | Najmniej: brak serwera | Najwięcej | Najwięcej punktów awarii |
| Ryzyko R1 | Jedno stałe IP: łatwo zmierzyć, łatwo dostać trwały ban | IP zmienne, z puli dostawcy | Jak A/B | **Najniższe** |
| Ocena | ✅ Etap 1 | ✅ Etap 3 (opcjonalnie) | ❌ Przerost formy dla jednego zadania | 🔁 Plan B, jeśli R1 się potwierdzi |

Uwaga dla maszyn ARM (Hetzner CAX, AWS Graviton, OCI Ampere): obraz jest dziś budowany tylko dla `linux/amd64`. ARM wymaga buildu multi-arch i sprawdzenia, czy Camoufox działa na `arm64`.

---

## 4. Rekomendacja

**Etap 1: przeniesienie 1:1 (lift & shift) na pojedynczy VM x86 w UE z docker compose, poprzedzone pilotem anty-botowym.**

Uzasadnienie:
- zero zmian w kodzie: obraz i `compose.yaml` już działają lokalnie,
- jedno stałe IP pozwala jednoznacznie zmierzyć ryzyko R1 przed dalszymi inwestycjami,
- najniższy koszt i najprostsze wycofanie (dane to jeden katalog).

Wybór dostawcy zależy od tego, dokąd chcemy dojść w etapie 3:
- tylko VM na stałe → **Hetzner** (najtańszy, lokalizacje w DE),
- docelowo serverless → **GCP, region `europe-central2` (Warszawa)**: VM teraz, Cloud Run Jobs później, ten sam projekt, Secret Manager i Artifact Registry albo GHCR.

---

## 5. Plan etapowy

### Etap 0 — gotowość repo ✅ (v0.2.0)

- [x] Obraz Docker z obiema przeglądarkami, użytkownik bez uprawnień root (REQ-067)
- [x] Konfiguracja ścieżek i trybu headless przez zmienne środowiskowe (REQ-069)
- [x] SemVer, CI i publikacja obrazu do GHCR na tagu (REQ-068)
- [x] Sekrety wyłącznie przez env; prywatne pliki usunięte z indeksu git

### Etap 1 — pilot i przeniesienie (VM)

1. Utworzenie VM (2 vCPU / 4 GB RAM, x86, region PL/DE), instalacja Dockera, firewall bez portów przychodzących poza SSH (najlepiej tylko po kluczu).
2. Wgranie `compose.yaml`, `.env` (`chmod 600`) i katalogu konfiguracji; `docker compose pull && up -d`.
3. **Pilot** równolegle z lokalną instancją, na osobnym katalogu danych i z wyłączonymi powiadomieniami (kryteria w sekcji 6).
4. Po pozytywnym pilocie: zatrzymanie instancji lokalnej, przeniesienie `data/otomoto` (rsync), start w chmurze z powiadomieniami.
5. Codzienny backup katalogu danych do object storage (retencja 30 dni) i jednorazowy test odtworzenia.

### Etap 2 — przygotowanie aplikacji pod chmurę

- REQ-071: niezerowy kod wyjścia, gdy wszystkie kwerendy zawiodą; alert Telegram po N kolejnych pustych przebiegach; plik heartbeat z czasem ostatniego udanego przebiegu.
- REQ-059: migracja CSV → SQLite (jeden plik, transakcje, prostszy backup).
- Opcjonalnie: logi w formacie JSON (łatwiejsze filtrowanie w Cloud Logging / Loki).

### Etap 3 (opcjonalny) — serverless

- Cloud Run Job (lub odpowiednik) uruchamiany przez scheduler co 30 min, bez `--loop`.
- Stan: SQLite na wolumenie albo zarządzany Postgres, gdy pojawi się potrzeba wielu instancji lub dashboardu.
- Sekrety z Secret Managera, obraz z rejestru, limit czasu zadania > najdłuższy przebieg.

---

## 6. Pilot — kryteria sukcesu

Czas trwania: **7 dni**, ta sama konfiguracja kwerend co lokalnie.

| Metryka | Próg akceptacji | Jak mierzyć |
|---|---|---|
| Przebiegi z ≥ 1 ofertą per kwerenda | ≥ 95% | logi `pages_with_results`, liczba ofert w CSV |
| Blokady Akamai / CAPTCHA | ≤ 1 dziennie, bez blokady trwającej > 2 h | logi + `debug-errors/` |
| Zgodność z instancją lokalną | ≥ 90% tych samych `listing_id` na kwerendę | porównanie CSV |
| Pamięć | szczyt < 3 GB | `docker stats` |
| Czas przebiegu | < 50% interwału | logi startu i końca iteracji |

Niespełnienie progu blokad → próba w innym regionie lub u innego dostawcy, potem opcja D (hybryda) albo proxy.

---

## 7. Bezpieczeństwo i sekrety

- Sekrety tylko w `.env` na serwerze (`chmod 600`, poza repo) albo w secret managerze dostawcy; nigdy w obrazie ani w `preferences.json`.
- Obraz działa jako użytkownik bez uprawnień root; kontener nie wystawia portów.
- **Historia git:** plik `.playwright-session-state.json` (ciasteczka sesji otomoto.pl) był wcześniej commitowany. Od v0.2.0 nie jest śledzony, ale zostaje w historii. Ciasteczka są dawno nieaktualne, więc ryzyko jest niskie. Jeśli repo ma być publiczne, warto oczyścić historię (`git filter-repo`) i zastąpić repo na GitHubie.
- Dostęp SSH tylko po kluczu; automatyczne aktualizacje bezpieczeństwa (`unattended-upgrades`).
- Pakiet GHCR: prywatny, jeśli repo jest prywatne.

---

## 8. Decyzje do podjęcia

| # | Decyzja | Opcje | Rekomendacja |
|---|---|---|---|
| D1 | Dostawca i region | Hetzner (DE) / GCP Warszawa / Azure Poland Central / AWS eu-central-1 | Hetzner, jeśli docelowo VM; GCP Warszawa, jeśli docelowo serverless |
| D2 | Akceptacja proxy rezydencyjnych w razie blokad | tak / nie / najpierw hybryda | Najpierw hybryda |
| D3 | Termin REQ-059 (SQLite) | przed etapem 1 / w etapie 2 | Etap 2 — nie blokuje przeniesienia na VM |
| D4 | Widoczność repo i obrazu | prywatne / publiczne | Prywatne (patrz historia git w sekcji 7) |
| D5 | Budżet miesięczny | — | Do ustalenia; etap 1 mieści się w ~10 € |
