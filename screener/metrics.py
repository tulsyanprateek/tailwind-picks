"""Performance metrics, benchmark and the pass / fail verdict."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .portfolio import SimResult


def _cagr(start_value: float, end_value: float, start: pd.Timestamp, end: pd.Timestamp) -> float:
    years = (end - start).days / 365.25
    if years <= 0 or start_value <= 0 or end_value <= 0:
        return float("nan")
    return ((end_value / start_value) ** (1 / years) - 1) * 100


def drawdown(equity: pd.Series) -> pd.Series:
    return (equity / equity.cummax() - 1) * 100


def summarize(res: SimResult, capital: float) -> dict:
    t, eq = res.trades, res.equity
    m: dict = {"start": eq.index[0], "end": eq.index[-1], "final_value": float(eq.iloc[-1])}
    m["net_pnl"] = m["final_value"] - capital
    m["cagr"] = _cagr(capital, m["final_value"], eq.index[0], eq.index[-1])
    dd = drawdown(eq)
    m["max_dd_pct"] = float(dd.min())
    m["max_dd_inr"] = float((eq - eq.cummax()).min())
    monthly = pd.concat([pd.Series([capital], index=[eq.index[0] - pd.Timedelta(days=1)]),
                         eq.resample("ME").last()])
    chg = monthly.diff().dropna()
    m["pct_months_positive"] = float((chg > 0).mean() * 100) if len(chg) else float("nan")
    m["pct_time_in_cash"] = float((res.open_count == 0).mean() * 100)
    m["trades"] = len(t)
    if len(t) == 0:
        m.update(win_rate=float("nan"), avg_win=float("nan"), avg_loss=float("nan"),
                 avg_r=float("nan"), expectancy_inr=float("nan"), expectancy_r=float("nan"),
                 profit_factor=float("nan"), longest_losing_streak=0,
                 avg_holding_sessions=float("nan"), avg_holding_days=float("nan"),
                 total_charges=0.0)
        return m
    wins, losses = t[t["net_pnl"] > 0], t[t["net_pnl"] <= 0]
    m["win_rate"] = len(wins) / len(t) * 100
    m["avg_win"] = float(wins["net_pnl"].mean()) if len(wins) else float("nan")
    m["avg_loss"] = float(losses["net_pnl"].mean()) if len(losses) else float("nan")
    m["avg_r"] = float(t["r_multiple"].mean())
    m["expectancy_inr"] = float(t["net_pnl"].mean())
    m["expectancy_r"] = m["avg_r"]
    loss_sum = -losses["net_pnl"].sum()
    m["profit_factor"] = float(wins["net_pnl"].sum() / loss_sum) if loss_sum > 0 else float("inf")
    streak = best = 0
    for pnl in t.sort_values("exit_date")["net_pnl"]:
        streak = streak + 1 if pnl <= 0 else 0
        best = max(best, streak)
    m["longest_losing_streak"] = best
    m["avg_holding_sessions"] = float(t["sessions"].mean())
    m["avg_holding_days"] = float((t["exit_date"] - t["entry_date"]).dt.days.mean())
    m["total_charges"] = float(t["charges"].sum() + t["slippage"].sum())
    return m


def benchmark(index_close: pd.Series, start: pd.Timestamp, end: pd.Timestamp,
              capital: float) -> tuple[dict, pd.Series]:
    c = index_close.loc[start:end].dropna()
    eq = capital * c / c.iloc[0]
    return {"start": c.index[0], "end": c.index[-1], "final_value": float(eq.iloc[-1]),
            "net_pnl": float(eq.iloc[-1] - capital),
            "cagr": _cagr(capital, float(eq.iloc[-1]), c.index[0], c.index[-1]),
            "max_dd_pct": float(drawdown(eq).min()),
            "max_dd_inr": float((eq - eq.cummax()).min())}, eq


def verdict(oos: dict, oos_bench: dict) -> dict:
    """FAILED if out-of-sample expectancy after costs <= 0, or if the system made less
    than Nifty 50 buy-and-hold while also falling deeper."""
    reasons = []
    exp = oos.get("expectancy_inr", float("nan"))
    if not (isinstance(exp, float) and not math.isnan(exp) and exp > 0):
        reasons.append("average profit per trade after costs is zero or negative")
    if oos["cagr"] < oos_bench["cagr"] and oos["max_dd_pct"] < oos_bench["max_dd_pct"]:
        reasons.append("it made less than simply holding the Nifty 50 and fell deeper")
    return {"passed": not reasons, "reasons": reasons,
            "oos_expectancy_inr": exp, "oos_expectancy_r": oos.get("expectancy_r"),
            "oos_cagr": oos["cagr"], "oos_max_dd_pct": oos["max_dd_pct"],
            "bench_oos_cagr": oos_bench["cagr"], "bench_oos_max_dd_pct": oos_bench["max_dd_pct"]}


def r_histogram(r: pd.Series, lo: float = -2.0, hi: float = 4.0, step: float = 0.5
                ) -> list[tuple[str, int]]:
    edges = np.arange(lo, hi + step, step)
    clipped = r.dropna().clip(lo, hi - 1e-9)
    counts, _ = np.histogram(clipped, bins=edges)
    labels = [f"{a:+.1f}" for a in edges[:-1]]
    labels[0] = f"<{edges[1]:+.1f}"
    labels[-1] = f">{edges[-2]:+.1f}"
    return list(zip(labels, counts.tolist()))
