"""Fetch the latest prices for the dashboard watchlist and write live.json.

Runs every few minutes during market hours (GitHub Actions). The dashboard reads the
file to show live prices and how fresh they are. Signals are NOT recomputed here: they
change only with the evening scan, after the market closes.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from screener.config import load_config
from screener.utils import IST, now_ist, setup_logging


def fetch_quote(ticker: str) -> dict | None:
    import yfinance as yf

    t = yf.Ticker(ticker)
    h = t.history(period="5d", interval="5m", auto_adjust=False)
    h = h.dropna(subset=["Close"])
    if h.empty:
        return None
    meta = getattr(t, "history_metadata", None) or {}
    last_day = h.index[-1].date()
    prev = h[h.index.date < last_day]
    prev_close = float(prev["Close"].iloc[-1]) if len(prev) else (meta.get("previousClose") or meta.get("chartPreviousClose"))
    price = float(meta.get("regularMarketPrice") or h["Close"].iloc[-1])
    ts = meta.get("regularMarketTime")
    if isinstance(ts, (int, float)):
        when = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(IST)
    else:
        when = h.index[-1].to_pydatetime().astimezone(IST)
    if when.date() != last_day:          # metadata out of step with the bars: trust the bars
        price, when = float(h["Close"].iloc[-1]), h.index[-1].to_pydatetime().astimezone(IST)
    chg = (price / prev_close - 1) * 100 if prev_close else None
    return {"price": round(price, 2), "chg": None if chg is None else round(chg, 2),
            "time": when.isoformat(timespec="seconds")}


def main() -> int:
    cfg = load_config()
    log = setup_logging(cfg["paths"]["log_dir"], "live")
    out_dir = cfg["paths"]["output_dir"]
    watch_path = out_dir / "watch.json"
    if not watch_path.exists():
        log.error("No %s yet. Run scan.py first.", watch_path)
        return 1
    watch = json.loads(watch_path.read_text(encoding="utf-8"))
    quotes, failed = {}, []
    for key, ticker in watch["tickers"].items():
        try:
            q = fetch_quote(ticker)
        except Exception as exc:
            q = None
            log.warning("%s: %s", key, exc)
        if q:
            quotes[key] = q
        else:
            failed.append(key)
    if not quotes:
        log.error("No prices fetched; keeping the previous live.json.")
        return 1
    as_of = max(q["time"] for q in quotes.values())
    live = {"updated": now_ist().isoformat(timespec="seconds"), "as_of": as_of,
            "page_generated": watch.get("page_generated"), "quotes": quotes, "failed": failed}
    (out_dir / "live.json").write_text(json.dumps(live, separators=(",", ":")), encoding="utf-8")
    log.info("Live prices as of %s for %d symbols%s", as_of, len(quotes),
             f" (failed: {', '.join(failed)})" if failed else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
