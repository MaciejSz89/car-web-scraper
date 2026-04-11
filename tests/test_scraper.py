import sys
from pathlib import Path

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "otomoto-scraper"))

import scraper


def test_get_navigation_attempt_settings_escalates_timeout_and_fallback_mode():
    assert scraper.get_navigation_attempt_settings(1, 45000) == ("domcontentloaded", 45000)
    assert scraper.get_navigation_attempt_settings(2, 45000) == ("domcontentloaded", 67500)
    assert scraper.get_navigation_attempt_settings(3, 45000) == ("commit", 67500)


def test_navigate_with_retry_uses_commit_fallback_on_final_attempt(monkeypatch):
    attempts: list[tuple[str, int]] = []
    waits: list[tuple[str, int]] = []

    class FakePage:
        url = "https://example.test/final"

        def goto(self, url, wait_until, timeout):
            attempts.append((wait_until, timeout))
            if len(attempts) < 3:
                raise PlaywrightTimeoutError("boom")
            return None

        def wait_for_load_state(self, state, timeout):
            waits.append((state, timeout))

        def wait_for_timeout(self, timeout):
            waits.append(("timeout", timeout))

        def evaluate(self, script):
            waits.append(("evaluate", script))

    monkeypatch.setattr(scraper, "wait_random_delay", lambda *args, **kwargs: None)

    result = scraper.navigate_with_retry(
        page=FakePage(),
        url="https://example.test",
        wait_ms=3000,
        post_navigation_delay_range_ms=(1, 1),
        retry_backoff_delay_range_ms=(1, 1),
        navigation_timeout_ms=45000,
        max_navigation_retries=3,
    )

    assert result == "https://example.test/final"
    assert attempts == [
        ("domcontentloaded", 45000),
        ("domcontentloaded", 67500),
        ("commit", 67500),
    ]
    assert ("domcontentloaded", 15000) in waits
    assert ("timeout", 3000) in waits
    assert len([entry for entry in waits if entry[0] == "evaluate"]) == 2


def test_navigate_with_retry_raises_after_last_failed_attempt(monkeypatch):
    class FakePage:
        url = "https://example.test/final"

        def goto(self, url, wait_until, timeout):
            raise PlaywrightTimeoutError("still failing")

        def evaluate(self, script):
            return None

    monkeypatch.setattr(scraper, "wait_random_delay", lambda *args, **kwargs: None)

    with pytest.raises(RuntimeError, match="Nie udało się otworzyć strony"):
        scraper.navigate_with_retry(
            page=FakePage(),
            url="https://example.test",
            wait_ms=3000,
            post_navigation_delay_range_ms=(1, 1),
            retry_backoff_delay_range_ms=(1, 1),
            navigation_timeout_ms=45000,
            max_navigation_retries=3,
        )


def test_navigate_with_retry_accepts_timeout_when_articles_are_already_loaded(monkeypatch):
    waits: list[tuple[str, object]] = []

    class FakeLocator:
        def count(self):
            return 32

    class FakePage:
        url = "https://example.test/loaded"

        def goto(self, url, wait_until, timeout):
            raise PlaywrightTimeoutError("late domcontentloaded")

        def locator(self, selector):
            assert selector == "article[data-id]"
            return FakeLocator()

        def wait_for_timeout(self, timeout):
            waits.append(("timeout", timeout))

        def evaluate(self, script):
            waits.append(("evaluate", script))

    monkeypatch.setattr(scraper, "wait_random_delay", lambda *args, **kwargs: waits.append(("delay", kwargs.get("label") or args[2])))

    result = scraper.navigate_with_retry(
        page=FakePage(),
        url="https://example.test",
        wait_ms=3000,
        post_navigation_delay_range_ms=(1, 1),
        retry_backoff_delay_range_ms=(1, 1),
        navigation_timeout_ms=45000,
        max_navigation_retries=3,
    )

    assert result == "https://example.test/loaded"
    assert ("evaluate", "window.stop()") in waits
    assert ("timeout", 3000) in waits
    assert any(entry[0] == "delay" for entry in waits)