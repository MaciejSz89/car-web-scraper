from __future__ import annotations

import random
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError


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
    print(f"{label}: czekam {delay_ms} ms")
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
        "extra_http_headers": {
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    }

    if session_state_file.exists():
        context_kwargs["storage_state"] = str(session_state_file)

    return context_kwargs


def navigate_with_retry(
    page: Page,
    url: str,
    wait_ms: int,
    post_navigation_delay_range_ms: tuple[int, int],
    retry_backoff_delay_range_ms: tuple[int, int],
    max_navigation_retries: int,
) -> str:
    for attempt in range(1, max_navigation_retries + 1):
        try:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(wait_ms)
            wait_random_delay(page, post_navigation_delay_range_ms, "Po wejściu na stronę")
            return page.url
        except PlaywrightTimeoutError as exc:
            print(f"Timeout podczas wejścia na {url} (próba {attempt}/{max_navigation_retries}): {exc}")
        except Exception as exc:
            print(f"Błąd podczas wejścia na {url} (próba {attempt}/{max_navigation_retries}): {exc}")

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
        print(f"Runda {round_no}: article[data-id] = {current_count}")

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
    max_navigation_retries: int,
    session_state_file: Path,
) -> list[str]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(**build_browser_context_kwargs(session_state_file))
        page = context.new_page()

        pages_html: list[str] = []
        visited_urls: set[str] = set()
        next_url = start_url

        for page_number in range(1, max_pages + 1):
            if not next_url:
                print("Brak kolejnego adresu do odwiedzenia. Kończę paginację.")
                break

            print(f"\nOtwieram stronę {page_number}: {next_url}")

            current_url = navigate_with_retry(
                page=page,
                url=next_url,
                wait_ms=wait_ms,
                post_navigation_delay_range_ms=post_navigation_delay_range_ms,
                retry_backoff_delay_range_ms=retry_backoff_delay_range_ms,
                max_navigation_retries=max_navigation_retries,
            )
            normalized_current_url = normalize_url_for_visit_check(current_url)

            if normalized_current_url in visited_urls:
                print(f"Wykryto ponowne przekierowanie na odwiedzony adres: {current_url}. Zatrzymuję paginację.")
                break

            visited_urls.add(normalized_current_url)

            initial_count = page.locator("article[data-id]").count()
            print("article[data-id] na starcie:", initial_count)

            final_count = wait_until_article_count_stabilizes(
                page,
                pause_range_ms=scroll_pause_range_ms,
                scroll_step_range_px=scroll_step_range_px,
            )
            print("article[data-id] po stabilizacji:", final_count)

            if final_count == 0:
                print("Brak ofert na stronie. Zatrzymuję pobieranie kolejnych stron.")
                break

            pages_html.append(page.content())
            session_state_file.parent.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=str(session_state_file))

            next_url = get_next_page_url(page, current_url)
            if not next_url:
                print("Nie znaleziono linku do następnej strony. To wygląda na koniec wyników.")
                break

            if page_number < max_pages:
                wait_random_delay(page, page_break_delay_range_ms, "Przerwa przed następną stroną")

        context.close()
        browser.close()
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
        max_navigation_retries=1,
        session_state_file=Path(".playwright-session-state.json"),
    )
    return pages[0] if pages else ""