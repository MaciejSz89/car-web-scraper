"""Utility script to find your Telegram chat_id.

Usage:
    1. Set OTOMOTO_TELEGRAM_BOT_TOKEN (or pass --token).
    2. Send any message to your bot in Telegram.
    3. Run this script — it prints all pending chat IDs.
"""
from __future__ import annotations

import argparse
import json
import os
from urllib.request import urlopen
from urllib.error import URLError


def get_updates(token: str) -> list[dict]:
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        with urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
    except URLError as exc:
        raise SystemExit(f"Błąd połączenia z Telegram API: {exc}") from exc

    if not data.get("ok"):
        raise SystemExit(f"Telegram API zwróciło błąd: {data.get('description')}")

    return data.get("result") or []


def main() -> None:
    parser = argparse.ArgumentParser(description="Znajdź chat_id w Telegram.")
    parser.add_argument(
        "--token",
        default=None,
        help="Token bota. Domyślnie czytany ze zmiennej OTOMOTO_TELEGRAM_BOT_TOKEN.",
    )
    args = parser.parse_args()

    token = args.token or os.environ.get("OTOMOTO_TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "Brak tokena bota. Ustaw zmienną OTOMOTO_TELEGRAM_BOT_TOKEN "
            "albo podaj --token <TOKEN>."
        )

    updates = get_updates(token)

    if not updates:
        print("Brak wiadomości. Wyślij dowolną wiadomość do bota w Telegram i uruchom skrypt ponownie.")
        return

    seen: set[int] = set()
    for update in updates:
        message = update.get("message") or update.get("channel_post") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None or chat_id in seen:
            continue
        seen.add(chat_id)
        chat_type = chat.get("type", "?")
        chat_title = chat.get("title") or chat.get("username") or chat.get("first_name") or ""
        from_user = (message.get("from") or {}).get("username") or ""
        print(
            f"chat_id: {chat_id}"
            f"  type: {chat_type}"
            + (f"  title/name: {chat_title}" if chat_title else "")
            + (f"  from: @{from_user}" if from_user else "")
        )

    if not seen:
        print("Nie znaleziono żadnych chat_id. Upewnij się, że wysłałeś wiadomość do bota.")


if __name__ == "__main__":
    main()
