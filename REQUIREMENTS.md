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

| ID      | Status      | Obszar        | Wymaganie                                                                                                                      | Uwagi                                                                                                                                                                                   |
| ------- | ----------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| REQ-001 | done        | Scraping      | System ma pobierać listy ogłoszeń z Otomoto dla zdefiniowanych kwerend.                                                        | Implemented: `otomoto-scraper` działa jako scrapper list.                                                                                                                               |
| REQ-002 | done        | Storage       | System ma zapisywać historię ofert, w tym aktywność, daty obserwacji i zmiany cen.                                             | Implemented: CSV storage w `otomoto-scraper/storage.py`.                                                                                                                                |
| REQ-003 | done        | Analytics     | System ma mieć osobną warstwę analityczną do wykrywania okazji cenowych.                                                       | Implemented: `otomoto-scraper/analytics.py` jako analityka v1.                                                                                                                          |
| REQ-004 | done        | Analytics     | Okazje mają być wykrywane najpierw przez tani scoring oparty o dane z listingu.                                                | Implemented: market scoring bez enrichmentu dla większości ofert.                                                                                                                       |
| REQ-005 | done        | Enrichment    | Szczegółowe dane tekstowe mają być pobierane tylko dla wybranych ofert.                                                        | Implemented: `enrichment_worker.py` pobiera szczegóły tylko z `enrichment_queue.csv` i zapisuje sidecar JSON dla wybranych ofert.                                                       |
| REQ-006 | planned     | LLM           | W późniejszym etapie system ma filtrować kandydatów z użyciem LLM.                                                             | LLM ma działać po wstępnym scoringu.                                                                                                                                                    |
| REQ-007 | in-progress | Notifications | W końcowym etapie system ma wysyłać powiadomienia o okazjach.                                                                  | Implemented first iteration: event engine + deduplikacja + kanał `log`; kanały email/Telegram nadal do wdrożenia.                                                                       |
| REQ-008 | done        | Analytics     | System ma definiować okazję relatywnie do porównywalnych ofert, a nie przez stały próg ceny.                                   | Implemented: segmentacja i porównania do mediany/percentyli w `analytics.py`.                                                                                                           |
| REQ-009 | done        | Analytics     | Warstwa analityczna v1 ma wyliczać wstępny score tylko na podstawie danych dostępnych z listingu.                              | Implemented: deal_score v1 oparty na danych z listingów (lista ofert).                                                                                                                  |
| REQ-010 | done        | Analytics     | System ma grupować oferty do porównań w segmenty podobnych pojazdów.                                                           | Implemented: segment rules + fallback logic w `analytics.py`.                                                                                                                           |
| REQ-011 | done        | Analytics     | Wstępny score ma składać się z wielu sygnałów, a nie tylko z samej ceny.                                                       | Implemented: market position, freshness, price drop, stability, data-quality penalties.                                                                                                 |
| REQ-012 | done        | Analytics     | System ma zwracać wynik analityczny w postaci score oraz listy powodów, które wpłynęły na ocenę.                               | Implemented: `market_reasons` oraz `preference_reasons` w wynikach JSON.                                                                                                                |
| REQ-013 | done        | Enrichment    | System ma kierować do enrichmentu tylko oferty spełniające reguły priorytetyzacji.                                             | Implemented: `enrichment_selector.py`/`enrichment_runner.py` wybierają kandydatów i tworzą kolejkę z priorytetami.                                                                      |
| REQ-014 | done        | Enrichment    | System nie ma pobierać szczegółów każdej oferty przy każdym przebiegu.                                                         | Implemented: `enrichment_worker.py` pomija wpisy `fetched`, a `failed` powtarza tylko po `--retry-failed`.                                                                              |
| REQ-015 | in-progress | LLM           | Do warstwy LLM mają trafiać tylko oferty wyselekcjonowane przez scoring i enrichment.                                          | Spec defined; integration with LLM not implemented yet.                                                                                                                                 |
| REQ-016 | done        | Notifications | Powiadomienia mają być wysyłane tylko dla nowych lub istotnie zmienionych okazji.                                              | Implemented: warstwa powiadomień wysyła eventy tylko przy nowych listingach, reaktywacji, awansie bucketu albo istotnym spadku ceny.                                                    |
| REQ-017 | done        | Analytics     | Segment porównawczy ma zaczynać się od tej samej kwerendy lub modelu bazowego.                                                 | Implemented: analityka buduje grupę porównawczą wyłącznie w obrębie aktywnych ofert z tego samego CSV/kwerendy.                                                                         |
| REQ-018 | done        | Analytics     | Segment porównawczy ma używać reguł tolerancji dla rocznika, przebiegu i parametrów silnika.                                   | Implemented: `SEGMENT_RULES` w `analytics.py` definiują jawne tolerancje dla rocznika, przebiegu, mocy i pojemności.                                                                    |
| REQ-019 | done        | Analytics     | System ma stosować fallback segmentacji, gdy grupa porównawcza jest zbyt mała.                                                 | Implemented: `_build_comparison_group()` przechodzi krokowo po regułach fallbacku i zapisuje `fallback_level`.                                                                          |
| REQ-020 | done        | Analytics     | System ma oznaczać niski poziom zaufania, gdy wynik opiera się na zbyt małej grupie porównawczej.                              | Implemented: `confidence_score` jest obniżany za małą grupę porównawczą i agresywny fallback segmentacji.                                                                               |
| REQ-021 | done        | Analytics     | `deal_score` v1 ma być liczbą znormalizowaną do zakresu `0-100`.                                                               | Implemented as `final_score` clamped to 0-100.                                                                                                                                          |
| REQ-022 | done        | Analytics     | Głównym składnikiem `deal_score` ma być relacja ceny oferty do rynku segmentu porównawczego.                                   | Implemented: `market_position_score` opiera się głównie o relację ceny oferty do mediany i dolnego kwartyla segmentu.                                                                   |
| REQ-023 | done        | Analytics     | `deal_score` ma uwzględniać dodatkowe sygnały czasowe i behawioralne.                                                          | Implemented: scoring uwzględnia świeżość oferty, spadki ceny, liczbę zmian ceny i lekki sygnał typu sprzedawcy.                                                                         |
| REQ-024 | done        | Analytics     | `deal_score` ma uwzględniać karę za niekompletność danych i niski confidence segmentu.                                         | Implemented: analityka nakłada kary za braki danych oraz fallback segmentacji, a confidence jest liczony osobno i wpływa na interpretację wyniku.                                       |
| REQ-025 | done        | Analytics     | Wynik analityczny ma zawierać osobno `deal_score` i `confidence_score`.                                                        | Implemented as `market_score`/`final_score` and `confidence_score`.                                                                                                                     |
| REQ-026 | done        | Analytics     | Wynik analityczny ma klasyfikować oferty do poziomów decyzji.                                                                  | Implemented: buckets `ignore`, `watch`, `candidate`, `high-priority`.                                                                                                                   |
| REQ-027 | done        | Enrichment    | Enrichment ma działać jako osobny etap po wstępnym scoringu.                                                                   | Implemented: osobny `enrichment_worker.py` oraz opcjonalne uruchomienie z `main.py` przez `--run-enrichment`.                                                                           |
| REQ-028 | done        | Enrichment    | System ma nadawać priorytet ofertom kierowanym do enrichmentu.                                                                 | Implemented: kolejka zapisuje `priority`; selektor uwzględnia świeżość, zmiany ceny i typ sprzedawcy.                                                                                   |
| REQ-029 | done        | Enrichment    | System ma ograniczać częstotliwość ponownego enrichmentu tej samej oferty.                                                     | Implemented cooldown 7 dni z bypass po zmianie `price_pln` albo promocji `decision_bucket`; `failed` nadal wraca tylko z `--retry-failed`.                                              |
| REQ-030 | done        | Enrichment    | Wynik enrichmentu ma zapisywać moment pobrania i stan oferty, dla którego pobrano szczegóły.                                   | Implemented pełny kontrakt CSV: `details_status`, `details_priority`, `details_fetched_at`, `details_based_on_*`, `details_fields_present` oraz skrócone pola operacyjne z detail page. |
| REQ-046 | done        | Enrichment    | System ma przetwarzać szczegóły oferty do ustrukturyzowanych sygnałów jakościowych po pobraniu detail page.                    | Implemented: `enrichment_analysis.py` normalizuje opis, wyposażenie, sprzedawcę i sygnały spójności do formy użytecznej dla dalszej analizy.                                            |
| REQ-047 | done        | Analytics     | Wynik po enrichmentcie ma zawierać osobny wynik jakościowy oparty o szczegóły oferty.                                          | Implemented: analytics output zwraca `enrichment_score`, `enrichment_confidence`, `enrichment_reasons` i `enrichment_flags`.                                                            |
| REQ-048 | done        | Pipeline      | System ma mieć drugi etap analizy po enrichmentcie dla ofert, które mają pobrane szczegóły.                                    | Implemented: po `--run-enrichment` `main.py` odświeża pliki analytics, aby uwzględnić świeżo pobrane szczegóły.                                                                         |
| REQ-049 | done        | Enrichment    | Sygnały z detail page nie mogą samodzielnie promować słabej cenowo oferty do okazji, ale mogą obniżać lub wzmacniać priorytet. | Implemented: enrichment działa jako ograniczony korektor `final_score`; dodatni wpływ jest blokowany dla ofert ze słabym `market_score`.                                                |
| REQ-031 | planned     | LLM           | Warstwa LLM ma oceniać tylko ograniczoną liczbę kandydatów po wcześniejszej filtracji.                                         | Potrzebny limit kosztu i liczby analiz per przebieg.                                                                                                                                    |
| REQ-032 | planned     | LLM           | LLM ma zwracać ustrukturyzowany wynik oceny oferty.                                                                            | Co najmniej werdykt, poziom ryzyka, powody i rekomendację dalszego działania.                                                                                                           |
| REQ-033 | planned     | LLM           | LLM ma być filtrem jakościowym, a nie źródłem podstawowej wyceny okazji.                                                       | Ocena cenowa ma pozostać po stronie analityki deterministycznej.                                                                                                                        |
| REQ-034 | done        | Notifications | System ma deduplikować powiadomienia na poziomie oferty i typu zdarzenia.                                                      | Implemented: `notification_state.csv` przechowuje ostatni stan oferty i blokuje ponowne eventy bez nowego sygnału.                                                                      |
| REQ-035 | done        | Notifications | System ma rozróżniać typy zdarzeń powiadomień.                                                                                 | Implemented: event types `new-listing`, `reactivated`, `bucket-upgrade`, `price-drop`.                                                                                                  |
| REQ-036 | done        | Notifications | Powiadomienie ma zawierać skrót powodów decyzji.                                                                               | Implemented: event log zapisuje podsumowanie z bucketa, score, confidence, ceny i skróconych sygnałów analitycznych/enrichment.                                                         |
| REQ-037 | done        | Preferences   | System ma mieć osobną warstwę preferencji użytkownika niezależną od bazowej analityki rynku.                                   | Implemented: `otomoto-scraper/preferences.py` with global + per-query profiles.                                                                                                         |
| REQ-038 | done        | Preferences   | System ma rozróżniać twarde filtry preferencji i miękkie preferencje rankingowe.                                               | Implemented: `hard_filters` and `soft_preferences` support.                                                                                                                             |
| REQ-039 | done        | Preferences   | Preferencje mają dać się konfigurować globalnie i per kwerenda.                                                                | Implemented: merging of global and per-query prefs.                                                                                                                                     |
| REQ-040 | done        | Analytics     | Wynik analityczny ma rozdzielać `market_score`, `preference_score` i `final_score`.                                            | Implemented: `AnalyticsResult` zapisuje osobno wynik rynku, preferencji i wynik końcowy po korekcie enrichmentem.                                                                       |
| REQ-041 | done        | Analytics     | System ma zwracać jawny wynik działania preferencji na ofertę.                                                                 | Implemented: wynik zawiera `hard_filter_passed` i `preference_reasons`, a `preferences.py` zwraca też użyty profil.                                                                     |
| REQ-042 | done        | Storage       | System ma mieć zdefiniowany model danych dla wyniku analityki, enrichmentu, LLM i powiadomień.                                 | Implemented na poziomie specyfikacji: `REQUIREMENTS.md` definiuje minimalny kontrakt danych dla analytics, enrichment, LLM i notifications.                                             |
| REQ-043 | done        | Parsing       | System ma wykrywać wzmianki o uszkodzeniu/kolizji na poziomie list-card i zapisać flagę do CSV.                                | Implemented: `detect_damage()` w `otomoto-scraper/utils.py`, pola `is_damaged`/`condition_note` zapisane w CSV.                                                                         |
| REQ-044 | done        | Tooling       | Repo ma narzędzie do lokalnej analizy CSV (`analyze.py`) do szybkiej weryfikacji scoringu.                                     | Implemented: `analyze.py` zapisuje wyniki do `data/otomoto/analytics/` i drukuje top-oferty.                                                                                            |
| REQ-045 | done        | Parsing       | System ma wykrywać typ sprzedawcy (`private`/`business`) z list-card, zapisywać go do CSV i uwzględniać w scoringu.            | Implemented: parser list-card wykrywa `Prywatny sprzedawca`/`Firma`, zapisuje `seller_type` i stosuje lekką korektę w `analytics.py`.                                                   |

## Preference Layer Rules

### 1. Cel warstwy preferencji

- Warstwa preferencji ma modelować to, czego użytkownik aktualnie szuka, niezależnie od tego, czy oferta jest obiektywnie dobra względem rynku.
- Preferencje nie mogą zmieniać sposobu liczenia segmentu porównawczego ani bazowego `market_score`.
- Zmiana preferencji użytkownika powinna umożliwiać szybkie przeliczenie shortlisty bez przebudowy historii rynku.

### 2. Typy reguł preferencji

- `hard_filters`: reguły odrzucające ofertę z dalszego procesu użytkowego, np. minimalna pojemność silnika albo maksymalny przebieg.
- `soft_preferences`: reguły zwiększające lub zmniejszające `preference_score`, np. premia za automat albo karanie LPG.
- `boost_rules`: dodatkowe premie za szczególnie pożądane konfiguracje, np. wyższy rocznik albo mocniejszy silnik.
- `notification_filters`: reguły blokujące powiadomienia mimo wysokiego `market_score`, jeśli oferta nie pasuje do preferencji użytkownika.

### 3. Zakres konfiguracji preferencji

- Preferencje globalne mają działać dla całego projektu.
- Preferencje per kwerenda mają nadpisywać lub rozszerzać ustawienia globalne dla konkretnego modelu.
- Preferencje powinny obsługiwać co najmniej: minimalny i maksymalny przebieg, minimalną pojemność, minimalną moc, paliwo, skrzynię, budżet i rocznik.

### 4. Wpływ preferencji na pipeline

- `market_score` ma być liczony bez udziału preferencji użytkownika.
- `preference_score` ma być liczony na podstawie konfiguracji preferencji.
- `final_score` ma uwzględniać oba wyniki, ale osobno zapisywać ich źródła.
- Oferta niespełniająca `hard_filters` może zostać zapisana jako ciekawa rynkowo, ale nie powinna trafiać do powiadomień użytkownika.

### 5. Wymagany wynik warstwy preferencji

- `hard_filter_passed`.
- `preference_score` w skali `0-100`.
- `preference_reasons`, czyli lista reguł, które zwiększyły lub obniżyły priorytet.
- `applied_preference_profile`, czyli nazwa profilu lub zestawu reguł użytych do oceny.

## Analytics Output Model

### 1. Minimalny kontrakt wyniku analityki

- `listing_id`.
- `query_name`.
- `market_score`.
- `confidence_score`.
- `preference_score`.
- `final_score`.
- `seller_type`.
- `decision_bucket`.
- `hard_filter_passed`.
- `comparison_group_size`.
- `fallback_level`.
- `market_reasons`.
- `preference_reasons`.
- `enrichment_score`.
- `enrichment_confidence`.
- `enrichment_reasons`.
- `enrichment_flags`.

### 2. Minimalny kontrakt enrichmentu

- `listing_id`.
- `enrichment_priority`.
- `details_status`.
- `details_fetched_at`.
- `details_based_on_price_pln`.
- `details_based_on_last_seen_date`.
- `details_based_on_decision_bucket`.
- `details_fields_present`.

### 2b. Operacyjny skrót enrichmentu w CSV

- `details_description_excerpt`.
- `details_seller_name`.
- `details_vin`.
- `details_country_origin`.
- `details_no_accident_flag`.
- `details_service_record_flag`.
- `details_imported_flag`.
- `details_enrichment_score`.
- `details_enrichment_confidence`.
- `details_enrichment_flags`.

### 2a. Minimalny kontrakt analizy enrichmentu

- `listing_id`.
- `enrichment_score`.
- `enrichment_confidence`.
- `enrichment_reasons`.
- `enrichment_flags`.
- `description_signals`.
- `equipment_signals`.
- `seller_signals`.
- `consistency_signals`.

### 3. Minimalny kontrakt LLM

- `listing_id`.
- `llm_verdict`.
- `llm_risk_level`.
- `llm_confidence`.
- `llm_summary`.
- `llm_reasons`.
- `llm_reviewed_at`.

### 4. Minimalny kontrakt powiadomień

- `listing_id`.
- `event_type`.
- `notification_channel`.
- `notification_decision`.
- `notification_sent_at`.
- `notification_status`.
- `notification_reason_summary`.

## Comparable Offer Segmentation Rules

### 1. Bazowy segment porównawczy

- Oferta jest porównywana najpierw tylko z ofertami z tej samej kwerendy, czyli w praktyce tego samego modelu bazowego.
- Paliwo i typ skrzyni biegów są traktowane jako pola silnie rozdzielające i w pierwszym kroku nie powinny być mieszane.
- Parametr silnika może być reprezentowany przez `power_hp`, a jeśli go brakuje, przez `engine_cm3`.

### 2. Domyślne tolerancje segmentacji v1

- Rocznik: preferowane oferty z przedziału `target_year +/- 1`.
- Przebieg: preferowane oferty z przedziału `target_mileage_km +/- 20000` km.
- Moc: preferowane oferty z przedziału `target_power_hp +/- 15` KM.
- Pojemność silnika: fallback do przedziału `target_engine_cm3 +/- 200` cm3, jeśli brakuje mocy.
- Paliwo: musi być zgodne, jeśli informacja jest dostępna.
- Skrzynia: musi być zgodna, jeśli informacja jest dostępna.

### 3. Minimalna liczność grupy porównawczej

- Bazowy segment powinien zawierać co najmniej `5` aktywnych ofert, aby wynik był uznany za wiarygodny.
- Jeśli segment ma mniej niż `5` ofert, analityka ma przejść do kontrolowanego fallbacku.
- Jeśli po fallbacku nadal jest mniej niż `3` ofert, wynik ma być oznaczony jako niski confidence.

### 4. Kolejność fallbacku

- Krok 1: rozszerzyć rocznik do `target_year +/- 2`.
- Krok 2: rozszerzyć przebieg do `target_mileage_km +/- 30000` km.
- Krok 3: rozszerzyć moc do `target_power_hp +/- 25` KM albo pojemność do `target_engine_cm3 +/- 300` cm3.
- Krok 4: dopuścić porównanie w ramach tej samej kwerendy bez zgodności skrzyni biegów, ale ze spadkiem confidence.
- Krok 5: dopuścić porównanie w ramach tej samej kwerendy bez zgodności dokładnego parametru silnika, ale nadal bez mieszania paliwa, jeśli paliwo jest znane.

### 5. Reguły bezpieczeństwa

- Nie wolno porównywać ofert benzynowych i diesla w jednym segmencie, jeśli obie wartości są znane.
- Nie wolno porównywać ofert z różnych modeli tylko po podobnym roczniku i cenie.
- Oferta z brakami w wielu kluczowych polach ma być liczona, ale z obniżonym confidence.
- Wartość referencyjna rynku powinna pochodzić z mediany lub percentyla grupy porównawczej, a nie ze średniej arytmetycznej.

### 6. Skutek dla dalszej analizy

- Segmentacja ma zwracać nie tylko grupę porównawczą, ale też informację, jaki poziom fallbacku został użyty.
- Poziom fallbacku ma wpływać na confidence i później na końcowy `deal_score`.
- Oferta bardzo tania względem słabego segmentu porównawczego nie powinna automatycznie trafiać do top okazji bez dodatkowej ostrożności.

## Deal Score V1 Rules

### 1. Cel score

- `deal_score` ma odpowiadać na pytanie, czy oferta wygląda atrakcyjnie cenowo i operacyjnie na tle porównywalnych ofert.
- `deal_score` nie jest oceną końcową jakości auta, tylko rankingiem kandydatów do dalszej weryfikacji.
- `confidence_score` ma mówić, jak bardzo można ufać wyliczeniu `deal_score`.

### 2. Zakres i interpretacja

- `deal_score` ma być liczbą z zakresu `0-100`.
- `confidence_score` ma być liczbą z zakresu `0-100`.
- Wysoki `deal_score` przy niskim `confidence_score` ma oznaczać ofertę ciekawą, ale wymagającą ostrożności.
- Wysoki `confidence_score` bez przewagi cenowej nie powinien sam tworzyć okazji.

### 3. Składowe deal_score v1

- `market_position_score`: główny składnik oparty o relację ceny oferty do mediany i dolnych percentyli grupy porównawczej.
- `freshness_score`: premia za nową ofertę lub ofertę świeżo zaktualizowaną z dobrym poziomem ceny.
- `price_drop_score`: premia za istotny spadek ceny względem wcześniejszych obserwacji.
- `stability_score`: lekka korekta za historię zmian ceny i długość obecności na rynku.
- `seller_type_adjustment`: lekka korekta za typ sprzedawcy, z premią dla ofert prywatnych i lekką karą dla ofert firmowych.
- `data_quality_penalty`: kara za brak kluczowych pól potrzebnych do porównania.
- `segment_confidence_penalty`: kara za użycie agresywnego fallbacku lub zbyt małą próbkę porównawczą.

### 4. Priorytet wag

- Największą wagę ma `market_position_score`.
- `freshness_score` i `price_drop_score` są wzmacniaczami, a nie głównym źródłem okazji.
- `stability_score` ma mniejszą wagę niż relacja ceny do rynku.
- `seller_type_adjustment` ma być słabym sygnałem pomocniczym, a nie dominującym czynnikiem.
- Kary za jakość danych i confidence mają działać tłumiąco na końcowy wynik.

## Change Log

- 2026-04-07: Implemented `detect_damage()`; added `is_damaged` and `condition_note` to CSV storage; applied penalty in `analytics.py` (DAMAGE_PENALTY). Backfilled existing CSVs and validated via `analyze.py`.
- 2026-04-07: Added `analyze.py` runner to execute analytics locally and save JSON outputs to `data/otomoto/analytics/`.
- 2026-04-07: Created and later removed temporary `backfill_damage.py` (used for one-off backfill). Deletion committed to repo.
- 2026-04-08: Updated `REQUIREMENTS.md` statuses to reflect implemented features (Scraping, Storage, Analytics v1, Preferences, Tooling). Added REQ-043 and REQ-044.
- 2026-04-08: Added `seller_type` extraction from list-card (`Prywatny sprzedawca`/`Firma`), persisted it to CSV, exposed it in analytics output, and applied a small score adjustment in `analytics.py`.
- 2026-04-11: Added selective enrichment pipeline: queue selection (`enrichment_selector.py`/`enrichment_runner.py`), detail fetch worker (`enrichment_worker.py`), CSV status updates (`details_status`, `details_priority`, `details_fetched_at`) and optional run from `main.py` via `--run-enrichment`.
- 2026-04-11: Improved `headless` scraping reliability in `scraper.py` by adding stealth browser launch flags, realistic user-agent and navigator masking to avoid CloudFront `403` blocks on Otomoto. Smoke test in `--headless` again returned listing cards and pagination logs.
- 2026-04-11: Added basic enrichment cooldown in `enrichment_worker.py` (default `7` days, configurable via `--cooldown-days`). Recently fetched offers are skipped until cooldown expires; stale fetched offers can be reprocessed.
- 2026-04-11: Extended enrichment CSV output with operational detail-page summary fields (`details_description_excerpt`, seller/VIN/origin fields, boolean quality flags and enrichment score/confidence) so the main storage CSV exposes key signals without opening sidecar JSON files.
- 2026-04-11: Added deterministic enrichment analysis v2 in `enrichment_analysis.py` and integrated it into `analytics.py`. Analytics now expose `enrichment_score`, `enrichment_confidence`, `enrichment_reasons` and `enrichment_flags`, and `main.py` re-runs analytics after `--run-enrichment` so the same run benefits from freshly fetched detail pages.
- 2026-04-11: Upgraded enrichment payload to extract real detail fields from offer pages (`description`, `seller`, `price`, `equipment`, `parameters`, feature lists, `__NEXT_DATA__` summary) and persist enrichment metadata in CSV (`details_based_on_price_pln`, `details_based_on_last_seen_date`, `details_based_on_decision_bucket`, `details_fields_present`). Cooldown is now bypassed when price changes or analytics promote the offer to a higher `decision_bucket`.
- 2026-04-11: Extended requirements for enrichment analysis v2. The spec now explicitly covers structured quality/risk signals from detail pages, a separate enrichment output contract, and a second analysis stage that refines shortlisted offers after enrichment.
- 2026-04-11: Synchronized requirement statuses with the implemented analytics and preference stack after full runtime validation. Marked comparable-offer segmentation, market-score composition, explicit preference outputs and the documented data contract as done.
- 2026-04-11: Added first notification pipeline iteration: per-listing state tracking, deduplicated event generation (`new-listing`, `reactivated`, `bucket-upgrade`, `price-drop`), append-only `notification_history.csv`, and CLI integration through `--run-notifications`.

### 5. Reguły interpretacji sygnałów

- Oferta wyraźnie poniżej mediany porównywalnego segmentu powinna dostawać mocną premię.
- Oferta tylko nieznacznie tańsza od rynku nie powinna trafiać wysoko wyłącznie dlatego, że jest nowa.
- Świeża obniżka ceny powinna podnosić priorytet, szczególnie jeśli po obniżce oferta schodzi poniżej mediany segmentu.
- Długo wisząca oferta bez reakcji rynku nie powinna być automatycznie traktowana jako okazja, nawet jeśli jest tańsza od mediany.
- Brak `year`, `mileage_km`, `fuel_type`, `gearbox` lub parametru silnika ma obniżać jakość analizy, jeśli blokuje dobre porównanie.

### 6. Progi decyzyjne v1

- `0-39`: `ignore`.
- `40-59`: `watch`.
- `60-79`: `candidate`.
- `80-100`: `high-priority`.
- Jeśli `confidence_score < 40`, oferta nie może wejść do `high-priority` bez dodatkowego potwierdzenia przez enrichment.

### 7. Wymagany format wyniku analitycznego

- Wynik ma zawierać `deal_score`.
- Wynik ma zawierać `confidence_score`.
- Wynik ma zawierać `decision_bucket`.
- Wynik ma zawierać `comparison_group_size`.
- Wynik ma zawierać `fallback_level`.
- Wynik ma zawierać listę `reasons`, np. "12% poniżej mediany segmentu" albo "niska liczność grupy porównawczej".

### 8. Zasady ostrożności

- Nie wolno windować `deal_score` wyłącznie na podstawie pojedynczego sygnału, jeśli reszta danych jest słaba.
- Oferta nie może dostać najwyższego priorytetu tylko dlatego, że ma bardzo niski przebieg lub bardzo nowy rocznik, jeśli cena nie wyróżnia się względem segmentu.
- `confidence_score` ma obniżać zdolność oferty do przejścia do enrichmentu i LLM, jeśli segmentacja była słaba.
- Wynik ma być wystarczająco czytelny, aby użytkownik mógł zrozumieć, dlaczego oferta została uznana za ciekawą.

## Enrichment Selection Rules

### 1. Cel enrichmentu

- Enrichment ma pobierać dane szczegółowe tylko tam, gdzie dodatkowy koszt wejścia w ogłoszenie ma uzasadnienie analityczne.
- Enrichment jest drugim etapem pipeline'u i nie może być wymagany do podstawowego monitorowania rynku.
- Brak enrichmentu nie może zatrzymywać wyliczenia `deal_score` v1.

### 2. Twarde wyzwalacze wejścia do enrichmentu

- Nowa oferta, która pojawiła się pierwszy raz w danych.
- Oferta z bucketem `high-priority`.
- Oferta z bucketem `candidate` i świeżym spadkiem ceny.
- Oferta z wysokim `deal_score`, ale niskim lub średnim `confidence_score`, jeśli szczegóły mogą pomóc w ocenie.
- Oferta z brakami danych tekstowych lub strukturalnych, które ograniczają decyzję na dalszym etapie.

### 3. Miękkie wyzwalacze wejścia do enrichmentu

- Oferta nowa w bucketcie `watch`, jeśli znajduje się blisko progu `candidate`.
- Oferta długo obserwowana, która nagle zmieniła cenę lub wróciła jako aktywna.
- Oferta wybrana do próbki kontrolnej w celu walidacji jakości scoringu.

### 4. Priorytety kolejki enrichmentu

- Priorytet `P1`: nowe oferty z bucketem `high-priority`.
- Priorytet `P2`: oferty `candidate` lub `high-priority` z istotnym spadkiem ceny.
- Priorytet `P3`: nowe oferty z bucketem `candidate`.
- Priorytet `P4`: oferty `watch`, które są blisko progu `candidate` albo mają niski confidence z powodu braków danych.
- Priorytet `P5`: próbka kontrolna lub odświeżenie starszych szczegółów.

### 5. Reguły ograniczające ponowne pobrania

- Nie pobierać szczegółów ponownie dla tej samej oferty przy każdym przebiegu bez nowego sygnału.
- Ponowny enrichment ma być uruchamiany, jeśli zmieniła się cena, status aktywności albo oferta przekroczyła wyższy bucket decyzji.
- Jeśli szczegóły zostały pobrane niedawno i oferta nie zmieniła istotnie stanu, enrichment ma zostać pominięty.
- Starsze szczegóły mogą być odświeżane okresowo, ale z niższym priorytetem niż nowe okazje.

### 6. Przykładowe warunki pominięcia enrichmentu

- Oferta w bucketcie `ignore` bez istotnej zmiany ceny.
- Oferta z niskim `deal_score` i wysokim confidence, jeśli analiza już stabilnie wskazuje brak okazji.
- Oferta już wzbogacona niedawno, bez zmiany ceny, statusu i bucketu.
- Oferta nieaktywna lub usunięta, jeśli szczegóły nie zostały pobrane wcześniej i nie ma powodu analitycznego do nadrabiania braków.

### 7. Wymagany stan zapisany po enrichmentcie

- `details_fetched_at`.
- `details_based_on_price_pln`.
- `details_based_on_last_seen_date`.
- `details_status`, np. `fresh`, `stale`, `failed`, `not-needed`.
- Lista pobranych pól tekstowych i strukturalnych, aby wiadomo było, co naprawdę udało się pozyskać.

### 8. Zależność od dalszych etapów

- Warstwa LLM ma korzystać przede wszystkim z ofert po enrichmentcie, a nie z samych listingów.
- Oferta z wysokim priorytetem, ale bez enrichmentu, może trafić do kolejki pilnej, lecz nie powinna być traktowana jak pełny kandydat jakościowy.
- Powiadomienia końcowe powinny preferować oferty, które przeszły enrichment lub mają bardzo mocny sygnał z analityki v1.

## Enrichment Analysis Rules

### 1. Cel analizy enrichmentu

- Analiza enrichmentu ma przetwarzać dane z detail page do jawnych sygnałów jakościowych i ryzyk, których nie widać na poziomie list-card.
- Analiza enrichmentu ma działać po pobraniu szczegółów i nie może być warunkiem działania analityki v1.
- Wynik enrichmentu ma doprecyzowywać ocenę kandydata, a nie zastępować bazową ocenę rynkową.

### 2. Zakres sygnałów enrichmentu

- System ma wykrywać sygnały pozytywne w opisie, np. `bezwypadkowy`, `serwis ASO`, `pierwszy właściciel`, `garażowany`, `udokumentowana historia`.
- System ma wykrywać sygnały ryzyka w opisie, np. `uszkodzony`, `do poprawek`, `po kolizji`, `naprawiany`, `brak dokumentów`, `świeżo sprowadzony`.
- System ma brać pod uwagę dane strukturalne z detail page, np. VIN, parametry pojazdu, kraj pochodzenia, typ napędu, wyposażenie i dane sprzedawcy.
- System ma wykrywać niespójności między listingiem a detail page, jeśli cena, parametry lub typ sprzedawcy nie zgadzają się między etapami.

### 3. Wymagany wynik analizy enrichmentu

- Wynik ma zawierać `enrichment_score` w skali `0-100`.
- Wynik ma zawierać `enrichment_confidence` w skali `0-100`.
- Wynik ma zawierać `enrichment_reasons`, czyli listę najważniejszych sygnałów użytych do oceny.
- Wynik ma zawierać `enrichment_flags`, czyli krótkie flagi diagnostyczne, np. `vin_present`, `damage_declared`, `aso_service`, `listing_detail_mismatch`.

### 4. Wpływ enrichmentu na dalszą decyzję

- Enrichment może wzmacniać albo osłabiać priorytet oferty już uznanej za ciekawą cenowo.
- Enrichment może obniżyć ofertę z shortlisty, jeśli wykryje istotne sygnały ryzyka mimo dobrego `market_score`.
- Enrichment nie może samodzielnie promować oferty z niskim `market_score` do najwyższego priorytetu.
- Finalny etap rankingu ma jawnie pokazywać, jaki wpływ miały dane listingowe, preferencje i enrichment.

### 5. Reguły ostrożności dla enrichmentu

- Brak części szczegółów na detail page nie może automatycznie oznaczać wysokiego ryzyka; powinien obniżać przede wszystkim `enrichment_confidence`.
- Pojedyncza pozytywna fraza marketingowa nie może dawać silnej premii bez potwierdzających sygnałów strukturalnych.
- Pojedyncza czerwona flaga o wysokiej istotności może znacząco obniżyć ocenę jakościową nawet przy dobrym wyposażeniu i opisie.
- Reguły enrichmentu mają być deterministyczne i testowalne przed ewentualnym przekazaniem oferty do warstwy LLM.

### 6. Zależność od LLM i powiadomień

- Warstwa LLM ma dostawać enrichment jako ustrukturyzowane wejście, a nie tylko surowy HTML albo pełny JSON strony.
- Powiadomienia końcowe powinny uwzględniać najważniejsze `enrichment_flags` i `enrichment_reasons`, jeśli enrichment był dostępny.
- Oferta bez enrichmentu może trafić do powiadomień tylko wtedy, gdy sygnał z analityki v1 jest bardzo mocny albo enrichment nie był jeszcze możliwy do wykonania.

## LLM Review Rules

### 1. Cel warstwy LLM

- LLM ma pełnić rolę filtra jakościowego dla kandydatów wybranych wcześniej przez analitykę i enrichment.
- LLM nie zastępuje segmentacji ani `deal_score`, tylko ocenia ryzyka i sygnały semantyczne trudne do ujęcia regułami.
- LLM ma działać na ograniczonym zbiorze ofert, aby koszt i czas były kontrolowane.

### 2. Wejście do LLM

- Do LLM trafiają przede wszystkim oferty z bucketem `high-priority` po enrichmentcie.
- Do LLM mogą trafiać oferty `candidate`, jeśli mają mocny sygnał cenowy i wystarczające dane tekstowe po enrichmentcie.
- Oferta bez enrichmentu może trafić do LLM wyjątkowo, jeśli ma bardzo wysoki `deal_score`, ale taki przypadek ma być oznaczony niższym confidence recenzji.
- System ma mieć limit liczby ofert kierowanych do LLM na jeden przebieg.

### 3. Zakres oceny LLM

- LLM ma szukać sygnałów ryzyka w opisie, tytule i polach szczegółowych oferty.
- LLM ma identyfikować wzmianki o szkodzie, naprawach, brakach dokumentacji, problemach prawnych, imporcie, komisie, niejasnej historii i agresywnym marketingu maskującym wady.
- LLM ma wskazywać także pozytywne sygnały, np. serwis ASO, pierwszy właściciel, udokumentowana historia, bezwypadkowość deklarowana wprost.

### 4. Wymagany wynik LLM

- `llm_verdict`, np. `approve`, `review`, `reject`.
- `llm_risk_level`, np. `low`, `medium`, `high`.
- `llm_summary`, czyli krótki opis najważniejszego wniosku.
- `llm_reasons`, czyli lista głównych sygnałów pozytywnych i negatywnych.
- `llm_confidence`, czyli poziom pewności odpowiedzi modelu.

### 5. Reguły bezpieczeństwa dla LLM

- LLM nie może samodzielnie promować oferty do okazji, jeśli analityka v1 nie wykazała przewagi cenowej.
- LLM może obniżyć priorytet oferty albo skierować ją do ręcznego sprawdzenia.
- Odpowiedzi LLM mają być możliwie ustrukturyzowane i krótkie, aby nadawały się do logowania i powiadomień.
- System ma zapisywać dane wejściowe do LLM i wynik oceny, aby dało się później przeanalizować błędne decyzje.

## Notification Rules

### 1. Cel powiadomień

- Powiadomienia mają informować tylko o ofertach, które realnie zasługują na uwagę użytkownika.
- Warstwa powiadomień ma minimalizować spam i duplikaty.
- Powiadomienie jest końcowym produktem pipeline'u, a nie surowym logiem technicznym.

### 2. Zdarzenia generujące powiadomienie

- Nowa oferta oceniona jako `high-priority`.
- Oferta, która awansowała z `watch` lub `candidate` do `high-priority`.
- Istotny spadek ceny w ofercie już znanej, jeśli po spadku oferta nadal spełnia kryteria okazji.
- Oferta ponownie aktywna, jeśli wcześniej była nieaktywna, a teraz wraca z mocnym sygnałem.
- Oferta zatwierdzona przez LLM jako niskiego ryzyka, jeśli warstwa LLM jest już aktywna.

### 3. Zdarzenia, które nie powinny generować powiadomienia

- Każdy kolejny przebieg bez nowego sygnału.
- Ta sama oferta z niezmienionym bucketem, ceną i statusem.
- Oferta z bucketem `watch`, jeśli nie przekracza progów istotności.
- Oferta odrzucona przez LLM albo oznaczona jako wysokiego ryzyka.

### 4. Reguły deduplikacji

- Deduplikacja ma działać co najmniej na parze `listing_id + event_type`.
- System ma zapisywać czas ostatniego wysłania powiadomienia dla danego typu zdarzenia.
- Ponowne powiadomienie dla tej samej oferty jest dozwolone tylko po nowym sygnale, np. dalszym spadku ceny albo awansie bucketu.
- Powiadomienie nie może być wysyłane wielokrotnie tylko dlatego, że oferta nadal istnieje w danych.

### 5. Minimalna zawartość powiadomienia

- Tytuł oferty.
- Link do ogłoszenia.
- Aktualna cena.
- Najważniejszy powód powiadomienia.
- `deal_score`, `confidence_score` i bucket decyzji.
- Skrócony komentarz LLM, jeśli warstwa LLM była użyta.

### 6. Kanały i niezależność dostawy

- Warstwa powiadomień ma być niezależna od konkretnego kanału dostawy.
- Ten sam event powinien dać się wysłać przez email albo Telegram bez zmiany logiki decyzyjnej.
- Informacja o sukcesie lub błędzie wysyłki ma być zapisywana osobno od samej decyzji o powiadomieniu.

## Analytics V1 Notes

- Okazja nie jest definiowana jako "niska cena" sama w sobie.
- Ocena ma być relatywna względem podobnych ofert w obrębie tej samej kwerendy lub segmentu porównawczego.
- Podobieństwo ofert ma uwzględniać przynajmniej: rocznik, przebieg, pojemność silnika lub moc, paliwo oraz typ skrzyni.
- Dwie oferty tego samego modelu mogą mieć zupełnie inną ocenę przy tej samej cenie, jeśli różnią się rocznikiem, silnikiem lub przebiegiem.
- Warstwa analityczna v1 ma działać nawet bez danych szczegółowych z wnętrza ogłoszenia.
- Enrichment i LLM są kolejnymi filtrami jakości, a nie częścią bazowej definicji okazji.
- Segmentacja ma być deterministyczna i czytelna, żeby można było wyjaśnić później, z jaką grupą oferta została porównana.
- `deal_score` i `confidence_score` mają być rozdzielone, bo atrakcyjność oferty i pewność oceny to dwa różne sygnały.
- Enrichment ma być selektywny, kolejkujący i reaktywny na nowe sygnały, a nie wykonywany hurtowo dla całego rynku.
- LLM ma redukować ryzyko fałszywych pozytywów, a powiadomienia mają trafiać dopiero po przejściu przez cały sensowny filtr decyzyjny.
- Preferencje użytkownika mają działać jako osobna warstwa decyzji, a nie jako substytut analityki rynkowej.

## Done Requirements

Na razie brak wpisów.

## Removed Requirements

Na razie brak wpisów.

## Change Log

| Date       | Change                                                                                                                                                                                        |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-04-07 | Utworzono plik wymagań i zapisano początkowy zestaw wymagań dla warstwy scrapingu, storage, analytics, enrichment, LLM i powiadomień.                                                         |
| 2026-04-07 | Doprecyzowano wymagania dla analityki v1: relatywna definicja okazji, segmentacja ofert porównywalnych, wieloskładnikowy scoring, selektywny enrichment, wejście do LLM i zasady powiadomień. |
| 2026-04-07 | Rozpisano techniczne reguły segmentacji ofert porównywalnych: bazowy segment, tolerancje, minimalną liczność grupy, fallback i wpływ confidence na dalszą analizę.                            |
| 2026-04-07 | Rozpisano reguły `deal_score` v1: zakres wyniku, składowe score, progi decyzyjne, oddzielenie `confidence_score` oraz wymagany format wyniku analitycznego.                                   |
| 2026-04-07 | Rozpisano reguły selekcji do enrichmentu: wyzwalacze, priorytety kolejki, cooldown ponownych pobrań, warunki pominięcia oraz minimalny stan zapisywany po enrichmentcie.                      |
| 2026-04-07 | Rozpisano reguły wejścia do LLM i powiadomień: zakres kandydatów, format werdyktu LLM, zdarzenia notyfikacyjne, deduplikację i minimalną zawartość komunikatu.                                |
| 2026-04-07 | Dodano warstwę preferencji użytkownika oraz minimalny kontrakt danych dla analityki, enrichmentu, LLM i powiadomień.                                                                          |
