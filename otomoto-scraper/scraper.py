from playwright.sync_api import sync_playwright, Page


def wait_until_article_count_stabilizes(
    page: Page,
    max_rounds: int = 10,
    pause_ms: int = 1500,
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

        page.mouse.wheel(0, 6000)
        page.wait_for_timeout(pause_ms)
        previous_count = current_count

    return page.locator("article[data-id]").count()


def get_html(url: str, headless: bool, wait_ms: int) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(wait_ms)

        initial_count = page.locator("article[data-id]").count()
        print("article[data-id] na starcie:", initial_count)

        final_count = wait_until_article_count_stabilizes(page)
        print("article[data-id] po stabilizacji:", final_count)

        html = page.content()
        browser.close()
        return html