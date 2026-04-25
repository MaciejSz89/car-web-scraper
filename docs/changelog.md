# CarWebScraper — Changelog

Chronologiczny dziennik istotnych zmian w projekcie. Nowe wpisy dopisuj na górze.

---

## 2026-04-22

- Zaimplementowano scoring świadomy źródła danych (REQ-066): nowa sekcja `source_adjustments` w `preferences.json`/`preferences.example.json` — per-source parametry `import_cost_pln` i `reliability_score_bonus`; `_calculate_market_score()` w `analytics.py` używa efektywnej ceny (cena + koszty importu) do obliczania pozycji vs mediana segmentu; hard-filter `max_price_pln` w `preferences.py` sprawdza efektywną cenę; domyślna konfiguracja: mobile.de → `import_cost_pln: 5000 PLN`.
- Naprawiono paginację mobile.de (REQ-062): `COOKIE_SELECTORS` w `scrapers/mobile_de.py` zawierał błędny selektor `button[data-testid=mde-consent-accept-btn]`; rzeczywisty przycisk „Einverstanden" ma wyłącznie klasę CSS `.mde-consent-accept-btn`; poprawiono na `button.mde-consent-accept-btn` jako priorytetowy selektor; modal GDPR blokował hover nad przyciskiem paginacji.
- Naprawiono błąd normalizacji `parametersDict` z Otomoto (REQ-060): `_normalize_parameters()` w `enrichment_worker.py` brał `.label` zamiast `.values[0].value`, co powodowało `"damaged": "damaged"` i błędnie oznaczało wszystkie oferty jako uszkodzone. Dodano guardy `key==value → None` w `_parameter_flag()`, `_score_parameters()` i `build_prompt()`. Dodano `--reprocess-details` w `main.py` wywołujący `reprocess_details_flags()`.
- Zaplanowano wsparcie dla wielu źródeł danych (REQ-061–064): pole `source` w `queries.json`, wydzielenie scrapera i parsera do `scrapers/` i `parsers/`, nowe moduły `scrapers/mobile_de.py` i `parsers/mobile_de.py`. Enrichment mobile.de odkładany do osobnej iteracji (REQ-064).
- Zaplanowano strukturyzację kwerend Otomoto (REQ-065): klucz `otomoto_params` w `queries.json`.

## 2026-04-20

- LLM przestał wpływać na decyzje o powiadomieniach — usunięto blokowanie przez `llm_verdict=reject`/`llm_risk_level=high` (REQ-052 removed) oraz event `llm-approved` (REQ-053 removed). LLM pełni wyłącznie rolę komentatora.
- Poprawiono jakość komentarzy LLM: `summary` zmienione z jednego zdania na 3-5 zdań, liczba powodów zwiększona do 8, `DEFAULT_MAX_TOKENS` podniesiony do 1600 (REQ-058 updated).
- Naprawiono błąd scrapera: `wait_until_article_count_stabilizes()` wychodziła po 2 rundach z zerową liczbą artykułów, zanim React zamontował listingi. Dodano `page.wait_for_selector("article[data-id]", timeout=20000)` przed pętlą stabilizacji.

## 2026-04-19

- Dodano LLM on-demand w warstwie powiadomień: oferty bez oceny LLM są oceniane przez LLM tuż przed wysłaniem powiadomienia (limit `llm.max_notification_llm_calls` per run, domyślnie 5).
- Naprawiono `upsert_cars_to_csv` w `storage.py`: hardcoded `fieldnames` nie zawierał `details_damaged_flag` ani pól LLM — `writerows` rzucał `ValueError` przy istniejących CSV wzbogaconych przez enrichment/LLM.
- Dodano `retry_failed_notifications()` w `notifications.py` — dostępne przez `--retry-failed-notifications`.
- Dodano mechanizm per-query override filtrów powiadomień w `preferences.json` (klucz `queries.<nazwa_kwerendy>.notification_filters`).
- Poprawka `_calculate_confidence_score` w `analytics.py`: kara za `fallback_level` jest skalowana przez rozmiar grupy porównawczej.
- Zintegrowano wynik LLM z warstwą powiadomień: event type `llm-approved`, deduplikacja przez `llm_notified_verdict`.
- Naprawiono detekcję importu w `enrichment_analysis._score_consistency()` — poprzedni kod nie wykrywał wzorca checkboxa otomoto (`value == key`). Dodano regułę `overseas_import` z karą -8 pkt (REQ-057).
- Naprawiono lukę w wykrywaniu uszkodzonych ofert — strukturalna flaga „Uszkodzony" z `parametersDict` (Next.js) nie była wcześniej uwzględniana. Dodano `_score_parameters()` w `enrichment_analysis.py` (REQ-054).
- Dodano tryb `damaged_handling=llm` w `notification_filters` (REQ-055).
- Dodano flagę `--loop` w `main.py` (REQ-056): nieskończona pętla scrapowania z konfigurowalnymi przerwami.

## 2026-04-18

- Dodano obsługę HTTP 410 Gone w `enrichment_worker.py`: status `gone` oddzielony od `failed`, automatyczny flush wpisów `gone` z kolejki, oznaczenie `is_active=0` w storage CSV.
- Zaimplementowano warstwę LLM (`llm_worker.py`): selekcja kandydatów po enrichmentcie, prompt po polsku, OpenAI API z `response_format=json_object`, hard cap 20, cooldown 30 dni, min_final_score, wymóg sidecar JSON.

## 2026-04-17

- Naprawiono paginację scrapera — selektor `div.eemmnsu4` przestał działać po aktualizacji frontendu Otomoto; zastąpiony selektorami atrybutowymi `button[title='Go to next Page']` / `button[aria-label='Go to next Page']`.
- Naprawiono `AttributeError: 'NoneType' has no attribute 'strip'` w `enrichment_worker.py` przy odczycie `details_status`.
- Dodano samoczyszczenie `enrichment_queue.csv` po każdym przebiegu (`flush_completed_from_queue`). Dodano throttling (1.5–4 s), logi postępu `[X/N]`, parametr `--enrichment-limit N`.
- Naprawiono wiszenie enrichment workera przy dużej kolejce — faza filtrowania buduje teraz jednorazowy indeks w pamięci (O(n×m) → O(n+m)).
- Kolejka enrichmentu jest teraz sortowana malejąco po `priority` przed przetwarzaniem.
- `--dry-run` w `main.py` pomija scraping stron, ale wykonuje enrichment i powiadomienia gdy podano `--run-enrichment`/`--run-notifications`.

## 2026-04-15

- Naprawiono fałszywe powiadomienia dla ofert, gdzie kwota z ogłoszenia była ratą lub elementem cesji, a nie realną ceną auta.
- Rozszerzono i scalono domyślne flagi uszkodzeń z konfiguracją użytkownika w filtrze powiadomień.
- Dodano testy regresyjne dla przypadków `finance/installment` oraz `damage flags`.

## 2026-04-12

- Dodano notification anti-noise controls: opcjonalne `min_confidence_score`, strictersze `allowed_buckets`, konfigurowalna obsługa `reactivated`, okno tłumienia dla `bucket-upgrade` zaraz po reaktywacji.
- Zaostrzono filtrowanie uszkodzonych ofert w powiadomieniach przez `exclude_damaged_listings` plus ciężkie flagi z enrichmentu (`airbags_deployed`, `severe_front_damage` itd.).

## 2026-04-11

- Dodano selektywny pipeline enrichmentu: selekcja kolejki (`enrichment_selector.py`/`enrichment_runner.py`), worker pobierający szczegóły (`enrichment_worker.py`), aktualizacja CSV statusów i opcjonalne uruchomienie z `main.py` przez `--run-enrichment`.
- Poprawiono niezawodność scrapera headless: dodano stealth browser launch flags i maskowanie UA.
- Dodano podstawowy cooldown enrichmentu (domyślnie 7 dni).
- Rozszerzono wyjście CSV enrichmentu o operacyjne pola z detail page.
- Dodano deterministyczną analizę enrichmentu v2 w `enrichment_analysis.py`.
- Zaktualizowano `main.py` o re-run analytics po `--run-enrichment`.
- Dodano pierwszy pipeline powiadomień: per-listing state tracking, deduplikowane eventy, `notification_history.csv`, integracja CLI przez `--run-notifications`.
- Dodano konfigurowalne kanały powiadomień z opcjonalnym transportem Telegram.

## 2026-04-08

- Dodano `seller_type` — ekstrakcja z list-card, zapis do CSV, korekta scoringu w `analytics.py`.
- Zaktualizowano statusy wymagań po pełnej walidacji runtime.

## 2026-04-07

- Zaimplementowano `detect_damage()` — flagi `is_damaged` i `condition_note` w CSV; kara w `analytics.py`.
- Dodano `analyze.py` runner do lokalnej analizy CSV.
- Zaimplementowane: scraping (REQ-001), storage (REQ-002), analytics v1 (REQ-003–REQ-026), preferences (REQ-037–REQ-041), tooling (REQ-044).
- Rozpisano techniczne reguły segmentacji, deal_score v1, selekcji enrichmentu, wejścia do LLM i powiadomień.
