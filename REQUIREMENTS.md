# CarWebScraper Requirements

Ten plik jest źródłem prawdy dla wymagań projektu.
Aktualizujemy go przy każdym nowym, zmienionym, wykonanym lub usuniętym wymaganiu.

## Statusy

- `planned` - wymaganie zaakceptowane, jeszcze niewykonane
- `in-progress` - praca trwa
- `done` - wykonane
- `removed` - usunięte lub porzucone

## Zasady aktualizacji

- Każde wymaganie ma stałe ID, np. `REQ-001`.
- Zmieniamy status istniejącego wpisu zamiast tworzyć duplikat.
- Istotne zmiany dopisujemy także do sekcji `Change Log`.
- Wymagania przyszłe zapisujemy od razu, nawet jeśli są odległe w czasie.

## Active Requirements

| ID      | Status  | Obszar        | Wymaganie                                                                          | Uwagi                                                              |
| ------- | ------- | ------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| REQ-001 | planned | Scraping      | System ma pobierać listy ogłoszeń z Otomoto dla zdefiniowanych kwerend.            | Już działa w obecnej wersji, ale traktujemy jako wymaganie bazowe. |
| REQ-002 | planned | Storage       | System ma zapisywać historię ofert, w tym aktywność, daty obserwacji i zmiany cen. | Obecnie realizowane przez CSV.                                     |
| REQ-003 | planned | Analytics     | System ma mieć osobną warstwę analityczną do wykrywania okazji cenowych.           | Warstwa powinna być oddzielona od scrapera.                        |
| REQ-004 | planned | Analytics     | Okazje mają być wykrywane najpierw przez tani scoring oparty o dane z listingu.    | Bez wchodzenia w szczegóły dla wszystkich ofert.                   |
| REQ-005 | planned | Enrichment    | Szczegółowe dane tekstowe mają być pobierane tylko dla wybranych ofert.            | Np. nowe oferty, mocny spadek ceny, wysoki score.                  |
| REQ-006 | planned | LLM           | W późniejszym etapie system ma filtrować kandydatów z użyciem LLM.                 | LLM ma działać po wstępnym scoringu.                               |
| REQ-007 | planned | Notifications | W końcowym etapie system ma wysyłać powiadomienia o okazjach.                      | Kanały: email lub Telegram.                                        |

## Done Requirements

Na razie brak wpisów.

## Removed Requirements

Na razie brak wpisów.

## Change Log

| Date       | Change                                                                                                                                |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-04-07 | Utworzono plik wymagań i zapisano początkowy zestaw wymagań dla warstwy scrapingu, storage, analytics, enrichment, LLM i powiadomień. |
