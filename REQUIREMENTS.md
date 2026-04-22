# CarWebScraper Requirements

Ten plik jest ĹşrĂłdĹ‚em prawdy dla wymagaĹ„ projektu.
Aktualizujemy go przy kaĹĽdym nowym, zmienionym, wykonanym lub usuniÄ™tym wymaganiu.

## Statusy

- `planned` - wymaganie zaakceptowane, jeszcze niewykonane
- `in-progress` - praca trwa
- `done` - wykonane
- `removed` - usuniÄ™te lub porzucone

## Zasady aktualizacji

- KaĹĽde wymaganie ma staĹ‚e ID, np. `REQ-001`.
- Zmieniamy status istniejÄ…cego wpisu zamiast tworzyÄ‡ duplikat.
- Istotne zmiany dopisujemy takĹĽe do sekcji `Change Log`.
- Wymagania przyszĹ‚e zapisujemy od razu, nawet jeĹ›li sÄ… odlegĹ‚e w czasie.

## Active Requirements

| ID      | Status  | Obszar        | Wymaganie                                                                                                                                          | Uwagi                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------- | ------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| REQ-001 | done    | Scraping      | System ma pobieraÄ‡ listy ogĹ‚oszeĹ„ z Otomoto dla zdefiniowanych kwerend.                                                                            | Implemented: `otomoto-scraper` dziaĹ‚a jako scrapper list.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| REQ-002 | done    | Storage       | System ma zapisywaÄ‡ historiÄ™ ofert, w tym aktywnoĹ›Ä‡, daty obserwacji i zmiany cen.                                                                 | Implemented: CSV storage w `otomoto-scraper/storage.py`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| REQ-003 | done    | Analytics     | System ma mieÄ‡ osobnÄ… warstwÄ™ analitycznÄ… do wykrywania okazji cenowych.                                                                           | Implemented: `otomoto-scraper/analytics.py` jako analityka v1.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| REQ-004 | done    | Analytics     | Okazje majÄ… byÄ‡ wykrywane najpierw przez tani scoring oparty o dane z listingu.                                                                    | Implemented: market scoring bez enrichmentu dla wiÄ™kszoĹ›ci ofert.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| REQ-005 | done    | Enrichment    | SzczegĂłĹ‚owe dane tekstowe majÄ… byÄ‡ pobierane tylko dla wybranych ofert.                                                                            | Implemented: `enrichment_worker.py` pobiera szczegĂłĹ‚y tylko z `enrichment_queue.csv` i zapisuje sidecar JSON dla wybranych ofert.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| REQ-006 | done    | LLM           | W pĂłĹşniejszym etapie system ma filtrowaÄ‡ kandydatĂłw z uĹĽyciem LLM.                                                                                 | Implemented: `llm_worker.py` integruje OpenAI API; wywoĹ‚ywany z `main.py` przez `--run-llm`; model konfigurowalny przez `preferences.json` (klucz `llm.model`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| REQ-007 | done    | Notifications | W koĹ„cowym etapie system ma wysyĹ‚aÄ‡ powiadomienia o okazjach.                                                                                      | Implemented: event engine + deduplikacja + kanaĹ‚ `log` oraz opcjonalny transport Telegram konfigurowany w preferencjach.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| REQ-008 | done    | Analytics     | System ma definiowaÄ‡ okazjÄ™ relatywnie do porĂłwnywalnych ofert, a nie przez staĹ‚y prĂłg ceny.                                                       | Implemented: segmentacja i porĂłwnania do mediany/percentyli w `analytics.py`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| REQ-009 | done    | Analytics     | Warstwa analityczna v1 ma wyliczaÄ‡ wstÄ™pny score tylko na podstawie danych dostÄ™pnych z listingu.                                                  | Implemented: deal_score v1 oparty na danych z listingĂłw (lista ofert).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| REQ-010 | done    | Analytics     | System ma grupowaÄ‡ oferty do porĂłwnaĹ„ w segmenty podobnych pojazdĂłw.                                                                               | Implemented: segment rules + fallback logic w `analytics.py`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| REQ-011 | done    | Analytics     | WstÄ™pny score ma skĹ‚adaÄ‡ siÄ™ z wielu sygnaĹ‚Ăłw, a nie tylko z samej ceny.                                                                           | Implemented: market position, freshness, price drop, stability, data-quality penalties.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| REQ-012 | done    | Analytics     | System ma zwracaÄ‡ wynik analityczny w postaci score oraz listy powodĂłw, ktĂłre wpĹ‚ynÄ™Ĺ‚y na ocenÄ™.                                                   | Implemented: `market_reasons` oraz `preference_reasons` w wynikach JSON.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| REQ-013 | done    | Enrichment    | System ma kierowaÄ‡ do enrichmentu tylko oferty speĹ‚niajÄ…ce reguĹ‚y priorytetyzacji.                                                                 | Implemented: `enrichment_selector.py`/`enrichment_runner.py` wybierajÄ… kandydatĂłw i tworzÄ… kolejkÄ™ z priorytetami.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| REQ-014 | done    | Enrichment    | System nie ma pobieraÄ‡ szczegĂłĹ‚Ăłw kaĹĽdej oferty przy kaĹĽdym przebiegu.                                                                             | Implemented: `enrichment_worker.py` pomija wpisy `fetched`, a `failed` powtarza tylko po `--retry-failed`. HTTP 410 Gone traktowany jako osobny status `gone` â€” oferty trwale niedostÄ™pne nie blokujÄ… kolejki i nie sÄ… retryowane.                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| REQ-015 | done    | LLM           | Do warstwy LLM majÄ… trafiaÄ‡ tylko oferty wyselekcjonowane przez scoring i enrichment.                                                              | Implemented: `select_candidates()` w `llm_worker.py` filtruje wyĹ‚Ä…cznie oferty z `details_status=fetched`, bucketu z `allowed_buckets` i `final_score >= min_final_score`; oferty bez sidecar JSON sÄ… pomijane.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| REQ-016 | done    | Notifications | Powiadomienia majÄ… byÄ‡ wysyĹ‚ane tylko dla nowych lub istotnie zmienionych okazji.                                                                  | Implemented: eventy `new-listing`/`reactivated`/`bucket-upgrade`/`price-drop` z dodatkowymi filtrami antyspamowymi, blokadÄ… podejrzanych ofert typu rata/cesja i rozszerzonym filtrem sygnaĹ‚Ăłw uszkodzeĹ„.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| REQ-017 | done    | Analytics     | Segment porĂłwnawczy ma zaczynaÄ‡ siÄ™ od tej samej kwerendy lub modelu bazowego.                                                                     | Implemented: analityka buduje grupÄ™ porĂłwnawczÄ… wyĹ‚Ä…cznie w obrÄ™bie aktywnych ofert z tego samego CSV/kwerendy.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| REQ-018 | done    | Analytics     | Segment porĂłwnawczy ma uĹĽywaÄ‡ reguĹ‚ tolerancji dla rocznika, przebiegu i parametrĂłw silnika.                                                       | Implemented: `SEGMENT_RULES` w `analytics.py` definiujÄ… jawne tolerancje dla rocznika, przebiegu, mocy i pojemnoĹ›ci.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| REQ-019 | done    | Analytics     | System ma stosowaÄ‡ fallback segmentacji, gdy grupa porĂłwnawcza jest zbyt maĹ‚a.                                                                     | Implemented: `_build_comparison_group()` przechodzi krokowo po reguĹ‚ach fallbacku i zapisuje `fallback_level`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| REQ-020 | done    | Analytics     | System ma oznaczaÄ‡ niski poziom zaufania, gdy wynik opiera siÄ™ na zbyt maĹ‚ej grupie porĂłwnawczej.                                                  | Implemented: `confidence_score` jest obniĹĽany za maĹ‚Ä… grupÄ™ porĂłwnawczÄ… i fallback segmentacji. Kara za fallback jest skalowana przez rozmiar ostatecznej grupy â€” przy duĹĽej grupie (â‰Ą MIN+30) spada do 20% wartoĹ›ci bazowej, bo duĹĽa prĂłbka gwarantuje wiarygodnoĹ›Ä‡ wyceny niezaleĹĽnie od poziomu fallbacku.                                                                                                                                                                                                                                                                                                                                                                                  |
| REQ-021 | done    | Analytics     | `deal_score` v1 ma byÄ‡ liczbÄ… znormalizowanÄ… do zakresu `0-100`.                                                                                   | Implemented as `final_score` clamped to 0-100.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| REQ-022 | done    | Analytics     | GĹ‚Ăłwnym skĹ‚adnikiem `deal_score` ma byÄ‡ relacja ceny oferty do rynku segmentu porĂłwnawczego.                                                       | Implemented: `market_position_score` opiera siÄ™ gĹ‚Ăłwnie o relacjÄ™ ceny oferty do mediany i dolnego kwartyla segmentu.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| REQ-023 | done    | Analytics     | `deal_score` ma uwzglÄ™dniaÄ‡ dodatkowe sygnaĹ‚y czasowe i behawioralne.                                                                              | Implemented: scoring uwzglÄ™dnia Ĺ›wieĹĽoĹ›Ä‡ oferty, spadki ceny, liczbÄ™ zmian ceny i lekki sygnaĹ‚ typu sprzedawcy.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| REQ-024 | done    | Analytics     | `deal_score` ma uwzglÄ™dniaÄ‡ karÄ™ za niekompletnoĹ›Ä‡ danych i niski confidence segmentu.                                                             | Implemented: analityka nakĹ‚ada kary za braki danych oraz fallback segmentacji, a confidence jest liczony osobno i wpĹ‚ywa na interpretacjÄ™ wyniku.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| REQ-025 | done    | Analytics     | Wynik analityczny ma zawieraÄ‡ osobno `deal_score` i `confidence_score`.                                                                            | Implemented as `market_score`/`final_score` and `confidence_score`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| REQ-026 | done    | Analytics     | Wynik analityczny ma klasyfikowaÄ‡ oferty do poziomĂłw decyzji.                                                                                      | Implemented: buckets `ignore`, `watch`, `candidate`, `high-priority`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| REQ-027 | done    | Enrichment    | Enrichment ma dziaĹ‚aÄ‡ jako osobny etap po wstÄ™pnym scoringu.                                                                                       | Implemented: osobny `enrichment_worker.py` oraz opcjonalne uruchomienie z `main.py` przez `--run-enrichment`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| REQ-028 | done    | Enrichment    | System ma nadawaÄ‡ priorytet ofertom kierowanym do enrichmentu.                                                                                     | Implemented: kolejka zapisuje `priority`; selektor uwzglÄ™dnia Ĺ›wieĹĽoĹ›Ä‡, zmiany ceny i typ sprzedawcy.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| REQ-029 | done    | Enrichment    | System ma ograniczaÄ‡ czÄ™stotliwoĹ›Ä‡ ponownego enrichmentu tej samej oferty.                                                                         | Implemented cooldown 7 dni z bypass po zmianie `price_pln` albo promocji `decision_bucket`; `failed` nadal wraca tylko z `--retry-failed`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| REQ-030 | done    | Enrichment    | Wynik enrichmentu ma zapisywaÄ‡ moment pobrania i stan oferty, dla ktĂłrego pobrano szczegĂłĹ‚y.                                                       | Implemented peĹ‚ny kontrakt CSV: `details_status`, `details_priority`, `details_fetched_at`, `details_based_on_*`, `details_fields_present` oraz skrĂłcone pola operacyjne z detail page.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| REQ-046 | done    | Enrichment    | System ma przetwarzaÄ‡ szczegĂłĹ‚y oferty do ustrukturyzowanych sygnaĹ‚Ăłw jakoĹ›ciowych po pobraniu detail page.                                        | Implemented: `enrichment_analysis.py` normalizuje opis, wyposaĹĽenie, sprzedawcÄ™ i sygnaĹ‚y spĂłjnoĹ›ci do formy uĹĽytecznej dla dalszej analizy.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| REQ-047 | done    | Analytics     | Wynik po enrichmentcie ma zawieraÄ‡ osobny wynik jakoĹ›ciowy oparty o szczegĂłĹ‚y oferty.                                                              | Implemented: analytics output zwraca `enrichment_score`, `enrichment_confidence`, `enrichment_reasons` i `enrichment_flags`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| REQ-048 | done    | Pipeline      | System ma mieÄ‡ drugi etap analizy po enrichmentcie dla ofert, ktĂłre majÄ… pobrane szczegĂłĹ‚y.                                                        | Implemented: po `--run-enrichment` `main.py` odĹ›wieĹĽa pliki analytics, aby uwzglÄ™dniÄ‡ Ĺ›wieĹĽo pobrane szczegĂłĹ‚y.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| REQ-049 | done    | Enrichment    | SygnaĹ‚y z detail page nie mogÄ… samodzielnie promowaÄ‡ sĹ‚abej cenowo oferty do okazji, ale mogÄ… obniĹĽaÄ‡ lub wzmacniaÄ‡ priorytet.                     | Implemented: enrichment dziaĹ‚a jako ograniczony korektor `final_score`; dodatni wpĹ‚yw jest blokowany dla ofert ze sĹ‚abym `market_score`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| REQ-031 | done    | LLM           | Warstwa LLM ma oceniaÄ‡ tylko ograniczonÄ… liczbÄ™ kandydatĂłw po wczeĹ›niejszej filtracji.                                                             | Implemented: `max_candidates_per_run` (domyĹ›lnie 5) w `preferences.json`; bezwzglÄ™dny hard cap `HARD_MAX_CANDIDATES=20` w kodzie; cooldown 30 dni na ponownÄ… ocenÄ™ tej samej oferty; przerwanie przebiegu przy `RateLimitError`.                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| REQ-032 | done    | LLM           | LLM ma zwracaÄ‡ ustrukturyzowany wynik oceny oferty.                                                                                                | Implemented: `response_format={"type":"json_object"}`; pola `llm_verdict` (approve/review/reject), `llm_risk_level` (low/medium/high), `llm_confidence`, `llm_summary`, `llm_reasons` zapisywane do storage CSV i logowane.                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| REQ-033 | done    | LLM           | LLM ma byÄ‡ filtrem jakoĹ›ciowym, a nie ĹşrĂłdĹ‚em podstawowej wyceny okazji.                                                                           | Implemented: prompt jawnie zakazuje awansu oferty do approve wyĹ‚Ä…cznie ze wzglÄ™du na cenÄ™; LLM dostaje gotowy `final_score` i `market_reasons` z analityki deterministycznej jako kontekst, ale nie moĹĽe ich zastÄ…piÄ‡.                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| REQ-034 | done    | Notifications | System ma deduplikowaÄ‡ powiadomienia na poziomie oferty i typu zdarzenia.                                                                          | Implemented: `notification_state.csv` przechowuje ostatni stan oferty i blokuje ponowne eventy bez nowego sygnaĹ‚u. `retry_failed_notifications()` w `notifications.py` pozwala ponowiÄ‡ wpisy `notification_status=failed` bez naruszania stanu deduplikacji; dostÄ™pne przez `--retry-failed-notifications` w `main.py`.                                                                                                                                                                                                                                                                                                                                                                        |
| REQ-035 | done    | Notifications | System ma rozrĂłĹĽniaÄ‡ typy zdarzeĹ„ powiadomieĹ„.                                                                                                     | Implemented: event types `new-listing`, `reactivated`, `bucket-upgrade`, `price-drop`, `llm-approved`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| REQ-036 | done    | Notifications | Powiadomienie ma zawieraÄ‡ skrĂłt powodĂłw decyzji.                                                                                                   | Implemented: event log zapisuje podsumowanie z bucketa, score, confidence, ceny, skrĂłconych sygnaĹ‚Ăłw analitycznych/enrichment oraz skrĂłconego komentarza LLM (`llm_summary`), jeĹ›li warstwa LLM byĹ‚a uĹĽyta.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| REQ-037 | done    | Preferences   | System ma mieÄ‡ osobnÄ… warstwÄ™ preferencji uĹĽytkownika niezaleĹĽnÄ… od bazowej analityki rynku.                                                       | Implemented: `otomoto-scraper/preferences.py` with global + per-query profiles.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| REQ-038 | done    | Preferences   | System ma rozrĂłĹĽniaÄ‡ twarde filtry preferencji i miÄ™kkie preferencje rankingowe.                                                                   | Implemented: `hard_filters` and `soft_preferences` support.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| REQ-039 | done    | Preferences   | Preferencje majÄ… daÄ‡ siÄ™ konfigurowaÄ‡ globalnie i per kwerenda.                                                                                    | Implemented: merging of global and per-query prefs.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| REQ-040 | done    | Analytics     | Wynik analityczny ma rozdzielaÄ‡ `market_score`, `preference_score` i `final_score`.                                                                | Implemented: `AnalyticsResult` zapisuje osobno wynik rynku, preferencji i wynik koĹ„cowy po korekcie enrichmentem.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| REQ-041 | done    | Analytics     | System ma zwracaÄ‡ jawny wynik dziaĹ‚ania preferencji na ofertÄ™.                                                                                     | Implemented: wynik zawiera `hard_filter_passed` i `preference_reasons`, a `preferences.py` zwraca teĹĽ uĹĽyty profil.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| REQ-042 | done    | Storage       | System ma mieÄ‡ zdefiniowany model danych dla wyniku analityki, enrichmentu, LLM i powiadomieĹ„.                                                     | Implemented na poziomie specyfikacji: `REQUIREMENTS.md` definiuje minimalny kontrakt danych dla analytics, enrichment, LLM i notifications.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| REQ-043 | done    | Parsing       | System ma wykrywaÄ‡ wzmianki o uszkodzeniu/kolizji na poziomie list-card i zapisaÄ‡ flagÄ™ do CSV.                                                    | Implemented: `detect_damage()` w `otomoto-scraper/utils.py`, pola `is_damaged`/`condition_note` zapisane w CSV.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| REQ-044 | done    | Tooling       | Repo ma narzÄ™dzie do lokalnej analizy CSV (`analyze.py`) do szybkiej weryfikacji scoringu.                                                         | Implemented: `analyze.py` zapisuje wyniki do `data/otomoto/analytics/` i drukuje top-oferty.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| REQ-045 | done    | Parsing       | System ma wykrywaÄ‡ typ sprzedawcy (`private`/`business`) z list-card, zapisywaÄ‡ go do CSV i uwzglÄ™dniaÄ‡ w scoringu.                                | Implemented: parser list-card wykrywa `Prywatny sprzedawca`/`Firma`, zapisuje `seller_type` i stosuje lekkÄ… korektÄ™ w `analytics.py`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| REQ-050 | done    | Enrichment    | Paginacja scrapera nie moĹĽe polegaÄ‡ na niestabilnych, auto-generowanych klasach CSS Otomoto.                                                       | Implemented: `get_next_page_url_from_pagination_button` w `scraper.py` uĹĽywa teraz `button[title='Go to next Page']` i `button[aria-label='Go to next Page']` jako gĹ‚Ăłwnych selektorĂłw; stary selektor oparty o klasÄ™ `eemmnsu4` zachowany wyĹ‚Ä…cznie jako fallback.                                                                                                                                                                                                                                                                                                                                                                                                                            |
| REQ-051 | done    | Enrichment    | System ma samoczyszciÄ‡ kolejkÄ™ enrichmentu po przetworzeniu oraz ograniczaÄ‡ liczbÄ™ pozycji w jednym przebiegu.                                     | Implemented: `flush_completed_from_queue()` usuwa z `enrichment_queue.csv` wpisy ze statusem `fetched`/`skipped`/`gone` po kaĹĽdym `run()`; dodany parametr `--enrichment-limit N` w `main.py`; throttling 1.5â€“4 s miÄ™dzy requestami; logi postÄ™pu `[X/N]` w trakcie przetwarzania; `storage.py` zapisuje `source_csv` w nowych wpisach kolejki.                                                                                                                                                                                                                                                                                                                                                |
| REQ-052 | removed | Notifications | Wynik LLM ma blokowaÄ‡ powiadomienia dla ofert odrzuconych lub wysokiego ryzyka.                                                                    | UsuniÄ™te: blokowanie przez `llm_verdict=reject` i `llm_risk_level=high` zostaĹ‚o wyĹ‚Ä…czone. LLM peĹ‚ni wyĹ‚Ä…cznie rolÄ™ komentatora â€” jego ocena nie blokuje ani nie generuje eventĂłw. Flagi `block_llm_rejected`/`block_llm_high_risk` usuniÄ™te z `_is_notification_eligible()`.                                                                                                                                                                                                                                                                                                                                                                                                                  |
| REQ-053 | removed | Notifications | Wynik LLM `approve` niskiego ryzyka ma generowaÄ‡ event powiadomienia i byÄ‡ deduplikowany.                                                          | UsuniÄ™te: event `llm-approved` i logika deduplikacji przez `llm_notified_verdict` usuniÄ™te z `determine_notification_event()`. LLM nie generuje wĹ‚asnych eventĂłw â€” powiadomienie jest zawsze wyzwalane przez sygnaĹ‚ rynkowy (nowe ogĹ‚oszenie, zmiana ceny, bucket upgrade), a komentarz LLM jest doĹ‚Ä…czany jako dodatkowa informacja.                                                                                                                                                                                                                                                                                                                                                          |
| REQ-054 | done    | Enrichment    | Strukturalna flaga â€žUszkodzony" z sekcji â€žStan i historia" na detail page ma byÄ‡ odczytywana i uwzglÄ™dniana w scoringu.                            | Implemented: `_score_parameters()` w `enrichment_analysis.py` odczytuje `parameters["damaged"]` z `parametersDict` (Next.js) i daje karÄ™ -25 pkt + flagÄ™ `damage_structural`; analogicznie premia +8 pkt i flaga `accident_free_structural` dla `no_accident=True`; `build_csv_detail_summary()` w `enrichment_worker.py` dodaje pole `damaged_flag` (OR tekst + strukturalne); `details_damaged_flag` zapisane do CSV; `_is_notification_eligible()` blokuje ofertÄ™ gdy `details_damaged_flag=True` przy `exclude_damaged_listings=True`.                                                                                                                                                     |
| REQ-055 | done    | Notifications | System ma umoĹĽliwiÄ‡ delegowanie decyzji o drobnym uszkodzeniu do warstwy LLM zamiast twardego blokowania.                                          | Implemented: nowy klucz `damaged_handling` w `notification_filters` (`"block"` domyĹ›lnie / `"llm"`). Tryb `"llm"`: drobne uszkodzenia (`damage_declared`, `damage_structural`, `is_damaged`) nie blokujÄ… automatycznie â€” wymagajÄ… `llm_verdict=approve` i `llm_risk_level != high`; ciÄ™ĹĽkie flagi (`airbags_deployed`, `severe_front_damage`, `severe_rear_damage`, `total_loss_declared`, `scrap_candidate`, `parts_only_vehicle`) zawsze twardy blok niezaleĹĽnie od trybu. Prompt LLM dostaje sekcjÄ™ `## Stan uszkodzenia` z jawnym ostrzeĹĽeniem.                                                                                                                                            |
| REQ-056 | done    | Tooling       | Scraper ma obsĹ‚ugiwaÄ‡ tryb ciÄ…gĹ‚ej pracy z konfigurowalnymi przerwami miÄ™dzy cyklami i przerwaniem przez Ctrl+C.                                   | Implemented: flaga `--loop` w `main.py` uruchamia nieskoĹ„czonÄ… pÄ™tlÄ™; `--loop-interval SEC` (domyĹ›lnie 1800 s = 30 min) kontroluje czas oczekiwania miÄ™dzy iteracjami; `KeyboardInterrupt` jest Ĺ‚apany na poziomie `main()` i logowany jako czyste zakoĹ„czenie; bĹ‚Ä™dy w pojedynczej iteracji sÄ… logowane bez przerwania pÄ™tli.                                                                                                                                                                                                                                                                                                                                                                 |
| REQ-057 | done    | Enrichment    | System ma wykrywaÄ‡ i penalizowaÄ‡ pojazdy sprowadzone z rynkĂłw zamorskich (USA, Japonia itd.) na etapie enrichmentu i w prompcie LLM.               | Implemented: naprawiono detekcjÄ™ flagi `is_imported_car` w `_score_consistency()` â€” poprzedni kod nie wykrywaĹ‚ wzorca checkboxa otomoto (`"is_imported_car": "is_imported_car"`). Dodano reguĹ‚Ä™ `overseas_import` w `_score_parameters()`: kara -8 pkt gdy `country_origin` zawiera kraj zamorski (USA/Stany Zjednoczone/Japonia/Kanada/Australia/Korea/Chiny). Prompt LLM dostaje nowÄ… sekcjÄ™ `## Import i kraj pochodzenia` z ostrzeĹĽeniem o weryfikacji homologacji, przebiegu (milâ†’km) i kosztĂłw. Prompt czyta parametry bezpoĹ›rednio z sidecar JSON aby obsĹ‚uĹĽyÄ‡ przestarzaĹ‚e rekordy CSV (rekordy enrichowane przed REQ-054 miaĹ‚y `details_damaged_flag=0` i `details_imported_flag=0`). |
| REQ-058 | done    | Notifications | KaĹĽde powiadomienie ma byÄ‡ opatrzone komentarzem LLM, jeĹ›li oferta nie ma jeszcze oceny LLM.                                                       | Implemented: `llm_worker.review_single()` + `llm_worker.OnDemandSession` enkapsulujÄ… caĹ‚Ä… logikÄ™ on-demand w warstwie LLM. `notifications.py` wywoĹ‚uje wyĹ‚Ä…cznie te publiczne API. Limit wywoĹ‚aĹ„ per run konfigurowany przez `llm.max_notification_llm_calls` w `preferences.json` (domyĹ›lnie 5). Wynik LLM jest doĹ‚Ä…czany do treĹ›ci powiadomienia jako komentarz â€” nie wpĹ‚ywa na eligibility ani typ eventu. Prompt rozszerzony: `summary` to 3-5 zdaĹ„ (ocena pozycji cenowej, kluczowe sygnaĹ‚y, rekomendacja), do 8 powodĂłw; `DEFAULT_MAX_TOKENS` zwiÄ™kszony do 1600.                                                                                                                        |
| REQ-059 | planned | Storage       | System ma zostaÄ‡ zmigrowany z plikĂłw CSV do bazy SQLite.                                                                                           | Storage CSV (`storage.py`), kolejka enrichmentu (`enrichment_queue.csv`), stan powiadomieĹ„ (`notification_state.csv`, `notification_history.csv`) oraz sidecar JSON z details majÄ… byÄ‡ zastÄ…pione tabelami SQLite. Migracja ma obejmowaÄ‡: schemat tabel, skrypt jednorazowej migracji istniejÄ…cych danych CSVâ†’SQLite, aktualizacjÄ™ wszystkich warstw (scraper, enrichment, analytics, LLM, notifications) do operacji na bazie, zachowanie moĹĽliwoĹ›ci uruchomienia bez zmian konfiguracji.                                                                                                                                                                                                     |
| REQ-060 | done    | Enrichment    | Normalizacja `parametersDict` z Otomoto ma poprawnie wyciÄ…gaÄ‡ wartoĹ›ci z formatu `{"label": "...", "values": [{"value": "...", "label": "..."}]}`. | Implemented: naprawiono `_normalize_parameters()` w `enrichment_worker.py` â€” stary kod braĹ‚ `.label` zamiast `.values[0].value`, co powodowaĹ‚o `"damaged": "damaged"` (key==value) i bĹ‚Ä™dnie oznaczaĹ‚o wszystkie oferty jako uszkodzone. Dodano guard `key==value â†’ None/False` w `_parameter_flag()`, `_score_parameters()` i `build_prompt()`. Dodano `--reprocess-details` w `main.py` wywoĹ‚ujÄ…cy `reprocess_details_flags()` â€” migracja jednorazowa bez scrapingu, ktĂłra przetwarza istniejÄ…ce sidecar JSON i nadpisuje flagi CSV z poprawionÄ… logikÄ….                                                                                                                                     |
| REQ-061 | done    | Scraping      | Architektura scrapera ma obsĹ‚ugiwaÄ‡ wiele ĹşrĂłdeĹ‚ danych (multi-source) bez zmian w warstwach storage, analytics, notifications.                    | KaĹĽda kwerenda w `queries.json` ma mieÄ‡ pole `"source"` (`"otomoto"` \| `"mobile_de"`). `main.process_query()` ma dyspatchowaÄ‡ do odpowiedniej pary scraper+parser na podstawie `source`. ModuĹ‚y scrapera i parsera majÄ… byÄ‡ wydzielone do podfolderĂłw `scrapers/` i `parsers/`. Warstwa storage (`storage.py`) oraz caĹ‚y dalszy pipeline (analytics, LLM, notifications) nie wymagajÄ… zmian â€” operujÄ… wyĹ‚Ä…cznie na zunifikowanym dict oferty. KaĹĽde ĹşrĂłdĹ‚o ma mieÄ‡ oddzielny plik stanu sesji przeglÄ…darki (`.session-state-<source>.json`).                                                                                                                                                  |
| REQ-062 | done    | Scraping      | System ma pobieraÄ‡ listy ogĹ‚oszeĹ„ z mobile.de dla zdefiniowanych kwerend.                                                                          | Nowy moduĹ‚ `scrapers/mobile_de.py` eksponuje `get_html_pages(start_url, ...) -> list[str]` â€” interfejs identyczny jak `scrapers/otomoto.py`. ObsĹ‚uga paginacji mobile.de (przycisk â€žWeiter" lub parametr URL `pageNumber`). Stealth/UA moĹĽe byÄ‡ uproszczony (mobile.de nie uĹĽywa CloudFront). Wczytywanie stanu sesji z wĹ‚asnego pliku `.session-state-mobile_de.json`.                                                                                                                                                                                                                                                                                                                        |
| REQ-063 | done    | Parsing       | Parser mobile.de ma wyciÄ…gaÄ‡ dane oferty do zunifikowanego dict o tej samej strukturze co parser Otomoto.                                          | Nowy moduĹ‚ `parsers/mobile_de.py` eksponuje `get_cars_from_content(html) -> list[dict]`. Wymagane pola: `listing_id`, `title`, `link`, `price_pln` (przeliczony z EUR po kursie dnia lub przybliĹĽonym), `year`, `mileage_km`, `fuel_type`, `gearbox`, `power_hp`, `engine_cm3`, `location`, `seller_type`, `is_damaged`, `condition_note`. Pola niedostÄ™pne na stronie wynikowej sÄ… pozostawiane puste. Parser nie moĹĽe rzucaÄ‡ wyjÄ…tkĂłw dla pojedynczej karty â€” bĹ‚Ä™dne karty sÄ… pomijane z logiem ostrzeĹĽenia.                                                                                                                                                                                 |
| REQ-064 | done    | Enrichment    | Enrichment dla ĹşrĂłdĹ‚a mobile.de jest opcjonalny i odkĹ‚adany do osobnej iteracji.                                                                   | `enrichment_worker.py` operuje na Otomoto API (numeric `listing_id` â†’ `https://www.otomoto.pl/...`). Oferty z `source=mobile_de` majÄ… byÄ‡ pomijane przez enrichment workera (brak sidecar JSON nie blokuje scoringu ani powiadomieĹ„). Docelowo osobny `enrichment_worker_mobile_de.py` lub rozszerzenie istniejÄ…cego workera o dispatch po `source`.                                                                                                                                                                                                                                                                                                                                           |
| REQ-065 | done    | Scraping      | Kwerendy Otomoto w `queries.json` majÄ… byÄ‡ definiowane jako struktury parametrĂłw, a nie surowe URL-e z zakodowanymi query stringami.               | KaĹĽdy wpis z `"source": "otomoto"` moĹĽe zawieraÄ‡ klucz `"otomoto_params"` z polami: `make` (slug marki, np. `"kia"`), `model` (slug modelu, np. `"sportage"`), `year_from` (int), `fuel_type` (string, np. `"petrol"`), `mileage_to` (int), `price_to` (int, opcjonalne), `gearbox` (string, opcjonalne) i dowolne dodatkowe klucze `search[filter_*]`. Config loader (`config.py`) buduje `start_url` z tych pĂłl w czasie Ĺ‚adowania. Pole `start_url` pozostaje obsĹ‚ugiwane jako fallback dla wpisĂłw bez `otomoto_params` (wsteczna kompatybilnoĹ›Ä‡). DziÄ™ki temu kwerendy sÄ… czytelne i edytowalne bez znajomoĹ›ci URL encodingu Otomoto.                                                      |
| REQ-066 | done    | Analytics     | Scoring ma uwzgledniać zrodlo ogloszenia - oferty z mobile.de powinny byc obcizone kosztami importu przy porownaniu cenowym, a jednoczesnie korzystac z premii za wiarygodnosc rynku. | Nowa sekcja `source_adjustments` w `preferences.json` (per-source config). Dwa parametry per zrodlo: `import_cost_pln` (PLN doliczane do efektywnej ceny przy obliczaniu market score i hard-filter `max_price_pln`) oraz `reliability_score_bonus` (delta preference score). Zmiany w `analytics.py`: `_calculate_market_score()` przyjmuje `import_cost_pln`, uzywa efektywnej ceny do pozycji vs mediana. Zmiany w `preferences.py`: hard-filter `max_price_pln` sprawdza `price_pln + import_cost_pln`; soft-prefs dolicza `reliability_score_bonus`. Domyslna konfiguracja: mobile.de -> `import_cost_pln: 5000`, `reliability_score_bonus: 5`. |

## Preference Layer Rules

### 1. Cel warstwy preferencji

- Warstwa preferencji ma modelowaÄ‡ to, czego uĹĽytkownik aktualnie szuka, niezaleĹĽnie od tego, czy oferta jest obiektywnie dobra wzglÄ™dem rynku.
- Preferencje nie mogÄ… zmieniaÄ‡ sposobu liczenia segmentu porĂłwnawczego ani bazowego `market_score`.
- Zmiana preferencji uĹĽytkownika powinna umoĹĽliwiaÄ‡ szybkie przeliczenie shortlisty bez przebudowy historii rynku.

### 2. Typy reguĹ‚ preferencji

- `hard_filters`: reguĹ‚y odrzucajÄ…ce ofertÄ™ z dalszego procesu uĹĽytkowego, np. minimalna pojemnoĹ›Ä‡ silnika albo maksymalny przebieg.
- `soft_preferences`: reguĹ‚y zwiÄ™kszajÄ…ce lub zmniejszajÄ…ce `preference_score`, np. premia za automat albo karanie LPG.
- `boost_rules`: dodatkowe premie za szczegĂłlnie poĹĽÄ…dane konfiguracje, np. wyĹĽszy rocznik albo mocniejszy silnik.
- `notification_filters`: reguĹ‚y blokujÄ…ce powiadomienia mimo wysokiego `market_score`, jeĹ›li oferta nie pasuje do preferencji uĹĽytkownika.

### 3. Zakres konfiguracji preferencji

- Preferencje globalne majÄ… dziaĹ‚aÄ‡ dla caĹ‚ego projektu.
- Preferencje per kwerenda majÄ… nadpisywaÄ‡ lub rozszerzaÄ‡ ustawienia globalne dla konkretnego modelu.
- Preferencje powinny obsĹ‚ugiwaÄ‡ co najmniej: minimalny i maksymalny przebieg, minimalnÄ… pojemnoĹ›Ä‡, minimalnÄ… moc, paliwo, skrzyniÄ™, budĹĽet i rocznik.

### 4. WpĹ‚yw preferencji na pipeline

- `market_score` ma byÄ‡ liczony bez udziaĹ‚u preferencji uĹĽytkownika.
- `preference_score` ma byÄ‡ liczony na podstawie konfiguracji preferencji.
- `final_score` ma uwzglÄ™dniaÄ‡ oba wyniki, ale osobno zapisywaÄ‡ ich ĹşrĂłdĹ‚a.
- Oferta niespeĹ‚niajÄ…ca `hard_filters` moĹĽe zostaÄ‡ zapisana jako ciekawa rynkowo, ale nie powinna trafiaÄ‡ do powiadomieĹ„ uĹĽytkownika.

### 5. Wymagany wynik warstwy preferencji

- `hard_filter_passed`.
- `preference_score` w skali `0-100`.
- `preference_reasons`, czyli lista reguĹ‚, ktĂłre zwiÄ™kszyĹ‚y lub obniĹĽyĹ‚y priorytet.
- `applied_preference_profile`, czyli nazwa profilu lub zestawu reguĹ‚ uĹĽytych do oceny.

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

### 2b. Operacyjny skrĂłt enrichmentu w CSV

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

### 4. Minimalny kontrakt powiadomieĹ„

- `listing_id`.
- `event_type`.
- `notification_channel`.
- `notification_decision`.
- `notification_sent_at`.
- `notification_status`.
- `notification_reason_summary`.

## Change Log

### 2026-04-20

- LLM przestaĹ‚ wpĹ‚ywaÄ‡ na decyzje o powiadomieniach â€” usuniÄ™to blokowanie przez `llm_verdict=reject`/`llm_risk_level=high` (REQ-052 removed) oraz event `llm-approved` (REQ-053 removed). LLM peĹ‚ni wyĹ‚Ä…cznie rolÄ™ komentatora: ocena jest doĹ‚Ä…czana do treĹ›ci powiadomienia, ale nie blokuje ani nie wyzwala eventĂłw.
- Poprawiono jakoĹ›Ä‡ komentarzy LLM: `summary` zmienione z jednego zdania na 3-5 zdaĹ„ (ocena cenowa, sygnaĹ‚y, rekomendacja), liczba powodĂłw zwiÄ™kszona do 8, `DEFAULT_MAX_TOKENS` podniesiony do 1600, system prompt uzupeĹ‚niony o instrukcjÄ™ konkretnoĹ›ci (REQ-058 updated).
- Naprawiono bĹ‚Ä…d scrapera: `wait_until_article_count_stabilizes()` w `scraper.py` wychodziĹ‚a po 2 rundach z zerowÄ… liczbÄ… artykuĹ‚Ăłw, zanim React zamontowaĹ‚ listingi. Dodano `page.wait_for_selector("article[data-id]", timeout=20000)` przed pÄ™tlÄ… stabilizacji.

### 2026-04-20

- LLM przestaĹ‚ wpĹ‚ywaÄ‡ na decyzje o powiadomieniach â€” usuniÄ™to blokowanie przez `llm_verdict=reject`/`llm_risk_level=high` (REQ-052 removed) oraz event `llm-approved` (REQ-053 removed). LLM peĹ‚ni wyĹ‚Ä…cznie rolÄ™ komentatora: ocena jest doĹ‚Ä…czana do treĹ›ci powiadomienia, ale nie blokuje ani nie wyzwala eventĂłw.
- Poprawiono jakoĹ›Ä‡ komentarzy LLM: `summary` zmienione z jednego zdania na 3-5 zdaĹ„ (ocena cenowa, sygnaĹ‚y, rekomendacja), liczba powodĂłw zwiÄ™kszona do 8, `DEFAULT_MAX_TOKENS` podniesiony do 1600, system prompt uzupeĹ‚niony o instrukcjÄ™ konkretnoĹ›ci (REQ-058 updated).
- Naprawiono bĹ‚Ä…d scrapera: `wait_until_article_count_stabilizes()` w `scraper.py` wychodziĹ‚a po 2 rundach z zerowÄ… liczbÄ… artykuĹ‚Ăłw, zanim React zamontowaĹ‚ listingi. Dodano `page.wait_for_selector("article[data-id]", timeout=20000)` przed pÄ™tlÄ… stabilizacji.

### 2026-04-19

- Dodano LLM on-demand w warstwie powiadomieĹ„: oferty bez oceny LLM sÄ… oceniane przez LLM tuĹĽ przed wysĹ‚aniem powiadomienia (limit `llm.max_notification_llm_calls` per run, domyĹ›lnie 5).
- Naprawiono `upsert_cars_to_csv` w `storage.py`: hardcoded `fieldnames` nie zawieraĹ‚ `details_damaged_flag` ani pĂłl LLM â€” `writerows` rzucaĹ‚ `ValueError` przy istniejÄ…cych CSV wzbogaconych przez enrichment/LLM. Naprawiono przez: dodanie brakujÄ…cego pola do baseline, scalanie baseline z nagĹ‚Ăłwkami istniejÄ…cego CSV (nowe kolumny dopisywane na koĹ„cu), `extrasaction="ignore"` jako dodatkowe zabezpieczenie.

### 2026-04-15

- Naprawiono faĹ‚szywe powiadomienia dla ofert, gdzie kwota z ogĹ‚oszenia byĹ‚a ratÄ… lub elementem cesji, a nie realnÄ… cenÄ… auta.
- Rozszerzono i scalono domyĹ›lne flagi uszkodzeĹ„ z konfiguracjÄ… uĹĽytkownika w filtrze powiadomieĹ„.
- Dodano testy regresyjne dla przypadkĂłw `finance/installment` oraz `damage flags`.

## Comparable Offer Segmentation Rules

### 1. Bazowy segment porĂłwnawczy

- Oferta jest porĂłwnywana najpierw tylko z ofertami z tej samej kwerendy, czyli w praktyce tego samego modelu bazowego.
- Paliwo i typ skrzyni biegĂłw sÄ… traktowane jako pola silnie rozdzielajÄ…ce i w pierwszym kroku nie powinny byÄ‡ mieszane.
- Parametr silnika moĹĽe byÄ‡ reprezentowany przez `power_hp`, a jeĹ›li go brakuje, przez `engine_cm3`.

### 2. DomyĹ›lne tolerancje segmentacji v1

- Rocznik: preferowane oferty z przedziaĹ‚u `target_year +/- 1`.
- Przebieg: preferowane oferty z przedziaĹ‚u `target_mileage_km +/- 20000` km.
- Moc: preferowane oferty z przedziaĹ‚u `target_power_hp +/- 15` KM.
- PojemnoĹ›Ä‡ silnika: fallback do przedziaĹ‚u `target_engine_cm3 +/- 200` cm3, jeĹ›li brakuje mocy.
- Paliwo: musi byÄ‡ zgodne, jeĹ›li informacja jest dostÄ™pna.
- Skrzynia: musi byÄ‡ zgodna, jeĹ›li informacja jest dostÄ™pna.

### 3. Minimalna licznoĹ›Ä‡ grupy porĂłwnawczej

- Bazowy segment powinien zawieraÄ‡ co najmniej `5` aktywnych ofert, aby wynik byĹ‚ uznany za wiarygodny.
- JeĹ›li segment ma mniej niĹĽ `5` ofert, analityka ma przejĹ›Ä‡ do kontrolowanego fallbacku.
- JeĹ›li po fallbacku nadal jest mniej niĹĽ `3` ofert, wynik ma byÄ‡ oznaczony jako niski confidence.

### 4. KolejnoĹ›Ä‡ fallbacku

- Krok 1: rozszerzyÄ‡ rocznik do `target_year +/- 2`.
- Krok 2: rozszerzyÄ‡ przebieg do `target_mileage_km +/- 30000` km.
- Krok 3: rozszerzyÄ‡ moc do `target_power_hp +/- 25` KM albo pojemnoĹ›Ä‡ do `target_engine_cm3 +/- 300` cm3.
- Krok 4: dopuĹ›ciÄ‡ porĂłwnanie w ramach tej samej kwerendy bez zgodnoĹ›ci skrzyni biegĂłw, ale ze spadkiem confidence.
- Krok 5: dopuĹ›ciÄ‡ porĂłwnanie w ramach tej samej kwerendy bez zgodnoĹ›ci dokĹ‚adnego parametru silnika, ale nadal bez mieszania paliwa, jeĹ›li paliwo jest znane.

### 5. ReguĹ‚y bezpieczeĹ„stwa

- Nie wolno porĂłwnywaÄ‡ ofert benzynowych i diesla w jednym segmencie, jeĹ›li obie wartoĹ›ci sÄ… znane.
- Nie wolno porĂłwnywaÄ‡ ofert z rĂłĹĽnych modeli tylko po podobnym roczniku i cenie.
- Oferta z brakami w wielu kluczowych polach ma byÄ‡ liczona, ale z obniĹĽonym confidence.
- WartoĹ›Ä‡ referencyjna rynku powinna pochodziÄ‡ z mediany lub percentyla grupy porĂłwnawczej, a nie ze Ĺ›redniej arytmetycznej.

### 6. Skutek dla dalszej analizy

- Segmentacja ma zwracaÄ‡ nie tylko grupÄ™ porĂłwnawczÄ…, ale teĹĽ informacjÄ™, jaki poziom fallbacku zostaĹ‚ uĹĽyty.
- Poziom fallbacku ma wpĹ‚ywaÄ‡ na confidence i pĂłĹşniej na koĹ„cowy `deal_score`.
- Oferta bardzo tania wzglÄ™dem sĹ‚abego segmentu porĂłwnawczego nie powinna automatycznie trafiaÄ‡ do top okazji bez dodatkowej ostroĹĽnoĹ›ci.

## Deal Score V1 Rules

### 1. Cel score

- `deal_score` ma odpowiadaÄ‡ na pytanie, czy oferta wyglÄ…da atrakcyjnie cenowo i operacyjnie na tle porĂłwnywalnych ofert.
- `deal_score` nie jest ocenÄ… koĹ„cowÄ… jakoĹ›ci auta, tylko rankingiem kandydatĂłw do dalszej weryfikacji.
- `confidence_score` ma mĂłwiÄ‡, jak bardzo moĹĽna ufaÄ‡ wyliczeniu `deal_score`.

### 2. Zakres i interpretacja

- `deal_score` ma byÄ‡ liczbÄ… z zakresu `0-100`.
- `confidence_score` ma byÄ‡ liczbÄ… z zakresu `0-100`.
- Wysoki `deal_score` przy niskim `confidence_score` ma oznaczaÄ‡ ofertÄ™ ciekawÄ…, ale wymagajÄ…cÄ… ostroĹĽnoĹ›ci.
- Wysoki `confidence_score` bez przewagi cenowej nie powinien sam tworzyÄ‡ okazji.

### 3. SkĹ‚adowe deal_score v1

- `market_position_score`: gĹ‚Ăłwny skĹ‚adnik oparty o relacjÄ™ ceny oferty do mediany i dolnych percentyli grupy porĂłwnawczej.
- `freshness_score`: premia za nowÄ… ofertÄ™ lub ofertÄ™ Ĺ›wieĹĽo zaktualizowanÄ… z dobrym poziomem ceny.
- `price_drop_score`: premia za istotny spadek ceny wzglÄ™dem wczeĹ›niejszych obserwacji.
- `stability_score`: lekka korekta za historiÄ™ zmian ceny i dĹ‚ugoĹ›Ä‡ obecnoĹ›ci na rynku.
- `seller_type_adjustment`: lekka korekta za typ sprzedawcy, z premiÄ… dla ofert prywatnych i lekkÄ… karÄ… dla ofert firmowych.
- `data_quality_penalty`: kara za brak kluczowych pĂłl potrzebnych do porĂłwnania.
- `segment_confidence_penalty`: kara za uĹĽycie agresywnego fallbacku lub zbyt maĹ‚Ä… prĂłbkÄ™ porĂłwnawczÄ….

### 4. Priorytet wag

- NajwiÄ™kszÄ… wagÄ™ ma `market_position_score`.
- `freshness_score` i `price_drop_score` sÄ… wzmacniaczami, a nie gĹ‚Ăłwnym ĹşrĂłdĹ‚em okazji.
- `stability_score` ma mniejszÄ… wagÄ™ niĹĽ relacja ceny do rynku.
- `seller_type_adjustment` ma byÄ‡ sĹ‚abym sygnaĹ‚em pomocniczym, a nie dominujÄ…cym czynnikiem.
- Kary za jakoĹ›Ä‡ danych i confidence majÄ… dziaĹ‚aÄ‡ tĹ‚umiÄ…co na koĹ„cowy wynik.

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
- 2026-04-11: Added configurable notification channels with Telegram delivery support. Preferences can now define per-query/global notification transports; `log` remains the default fallback.
- 2026-04-12: Added notification anti-noise controls: optional `min_confidence_score`, stricter `allowed_buckets`, configurable handling of `reactivated`, and suppression window for `bucket-upgrade` right after reactivation.
- 2026-04-12: Tightened damaged-offer filtering in notifications via `exclude_damaged_listings` plus severe damage flags from enrichment (`airbags_deployed`, `severe_front_damage`, `severe_rear_damage`, `total_loss_declared`, `scrap_candidate`, `parts_only_vehicle`).
- 2026-04-15: Naprawiono faĹ‚szywe powiadomienia dla ofert, gdzie kwota z ogĹ‚oszenia byĹ‚a ratÄ… lub elementem cesji, a nie realnÄ… cenÄ… auta. Rozszerzono i scalono domyĹ›lne flagi uszkodzeĹ„ z konfiguracjÄ… uĹĽytkownika w filtrze powiadomieĹ„. Dodano testy regresyjne.
- 2026-04-17: Naprawiono paginacjÄ™ scrapera â€” selektor `div.eemmnsu4` (auto-generowana klasa CSS Otomoto) przestaĹ‚ dziaĹ‚aÄ‡ po aktualizacji frontendu serwisu. ZastÄ…piony stabilnymi selektorami atrybutowymi `button[title='Go to next Page']` / `button[aria-label='Go to next Page']`.
- 2026-04-17: Naprawiono `AttributeError: 'NoneType' has no attribute 'strip'` w `enrichment_worker.py` przy odczycie `details_status` â€” wartoĹ›Ä‡ None jest teraz bezpiecznie traktowana jako pusty string.
- 2026-04-17: Dodano samoczyszczenie `enrichment_queue.csv` po kaĹĽdym przebiegu (`flush_completed_from_queue`). Wpisy `fetched`/`skipped` sÄ… usuwane z kolejki; `failed` zostajÄ… do ponowienia. Dodano throttling (1.5â€“4 s) miÄ™dzy requestami enrichmentu, logi postÄ™pu `[X/N]`, parametr `--enrichment-limit N` w `main.py` oraz pole `source_csv` w nowych wpisach kolejki.
- 2026-04-17: Naprawiono wiszenie enrichment workera przy duĹĽej kolejce â€” faza filtrowania buduje teraz jednorazowy indeks w pamiÄ™ci ze wszystkich storage CSV zamiast odczytywaÄ‡ kaĹĽdy plik dla kaĹĽdego wpisu kolejki (O(nĂ—m) â†’ O(n+m)). Wpisy w cooldownie sÄ… teĹĽ od razu usuwane z pliku kolejki.
- 2026-04-17: Kolejka enrichmentu jest teraz sortowana malejÄ…co po `priority` przed przetwarzaniem â€” przy uĹĽyciu `--enrichment-limit N` zawsze procesowane sÄ… najpierw najwyĹĽej priorytetowe oferty.
- 2026-04-17: `--dry-run` w `main.py` pomija scraping stron, ale wykonuje enrichment i powiadomienia gdy podano `--run-enrichment`/`--run-notifications`. Naprawiono bĹ‚Ä…d gdzie `--dry-run` przerywaĹ‚ dziaĹ‚anie przed tymi blokami (`return` zastÄ…piony blokiem `else`).
- 2026-04-19: Naprawiono lukÄ™ w wykrywaniu uszkodzonych ofert â€” strukturalna flaga â€žUszkodzony" z sekcji â€žStan i historia" (checkbox `parametersDict["damaged"]` z `__NEXT_DATA__`) nie byĹ‚a wczeĹ›niej uwzglÄ™dniana w scoringu ani filtrze powiadomieĹ„. Dodano `_score_parameters()` w `enrichment_analysis.py` z karÄ… -25 pkt i flagÄ… `damage_structural`; analogicznie premia +8 pkt i flaga `accident_free_structural` dla `no_accident=True`. Nowe pole `details_damaged_flag` w CSV (OR tekstu i struktury); `notifications.py` sprawdza to pole obok `is_damaged`.
- 2026-04-19: Dodano tryb `damaged_handling=llm` w `notification_filters` (REQ-055): drobne uszkodzenia delegowane do oceny LLM â€” powiadomienie tylko przy `llm_verdict=approve` + ryzyko non-high; ciÄ™ĹĽkie flagi (szkoda caĹ‚kowita, wystrzelone poduszki itd.) zawsze twardy blok. Prompt LLM rozszerzony o sekcjÄ™ `## Stan uszkodzenia`.
- 2026-04-19: Dodano flagÄ™ `--loop` w `main.py` (REQ-056): nieprzerwana pÄ™tla scrapowania z konfigurowalnymi przerwami (`--loop-interval SEC`, domyĹ›lnie 1800 s). Ctrl+C przerywa czysto w dowolnym momencie.
- 2026-04-19: Naprawiono detekcjÄ™ importu w `enrichment_analysis._score_consistency()` â€” poprzedni kod nie wykrywaĹ‚ wzorca checkboxa otomoto (`value == key`). Dodano reguĹ‚Ä™ `overseas_import` z karÄ… -8 pkt dla rynkĂłw zamorskich (REQ-057). Prompt LLM uzupeĹ‚niony o sekcjÄ™ `## Import i kraj pochodzenia`. Naprawiono teĹĽ problem przestarzaĹ‚ych rekordĂłw CSV: `build_prompt()` teraz czyta `parameters` bezpoĹ›rednio z sidecar JSON jako fallback â€” uszkodzenie i import sÄ… zawsze widoczne dla LLM niezaleĹĽnie od wieku enrichmentu.

### 5. ReguĹ‚y interpretacji sygnaĹ‚Ăłw

- Oferta wyraĹşnie poniĹĽej mediany porĂłwnywalnego segmentu powinna dostawaÄ‡ mocnÄ… premiÄ™.
- Oferta tylko nieznacznie taĹ„sza od rynku nie powinna trafiaÄ‡ wysoko wyĹ‚Ä…cznie dlatego, ĹĽe jest nowa.
- ĹšwieĹĽa obniĹĽka ceny powinna podnosiÄ‡ priorytet, szczegĂłlnie jeĹ›li po obniĹĽce oferta schodzi poniĹĽej mediany segmentu.
- DĹ‚ugo wiszÄ…ca oferta bez reakcji rynku nie powinna byÄ‡ automatycznie traktowana jako okazja, nawet jeĹ›li jest taĹ„sza od mediany.
- Brak `year`, `mileage_km`, `fuel_type`, `gearbox` lub parametru silnika ma obniĹĽaÄ‡ jakoĹ›Ä‡ analizy, jeĹ›li blokuje dobre porĂłwnanie.

### 6. Progi decyzyjne v1

- `0-39`: `ignore`.
- `40-59`: `watch`.
- `60-79`: `candidate`.
- `80-100`: `high-priority`.
- JeĹ›li `confidence_score < 40`, oferta nie moĹĽe wejĹ›Ä‡ do `high-priority` bez dodatkowego potwierdzenia przez enrichment.

### 7. Wymagany format wyniku analitycznego

- Wynik ma zawieraÄ‡ `deal_score`.
- Wynik ma zawieraÄ‡ `confidence_score`.
- Wynik ma zawieraÄ‡ `decision_bucket`.
- Wynik ma zawieraÄ‡ `comparison_group_size`.
- Wynik ma zawieraÄ‡ `fallback_level`.
- Wynik ma zawieraÄ‡ listÄ™ `reasons`, np. "12% poniĹĽej mediany segmentu" albo "niska licznoĹ›Ä‡ grupy porĂłwnawczej".

### 8. Zasady ostroĹĽnoĹ›ci

- Nie wolno windowaÄ‡ `deal_score` wyĹ‚Ä…cznie na podstawie pojedynczego sygnaĹ‚u, jeĹ›li reszta danych jest sĹ‚aba.
- Oferta nie moĹĽe dostaÄ‡ najwyĹĽszego priorytetu tylko dlatego, ĹĽe ma bardzo niski przebieg lub bardzo nowy rocznik, jeĹ›li cena nie wyrĂłĹĽnia siÄ™ wzglÄ™dem segmentu.
- `confidence_score` ma obniĹĽaÄ‡ zdolnoĹ›Ä‡ oferty do przejĹ›cia do enrichmentu i LLM, jeĹ›li segmentacja byĹ‚a sĹ‚aba.
- Wynik ma byÄ‡ wystarczajÄ…co czytelny, aby uĹĽytkownik mĂłgĹ‚ zrozumieÄ‡, dlaczego oferta zostaĹ‚a uznana za ciekawÄ….

## Enrichment Selection Rules

### 1. Cel enrichmentu

- Enrichment ma pobieraÄ‡ dane szczegĂłĹ‚owe tylko tam, gdzie dodatkowy koszt wejĹ›cia w ogĹ‚oszenie ma uzasadnienie analityczne.
- Enrichment jest drugim etapem pipeline'u i nie moĹĽe byÄ‡ wymagany do podstawowego monitorowania rynku.
- Brak enrichmentu nie moĹĽe zatrzymywaÄ‡ wyliczenia `deal_score` v1.

### 2. Twarde wyzwalacze wejĹ›cia do enrichmentu

- Nowa oferta, ktĂłra pojawiĹ‚a siÄ™ pierwszy raz w danych.
- Oferta z bucketem `high-priority`.
- Oferta z bucketem `candidate` i Ĺ›wieĹĽym spadkiem ceny.
- Oferta z wysokim `deal_score`, ale niskim lub Ĺ›rednim `confidence_score`, jeĹ›li szczegĂłĹ‚y mogÄ… pomĂłc w ocenie.
- Oferta z brakami danych tekstowych lub strukturalnych, ktĂłre ograniczajÄ… decyzjÄ™ na dalszym etapie.

### 3. MiÄ™kkie wyzwalacze wejĹ›cia do enrichmentu

- Oferta nowa w bucketcie `watch`, jeĹ›li znajduje siÄ™ blisko progu `candidate`.
- Oferta dĹ‚ugo obserwowana, ktĂłra nagle zmieniĹ‚a cenÄ™ lub wrĂłciĹ‚a jako aktywna.
- Oferta wybrana do prĂłbki kontrolnej w celu walidacji jakoĹ›ci scoringu.

### 4. Priorytety kolejki enrichmentu

- Priorytet `P1`: nowe oferty z bucketem `high-priority`.
- Priorytet `P2`: oferty `candidate` lub `high-priority` z istotnym spadkiem ceny.
- Priorytet `P3`: nowe oferty z bucketem `candidate`.
- Priorytet `P4`: oferty `watch`, ktĂłre sÄ… blisko progu `candidate` albo majÄ… niski confidence z powodu brakĂłw danych.
- Priorytet `P5`: prĂłbka kontrolna lub odĹ›wieĹĽenie starszych szczegĂłĹ‚Ăłw.

### 5. ReguĹ‚y ograniczajÄ…ce ponowne pobrania

- Nie pobieraÄ‡ szczegĂłĹ‚Ăłw ponownie dla tej samej oferty przy kaĹĽdym przebiegu bez nowego sygnaĹ‚u.
- Ponowny enrichment ma byÄ‡ uruchamiany, jeĹ›li zmieniĹ‚a siÄ™ cena, status aktywnoĹ›ci albo oferta przekroczyĹ‚a wyĹĽszy bucket decyzji.
- JeĹ›li szczegĂłĹ‚y zostaĹ‚y pobrane niedawno i oferta nie zmieniĹ‚a istotnie stanu, enrichment ma zostaÄ‡ pominiÄ™ty.
- Starsze szczegĂłĹ‚y mogÄ… byÄ‡ odĹ›wieĹĽane okresowo, ale z niĹĽszym priorytetem niĹĽ nowe okazje.

### 6. PrzykĹ‚adowe warunki pominiÄ™cia enrichmentu

- Oferta w bucketcie `ignore` bez istotnej zmiany ceny.
- Oferta z niskim `deal_score` i wysokim confidence, jeĹ›li analiza juĹĽ stabilnie wskazuje brak okazji.
- Oferta juĹĽ wzbogacona niedawno, bez zmiany ceny, statusu i bucketu.
- Oferta nieaktywna lub usuniÄ™ta, jeĹ›li szczegĂłĹ‚y nie zostaĹ‚y pobrane wczeĹ›niej i nie ma powodu analitycznego do nadrabiania brakĂłw.

### 7. Wymagany stan zapisany po enrichmentcie

- `details_fetched_at`.
- `details_based_on_price_pln`.
- `details_based_on_last_seen_date`.
- `details_status`, np. `fresh`, `stale`, `failed`, `not-needed`.
- Lista pobranych pĂłl tekstowych i strukturalnych, aby wiadomo byĹ‚o, co naprawdÄ™ udaĹ‚o siÄ™ pozyskaÄ‡.

### 8. ZaleĹĽnoĹ›Ä‡ od dalszych etapĂłw

- Warstwa LLM ma korzystaÄ‡ przede wszystkim z ofert po enrichmentcie, a nie z samych listingĂłw.
- Oferta z wysokim priorytetem, ale bez enrichmentu, moĹĽe trafiÄ‡ do kolejki pilnej, lecz nie powinna byÄ‡ traktowana jak peĹ‚ny kandydat jakoĹ›ciowy.
- Powiadomienia koĹ„cowe powinny preferowaÄ‡ oferty, ktĂłre przeszĹ‚y enrichment lub majÄ… bardzo mocny sygnaĹ‚ z analityki v1.

## Enrichment Analysis Rules

### 1. Cel analizy enrichmentu

- Analiza enrichmentu ma przetwarzaÄ‡ dane z detail page do jawnych sygnaĹ‚Ăłw jakoĹ›ciowych i ryzyk, ktĂłrych nie widaÄ‡ na poziomie list-card.
- Analiza enrichmentu ma dziaĹ‚aÄ‡ po pobraniu szczegĂłĹ‚Ăłw i nie moĹĽe byÄ‡ warunkiem dziaĹ‚ania analityki v1.
- Wynik enrichmentu ma doprecyzowywaÄ‡ ocenÄ™ kandydata, a nie zastÄ™powaÄ‡ bazowÄ… ocenÄ™ rynkowÄ….

### 2. Zakres sygnaĹ‚Ăłw enrichmentu

- System ma wykrywaÄ‡ sygnaĹ‚y pozytywne w opisie, np. `bezwypadkowy`, `serwis ASO`, `pierwszy wĹ‚aĹ›ciciel`, `garaĹĽowany`, `udokumentowana historia`.
- System ma wykrywaÄ‡ sygnaĹ‚y ryzyka w opisie, np. `uszkodzony`, `do poprawek`, `po kolizji`, `naprawiany`, `brak dokumentĂłw`, `Ĺ›wieĹĽo sprowadzony`.
- System ma braÄ‡ pod uwagÄ™ dane strukturalne z detail page, np. VIN, parametry pojazdu, kraj pochodzenia, typ napÄ™du, wyposaĹĽenie i dane sprzedawcy.
- System ma wykrywaÄ‡ niespĂłjnoĹ›ci miÄ™dzy listingiem a detail page, jeĹ›li cena, parametry lub typ sprzedawcy nie zgadzajÄ… siÄ™ miÄ™dzy etapami.

### 3. Wymagany wynik analizy enrichmentu

- Wynik ma zawieraÄ‡ `enrichment_score` w skali `0-100`.
- Wynik ma zawieraÄ‡ `enrichment_confidence` w skali `0-100`.
- Wynik ma zawieraÄ‡ `enrichment_reasons`, czyli listÄ™ najwaĹĽniejszych sygnaĹ‚Ăłw uĹĽytych do oceny.
- Wynik ma zawieraÄ‡ `enrichment_flags`, czyli krĂłtkie flagi diagnostyczne, np. `vin_present`, `damage_declared`, `aso_service`, `listing_detail_mismatch`.

### 4. WpĹ‚yw enrichmentu na dalszÄ… decyzjÄ™

- Enrichment moĹĽe wzmacniaÄ‡ albo osĹ‚abiaÄ‡ priorytet oferty juĹĽ uznanej za ciekawÄ… cenowo.
- Enrichment moĹĽe obniĹĽyÄ‡ ofertÄ™ z shortlisty, jeĹ›li wykryje istotne sygnaĹ‚y ryzyka mimo dobrego `market_score`.
- Enrichment nie moĹĽe samodzielnie promowaÄ‡ oferty z niskim `market_score` do najwyĹĽszego priorytetu.
- Finalny etap rankingu ma jawnie pokazywaÄ‡, jaki wpĹ‚yw miaĹ‚y dane listingowe, preferencje i enrichment.

### 5. ReguĹ‚y ostroĹĽnoĹ›ci dla enrichmentu

- Brak czÄ™Ĺ›ci szczegĂłĹ‚Ăłw na detail page nie moĹĽe automatycznie oznaczaÄ‡ wysokiego ryzyka; powinien obniĹĽaÄ‡ przede wszystkim `enrichment_confidence`.
- Pojedyncza pozytywna fraza marketingowa nie moĹĽe dawaÄ‡ silnej premii bez potwierdzajÄ…cych sygnaĹ‚Ăłw strukturalnych.
- Pojedyncza czerwona flaga o wysokiej istotnoĹ›ci moĹĽe znaczÄ…co obniĹĽyÄ‡ ocenÄ™ jakoĹ›ciowÄ… nawet przy dobrym wyposaĹĽeniu i opisie.
- ReguĹ‚y enrichmentu majÄ… byÄ‡ deterministyczne i testowalne przed ewentualnym przekazaniem oferty do warstwy LLM.

### 6. ZaleĹĽnoĹ›Ä‡ od LLM i powiadomieĹ„

- Warstwa LLM ma dostawaÄ‡ enrichment jako ustrukturyzowane wejĹ›cie, a nie tylko surowy HTML albo peĹ‚ny JSON strony.
- Powiadomienia koĹ„cowe powinny uwzglÄ™dniaÄ‡ najwaĹĽniejsze `enrichment_flags` i `enrichment_reasons`, jeĹ›li enrichment byĹ‚ dostÄ™pny.
- Oferta bez enrichmentu moĹĽe trafiÄ‡ do powiadomieĹ„ tylko wtedy, gdy sygnaĹ‚ z analityki v1 jest bardzo mocny albo enrichment nie byĹ‚ jeszcze moĹĽliwy do wykonania.

## LLM Review Rules

### 1. Cel warstwy LLM

- LLM ma peĹ‚niÄ‡ rolÄ™ filtra jakoĹ›ciowego dla kandydatĂłw wybranych wczeĹ›niej przez analitykÄ™ i enrichment.
- LLM nie zastÄ™puje segmentacji ani `deal_score`, tylko ocenia ryzyka i sygnaĹ‚y semantyczne trudne do ujÄ™cia reguĹ‚ami.
- LLM ma dziaĹ‚aÄ‡ na ograniczonym zbiorze ofert, aby koszt i czas byĹ‚y kontrolowane.

### 2. WejĹ›cie do LLM

- Do LLM trafiajÄ… przede wszystkim oferty z bucketem `high-priority` po enrichmentcie.
- Do LLM mogÄ… trafiaÄ‡ oferty `candidate`, jeĹ›li majÄ… mocny sygnaĹ‚ cenowy i wystarczajÄ…ce dane tekstowe po enrichmentcie.
- Oferta bez enrichmentu moĹĽe trafiÄ‡ do LLM wyjÄ…tkowo, jeĹ›li ma bardzo wysoki `deal_score`, ale taki przypadek ma byÄ‡ oznaczony niĹĽszym confidence recenzji.
- System ma mieÄ‡ limit liczby ofert kierowanych do LLM na jeden przebieg.

### 3. Zakres oceny LLM

- LLM ma szukaÄ‡ sygnaĹ‚Ăłw ryzyka w opisie, tytule i polach szczegĂłĹ‚owych oferty.
- LLM ma identyfikowaÄ‡ wzmianki o szkodzie, naprawach, brakach dokumentacji, problemach prawnych, imporcie, komisie, niejasnej historii i agresywnym marketingu maskujÄ…cym wady.
- LLM ma wskazywaÄ‡ takĹĽe pozytywne sygnaĹ‚y, np. serwis ASO, pierwszy wĹ‚aĹ›ciciel, udokumentowana historia, bezwypadkowoĹ›Ä‡ deklarowana wprost.

### 4. Wymagany wynik LLM

- `llm_verdict`, np. `approve`, `review`, `reject`.
- `llm_risk_level`, np. `low`, `medium`, `high`.
- `llm_summary`, czyli krĂłtki opis najwaĹĽniejszego wniosku.
- `llm_reasons`, czyli lista gĹ‚Ăłwnych sygnaĹ‚Ăłw pozytywnych i negatywnych.
- `llm_confidence`, czyli poziom pewnoĹ›ci odpowiedzi modelu.

### 5. ReguĹ‚y bezpieczeĹ„stwa dla LLM

- LLM nie moĹĽe samodzielnie promowaÄ‡ oferty do okazji, jeĹ›li analityka v1 nie wykazaĹ‚a przewagi cenowej.
- LLM moĹĽe obniĹĽyÄ‡ priorytet oferty albo skierowaÄ‡ jÄ… do rÄ™cznego sprawdzenia.
- Odpowiedzi LLM majÄ… byÄ‡ moĹĽliwie ustrukturyzowane i krĂłtkie, aby nadawaĹ‚y siÄ™ do logowania i powiadomieĹ„.
- System ma zapisywaÄ‡ dane wejĹ›ciowe do LLM i wynik oceny, aby daĹ‚o siÄ™ pĂłĹşniej przeanalizowaÄ‡ bĹ‚Ä™dne decyzje.

## Notification Rules

### 1. Cel powiadomieĹ„

- Powiadomienia majÄ… informowaÄ‡ tylko o ofertach, ktĂłre realnie zasĹ‚ugujÄ… na uwagÄ™ uĹĽytkownika.
- Warstwa powiadomieĹ„ ma minimalizowaÄ‡ spam i duplikaty.
- Powiadomienie jest koĹ„cowym produktem pipeline'u, a nie surowym logiem technicznym.

### 2. Zdarzenia generujÄ…ce powiadomienie

- Nowa oferta oceniona jako `high-priority`.
- Oferta, ktĂłra awansowaĹ‚a z `watch` lub `candidate` do `high-priority`.
- Istotny spadek ceny w ofercie juĹĽ znanej, jeĹ›li po spadku oferta nadal speĹ‚nia kryteria okazji.
- Oferta ponownie aktywna, jeĹ›li wczeĹ›niej byĹ‚a nieaktywna, a teraz wraca z mocnym sygnaĹ‚em.
- Oferta zatwierdzona przez LLM jako niskiego ryzyka, jeĹ›li warstwa LLM jest juĹĽ aktywna.

### 3. Zdarzenia, ktĂłre nie powinny generowaÄ‡ powiadomienia

- KaĹĽdy kolejny przebieg bez nowego sygnaĹ‚u.
- Ta sama oferta z niezmienionym bucketem, cenÄ… i statusem.
- Oferta z bucketem `watch`, jeĹ›li nie przekracza progĂłw istotnoĹ›ci.
- Oferta odrzucona przez LLM albo oznaczona jako wysokiego ryzyka.

### 4. ReguĹ‚y deduplikacji

- Deduplikacja ma dziaĹ‚aÄ‡ co najmniej na parze `listing_id + event_type`.
- System ma zapisywaÄ‡ czas ostatniego wysĹ‚ania powiadomienia dla danego typu zdarzenia.
- Ponowne powiadomienie dla tej samej oferty jest dozwolone tylko po nowym sygnale, np. dalszym spadku ceny albo awansie bucketu.
- Powiadomienie nie moĹĽe byÄ‡ wysyĹ‚ane wielokrotnie tylko dlatego, ĹĽe oferta nadal istnieje w danych.

### 5. Minimalna zawartoĹ›Ä‡ powiadomienia

- TytuĹ‚ oferty.
- Link do ogĹ‚oszenia.
- Aktualna cena.
- NajwaĹĽniejszy powĂłd powiadomienia.
- `deal_score`, `confidence_score` i bucket decyzji.
- SkrĂłcony komentarz LLM, jeĹ›li warstwa LLM byĹ‚a uĹĽyta.

### 6. KanaĹ‚y i niezaleĹĽnoĹ›Ä‡ dostawy

- Warstwa powiadomieĹ„ ma byÄ‡ niezaleĹĽna od konkretnego kanaĹ‚u dostawy.
- Ten sam event powinien daÄ‡ siÄ™ wysĹ‚aÄ‡ przez email albo Telegram bez zmiany logiki decyzyjnej.
- Informacja o sukcesie lub bĹ‚Ä™dzie wysyĹ‚ki ma byÄ‡ zapisywana osobno od samej decyzji o powiadomieniu.

## Analytics V1 Notes

- Okazja nie jest definiowana jako "niska cena" sama w sobie.
- Ocena ma byÄ‡ relatywna wzglÄ™dem podobnych ofert w obrÄ™bie tej samej kwerendy lub segmentu porĂłwnawczego.
- PodobieĹ„stwo ofert ma uwzglÄ™dniaÄ‡ przynajmniej: rocznik, przebieg, pojemnoĹ›Ä‡ silnika lub moc, paliwo oraz typ skrzyni.
- Dwie oferty tego samego modelu mogÄ… mieÄ‡ zupeĹ‚nie innÄ… ocenÄ™ przy tej samej cenie, jeĹ›li rĂłĹĽniÄ… siÄ™ rocznikiem, silnikiem lub przebiegiem.
- Warstwa analityczna v1 ma dziaĹ‚aÄ‡ nawet bez danych szczegĂłĹ‚owych z wnÄ™trza ogĹ‚oszenia.
- Enrichment i LLM sÄ… kolejnymi filtrami jakoĹ›ci, a nie czÄ™Ĺ›ciÄ… bazowej definicji okazji.
- Segmentacja ma byÄ‡ deterministyczna i czytelna, ĹĽeby moĹĽna byĹ‚o wyjaĹ›niÄ‡ pĂłĹşniej, z jakÄ… grupÄ… oferta zostaĹ‚a porĂłwnana.
- `deal_score` i `confidence_score` majÄ… byÄ‡ rozdzielone, bo atrakcyjnoĹ›Ä‡ oferty i pewnoĹ›Ä‡ oceny to dwa rĂłĹĽne sygnaĹ‚y.
- Enrichment ma byÄ‡ selektywny, kolejkujÄ…cy i reaktywny na nowe sygnaĹ‚y, a nie wykonywany hurtowo dla caĹ‚ego rynku.
- LLM ma redukowaÄ‡ ryzyko faĹ‚szywych pozytywĂłw, a powiadomienia majÄ… trafiaÄ‡ dopiero po przejĹ›ciu przez caĹ‚y sensowny filtr decyzyjny.
- Preferencje uĹĽytkownika majÄ… dziaĹ‚aÄ‡ jako osobna warstwa decyzji, a nie jako substytut analityki rynkowej.

## Done Requirements

Na razie brak wpisĂłw.

## Removed Requirements

Na razie brak wpisĂłw.

## Change Log

| Date       | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-04-07 | Utworzono plik wymagaĹ„ i zapisano poczÄ…tkowy zestaw wymagaĹ„ dla warstwy scrapingu, storage, analytics, enrichment, LLM i powiadomieĹ„.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 2026-04-07 | Doprecyzowano wymagania dla analityki v1: relatywna definicja okazji, segmentacja ofert porĂłwnywalnych, wieloskĹ‚adnikowy scoring, selektywny enrichment, wejĹ›cie do LLM i zasady powiadomieĹ„.                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| 2026-04-07 | Rozpisano techniczne reguĹ‚y segmentacji ofert porĂłwnywalnych: bazowy segment, tolerancje, minimalnÄ… licznoĹ›Ä‡ grupy, fallback i wpĹ‚yw confidence na dalszÄ… analizÄ™.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| 2026-04-07 | Rozpisano reguĹ‚y `deal_score` v1: zakres wyniku, skĹ‚adowe score, progi decyzyjne, oddzielenie `confidence_score` oraz wymagany format wyniku analitycznego.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 2026-04-07 | Rozpisano reguĹ‚y selekcji do enrichmentu: wyzwalacze, priorytety kolejki, cooldown ponownych pobraĹ„, warunki pominiÄ™cia oraz minimalny stan zapisywany po enrichmentcie.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| 2026-04-07 | Rozpisano reguĹ‚y wejĹ›cia do LLM i powiadomieĹ„: zakres kandydatĂłw, format werdyktu LLM, zdarzenia notyfikacyjne, deduplikacjÄ™ i minimalnÄ… zawartoĹ›Ä‡ komunikatu.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 2026-04-07 | Dodano warstwÄ™ preferencji uĹĽytkownika oraz minimalny kontrakt danych dla analityki, enrichmentu, LLM i powiadomieĹ„.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 2026-04-18 | Dodano obsĹ‚ugÄ™ HTTP 410 Gone w `enrichment_worker.py`: status `gone` oddzielony od `failed`, automatyczny flush wpisĂłw `gone` z kolejki, oznaczenie `is_active=0` w storage CSV i pominiÄ™cie `gone` w kolejnych przebiegach bez potrzeby `--retry-failed`.                                                                                                                                                                                                                                                                                                                                                                                                            |
| 2026-04-18 | Zaimplementowano warstwÄ™ LLM (`llm_worker.py`): selekcja kandydatĂłw po enrichmentcie, prompt po polsku z danymi oferty i sygnaĹ‚ami analityki, wywoĹ‚anie OpenAI API z `response_format=json_object`, zapis wyniku (`llm_verdict`, `llm_risk_level`, `llm_confidence`, `llm_summary`, `llm_reasons`, `llm_reviewed_at`) do storage CSV. Zabezpieczenia: hard cap 20, `max_candidates_per_run` (domyĹ›lnie 5), cooldown 30 dni, `min_final_score`, wymĂłg sidecar JSON, przerwanie przy `RateLimitError`. Model konfigurowalny przez `preferences.json` (klucz `llm`). Integracja z `main.py` przez `--run-llm`, `--llm-limit`, `--llm-model`.                             |
| 2026-04-19 | Dodano `retry_failed_notifications()` w `notifications.py`: ponawia dostarczenie powiadomieĹ„ oznaczonych `notification_status=failed` w `notification_history.csv` bez modyfikowania `notification_state.csv`. DostÄ™pne przez `--retry-failed-notifications` w `main.py`.                                                                                                                                                                                                                                                                                                                                                                                             |
| 2026-04-19 | Dodano mechanizm per-query override filtrĂłw powiadomieĹ„ w `preferences.json` (klucz `queries.<nazwa_kwerendy>.notification_filters`). UmoĹĽliwia poluzowanie lub zaostrzenie progĂłw (np. `min_confidence_score`) dla modeli z maĹ‚Ä… grupÄ… porĂłwnawczÄ… (np. Honda Jazz).                                                                                                                                                                                                                                                                                                                                                                                                 |
| 2026-04-19 | Poprawka `_calculate_confidence_score` w `analytics.py`: kara za `fallback_level` jest teraz skalowana przez rozmiar grupy porĂłwnawczej (`size_factor = max(0.2, 1 - (group_size - MIN) / 30)`). Modele z maĹ‚ym rynkiem (Jazz, Golf Sportsvan) â€” bez zmian. Modele z duĹĽÄ… grupÄ… mimo fallbacku (Sportage gs=165: conf 64â†’93, Qashqai gs=88: conf 76â†’95) przestajÄ… blokowaÄ‡ realne okazje.                                                                                                                                                                                                                                                                             |
| 2026-04-19 | Zintegrowano wynik LLM z warstwÄ… powiadomieĹ„: (1) `_is_notification_eligible()` blokuje oferty z `llm_verdict=reject` lub `llm_risk_level=high` (domyĹ›lnie wĹ‚Ä…czone, konfigurowalne przez `block_llm_rejected`/`block_llm_high_risk` w `notification_filters`); (2) dodano event type `llm-approved` â€” fires gdy `llm_verdict=approve` + `llm_risk_level in {low,medium}` i nie wysĹ‚ano wczeĹ›niej; deduplikacja przez nowe pole `llm_notified_verdict` w `notification_state.csv`; (3) `llm_summary` doĹ‚Ä…czany do treĹ›ci wiadomoĹ›ci i pola `notification_reason_summary`; (4) dodano 4 testy regresyjne w `test_notifications.py`.                                    |
| 2026-04-22 | Naprawiono bĹ‚Ä…d normalizacji `parametersDict` z Otomoto (REQ-060): `_normalize_parameters()` w `enrichment_worker.py` braĹ‚ `.label` zamiast `.values[0].value`, co powodowaĹ‚o `"damaged": "damaged"` i oznaczaĹ‚o wszystkie oferty jako uszkodzone. Naprawiono: (1) `_normalize_parameters()` wyciÄ…ga wartoĹ›ci z listy `values`; (2) guard `key==value â†’ None` w `_parameter_flag()`; (3) analogiczny guard w `_score_parameters()` w `enrichment_analysis.py`; (4) guard w `build_prompt()` w `llm_worker.py`; (5) dodano `--reprocess-details` w `main.py` wywoĹ‚ujÄ…cy `reprocess_details_flags()` â€” jednorazowa migracja 4787 wierszy CSV bez ponownego scrapowania. |
| 2026-04-22 | Zaplanowano wsparcie dla wielu ĹşrĂłdeĹ‚ danych (REQ-061â€“064): pole `source` w `queries.json`, wydzielenie scrapera i parsera do `scrapers/` i `parsers/`, nowe moduĹ‚y `scrapers/mobile_de.py` i `parsers/mobile_de.py`. Warstwy storage/analytics/notifications nie wymagajÄ… zmian. Enrichment mobile.de odkĹ‚adany do osobnej iteracji (REQ-064).                                                                                                                                                                                                                                                                                                                       |
| 2026-04-22 | Zaplanowano strukturyzacjÄ™ kwerend Otomoto (REQ-065): klucz `otomoto_params` w `queries.json` z polami `make`, `model`, `year_from`, `fuel_type`, `mileage_to` itp. â€” config loader buduje `start_url` w czasie Ĺ‚adowania. Pole `start_url` pozostaje jako fallback dla wstecznej kompatybilnoĹ›ci.                                                                                                                                                                                                                                                                                                                                                                    |
| 2026-04-22 | Naprawiono paginacje mobile.de (REQ-062): (1) COOKIE_SELECTORS w scrapers/mobile_de.py zawierl bledny selektor button[data-testid=mde-consent-accept-btn] - rzeczywisty przycisk Einverstanden w #mde-consent-modal-container ma wylacznie klase CSS .mde-consent-accept-btn, bez atrybutu data-testid; poprawiono na button.mde-consent-accept-btn jako priorytetowy selektor; (2) modal GDPR blokowal hover nad przyciskiem paginacji - po poprawce paginacja dziala: strona 1 (24 oferty) -> klikniecie przycisku -> strona 2 (20 ofert) bez blokady Akamai; (3) kwerenda mobile.de w queries.json ustawiona na enabled:true, max_pages:3. |
| 2026-04-22 | Zaimplementowano scoring swiadomy zrodla danych (REQ-066): (1) nowa sekcja `source_adjustments` w `preferences.json`/`preferences.example.json` - per-source parametry `import_cost_pln` i `reliability_score_bonus`; (2) `_calculate_market_score()` w `analytics.py` uzywa efektywnej ceny (cena + koszty importu) do obliczania pozycji vs mediana segmentu; (3) hard-filter `max_price_pln` w `preferences.py` sprawdza efektywna cene - oferta z mobile.de za 51k PLN + 5k importu = 56k blokowana przy limicie 55k; (4) `reliability_score_bonus: +5` dla mobile.de w preference score; domyslna konfiguracja: `import_cost_pln: 5000 PLN`. |
