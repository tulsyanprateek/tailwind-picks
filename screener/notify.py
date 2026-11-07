"""Telegram messages to your phone (free). Secrets live in secrets.yaml, never in git."""
from __future__ import annotations

import logging
from pathlib import Path

import requests
import yaml

from .config import ROOT

log = logging.getLogger("screener.notify")
SECRETS = ROOT / "secrets.yaml"
API = "https://api.telegram.org/bot{token}/{method}"


def load_secrets() -> dict:
    if not SECRETS.exists():
        return {}
    with open(SECRETS, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def save_secret(key: str, value) -> None:
    data = load_secrets()
    data[key] = value
    with open(SECRETS, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False)


def telegram_ready(cfg: dict) -> bool:
    s = load_secrets()
    return bool(cfg.get("telegram", {}).get("enabled") and s.get("telegram_bot_token") and s.get("telegram_chat_id"))


def _call(method: str, token: str, **kw) -> dict:
    r = requests.post(API.format(token=token, method=method), timeout=30, **kw)
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", f"HTTP {r.status_code}"))
    return data


def send(cfg: dict, text: str, attachment: Path | None = None) -> bool:
    """Send a message (and optionally a file). Never raises: a failed message must not
    break the scan."""
    if not telegram_ready(cfg):
        log.info("Telegram not set up; no phone message sent (see README, Phone messages).")
        return False
    s = load_secrets()
    token, chat = s["telegram_bot_token"], s["telegram_chat_id"]
    try:
        _call("sendMessage", token, data={"chat_id": chat, "text": text[:4000],
                                          "disable_web_page_preview": True})
        if attachment is not None and attachment.exists() and cfg["telegram"].get("send_report_file", True):
            with open(attachment, "rb") as fh:
                _call("sendDocument", token, data={"chat_id": chat}, files={"document": (attachment.name, fh)})
        log.info("Telegram message sent.")
        return True
    except Exception as exc:
        log.error("Telegram message failed: %s", exc)
        return False


def find_chat_id(token: str) -> int | None:
    """Chat id of the most recent message sent to the bot."""
    data = _call("getUpdates", token, data={"timeout": 0})
    for upd in reversed(data.get("result", [])):
        msg = upd.get("message") or upd.get("edited_message")
        if msg and "chat" in msg:
            return msg["chat"]["id"]
    return None
