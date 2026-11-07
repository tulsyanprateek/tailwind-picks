"""Data layer: Nifty 100 universe, daily prices from Yahoo Finance, and a local CSV cache.

Prices are split-adjusted (yfinance auto_adjust=False keeps Open/High/Low/Close
adjusted for splits and bonuses but not for dividends).
"""
from __future__ import annotations

import io
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

from .utils import now_ist

log = logging.getLogger("screener.data")

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept": "text/csv,text/plain,*/*",
    "Referer": "https://niftyindices.com/",
}

REFRESH_REMINDER = ("Update data/nifty100.csv every March and September, when NSE "
                    "rebalances the index.")


# --------------------------------------------------------------------------- universe

@dataclass
class UniverseInfo:
    source: str
    path: Path
    rows: int
    warning: str | None = None


def _normalise_universe(raw: pd.DataFrame) -> pd.DataFrame:
    cols = {str(c).strip().lower(): c for c in raw.columns}
    sym = cols.get("symbol")
    comp = cols.get("company name") or cols.get("company")
    ind = cols.get("industry")
    if sym is None:
        raise ValueError("no 'symbol' column")
    out = pd.DataFrame({
        "symbol": raw[sym].astype(str).str.strip().str.upper(),
        "company": raw[comp].astype(str).str.strip() if comp else "",
        "industry": raw[ind].astype(str).str.strip() if ind else "",
    })
    out = out[out["symbol"].str.len() > 0].drop_duplicates("symbol").reset_index(drop=True)
    return out


def load_universe(cfg: dict) -> tuple[pd.DataFrame, UniverseInfo]:
    ucfg = cfg["universe"]
    path = cfg["paths"]["data_dir"] / ucfg["file"]
    try:
        resp = requests.get(ucfg["download_url"], headers=BROWSER_HEADERS, timeout=20)
        resp.raise_for_status()
        df = _normalise_universe(pd.read_csv(io.StringIO(resp.text)))
        if len(df) < ucfg["min_rows"]:
            raise ValueError(f"only {len(df)} rows in the downloaded list")
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
        log.info("Universe: downloaded %d symbols from niftyindices.com", len(df))
        return df, UniverseInfo("downloaded from niftyindices.com", path, len(df))
    except Exception as exc:  # network, HTTP or parse failure
        log.warning("Universe download failed (%s). Falling back to %s", exc, path)
        if not path.exists():
            raise SystemExit(f"Could not download the Nifty 100 list and {path} does not exist. "
                             "Create it with columns symbol, company, industry.")
        df = _normalise_universe(pd.read_csv(path))
        warning = (f"Could not download the Nifty 100 list ({exc}). Using the local file "
                   f"{path.name} ({len(df)} symbols). {REFRESH_REMINDER}")
        return df, UniverseInfo("local file", path, len(df), warning)


# --------------------------------------------------------------------------- prices

@dataclass
class PriceLoadResult:
    prices: dict[str, pd.DataFrame] = field(default_factory=dict)
    failed: dict[str, str] = field(default_factory=dict)   # no usable data: skipped
    stale: dict[str, str] = field(default_factory=dict)    # update failed, cached data used
    short: dict[str, str] = field(default_factory=dict)    # too little history: skipped


def yahoo_ticker(symbol: str, cfg: dict) -> str:
    return symbol if symbol.startswith("^") else symbol + cfg["prices"]["yahoo_suffix"]


def cache_path(ticker: str, cfg: dict) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", ticker)
    return cfg["paths"]["cache_dir"] / f"{safe}.csv"


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    idx = pd.DatetimeIndex(df.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    df.index = idx.normalize()
    df.index.name = "Date"
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df = df[(df["Close"] > 0) & (df["High"] > 0) & (df["Low"] > 0) & (df["Open"] > 0)]
    df["Volume"] = df["Volume"].fillna(0).astype(float)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df.astype(float)


def _drop_incomplete_today(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    if df.empty:
        return df
    now = now_ist()
    hh, mm = (int(x) for x in cfg["prices"]["session_complete_time_ist"].split(":"))
    if df.index[-1].date() == now.date() and (now.hour, now.minute) < (hh, mm):
        log.info("Ignoring today's incomplete bar (before %02d:%02d IST)", hh, mm)
        return df.iloc[:-1]
    return df


def _download(ticker: str, start: str, cfg: dict) -> pd.DataFrame:
    import yfinance as yf

    pcfg = cfg["prices"]
    end = (now_ist() + timedelta(days=1)).strftime("%Y-%m-%d")
    last_exc: Exception | None = None
    for attempt in range(pcfg["max_retries"] + 1):
        try:
            raw = yf.Ticker(ticker).history(start=start, end=end, interval="1d",
                                            auto_adjust=False, actions=False,
                                            raise_errors=True)
            df = _clean(raw)
            if df.empty:
                raise ValueError("no rows returned")
            return df
        except Exception as exc:
            last_exc = exc
            time.sleep(pcfg["request_pause_seconds"] + 2 * (attempt + 1))
    raise RuntimeError(f"{type(last_exc).__name__}: {last_exc}")


def update_symbol(ticker: str, cfg: dict) -> tuple[pd.DataFrame, str | None]:
    """Return (prices, stale_reason). Raises if there is no usable data at all."""
    pcfg = cfg["prices"]
    path = cache_path(ticker, cfg)
    cached = None
    if path.exists():
        try:
            cached = pd.read_csv(path, index_col="Date", parse_dates=["Date"])
            cached = _clean(cached)
        except Exception as exc:
            log.warning("%s: unreadable cache (%s), downloading full history", ticker, exc)
            cached = None

    try:
        if cached is None or cached.empty:
            df = _download(ticker, pcfg["history_start"], cfg)
        else:
            refetch_from = (cached.index[-1] - timedelta(days=10)).strftime("%Y-%m-%d")
            fresh = _download(ticker, refetch_from, cfg)
            overlap = cached.index.intersection(fresh.index)
            if len(overlap):
                diff = (cached.loc[overlap, "Close"] / fresh.loc[overlap, "Close"] - 1).abs()
                if diff.max() * 100 > pcfg["split_check_tolerance_pct"]:
                    log.info("%s: cached prices no longer match (split or bonus?), "
                             "downloading full history", ticker)
                    fresh = _download(ticker, pcfg["history_start"], cfg)
                    cached = cached.iloc[0:0]
            df = pd.concat([cached[~cached.index.isin(fresh.index)], fresh]).sort_index()
        df = _drop_incomplete_today(df, cfg)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index_label="Date")
        return df, None
    except Exception as exc:
        if cached is not None and not cached.empty:
            reason = f"update failed ({exc}); using cached data to {cached.index[-1].date()}"
            return _drop_incomplete_today(cached, cfg), reason
        raise


def load_prices(symbols: list[str], cfg: dict, include_benchmark: bool = True) -> PriceLoadResult:
    """Update the cache for every symbol and return the price frames."""
    res = PriceLoadResult()
    tickers = [(s, yahoo_ticker(s, cfg)) for s in symbols]
    if include_benchmark:
        bench = cfg["prices"]["benchmark_symbol"]
        tickers.append((bench, bench))
    t0 = time.time()
    for i, (sym, ticker) in enumerate(tickers, 1):
        try:
            df, stale = update_symbol(ticker, cfg)
            if stale:
                res.stale[sym] = stale
                log.warning("%s: %s", sym, stale)
            if not sym.startswith("^") and len(df) < cfg["prices"]["min_sessions"]:
                res.short[sym] = f"only {len(df)} sessions of history (since {df.index[0].date()})"
                log.warning("%s: %s, skipped", sym, res.short[sym])
                continue
            res.prices[sym] = df
        except Exception as exc:
            res.failed[sym] = str(exc)
            log.error("%s: download failed, skipped (%s)", sym, exc)
        if i % 10 == 0 or i == len(tickers):
            log.info("Prices: %d/%d symbols (%.0fs)", i, len(tickers), time.time() - t0)
        time.sleep(cfg["prices"]["request_pause_seconds"])
    return res
