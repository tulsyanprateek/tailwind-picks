"""Second-opinion indicators (RSI, MACD, ADX, OBV volume) for validating each stock.

These are shown on the dashboard for transparency. They are NOT part of the tested
buy/sell rules, so they never change what Tailwind Picks picks.
"""
from __future__ import annotations

import math

import pandas as pd

from . import indicators as ind


def _line(s: pd.Series, n: int) -> list:
    s = s.iloc[-n:]
    return [[d.strftime("%Y-%m-%d"), round(float(v), 2)] for d, v in s.items() if not math.isnan(v)]


def second_opinion(df: pd.DataFrame, data_ts: pd.Timestamp, sessions: int = 500) -> tuple[list, int, dict]:
    """Returns (rows, number saying BUY, chart series)."""
    d = df.loc[:data_ts]
    c = d["Close"]
    r = ind.rsi(c)
    line, sig, hist = ind.macd(c)
    a, pdi, mdi = ind.adx(d["High"], d["Low"], c)
    o = ind.obv(c, d["Volume"])
    rv, lv, sv = float(r.iloc[-1]), float(line.iloc[-1]), float(sig.iloc[-1])
    av, pv, mv = float(a.iloc[-1]), float(pdi.iloc[-1]), float(mdi.iloc[-1])
    obv_up = float(o.iloc[-1] - o.iloc[-51]) > 0 if len(o) > 51 else False
    vol_ratio = float(d["Volume"].iloc[-20:].mean() / max(d["Volume"].iloc[-100:].mean(), 1))

    rows = []
    if rv >= 70:
        rows.append(("RSI (14)", f"{rv:.0f}", "HOLD", "Very strong but stretched above 70: may pause or dip"))
    elif rv >= 50:
        rows.append(("RSI (14)", f"{rv:.0f}", "BUY", "Between 50 and 70: healthy upward momentum"))
    else:
        rows.append(("RSI (14)", f"{rv:.0f}", "SELL", "Below 50: momentum is fading"))
    if lv > sv and lv > 0:
        rows.append(("MACD (12, 26, 9)", f"{lv:.1f} / {sv:.1f}", "BUY", "Above its signal line and above zero: momentum rising"))
    elif lv > 0:
        rows.append(("MACD (12, 26, 9)", f"{lv:.1f} / {sv:.1f}", "HOLD", "Still above zero, but momentum is cooling"))
    else:
        rows.append(("MACD (12, 26, 9)", f"{lv:.1f} / {sv:.1f}", "SELL", "Below zero: the trend is down"))
    if av >= 25 and pv > mv:
        rows.append(("ADX (14)", f"{av:.0f}", "BUY", "Above 25 with buyers in control: a strong uptrend"))
    elif pv > mv:
        rows.append(("ADX (14)", f"{av:.0f}", "HOLD", "Buyers in control, but the trend is not strong yet"))
    else:
        rows.append(("ADX (14)", f"{av:.0f}", "SELL", "Sellers in control"))
    rows.append(("Volume (OBV, 50 days)", f"{'Rising' if obv_up else 'Falling'}, {vol_ratio:.1f}x avg",
                 "BUY" if obv_up else "SELL",
                 "More volume on up days: buyers are stepping in" if obv_up else "More volume on down days: selling pressure"))
    agree = sum(1 for x in rows if x[2] == "BUY")
    series = {"rsi": _line(r, sessions), "macd": _line(line, sessions), "macds": _line(sig, sessions),
              "macdh": _line(hist, sessions)}
    return rows, agree, series
