"""Zerodha equity delivery charges. Slippage is applied separately to fill prices."""
from __future__ import annotations


def side_charges(value: float, cfg: dict, side: str) -> float:
    """Statutory and broker charges for one side (excluding slippage)."""
    k = cfg["costs"]
    stt = value * k["stt_pct"] / 100
    txn = value * k["exchange_txn_pct"] / 100
    sebi = value * k["sebi_per_crore"] / 1e7
    gst = (txn + sebi) * k["gst_pct"] / 100
    total = stt + txn + sebi + gst
    if side == "buy":
        total += value * k["stamp_duty_buy_pct"] / 100
    else:
        total += k["dp_charge_per_sell"]
    return total


def round_trip_charges(buy_value: float, sell_value: float, cfg: dict) -> float:
    return side_charges(buy_value, cfg, "buy") + side_charges(sell_value, cfg, "sell")


def slippage_amount(value: float, cfg: dict) -> float:
    return value * cfg["costs"]["slippage_pct"] / 100


def buy_fill(price: float, cfg: dict) -> float:
    return price * (1 + cfg["costs"]["slippage_pct"] / 100)


def sell_fill(price: float, cfg: dict) -> float:
    return price * (1 - cfg["costs"]["slippage_pct"] / 100)
