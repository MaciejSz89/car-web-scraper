# CarWebScraper — Architektura i reguły systemu

Szczegółowe reguły projektowe, kontrakty danych i zasady działania każdej warstwy pipeline'u.

## Spis treści

- [Warstwa preferencji](#warstwa-preferencji)
- [Kontrakt danych analityki i enrichmentu](#kontrakt-danych-analityki-i-enrichmentu)
- [Reguły segmentacji ofert porównywalnych](#reguły-segmentacji-ofert-porównywalnych)
- [Reguły deal_score v1](#reguły-deal_score-v1)
- [Reguły selekcji do enrichmentu](#reguły-selekcji-do-enrichmentu)
- [Reguły analizy enrichmentu](#reguły-analizy-enrichmentu)
- [Reguły warstwy LLM](#reguły-warstwy-llm)
- [Reguły powiadomień](#reguły-powiadomień)
- [Uwagi analityczne v1](#uwagi-analityczne-v1)

---

## Warstwa preferencji

### 1. Cel warstwy preferencji

- Warstwa preferencji ma modelować to, czego użytkownik aktualnie szuka, niezależnie od tego, czy oferta jest obiektywnie dobra względem rynku.
- Preferencje nie mogą zmieniać sposobu liczenia segmentu porównawczego ani bazowego `market_score`.
- Zmiana preferencji użytkownika powinna umożliwiać szybkie przeliczenie shortlisty bez przebudowy historii rynku.

### 2. Typy reguł preferencji

- `hard_filters`: reguły odrzucające ofertę z dalszego procesu użytkowego, np. minimalna pojemność silnika albo maksymalny przebieg.
- `soft_preferences`: reguły zwiększające lub zmniejszające `preference_score`, np. premia za automat albo karanie LPG.
- `boost_rules`: dodatkowe premie za szczególnie pożądane konfiguracje, np. wyższy rocznik albo mocniejszy silnik.
- `notification_filters`: reguły blokujące powiadomienia mimo wysokiego `market_score`, jeśli oferta nie pasuje do preferencji użytkownika.
- `origin_scoring` (podsekcja `soft_preferences`): premia/kara za kraj pochodzenia pojazdu — `poland_bonus`, `private_poland_bonus`, `eu_penalty`, `non_eu_penalty`.

### 3. Zakres konfiguracji preferencji

- Preferencje globalne mają działać dla całego projektu.
- Preferencje per kwerenda mają nadpisywać lub rozszerzać ustawienia globalne dla konkretnego modelu.
- Preferencje powinny obsługiwać co najmniej: minimalny i maksymalny przebieg, minimalną pojemność, minimalną moc, paliwo, skrzynię, budżet, rocznik i kraj pochodzenia pojazdu.

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

---

## Kontrakt danych analityki i enrichmentu

### 1. Minimalny kontrakt wyniku analityki

- `listing_id`, `query_name`, `market_score`, `confidence_score`, `preference_score`, `final_score`.
- `seller_type`, `decision_bucket`, `hard_filter_passed`.
- `comparison_group_size`, `fallback_level`.
- `market_reasons`, `preference_reasons`.
- `enrichment_score`, `enrichment_confidence`, `enrichment_reasons`, `enrichment_flags`.

### 2. Minimalny kontrakt enrichmentu

- `listing_id`, `enrichment_priority`, `details_status`, `details_fetched_at`.
- `details_based_on_price_pln`, `details_based_on_last_seen_date`, `details_based_on_decision_bucket`.
- `details_fields_present`.

### 2a. Operacyjny skrót enrichmentu w CSV

- `details_description_excerpt`, `details_seller_name`, `details_vin`.
- `details_country_origin`, `details_no_accident_flag`, `details_service_record_flag`.
- `details_imported_flag`, `details_enrichment_score`, `details_enrichment_confidence`, `details_enrichment_flags`.

### 2b. Minimalny kontrakt analizy enrichmentu

- `listing_id`, `enrichment_score`, `enrichment_confidence`, `enrichment_reasons`, `enrichment_flags`.
- `description_signals`, `equipment_signals`, `seller_signals`, `consistency_signals`.

### 3. Minimalny kontrakt LLM

- `listing_id`, `llm_verdict`, `llm_risk_level`, `llm_confidence`, `llm_summary`, `llm_reasons`, `llm_reviewed_at`.

### 4. Minimalny kontrakt powiadomień

- `listing_id`, `event_type`, `notification_channel`, `notification_decision`.
- `notification_sent_at`, `notification_status`, `notification_reason_summary`.

---

## Reguły segmentacji ofert porównywalnych

### 1. Bazowy segment porównawczy

- Oferta jest porównywana najpierw tylko z ofertami z tej samej kwerendy (ten sam model bazowy).
- Paliwo i typ skrzyni biegów są traktowane jako pola silnie rozdzielające.
- Parametr silnika może być reprezentowany przez `power_hp`, a jeśli go brakuje, przez `engine_cm3`.

### 2. Domyślne tolerancje segmentacji v1

- Rocznik: `target_year +/- 1`.
- Przebieg: `target_mileage_km +/- 20 000` km.
- Moc: `target_power_hp +/- 15` KM.
- Pojemność silnika: `target_engine_cm3 +/- 200` cm3 (fallback gdy brak mocy).
- Paliwo i skrzynia: muszą być zgodne, jeśli informacja jest dostępna.

### 3. Minimalna liczność grupy porównawczej

- Bazowy segment: minimum `5` aktywnych ofert dla wiarygodnego wyniku.
- Poniżej `5` ofert → kontrolowany fallback.
- Poniżej `3` ofert po fallbacku → niski confidence.

### 4. Kolejność fallbacku

1. Rozszerzyć rocznik do `+/- 2`.
2. Rozszerzyć przebieg do `+/- 30 000` km.
3. Rozszerzyć moc do `+/- 25` KM albo pojemność do `+/- 300` cm3.
4. Dopuścić porównanie bez zgodności skrzyni biegów (ze spadkiem confidence).
5. Dopuścić porównanie bez zgodności dokładnego parametru silnika (bez mieszania paliw).

### 5. Reguły bezpieczeństwa

- Nie wolno porównywać ofert benzynowych i diesla w jednym segmencie, jeśli obie wartości są znane.
- Nie wolno porównywać ofert z różnych modeli tylko po podobnym roczniku i cenie.
- Wartość referencyjna rynku powinna pochodzić z mediany lub percentyla, a nie ze średniej arytmetycznej.

### 6. Skutek dla dalszej analizy

- Segmentacja zwraca grupę porównawczą + informację o użytym poziomie fallbacku.
- Poziom fallbacku wpływa na confidence i na końcowy `deal_score`.

---

## Reguły deal_score v1

### 1. Cel score

- `deal_score` odpowiada na pytanie, czy oferta wygląda atrakcyjnie cenowo i operacyjnie na tle porównywalnych ofert.
- `confidence_score` mówi, jak bardzo można ufać wyliczeniu `deal_score`.

### 2. Zakres i interpretacja

- `deal_score` i `confidence_score`: liczby `0-100`.
- Wysoki `deal_score` przy niskim `confidence_score` → oferta ciekawa, ale wymaga ostrożności.
- Wysoki `confidence_score` bez przewagi cenowej → nie tworzy sam w sobie okazji.

### 3. Składowe deal_score v1

| Składnik                     | Opis                                                                           |
| ---------------------------- | ------------------------------------------------------------------------------ |
| `market_position_score`      | Główny składnik — relacja ceny oferty do mediany i dolnych percentyli segmentu |
| `freshness_score`            | Premia za nową lub świeżo zaktualizowaną ofertę                                |
| `price_drop_score`           | Premia za istotny spadek ceny                                                  |
| `stability_score`            | Korekta za historię zmian ceny i długość obecności na rynku                    |
| `seller_type_adjustment`     | Lekka korekta za typ sprzedawcy                                                |
| `data_quality_penalty`       | Kara za brak kluczowych pól                                                    |
| `segment_confidence_penalty` | Kara za agresywny fallback lub za małą próbkę                                  |

### 4. Progi decyzyjne v1

| Zakres | Bucket          |
| ------ | --------------- |
| 0–39   | `ignore`        |
| 40–59  | `watch`         |
| 60–79  | `candidate`     |
| 80–100 | `high-priority` |

- Jeśli `confidence_score < 40`, oferta nie może wejść do `high-priority` bez dodatkowego potwierdzenia przez enrichment.

### 5. Reguły ostrożności

- Nie wolno windować `deal_score` wyłącznie na podstawie pojedynczego sygnału, jeśli reszta danych jest słaba.
- `confidence_score` ma obniżać zdolność oferty do przejścia do enrichmentu i LLM, jeśli segmentacja była słaba.

---

## Reguły selekcji do enrichmentu

### 1. Cel enrichmentu

- Enrichment ma pobierać dane szczegółowe tylko tam, gdzie dodatkowy koszt wejścia w ogłoszenie ma uzasadnienie analityczne.
- Brak enrichmentu nie może zatrzymywać wyliczenia `deal_score` v1.

### 2. Twarde wyzwalacze wejścia do enrichmentu

- Nowa oferta pojawiająca się pierwszy raz w danych.
- Oferta z bucketem `high-priority`.
- Oferta z bucketem `candidate` i świeżym spadkiem ceny.
- Oferta z wysokim `deal_score`, ale niskim lub średnim `confidence_score`.
- Oferta z brakami danych tekstowych lub strukturalnych.

### 3. Miękkie wyzwalacze wejścia do enrichmentu

- Oferta nowa w buckecie `watch`, jeśli jest blisko progu `candidate`.
- Oferta długo obserwowana, która nagle zmieniła cenę lub wróciła jako aktywna.
- Oferta wybrana do próbki kontrolnej.

### 4. Priorytety kolejki enrichmentu

| Priorytet | Warunek                                                          |
| --------- | ---------------------------------------------------------------- |
| P1        | Nowe oferty z `high-priority`                                    |
| P2        | Oferty `candidate`/`high-priority` z istotnym spadkiem ceny      |
| P3        | Nowe oferty z `candidate`                                        |
| P4        | Oferty `watch` blisko progu `candidate` albo z niskim confidence |
| P5        | Próbka kontrolna lub odświeżenie starszych szczegółów            |

### 5. Reguły ograniczające ponowne pobrania

- Nie pobierać szczegółów ponownie bez nowego sygnału.
- Cooldown domyślnie 7 dni; bypass po zmianie `price_pln` lub awansie `decision_bucket`.
- Starsze szczegóły mogą być odświeżane z niższym priorytetem.

### 6. Zależność od dalszych etapów

- Warstwa LLM korzysta przede wszystkim z ofert po enrichmentcie.
- Powiadomienia powinny preferować oferty, które przeszły enrichment lub mają bardzo mocny sygnał z analityki v1.

---

## Reguły analizy enrichmentu

### 1. Cel analizy enrichmentu

- Analiza enrichmentu przetwarza dane z detail page do jawnych sygnałów jakościowych i ryzyk.
- Wynik enrichmentu doprecyzowuje ocenę kandydata, a nie zastępuje bazową ocenę rynkową.

### 2. Zakres sygnałów enrichmentu

- **Sygnały pozytywne**: `bezwypadkowy`, `serwis ASO`, `pierwszy właściciel`, `garażowany`, `udokumentowana historia`.
- **Sygnały ryzyka**: `uszkodzony`, `do poprawek`, `po kolizji`, `naprawiany`, `brak dokumentów`, `świeżo sprowadzony`.
- Dane strukturalne: VIN, parametry, kraj pochodzenia, typ napędu, wyposażenie, dane sprzedawcy.
- Niespójności między listingiem a detail page.

### 3. Wymagany wynik analizy enrichmentu

- `enrichment_score` (0-100), `enrichment_confidence` (0-100).
- `enrichment_reasons` — lista najważniejszych sygnałów.
- `enrichment_flags` — krótkie flagi diagnostyczne, np. `vin_present`, `damage_declared`, `aso_service`, `listing_detail_mismatch`.

### 4. Wpływ enrichmentu na dalszą decyzję

- Enrichment może wzmacniać lub osłabiać priorytet oferty.
- Enrichment **nie może** samodzielnie promować oferty z niskim `market_score` do najwyższego priorytetu.

### 5. Reguły ostrożności dla enrichmentu

- Brak części szczegółów obniża przede wszystkim `enrichment_confidence`, a nie automatycznie oznacza wysokiego ryzyka.
- Reguły enrichmentu mają być deterministyczne i testowalne przed przekazaniem oferty do LLM.

---

## Reguły warstwy LLM

### 1. Cel warstwy LLM

- LLM pełni rolę filtra jakościowego dla kandydatów wybranych przez analitykę i enrichment.
- LLM nie zastępuje segmentacji ani `deal_score` — ocenia ryzyka i sygnały semantyczne.
- LLM działa na ograniczonym zbiorze ofert (kontrola kosztów i czasu).

### 2. Wejście do LLM

- Oferty `high-priority` po enrichmentcie + oferty `candidate` z mocnym sygnałem cenowym i wystarczającymi danymi tekstowymi.
- System ma limit liczby ofert kierowanych do LLM na jeden przebieg (`max_candidates_per_run`).

### 3. Zakres oceny LLM

- Sygnały ryzyka: szkoda, naprawy, brak dokumentacji, problemy prawne, import, komis, niejasna historia, agresywny marketing.
- Sygnały pozytywne: serwis ASO, pierwszy właściciel, udokumentowana historia, bezwypadkowość.
- Kraj pochodzenia: jeśli brak strukturalnego `details_country_origin`, LLM wyekstrahuje kraj z opisu ogłoszenia i zwróci go w polu `country_origin` odpowiedzi JSON. Wartość jest natychmiast zapisywana do CSV (`details_country_origin`) i wpływa na filtr powiadomień w tym samym runie.

### 4. Wymagany wynik LLM

- `llm_verdict` (`approve` / `review` / `reject`).
- `llm_risk_level` (`low` / `medium` / `high`).
- `llm_summary` — 3-5 zdań (ocena cenowa, kluczowe sygnały, rekomendacja).
- `llm_reasons` — do 8 głównych sygnałów.
- `llm_confidence` — poziom pewności modelu.
- `country_origin` — kraj wyekstrahowany z opisu (pusty string gdy kraj jest już znany ze struktury danych).

### 5. Reguły bezpieczeństwa dla LLM

- LLM **nie może** samodzielnie promować oferty do okazji, jeśli analityka v1 nie wykazała przewagi cenowej.
- LLM może obniżyć priorytet oferty albo skierować ją do ręcznego sprawdzenia.
- System zapisuje dane wejściowe i wynik oceny dla późniejszej analizy błędnych decyzji.

---

## Reguły powiadomień

### 1. Cel powiadomień

- Informowanie wyłącznie o ofertach, które realnie zasługują na uwagę użytkownika.
- Minimalizacja spamu i duplikatów.
- Powiadomienie jest końcowym produktem pipeline'u, a nie surowym logiem technicznym.

### 2. Zdarzenia generujące powiadomienie

- Nowa oferta oceniona jako `high-priority`.
- Oferta, która awansowała z `watch`/`candidate` do `high-priority`.
- Istotny spadek ceny w ofercie już znanej (jeśli po spadku nadal spełnia kryteria okazji).
- Oferta ponownie aktywna z mocnym sygnałem.

### 3. Zdarzenia, które nie powinny generować powiadomienia

- Każdy kolejny przebieg bez nowego sygnału.
- Ta sama oferta z niezmienionymi: bucketem, ceną i statusem.
- Oferta z bucketem `watch` niespełniająca progów istotności.
- Oferta z potwierdzonym krajem pochodzenia spoza UE, gdy włączony jest filtr `exclude_non_eu_origin`.

### 4. Reguły deduplikacji

- Deduplikacja na parze `listing_id + event_type`.
- Ponowne powiadomienie dozwolone tylko po nowym sygnale (dalszy spadek ceny, awans bucketu).

### 5. Minimalna zawartość powiadomienia

- Tytuł oferty, link, aktualna cena.
- Najważniejszy powód powiadomienia.
- `deal_score`, `confidence_score`, bucket decyzji.
- Skrócony komentarz LLM (`llm_summary`), jeśli warstwa LLM była użyta.

### 6. Kanały i niezależność dostawy

- Warstwa powiadomień jest niezależna od konkretnego kanału (log, Telegram, email).
- Ten sam event powinien dać się wysłać przez dowolny kanał bez zmiany logiki decyzyjnej.

---

## Uwagi analityczne v1

- Okazja nie jest definiowana jako „niska cena" sama w sobie — ocena jest relatywna względem podobnych ofert.
- Dwie oferty tego samego modelu mogą mieć zupełnie inną ocenę przy tej samej cenie, jeśli różnią się rocznikiem, silnikiem lub przebiegiem.
- Warstwa analityczna v1 działa nawet bez danych szczegółowych z wnętrza ogłoszenia.
- Enrichment i LLM są kolejnymi filtrami jakości, a nie częścią bazowej definicji okazji.
- `deal_score` i `confidence_score` są rozdzielone — atrakcyjność oferty i pewność oceny to dwa różne sygnały.
