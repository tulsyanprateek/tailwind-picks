"""Filters and ranking for the momentum rotation.

Everything for day t uses data up to the close of day t only. Orders go in on day t+1.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import indicators as ind


# --------------------------------------------------------------------------- A. market filter

def regime_series(index_df: pd.DataFrame, cfg: dict) -> pd.Series:
    c = index_df["Close"]
    fast = ind.sma(c, cfg["regime"]["sma_fast"])
    slow = ind.sma(c, cfg["regime"]["sma_slow"])
    return ((c > slow) & (fast > slow)).rename("regime_on")


# --------------------------------------------------------------------------- per stock

def compute_symbol_signals(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Trend template flag, momentum score and ATR for one stock, one row per session."""
    h, l, c = df["High"], df["Low"], df["Close"]
    tt, rs = cfg["trend_template"], cfg["relative_strength"]
    s_short, s_mid, s_long = (ind.sma(c, tt[k]) for k in ("sma_short", "sma_mid", "sma_long"))
    hi52 = ind.rolling_high(h, tt["week52_sessions"])
    lo52 = ind.rolling_low(l, tt["week52_sessions"])
    out = pd.DataFrame(index=df.index)
    out["close"] = c
    out["trend_ok"] = ((c > s_short) & (c > s_mid) & (c > s_long) & (s_mid > s_long)
                       & (s_long > s_long.shift(tt["long_sma_rising_sessions"]))
                       & (c >= tt["min_above_52w_low"] * lo52)
                       & (c >= tt["min_of_52w_high"] * hi52))
    out["rs_score"] = ind.rs_score(c, rs["weights"], rs["skip_recent_sessions"])
    out["atr"] = ind.atr(h, l, c, cfg["trade"]["atr_period"])
    out["high_52w"] = hi52
    # Volume: more volume on up days than down days over the last 50 sessions (OBV rising).
    obv = ind.obv(c, df["Volume"])
    out["volume_ok"] = (obv - obv.shift(50)) > 0
    # Volatility: yearly-scaled standard deviation of daily returns over 63 sessions.
    out["vol63"] = c.pct_change().rolling(63, min_periods=63).std() * np.sqrt(252)
    return out


# --------------------------------------------------------------------------- universe panels

@dataclass
class Panels:
    """Dates x symbols tables aligned on one trading calendar."""
    calendar: pd.DatetimeIndex
    close: pd.DataFrame
    trend_ok: pd.DataFrame
    rs_score: pd.DataFrame
    rs_pct: pd.DataFrame
    atr: pd.DataFrame
    regime: pd.Series
    volume_ok: pd.DataFrame | None = None
    vol63: pd.DataFrame | None = None


def trading_calendar(prices: dict[str, pd.DataFrame], min_symbols: int = 20) -> pd.DatetimeIndex:
    counts = pd.Series(np.concatenate([df.index.values for df in prices.values()])).value_counts()
    cal = counts[counts >= min(min_symbols, max(1, len(prices) // 2))].index
    return pd.DatetimeIndex(cal).sort_values()


def build_panels(signals: dict[str, pd.DataFrame], regime: pd.Series,
                 calendar: pd.DatetimeIndex) -> Panels:
    def panel(col):
        return pd.DataFrame({s: d[col] for s, d in signals.items()}).reindex(calendar)

    rs_score = panel("rs_score")
    return Panels(
        calendar=calendar,
        close=panel("close"),
        trend_ok=panel("trend_ok").fillna(False).astype(bool),
        rs_score=rs_score,
        rs_pct=rs_score.rank(axis=1, pct=True) * 100,
        atr=panel("atr"),
        regime=regime.reindex(calendar, method="ffill").fillna(False).astype(bool),
        volume_ok=panel("volume_ok").fillna(False).astype(bool),
        vol63=panel("vol63"),
    )


def ranked_eligible(p: Panels, i: int, cfg: dict, modules: dict,
                    extra_ok: dict[str, bool] | None = None) -> list[str]:
    """Stocks passing the enabled filters on calendar day i, strongest momentum first."""
    score = p.rs_score.iloc[i]
    ok = score.notna() & p.close.iloc[i].notna()
    if modules.get("trend_template", True):
        ok &= p.trend_ok.iloc[i]
    if modules.get("relative_strength", True):
        ok &= p.rs_pct.iloc[i] >= cfg["relative_strength"]["min_percentile"]
    if modules.get("volume_confirm", False) and p.volume_ok is not None:
        ok &= p.volume_ok.iloc[i]
    if modules.get("calm_filter", False) and p.vol63 is not None:
        vol = p.vol63.iloc[i]
        ok &= vol.rank(pct=True) <= cfg.get("filters", {}).get("max_volatility_pct", 70) / 100
    if extra_ok is not None:
        ok &= pd.Series(extra_ok).reindex(ok.index).fillna(False).astype(bool)
    if modules.get("smooth_rank", False) and p.vol63 is not None:
        score = score / p.vol63.iloc[i]
    return list(score[ok].sort_values(ascending=False, kind="mergesort").index)


def rebalance_indices(calendar: pd.DatetimeIndex, days_of_month: list[int]) -> list[int]:
    """Index of the first trading day on or after each listed day of every month."""
    if len(calendar) == 0:
        return []
    out = set()
    months = pd.period_range(calendar[0], calendar[-1], freq="M")
    for m in months:
        for d in days_of_month:
            anchor = pd.Timestamp(year=m.year, month=m.month, day=d)
            i = int(np.searchsorted(calendar.values, np.datetime64(anchor)))
            if i < len(calendar) and calendar[i].to_period("M") == m:
                out.add(i)
    return sorted(out)
