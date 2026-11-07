"""Company profiles (what the business does) from Yahoo Finance, cached for 30 days."""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timedelta

from .data import yahoo_ticker

log = logging.getLogger("screener.profiles")
REFRESH_DAYS = 30


def _short_summary(text: str, max_sentences: int = 2, max_chars: int = 320) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    out = ""
    for s in sentences[:max_sentences]:
        if len(out) + len(s) > max_chars and out:
            break
        out = f"{out} {s}".strip()
    if len(out) > max_chars:
        out = out[:max_chars].rsplit(" ", 1)[0] + "..."
    return out


def get_profile(symbol: str, cfg: dict) -> dict:
    """{'name', 'sector', 'industry', 'market_cap', 'summary', 'website'}; empty values on failure."""
    folder = cfg["paths"]["cache_dir"] / "profiles"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{re.sub(r'[^A-Za-z0-9_-]', '_', symbol)}.json"
    cached = None
    if path.exists():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            age = datetime.now() - datetime.fromisoformat(cached["fetched"])
            if age < timedelta(days=REFRESH_DAYS):
                return cached
        except Exception:
            cached = None
    try:
        import yfinance as yf

        info = yf.Ticker(yahoo_ticker(symbol, cfg)).info or {}
        prof = {"name": info.get("longName") or info.get("shortName") or symbol,
                "sector": info.get("sector") or "", "industry": info.get("industry") or "",
                "market_cap": info.get("marketCap"), "website": info.get("website") or "",
                "summary": _short_summary(info.get("longBusinessSummary") or ""),
                "fetched": datetime.now().isoformat(timespec="seconds")}
        path.write_text(json.dumps(prof, indent=1), encoding="utf-8")
        time.sleep(cfg["prices"]["request_pause_seconds"])
        return prof
    except Exception as exc:
        log.warning("%s: company profile not available (%s)", symbol, exc)
        return cached or {"name": symbol, "sector": "", "industry": "", "market_cap": None,
                          "website": "", "summary": "", "fetched": ""}


def get_logo(domain: str, cfg: dict) -> str:
    """Company logo as an embedded data URI (downloaded once and cached), or "" if none."""
    import base64

    import requests

    if not domain:
        return ""
    folder = cfg["paths"]["cache_dir"] / "logos"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', domain)}.png"
    miss = path.with_suffix(".none")
    if not path.exists() and not miss.exists():
        try:
            r = requests.get(f"https://www.google.com/s2/favicons?domain={domain}&sz=64", timeout=15)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/") and len(r.content) > 200:
                path.write_bytes(r.content)
            else:
                miss.write_text("no logo", encoding="utf-8")
        except Exception as exc:
            log.warning("%s: logo not available (%s)", domain, exc)
            return ""
    if path.exists():
        return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")
    return ""
