"""Trade construction: limit price, stop loss, target, quantity, stop updates."""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class TradePlan:
    entry: float
    stop: float
    risk_per_share: float   # R = entry - stop
    breakeven_level: float  # entry + 1R: once the price is above this, the stop goes to entry
    target: float           # entry + 3R


def limit_price(last_close: float, cfg: dict) -> float:
    """Buy limit: last close + max_gap_pct. Above this the order does not chase."""
    return last_close * (1 + cfg["trade"]["max_gap_pct"] / 100)


def gap_too_large(next_open: float, last_close: float, cfg: dict) -> bool:
    return next_open > limit_price(last_close, cfg)


def limit_fill(day_open: float, day_low: float, limit: float) -> float | None:
    """Fill price of a buy limit order on one day, or None if it does not fill."""
    if day_open <= limit:
        return day_open
    if day_low <= limit:
        return limit
    return None


def plan_trade(entry: float, atr_value: float, cfg: dict) -> TradePlan:
    """Stop = entry - 2 x ATR, capped at max_stop_pct below entry. Target = entry + 3R."""
    t = cfg["trade"]
    stop = max(entry - t["atr_stop_multiple"] * atr_value, entry * (1 - t["max_stop_pct"] / 100))
    r = entry - stop
    return TradePlan(entry=entry, stop=stop, risk_per_share=r,
                     breakeven_level=entry + t["breakeven_after_r"] * r,
                     target=entry + t["target_r"] * r)


def raised_stop(current_stop: float, entry: float, risk_per_share: float,
                last_close: float, atr_value: float, cfg: dict) -> float:
    """Stop for a kept holding at a check-in. Never lower than the current stop."""
    t = cfg["trade"]
    new = current_stop
    if not math.isnan(atr_value):
        new = max(new, last_close - t["atr_stop_multiple"] * atr_value)
    if last_close >= entry + t["breakeven_after_r"] * risk_per_share:
        new = max(new, entry)
    return new


def quantity(budget: float, price: float) -> int:
    if price <= 0 or budget <= 0:
        return 0
    return math.floor(budget / price + 1e-9)


def round_tick(price: float, tick: float, mode: str = "nearest") -> float:
    steps = price / tick
    if mode == "up":
        steps = math.ceil(steps - 1e-9)
    elif mode == "down":
        steps = math.floor(steps + 1e-9)
    else:
        steps = round(steps)
    return round(steps * tick, 2)
