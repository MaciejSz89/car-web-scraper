from __future__ import annotations

import random
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
import traceback
import logging
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger(__name__)

CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/135.0.0.0 Safari/537.36"
)

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
Object.defineProperty(navigator, 'language', { get: () => 'pl-PL' });
Object.defineProperty(navigator, 'languages', { get: () => ['pl-PL', 'pl', 'en-US', 'en'] });
window.chrome = window.chrome || { runtime: {} };
"""


def build_page_url(base_url: str, page_number: int) -> str:
    parsed = urlsplit(base_url)
    query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))

    if page_number <= 1:
        query_params.pop("page", None)
    else:
        query_params["page"] = str(page_number)

    query = urlencode(query_params, doseq=True)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, parsed.fragment))


def wait_random_delay(page: Page, delay_range_ms: tuple[int, int], label: str) -> None:
    min_delay_ms, max_delay_ms = delay_range_ms
    delay_ms = random.randint(min_delay_ms, max_delay_ms)
    logger.info("%s: czekam %d ms", label, delay_ms)
    page.wait_for_timeout(delay_ms)


def normalize_url_for_visit_check(url: str) -> str:
    parsed = urlsplit(url)
    query_params = sorted(parse_qsl(parsed.query, keep_blank_values=True))
    normalized_query = urlencode(query_params, doseq=True)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, normalized_query, ""))


def build_browser_context_kwargs(session_state_file: Path) -> dict:
    context_kwargs = {
        "viewport": {"width": 1440, "height": 960},
        "locale": "pl-PL",
        "timezone_id": "Europe/Warsaw",
        "user_agent": CHROME_USER_AGENT,
        "extra_http_headers": {
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    }

    if session_state_file.exists():
        context_kwargs["storage_state"] = str(session_state_file)

    return context_kwargs


def build_browser_launch_kwargs(headless: bool) -> dict:
    launch_kwargs = {
        "headless": headless,
    }

    if headless:
        launch_kwargs["args"] = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-features=IsolateOrigins,site-per-process",
        ]

    return launch_kwargs


def get_navigation_attempt_settings(
    attempt: int,
    navigation_timeout_ms: int,
) -> tuple[str, int]:
    if attempt <= 1:
        return "domcontentloaded", navigation_timeout_ms

    if attempt == 2:
        return "domcontentloaded", int(navigation_timeout_ms * 1.5)

    return "commit", int(navigation_timeout_ms * 1.5)


def get_loaded_article_count(page: Page) -> int:
    try:
        return page.locator("article[data-id]").count()
    except Exception:
        return 0


def navigate_with_retry(
    page: Page,
    url: str,
    wait_ms: int,
    post_navigation_delay_range_ms: tuple[int, int],
    retry_backoff_delay_range_ms: tuple[int, int],
    navigation_timeout_ms: int,
    max_navigation_retries: int,
) -> str:
    for attempt in range(1, max_navigation_retries + 1):
        wait_until, timeout_ms = get_navigation_attempt_settings(
            attempt=attempt,
            navigation_timeout_ms=navigation_timeout_ms,
        )

        try:
            page.goto(url, wait_until=wait_until, timeout=timeout_ms)

            if wait_until == "commit":
                try:
                    page.wait_for_load_state(
                        "domcontentloaded",
                        timeout=max(5000, navigation_timeout_ms // 3),
                    )
                except PlaywrightTimeoutError:
                    logger.info(
                        "Nawigacja do %s nie osiagnela domcontentloaded po fallbacku commit; przechodze dalej.",
                        url,
                    )

            page.wait_for_timeout(wait_ms)
            wait_random_delay(page, post_navigation_delay_range_ms, "Po wejściu na stronę")
            return page.url
        except PlaywrightTimeoutError as exc:
            logger.warning(
                "Timeout podczas wejścia na %s (próba %d/%d, wait_until=%s, timeout=%d ms): %s",
                url,
                attempt,
                max_navigation_retries,
                wait_until,
                timeout_ms,
                exc,
            )
            try:
                page.evaluate("window.stop()")
            except Exception:
                pass

            loaded_article_count = get_loaded_article_count(page)
            if loaded_article_count > 0:
                logger.info(
                    "Mimo timeoutu nawigacja do %s zaladowala %d ofert; uznaje probe za udana.",
                    url,
                    loaded_article_count,
                )
                page.wait_for_timeout(wait_ms)
                wait_random_delay(page, post_navigation_delay_range_ms, "Po wejściu na stronę")
                return page.url
        except Exception as exc:
            logger.warning("Błąd podczas wejścia na %s (próba %d/%d): %s", url, attempt, max_navigation_retries, exc)

        if attempt < max_navigation_retries:
            wait_random_delay(page, retry_backoff_delay_range_ms, "Backoff przed ponowną próbą")

    raise RuntimeError(f"Nie udało się otworzyć strony po {max_navigation_retries} próbach: {url}")


def get_current_page_number(url: str) -> int:
    page_param = dict(parse_qsl(urlsplit(url).query)).get("page", "1")

    try:
        return max(1, int(page_param))
    except ValueError:
        return 1


def is_disabled_button(button) -> bool:
    aria_disabled = button.get_attribute("aria-disabled")
    disabled_attr = button.get_attribute("disabled")
    classes = (button.get_attribute("class") or "").lower()
    return aria_disabled == "true" or disabled_attr is not None or "disabled" in classes


def get_next_page_url_from_pagination_button(page: Page, current_url: str) -> str | None:
    next_button = page.locator("div.eemmnsu4 ul li button[title='Go to next Page']").first

    if next_button.count() == 0:
        return None

    if is_disabled_button(next_button):
        return None

    current_page_number = get_current_page_number(current_url)
    return build_page_url(current_url, current_page_number + 1)


def get_next_page_url(page: Page, current_url: str) -> str | None:
    next_url_from_button = get_next_page_url_from_pagination_button(page, current_url)
    if next_url_from_button:
        return next_url_from_button

    selectors = [
        "a[rel='next']",
        "a[aria-label*='Następna']",
        "a[aria-label*='następna']",
        "a[aria-label*='Next']",
        "a[title*='Następna']",
        "nav a[href*='page=']",
    ]

    normalized_current_url = normalize_url_for_visit_check(current_url)

    for selector in selectors:
        locator = page.locator(selector)
        count = locator.count()

        for index in range(count):
            candidate = locator.nth(index)
            href = candidate.get_attribute("href")
            aria_disabled = candidate.get_attribute("aria-disabled")
            classes = (candidate.get_attribute("class") or "").lower()

            if not href or aria_disabled == "true" or "disabled" in classes:
                continue

            candidate_url = normalize_url_for_visit_check(urljoin(current_url, href))
            if candidate_url == normalized_current_url:
                continue

            current_page_param = dict(parse_qsl(urlsplit(current_url).query)).get("page", "1")
            candidate_page_param = dict(parse_qsl(urlsplit(candidate_url).query)).get("page", "1")

            try:
                if int(candidate_page_param) <= int(current_page_param):
                    continue
            except ValueError:
                pass

            return candidate_url

    return None


def wait_until_article_count_stabilizes(
    page: Page,
    max_rounds: int = 10,
    pause_range_ms: tuple[int, int] = (900, 2200),
    scroll_step_range_px: tuple[int, int] = (1400, 4200),
) -> int:
    previous_count = -1
    same_count_rounds = 0

    for round_no in range(1, max_rounds + 1):
        current_count = page.locator("article[data-id]").count()
        logger.info("Runda %d: article[data-id] = %d", round_no, current_count)

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

        wait_random_delay(page, pause_range_ms, f"Pauza po scrollu {round_no}")
        previous_count = current_count

    return page.locator("article[data-id]").count()


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
    """Pobierz HTML kilku stron z paginacji, z odpornością na zamknięcie przeglądarki.

    Zwraca listę HTMLi stron.
    """

    def _create_browser_context_page(pw, headless_flag, session_state_path):
        browser = pw.chromium.launch(**build_browser_launch_kwargs(headless_flag))
        context = browser.new_context(**build_browser_context_kwargs(session_state_path))
        context.add_init_script(STEALTH_INIT_SCRIPT)
        page = context.new_page()
        return browser, context, page

    recovery_max = 3

    with sync_playwright() as p:
        browser, context, page = _create_browser_context_page(p, headless, session_state_file)

        pages_html: list[str] = []
        visited_urls: set[str] = set()
        next_url = start_url

        for page_number in range(1, max_pages + 1):
            if not next_url:
                logger.info("Brak kolejnego adresu do odwiedzenia. Kończę paginację.")
                break

            logger.info("\nOtwieram stronę %d: %s", page_number, next_url)

            per_page_retries = 0
            while True:
                try:
                    current_url = navigate_with_retry(
                        page=page,
                        url=next_url,
                        wait_ms=wait_ms,
                        post_navigation_delay_range_ms=post_navigation_delay_range_ms,
                        retry_backoff_delay_range_ms=retry_backoff_delay_range_ms,
                        navigation_timeout_ms=navigation_timeout_ms,
                        max_navigation_retries=max_navigation_retries,
                    )
                    normalized_current_url = normalize_url_for_visit_check(current_url)

                    if normalized_current_url in visited_urls:
                        logger.info("Wykryto ponowne przekierowanie na odwiedzony adres: %s. Zatrzymuję paginację.", current_url)
                        next_url = None
                        break

                    visited_urls.add(normalized_current_url)

                    initial_count = page.locator("article[data-id]").count()
                    logger.info("article[data-id] na starcie: %d", initial_count)

                    final_count = wait_until_article_count_stabilizes(
                        page,
                        pause_range_ms=scroll_pause_range_ms,
                        scroll_step_range_px=scroll_step_range_px,
                    )
                    logger.info("article[data-id] po stabilizacji: %d", final_count)

                    if final_count == 0:
                        logger.info("Brak ofert na stronie. Zatrzymuję pobieranie kolejnych stron.")
                        next_url = None
                        break

                    pages_html.append(page.content())
                    session_state_file.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        context.storage_state(path=str(session_state_file))
                    except Exception as exc:
                        logger.warning("Błąd podczas zapisu storage_state: %s", exc)

                    next_url = get_next_page_url(page, current_url)
                    if not next_url:
                        logger.info("Nie znaleziono linku do następnej strony. To wygląda na koniec wyników.")
                        break

                    if page_number < max_pages:
                        wait_random_delay(page, page_break_delay_range_ms, "Przerwa przed następną stroną")

                    break

                except PlaywrightTimeoutError as exc:
                    logger.warning("Timeout podczas przetwarzania strony %s: %s", next_url, exc)
                    per_page_retries += 1
                    if per_page_retries > recovery_max:
                        raise
                    wait_random_delay(page, retry_backoff_delay_range_ms, "Backoff po timeoutie")
                    continue

                except Exception as exc:
                    msg = str(exc).lower()
                    logger.error("Błąd podczas przetwarzania strony %s: %s", next_url, exc)
                    traceback.print_exc()

                    # zapisz snapshot strony dla diagnostyki
                    try:
                        debug_dir = session_state_file.parent / "debug-errors"
                        debug_dir.mkdir(parents=True, exist_ok=True)
                        ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
                        safe_name = (next_url.replace('https://', '').replace('http://', '').replace('/', '_')[:100])
                        snapshot_path = debug_dir / f"snapshot_{safe_name}_{ts}.html"
                        try:
                            html = page.content()
                            snapshot_path.write_text(html, encoding='utf-8')
                            logger.info("Zapisano snapshot strony: %s", snapshot_path)
                        except Exception as e2:
                            logger.warning("Nie udało się zapisać snapshotu HTML: %s", e2)
                    except Exception:
                        logger.exception("Błąd podczas tworzenia katalogu debug-errors")

                    # jeśli przeglądarka lub kontekst zostały zamknięte, spróbuj odtworzyć
                    if "closed" in msg or "target page, context or browser has been closed" in msg:
                        per_page_retries += 1
                        logger.info("Wykryto zamknięcie przeglądarki/contextu (próba odtworzenia %d/%d)", per_page_retries, recovery_max)
                        try:
                            # log pid jeśli dostępny
                            try:
                                proc = getattr(browser, 'process', None)
                                pid_val = proc.pid if proc is not None else None
                                logger.info("Browser process pid: %s", pid_val)
                            except Exception:
                                logger.debug("Nie udało się odczytać pid procesu przeglądarki")
                            context.close()
                        except Exception:
                            pass
                        try:
                            browser.close()
                        except Exception:
                            pass

                        if per_page_retries > recovery_max:
                            raise RuntimeError(f"Nie udało się odtworzyć przeglądarki po {recovery_max} próbach")

                        # odtwórz browser/context/page
                        browser, context, page = _create_browser_context_page(p, headless, session_state_file)
                        wait_random_delay(page, retry_backoff_delay_range_ms, "Backoff przed ponowną próbą (recreate)")
                        continue

                    # inne błędy - rethrow
                    raise

        try:
            context.close()
        except Exception:
            pass

        try:
            browser.close()
        except Exception:
            pass

        return pages_html


def get_html(url: str, headless: bool, wait_ms: int) -> str:
    pages = get_html_pages(
        start_url=url,
        headless=headless,
        wait_ms=wait_ms,
        max_pages=1,
        post_navigation_delay_range_ms=(wait_ms, wait_ms),
        page_break_delay_range_ms=(wait_ms, wait_ms),
        scroll_pause_range_ms=(900, 2200),
        scroll_step_range_px=(1400, 4200),
        retry_backoff_delay_range_ms=(wait_ms, wait_ms),
        navigation_timeout_ms=30000,
        max_navigation_retries=1,
        session_state_file=Path(".playwright-session-state.json"),
    )
    return pages[0] if pages else ""
