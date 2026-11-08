"""Day-by-day simulation of the 2-week momentum rotation.

On a check-in day i (signals from the close of day i-1):
  1. Stops of current holdings are raised (never lowered) as the report would tell you.
  2. Gap exits at the open: open at or below the stop, or at or above the target.
  3. Holdings that no longer qualify (or every holding, when the market filter is OFF)
     are sold at the open.
  4. Free slots are filled with the strongest qualifying stocks not already held, using a
     limit order at last close + 2%. Each new holding gets 1/N of the portfolio value.
  5. Intraday: stop first, then target (if both are touched the same day, the stop is
     assumed to come first).
On every other day only steps 2 and 5 happen (that is the GTT order working on its own).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import costs
from .signals import Panels, ranked_eligible, rebalance_indices
from .trade import limit_fill, limit_price, plan_trade, quantity, raised_stop


@dataclass
class Position:
    symbol: str
    signal_i: int
    entry_i: int
    entry_ref: float
    entry_fill: float
    qty: int
    stop: float
    initial_stop: float
    risk_per_share: float
    target: float
    rank: int
    buy_charges: float
    sessions: int = 0
    last_close: float = float("nan")
    breakeven: bool = False


@dataclass
class SimResult:
    trades: pd.DataFrame
    equity: pd.Series
    open_count: pd.Series
    stats: dict = field(default_factory=dict)


@dataclass
class OHLC:
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    col: dict


def build_ohlc(prices: dict[str, pd.DataFrame], symbols: list[str],
               calendar: pd.DatetimeIndex) -> OHLC:
    frames = {k: pd.DataFrame({s: prices[s][k] for s in symbols}).reindex(calendar)
              for k in ("Open", "High", "Low", "Close")}
    return OHLC(frames["Open"].to_numpy(float), frames["High"].to_numpy(float),
                frames["Low"].to_numpy(float), frames["Close"].to_numpy(float),
                {s: j for j, s in enumerate(symbols)})


def simulate(panels: Panels, ohlc: OHLC, cfg: dict, start: pd.Timestamp, end: pd.Timestamp,
             modules: dict, sectors: dict[str, str] | None = None) -> SimResult:
    cal = panels.calendar
    pcfg = cfg["portfolio"]
    use_regime = modules.get("regime_filter", True)
    use_exits = modules.get("stop_and_target", True)
    n_hold, keep_rank = pcfg["holdings"], pcfg["keep_if_rank_within"]

    start_i = int(np.searchsorted(cal.values, np.datetime64(start)))
    end_i = int(np.searchsorted(cal.values, np.datetime64(end), side="right")) - 1
    mode = cfg["schedule"].get("mode", "twice_monthly")
    if mode == "daily":
        rebal = set(range(max(start_i, 1), end_i + 1))
        keep_rank = cfg["schedule"].get("daily_keep_if_rank_within", keep_rank)
    elif mode == "weekly":
        weeks = cal.to_period("W")
        rebal = {i for i in range(max(start_i, 1), end_i + 1) if weeks[i] != weeks[i - 1]}
    else:
        months = cfg["schedule"].get("months")   # e.g. [3, 6, 9, 12] for quarterly; None = every month
        rebal = {i for i in rebalance_indices(cal, cfg["schedule"]["rebalance_days_of_month"])
                 if start_i <= i <= end_i and i >= 1 and (not months or cal[i].month in months)}

    cash = float(pcfg["capital"])
    held: list[Position] = []
    trades: list[dict] = []
    equity = np.full(end_i - start_i + 1, np.nan)
    open_count = np.zeros(end_i - start_i + 1, int)
    stats = {"checkins": 0, "checkins_regime_off": 0, "buys": 0, "gap_skipped": 0,
             "no_cash": 0, "sold_at_checkin": 0}

    def bar(sym, i):
        j = ohlc.col[sym]
        return ohlc.open[i, j], ohlc.high[i, j], ohlc.low[i, j], ohlc.close[i, j]

    def sell(p: Position, i: int, price: float, reason: str):
        nonlocal cash
        fill = costs.sell_fill(price, cfg)
        sell_value = fill * p.qty
        sell_charges = costs.side_charges(sell_value, cfg, "sell")
        cash += sell_value - sell_charges
        buy_value = p.entry_fill * p.qty
        net = sell_value - buy_value - p.buy_charges - sell_charges
        # No-lookahead guard: every trade is entered after the day its signal was computed.
        assert p.entry_i > p.signal_i, "lookahead: entry must come after the signal day"
        assert i >= p.entry_i, "exit before entry"
        trades.append({
            "symbol": p.symbol, "signal_date": cal[p.signal_i], "entry_date": cal[p.entry_i],
            "exit_date": cal[i], "entry": p.entry_ref, "entry_fill": p.entry_fill,
            "initial_stop": p.initial_stop, "final_stop": p.stop, "R": p.risk_per_share,
            "target": p.target, "qty": p.qty, "position_value": buy_value, "exit": price,
            "exit_fill": fill, "exit_reason": reason, "sessions": p.sessions,
            "charges": p.buy_charges + sell_charges,
            "slippage": (p.entry_fill - p.entry_ref) * p.qty + (price - fill) * p.qty,
            "gross_pnl": (price - p.entry_ref) * p.qty, "net_pnl": net,
            "r_multiple": net / (p.qty * p.risk_per_share) if p.risk_per_share > 0 else np.nan,
            "rank_at_entry": p.rank,
        })
        held.remove(p)

    for i in range(start_i, end_i + 1):
        is_checkin = i in rebal
        s = i - 1  # signal day: the close before the check-in
        ranked: list[str] = []
        regime_on = True
        if is_checkin:
            stats["checkins"] += 1
            regime_on = bool(panels.regime.iloc[s]) if use_regime else True
            if not regime_on:
                stats["checkins_regime_off"] += 1
            else:
                ranked = ranked_eligible(panels, s, cfg, modules)
            # 1. raise stops of holdings (the GTT is modified before the open)
            if use_exits:
                for p in held:
                    lc = panels.close.iloc[s][p.symbol]
                    if not math.isnan(lc):
                        new = raised_stop(p.stop, p.entry_ref, p.risk_per_share, lc,
                                          panels.atr.iloc[s][p.symbol], cfg)
                        p.breakeven = p.breakeven or new >= p.entry_ref
                        p.stop = new

        # 2. GTT gap exits at the open
        if use_exits:
            for p in list(held):
                o, _, _, _ = bar(p.symbol, i)
                if math.isnan(o):
                    continue
                if o <= p.stop:
                    sell(p, i, o, "stop loss (gap down)")
                elif o >= p.target:
                    sell(p, i, o, "target (gap up)")

        if is_checkin:
            # 3. sell holdings that no longer qualify
            keep = set(ranked[:keep_rank])
            max_hold = cfg["trade"].get("max_hold_sessions")   # optional: force short swing trades
            just_sold: set[str] = set()
            for p in list(held):
                o, _, _, _ = bar(p.symbol, i)
                if math.isnan(o):
                    continue
                if p.symbol not in keep or (max_hold and p.sessions >= max_hold):
                    reason = ("check-in: market filter OFF" if not regime_on else
                              "check-in: dropped off the list" if p.symbol not in keep else "check-in: holding time limit")
                    sell(p, i, o, reason)
                    just_sold.add(p.symbol)
                    stats["sold_at_checkin"] += 1
            # 4. buy the strongest stocks not held
            free = n_hold - len(held)
            if free > 0 and ranked:
                held_syms = {p.symbol for p in held} | (just_sold if max_hold else set())
                port_value = cash + sum(p.qty * p.last_close for p in held)
                budget = port_value / n_hold
                # Skip stocks where even one share costs more than the per-stock amount.
                picks = [(r, sym) for r, sym in enumerate(ranked, 1) if sym not in held_syms
                         and limit_price(panels.close.iloc[s][sym], cfg) <= budget]
                # Optional: at most N stocks from the same sector.
                cap = pcfg.get("max_per_sector")
                if cap and sectors:
                    count: dict[str, int] = {}
                    for p in held:
                        count[sectors.get(p.symbol, p.symbol)] = count.get(sectors.get(p.symbol, p.symbol), 0) + 1
                    chosen = []
                    for r, sym in picks:
                        sec = sectors.get(sym, sym)
                        if count.get(sec, 0) < cap:
                            chosen.append((r, sym))
                            count[sec] = count.get(sec, 0) + 1
                    picks = chosen
                picks = picks[:free]
                for rank, sym in picks:
                    o, h, l, _ = bar(sym, i)
                    lc = panels.close.iloc[s][sym]
                    if math.isnan(o) or math.isnan(lc):
                        continue
                    lim = limit_price(lc, cfg)
                    ref = limit_fill(o, l, lim)
                    if ref is None:
                        stats["gap_skipped"] += 1
                        continue
                    fill = costs.buy_fill(ref, cfg)
                    qty = quantity(min(budget, cash / 1.0015), fill)
                    if qty < 1:
                        stats["no_cash"] += 1
                        continue
                    plan = plan_trade(ref, panels.atr.iloc[s][sym], cfg)
                    buy_value = fill * qty
                    buy_charges = costs.side_charges(buy_value, cfg, "buy")
                    cash -= buy_value + buy_charges
                    held.append(Position(symbol=sym, signal_i=s, entry_i=i, entry_ref=ref,
                                         entry_fill=fill, qty=qty, stop=plan.stop,
                                         initial_stop=plan.stop, risk_per_share=plan.risk_per_share,
                                         target=plan.target, rank=rank, buy_charges=buy_charges))
                    stats["buys"] += 1

        # 5. intraday GTT exits, then mark to market
        for p in list(held):
            _, h, l, c = bar(p.symbol, i)
            if math.isnan(c):
                continue
            p.sessions += 1
            p.last_close = c
            if use_exits:
                if l <= p.stop:
                    sell(p, i, p.stop, "stop loss (raised)" if p.stop > p.initial_stop else "stop loss")
                    continue
                if h >= p.target:
                    sell(p, i, p.target, "target")
                    continue

        if i == end_i:
            for p in list(held):
                sell(p, i, p.last_close, "still held at period end (marked at close)")

        equity[i - start_i] = cash + sum(p.qty * p.last_close for p in held)
        open_count[i - start_i] = len(held)

    idx = cal[start_i:end_i + 1]
    tdf = pd.DataFrame(trades)
    if len(tdf):
        tdf = tdf.sort_values(["exit_date", "entry_date", "symbol"]).reset_index(drop=True)
    return SimResult(tdf, pd.Series(equity, index=idx), pd.Series(open_count, index=idx), stats)
