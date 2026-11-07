"""One-time Telegram setup.

1. In Telegram, open @BotFather, send /newbot and follow the steps. Copy the token it gives.
2. Run:  python telegram_setup.py
   Paste the token when asked (it is saved in secrets.yaml on this computer only).
3. Open your new bot in Telegram and send it any message (for example "hi").
4. Press Enter here. A test message is sent to your phone.
"""
from __future__ import annotations

import getpass
import sys

from screener.config import load_config
from screener.notify import find_chat_id, load_secrets, save_secret, send


def main() -> int:
    cfg = load_config()
    token = load_secrets().get("telegram_bot_token")
    if not token:
        token = getpass.getpass("Paste the bot token from @BotFather (hidden): ").strip()
        if not token:
            print("No token given.")
            return 1
        save_secret("telegram_bot_token", token)
    input("Now send any message to your bot in Telegram, then press Enter here...")
    try:
        chat = find_chat_id(token)
    except Exception as exc:
        print(f"Telegram said: {exc}. Check the token in secrets.yaml.")
        return 1
    if chat is None:
        print("No message found. Send your bot a message in Telegram and run this again.")
        return 1
    save_secret("telegram_chat_id", chat)
    ok = send(cfg, "Stock screener connected. You will get a short message after each evening run.")
    print("Done. Check your phone." if ok else "Saved, but the test message failed. See logs/telegram_setup.log")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
