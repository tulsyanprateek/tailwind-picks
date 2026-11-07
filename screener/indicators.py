"""Technical indicators, all computed with pandas / numpy (no TA-Lib)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev = close.shift(1)
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    tr.iloc[0] = high.iloc[0] - low.iloc[0]
    return tr


def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int) -> pd.Series:
    """Wilder's ATR: first value is the simple mean of the first n true ranges,
    then ATR_t = (ATR_{t-1} * (n - 1) + TR_t) / n."""
    tr = true_range(high, low, close).to_numpy(dtype=float)
    out = np.full(len(tr), np.nan)
    if len(tr) >= n:
        out[n - 1] = tr[:n].mean()
        for i in range(n, len(tr)):
            out[i] = (out[i - 1] * (n - 1) + tr[i]) / n
    return pd.Series(out, index=high.index)


def rolling_high(high: pd.Series, n: int) -> pd.Series:
    return high.rolling(n, min_periods=n).max()


def rolling_low(low: pd.Series, n: int) -> pd.Series:
    return low.rolling(n, min_periods=n).min()


def rs_score(close: pd.Series, weights: dict[int, float], skip: int = 5) -> pd.Series:
    """Weighted sum of returns over each lookback, ending `skip` sessions ago."""
    base = close.shift(skip)
    total = None
    for lookback, w in weights.items():
        r = base / close.shift(skip + lookback) - 1
        total = r * w if total is None else total + r * w
    return total


# --------------------------------------------------------------------------- second-opinion indicators
# Shown on the dashboard for validation. They are NOT part of the tested buy/sell rules.

def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """Wilder's RSI, 0 to 100."""
    d = close.diff()
    gain = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    loss = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).where(loss != 0, 100.0)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    line = ema(close, fast) - ema(close, slow)
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return line, sig, line - sig


def adx(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14):
    """Returns (ADX, +DI, -DI) using Wilder smoothing."""
    up, down = high.diff(), -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    tr = true_range(high, low, close)
    a = 1 / n
    atr_ = tr.ewm(alpha=a, adjust=False, min_periods=n).mean()
    pdi = 100 * plus_dm.ewm(alpha=a, adjust=False, min_periods=n).mean() / atr_
    mdi = 100 * minus_dm.ewm(alpha=a, adjust=False, min_periods=n).mean() / atr_
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=a, adjust=False, min_periods=n).mean(), pdi, mdi


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    return (np.sign(close.diff()).fillna(0) * volume).cumsum()
