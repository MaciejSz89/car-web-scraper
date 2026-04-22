"""Scraper mobile.de — REQ-062.

Eksponuje `get_html_pages(start_url, ...) -> list[str]` o interfejsie identycznym
z scrapers.otomoto / scraper.py.

Kluczowe różnice względem Otomoto:
- Przeglądarka Firefox (Chromium jest blokowany przez Akamai).
- Brak stealth init-script dla Chromium — Firefox nie wymaga.
- Przed pierwszym wejściem na stronę wynikową odwiedza stronę główną mobile.de,
  aby ustanowić sesję i uniknąć odpowiedzi "Zugriff verweigert".
- Paginacja przez parametr URL `pageNumber` (fallback: `a[data-testid*=pagination]`).
- Wykrywanie ofert na stronie przez `article` z linkiem `/fahrzeuge/details`.
- Stan sesji zapisywany do `.session-state-mobile_de.json`.
"""
from __future__ import annotations

import logging
import random
import traceback
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from camoufox.sync_api import Camoufox
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger(__name__)

MOBILE_DE_HOME = "https://www.mobile.de/"

COOKIE_SELECTORS = [
    "button.mde-consent-accept-btn",
    "button[data-testid='mde-consent-accept-btn']",
    "button[id='consentBanner-acceptAll']",
    "#consent-banner button",
    "button:has-text('Einverstanden')",
    "button:has-text('Alle akzeptieren')",
    "button:has-text('Akzeptieren')",
    "button:has-text('Zustimmen')",
]


# ---------------------------------------------------------------------------
# Pomocnicze funkcje
# ---------------------------------------------------------------------------

def _wait_random(page: Page, delay_range_ms: tuple[int, int], label: str) -> None:
    delay_ms = random.randint(*delay_range_ms)
    logger.info("%s: czekam %d ms", label, delay_ms)
    page.wait_for_timeout(delay_ms)


def _normalize_url(url: str) -> str:
    parsed = urlsplit(url)
    qs = sorted(parse_qsl(parsed.query, keep_blank_values=True))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(qs, doseq=True), ""))


def _accept_cookies(page: Page) -> None:
    for sel in COOKIE_SELECTORS:
        try:
            btn = page.locator(sel).first
            if btn.count() > 0:
                btn.click(timeout=3000)
                logger.info("mobile.de cookies zaakceptowane przez: %s", sel)
                page.wait_for_timeout(1500)
                return
        except Exception:
            pass


def _build_page_url(base_url: str, page_number: int) -> str:
    parsed = urlsplit(base_url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if page_number <= 1:
        params.pop("pageNumber", None)
    else:
        params["pageNumber"] = str(page_number)
    qs = urlencode(params, doseq=True)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, qs, ""))


def _get_current_page_number(url: str) -> int:
    param = dict(parse_qsl(urlsplit(url).query)).get("pageNumber", "1")
    try:
        return max(1, int(param))
    except ValueError:
        return 1


def _build_browser_context(browser, session_state_file: Path):
    """Tworzy kontekst przeglądarki Camoufox.

    Nie ustawiamy viewport/timezone/locale — Camoufox z geoip=True dobiera
    je spójnie na podstawie adresu IP. Nadpisanie tych wartości w new_context()
    tworzyłoby wykrywalną niespójność fingerprintu (np. polskie IP + Berlin tz).

    Przywracamy cookies z poprzedniej sesji — Akamai używa ciasteczek (ak_bmsc,
    bm_sz) do śledzenia zaufanych użytkowników. Bez nich każda sesja wygląda
    jak nowy bot. Przy blokadzie cookies są czyszczone przed kolejną próbą.
    """
    ctx_kwargs: dict = {}
    if session_state_file.exists():
        ctx_kwargs["storage_state"] = str(session_state_file)
        logger.info("mobile.de: przywracam cookies z %s", session_state_file)
    ctx = browser.new_context(**ctx_kwargs)
    page = ctx.new_page()
    return ctx, page


# ---------------------------------------------------------------------------
# Wykrywanie ofert i paginacji
# ---------------------------------------------------------------------------

def _count_listings(page: Page) -> int:
    """Zwraca liczbę artykułów zawierających link do szczegółów oferty."""
    try:
        return page.locator("article:has(a[href*='/fahrzeuge/details'])").count()
    except Exception:
        return 0


def _wait_for_listings(
    page: Page,
    max_rounds: int = 10,
    pause_range_ms: tuple[int, int] = (900, 2200),
    scroll_step_range_px: tuple[int, int] = (1400, 4200),
    first_listing_timeout_ms: int = 20000,
) -> int:
    """Scrolluje stronę i czeka na stabilizację liczby ofert.

    Wzorowany na wait_until_article_count_stabilizes() z scraper.py Otomoto.
    """
    try:
        page.wait_for_selector(
            "article:has(a[href*='/fahrzeuge/details'])",
            timeout=first_listing_timeout_ms,
        )
        logger.info("mobile.de: pierwsza oferta załadowana, startuję stabilizację.")
    except PlaywrightTimeoutError:
        logger.info("mobile.de: brak ofert po %d ms; strona prawdopodobnie pusta.", first_listing_timeout_ms)
        return 0

    previous_count = -1
    same_count_rounds = 0

    for round_no in range(1, max_rounds + 1):
        current_count = _count_listings(page)
        logger.info("mobile.de: runda %d, oferty=%d", round_no, current_count)

        if current_count == previous_count:
            same_count_rounds += 1
        else:
            same_count_rounds = 0

        if same_count_rounds >= 2:
            return current_count

        page.mouse.wheel(0, random.randint(*scroll_step_range_px))
        if round_no % 3 == 0:
            page.wait_for_timeout(random.randint(300, 900))
            page.mouse.wheel(0, -random.randint(120, 480))

        _wait_random(page, pause_range_ms, f"mobile.de: pauza po scrollu {round_no}")
        previous_count = current_count

    return _count_listings(page)


# Selektory przycisku "następna strona" — sprawdzane po kolei
_NEXT_PAGE_SELECTORS = [
    "button[data-testid='pagination:next']",
    "a[data-testid='pagination:next']",
    "a[data-testid*='pagination'][data-testid*='next']",
    "a[aria-label*='Weiter']",
    "a[aria-label*='nächste']",
    "a[title*='Weiter']",
    "a[rel='next']",
    "button[aria-label='Weiter']",
    "a:has-text('Weiter')",
]


def _find_next_page_button(page: Page):
    """Zwraca locator przycisku następnej strony lub None."""
    for sel in _NEXT_PAGE_SELECTORS:
        try:
            locator = page.locator(sel).first
            if locator.count() == 0:
                continue
            aria_disabled = locator.get_attribute("aria-disabled")
            disabled = locator.get_attribute("disabled")
            classes = (locator.get_attribute("class") or "").lower()
            if aria_disabled == "true" or disabled is not None or "disabled" in classes:
                return None
            return locator
        except Exception:
            pass
    return None


def _click_next_page(
    page: Page,
    current_url: str,
    navigation_timeout_ms: int,
    post_navigation_delay_range_ms: tuple[int, int],
    wait_ms: int,
) -> str | None:
    """Klika przycisk następnej strony jak prawdziwy użytkownik.

    Zwraca URL nowej strony lub None jeśli nie ma następnej strony.
    Używamy kliknięcia zamiast page.goto(), bo Akamai wykrywa brak eventu
    kliknięcia przed zmianą URL jako sygnał bota.
    """
    btn = _find_next_page_button(page)
    if btn is None:
        return None

    try:
        # Zamknij modal cookies/GDPR jeśli blokuje kliknięcie
        _accept_cookies(page)
        page.wait_for_timeout(random.randint(300, 600))

        # Przewiń do przycisku i najedź myszą (human-like)
        btn.scroll_into_view_if_needed(timeout=3000)
        page.wait_for_timeout(random.randint(300, 700))
        try:
            btn.hover(timeout=5000)
        except Exception:
            # Modal może nadal blokować — użyj force click
            logger.info("mobile.de: hover zablokowany, próba force click")
            btn.click(force=True, timeout=3000)
            page.wait_for_timeout(wait_ms)
            _wait_random(page, post_navigation_delay_range_ms, "mobile.de: po force click paginacji")
            new_url = page.url
            if _normalize_url(new_url) == _normalize_url(current_url):
                return None
            return new_url
        page.wait_for_timeout(random.randint(200, 500))

        with page.expect_navigation(timeout=navigation_timeout_ms, wait_until="domcontentloaded"):
            btn.click(timeout=3000)

        page.wait_for_timeout(wait_ms)
        _wait_random(page, post_navigation_delay_range_ms, "mobile.de: po kliknięciu paginacji")
        new_url = page.url
        if _normalize_url(new_url) == _normalize_url(current_url):
            logger.warning("mobile.de: po kliknięciu URL się nie zmienił: %s", new_url)
            return None
        return new_url
    except Exception as exc:
        logger.warning("mobile.de: błąd kliknięcia paginacji: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Nawigacja z retry
# ---------------------------------------------------------------------------

def _navigate_with_retry(
    page: Page,
    url: str,
    wait_ms: int,
    post_navigation_delay_range_ms: tuple[int, int],
    retry_backoff_delay_range_ms: tuple[int, int],
    navigation_timeout_ms: int,
    max_navigation_retries: int,
) -> str:
    for attempt in range(1, max_navigation_retries + 1):
        timeout = navigation_timeout_ms if attempt <= 2 else int(navigation_timeout_ms * 1.5)
        wait_until = "domcontentloaded" if attempt <= 2 else "commit"
        try:
            page.goto(url, wait_until=wait_until, timeout=timeout)
            if wait_until == "commit":
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=max(5000, navigation_timeout_ms // 3))
                except PlaywrightTimeoutError:
                    pass
            page.wait_for_timeout(wait_ms)
            _wait_random(page, post_navigation_delay_range_ms, "mobile.de: po wejściu")
            return page.url
        except PlaywrightTimeoutError as exc:
            logger.warning("mobile.de: timeout nawigacji do %s (próba %d/%d): %s", url, attempt, max_navigation_retries, exc)
            try:
                page.evaluate("window.stop()")
            except Exception:
                pass
            if _count_listings(page) > 0:
                page.wait_for_timeout(wait_ms)
                _wait_random(page, post_navigation_delay_range_ms, "mobile.de: po wejściu (po timeout)")
                return page.url
        except Exception as exc:
            logger.warning("mobile.de: błąd nawigacji do %s (próba %d/%d): %s", url, attempt, max_navigation_retries, exc)

        if attempt < max_navigation_retries:
            _wait_random(page, retry_backoff_delay_range_ms, "mobile.de: backoff")

    raise RuntimeError(f"mobile.de: nie udało się otworzyć strony po {max_navigation_retries} próbach: {url}")


# ---------------------------------------------------------------------------
# Publiczne API
# ---------------------------------------------------------------------------

def get_html_pages(
    start_url: str,
    headless: bool,
    wait_ms: int,
    max_pages: int,
    post_navigation_delay_range_ms: tuple[int, int],
    page_break_delay_range_ms: tuple[int, int],
    scroll_pause_range_ms: tuple[int, int],
    scroll_step_range_px: tuple[int, int],
    retry_backoff_delay_range_ms: tuple[int, int],
    navigation_timeout_ms: int,
    max_navigation_retries: int,
    session_state_file: Path,
) -> list[str]:
    """Pobierz HTML stron wynikowych mobile.de dla podanego start_url.

    Zwraca listę HTMLi stron (identyczny interfejs jak scraper.get_html_pages).
    """
    recovery_max = 3

    with Camoufox(
        headless=headless,
        humanize=True,
        os="windows",
        geoip=True,
    ) as browser:
        ctx, page = _build_browser_context(browser, session_state_file)
        pages_html: list[str] = []
        visited_urls: set[str] = set()
        next_url: str | None = start_url

        try:
            # Krok 1: Zawsze odwiedź stronę główną mobile.de aby odświeżyć sesję.
            # Bez tego mobile.de może nie załadować artykułów na stronie wynikowej.
            logger.info("mobile.de: wizyta na stronie głównej celem odświeżenia sesji")
            try:
                page.goto(MOBILE_DE_HOME, wait_until="domcontentloaded", timeout=navigation_timeout_ms)
                page.wait_for_timeout(2000)

                # Sprawdź czy Akamai pokazuje Behavioral Challenge (auto-wykonywalny JS)
                # Czeka aż challenge się wykona i strona się przeładuje / tytuł się pojawi
                for _attempt in range(12):
                    home_title = page.title()
                    has_challenge = page.locator("#sec-if-cpt-container, #sec-bc-tile-container").count() > 0
                    is_blocked = "zugriff verweigert" in home_title.lower() or "access denied" in home_title.lower()

                    if is_blocked:
                        logger.warning("mobile.de: homepage zablokowana — czyszczę cookies i przerywam")
                        if session_state_file.exists():
                            session_state_file.unlink()
                            logger.info("mobile.de: usunięto cookies zablokowanej sesji")
                        raise RuntimeError("mobile.de: dostęp zablokowany przez Akamai na stronie głównej")

                    if has_challenge:
                        logger.info("mobile.de: Akamai challenge wykryty, czekam na auto-wykonanie... (próba %d/12)", _attempt + 1)
                        page.wait_for_timeout(3000)
                        continue

                    # Brak challenge i brak blokady — strona załadowana
                    break
                else:
                    logger.warning("mobile.de: Akamai challenge nie zakończył się po 36s — kontynuuję mimo to")

                _accept_cookies(page)
                page.wait_for_timeout(1500)
                logger.info("mobile.de: strona główna załadowana: %s", page.title())
                # Zapisz HTML homepage do debugowania
                try:
                    home_html = page.content()
                    debug_home = session_state_file.parent / "_debug-mobile-de-homepage.html"
                    debug_home.write_text(home_html, encoding="utf-8")
                    logger.info("mobile.de: HTML homepage zapisany do %s (%d znaków)", debug_home, len(home_html))
                except Exception:
                    pass
            except Exception as exc:
                logger.warning("mobile.de: błąd podczas wizyty na stronie głównej: %s", exc)

            # Krok 2: Pobierz kolejne strony wyników
            for page_number in range(1, max_pages + 1):
                if not next_url:
                    logger.info("mobile.de: brak kolejnego URL. Kończę paginację.")
                    break

                logger.info("mobile.de: otwieram stronę %d: %s", page_number, next_url)
                per_page_retries = 0

                while True:
                    try:
                        if page_number == 1:
                            # Pierwsza strona — zawsze przez goto()
                            current_url = _navigate_with_retry(
                                page=page,
                                url=next_url,
                                wait_ms=wait_ms,
                                post_navigation_delay_range_ms=post_navigation_delay_range_ms,
                                retry_backoff_delay_range_ms=retry_backoff_delay_range_ms,
                                navigation_timeout_ms=navigation_timeout_ms,
                                max_navigation_retries=max_navigation_retries,
                            )
                            _accept_cookies(page)
                            page.wait_for_timeout(1000)
                        else:
                            # Strona 2+ — już jesteśmy na stronie po kliknięciu paginacji
                            current_url = page.url

                        normalized = _normalize_url(current_url)
                        if normalized in visited_urls:
                            logger.info("mobile.de: ponowne przekierowanie na %s. Kończę.", current_url)
                            next_url = None
                            break
                        visited_urls.add(normalized)

                        # Sprawdź czy to nie jest strona błędu
                        title = page.title()
                        if "zugriff verweigert" in title.lower() or "access denied" in title.lower():
                            logger.warning("mobile.de: strona zwróciła 'Zugriff verweigert' dla %s", current_url)
                            # Usuń zapisane cookies — były z zablokowanej sesji
                            if session_state_file.exists():
                                session_state_file.unlink()
                                logger.info("mobile.de: usunięto cookies zablokowanej sesji (%s)", session_state_file)
                            next_url = None
                            break

                        final_count = _wait_for_listings(
                            page,
                            pause_range_ms=scroll_pause_range_ms,
                            scroll_step_range_px=scroll_step_range_px,
                        )
                        logger.info("mobile.de: oferty po stabilizacji: %d", final_count)

                        if final_count == 0:
                            logger.info("mobile.de: brak ofert na stronie. Kończę pobieranie.")
                            next_url = None
                            break

                        pages_html.append(page.content())

                        # Zapisz cookies po udanym pobraniu strony
                        try:
                            session_state_file.parent.mkdir(parents=True, exist_ok=True)
                            ctx.storage_state(path=str(session_state_file))
                        except Exception as exc:
                            logger.warning("mobile.de: błąd zapisu cookies: %s", exc)

                        if page_number >= max_pages:
                            break

                        # Przerwa przed paginacją (human-like)
                        _wait_random(page, page_break_delay_range_ms, "mobile.de: przerwa między stronami")

                        # Klikamy przycisk paginacji zamiast goto() —
                        # Akamai wykrywa brak eventu kliknięcia jako bota
                        if _find_next_page_button(page) is None:
                            logger.info("mobile.de: brak przycisku następnej strony.")
                            next_url = None
                            break

                        next_url = _click_next_page(
                            page=page,
                            current_url=current_url,
                            navigation_timeout_ms=navigation_timeout_ms,
                            post_navigation_delay_range_ms=post_navigation_delay_range_ms,
                            wait_ms=wait_ms,
                        )
                        if not next_url:
                            logger.info("mobile.de: kliknięcie paginacji nie zmieniło strony.")
                            break
                        # Pętla while obsłuży teraz nowy URL bez goto()
                        # — ustawiamy next_url i break z wewnętrznego while
                        break

                    except PlaywrightTimeoutError as exc:
                        logger.warning("mobile.de: timeout strony %s: %s", next_url, exc)
                        per_page_retries += 1
                        if per_page_retries > recovery_max:
                            raise
                        _wait_random(page, retry_backoff_delay_range_ms, "mobile.de: backoff po timeout")
                        continue

                    except Exception as exc:
                        msg = str(exc).lower()
                        logger.error("mobile.de: błąd strony %s: %s", next_url, exc)
                        traceback.print_exc()

                        debug_dir = session_state_file.parent / "debug-errors"
                        debug_dir.mkdir(parents=True, exist_ok=True)
                        ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
                        safe_name = (next_url.replace('https://', '').replace('http://', '').replace('/', '_')[:100])
                        try:
                            snap = page.content()
                            (debug_dir / f"mobile_de_{safe_name}_{ts}.html").write_text(snap, encoding='utf-8')
                        except Exception:
                            pass

                        raise

        finally:
            try:
                ctx.close()
            except Exception:
                pass

    return pages_html
