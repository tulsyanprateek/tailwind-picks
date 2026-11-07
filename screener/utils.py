"""Small shared helpers: logging setup and Indian number formatting."""
from __future__ import annotations

import logging
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))


def now_ist() -> datetime:
    return datetime.now(IST)


def setup_logging(log_dir: Path, name: str) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)
    fileh = logging.FileHandler(log_dir / f"{name}.log", mode="w", encoding="utf-8")
    fileh.setFormatter(fmt)
    root.addHandler(fileh)
    # yfinance is chatty; keep its own warnings out of the console.
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    logging.getLogger("peewee").setLevel(logging.WARNING)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    return logging.getLogger(name)


def group_indian(int_digits: str) -> str:
    """'10000000' -> '1,00,00,000'."""
    if len(int_digits) <= 3:
        return int_digits
    head, tail = int_digits[:-3], int_digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups) + "," + tail


def inr(x: float | None, decimals: int = 0, symbol: bool = True) -> str:
    """Indian number format: inr(100000) -> '₹1,00,000'."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "N/A"
    neg = x < 0
    s = f"{abs(x):.{decimals}f}"
    int_part, _, frac = s.partition(".")
    out = group_indian(int_part) + (f".{frac}" if frac else "")
    return ("-" if neg else "") + ("₹" if symbol else "") + out


def num(x: float | None, decimals: int = 2) -> str:
    return inr(x, decimals, symbol=False)


def pct(x: float | None, decimals: int = 1, signed: bool = False) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "N/A"
    return f"{x:+.{decimals}f}%" if signed else f"{x:.{decimals}f}%"
