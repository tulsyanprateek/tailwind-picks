"""Check-in report. Run any evening after 4 pm IST (needed the evening before a check-in).

Usage:  python scan.py
Writes output/report.html and output/candidates.json.
"""
from __future__ import annotations

import json
import sys
import time

import pandas as pd

from screener.checkin import (check_holdings, is_checkin_session, load_open_trades, make_pick,
                              next_checkin, next_weekday)
from screener.config import load_config
from screener.data import load_prices, load_universe
from screener.fundamentals import evaluate, load_fundamentals, load_results_calendar
from screener.report_scan import build_report_html, candidates_json
from screener.signals import build_panels, compute_symbol_signals, ranked_eligible, regime_series, trading_calendar
from screener.utils import now_ist, setup_logging


def main() -> int:
    cfg = load_config()
    log = setup_logging(cfg["paths"]["log_dir"], "scan")
    t0 = time.time()
    out_dir = cfg["paths"]["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    notes: list[str] = []

    universe, uinfo = load_universe(cfg)
    if uinfo.warning:
        notes.append(uinfo.warning)
    trades, twarn = load_open_trades(cfg)
    if twarn:
        notes.append(twarn)
    held = list(trades["symbol"]) if len(trades) else []
    uni_syms = list(universe["symbol"])
    res = load_prices(uni_syms + [s for s in held if s not in uni_syms], cfg)
    bench = cfg["prices"]["benchmark_symbol"]
    if bench not in res.prices:
        log.error("Nifty 50 index could not be loaded; cannot run the market filter.")
        return 1
    index_df = res.prices.pop(bench)
    for s, why in res.failed.items():
        notes.append(f"{s}: download failed, skipped ({why}).")
    for s, why in res.short.items():
        notes.append(f"{s}: {why}, skipped (needs about a year of prices).")

    stock_prices = {s: df for s, df in res.prices.items() if s in uni_syms}
    last_dates = pd.Series({s: df.index[-1] for s, df in stock_prices.items()})
    data_ts = last_dates.mode().max()
    stale = sorted(last_dates[last_dates < data_ts].index)
    for s in stale:
        notes.append(f"{s}: prices only up to {last_dates[s]:%d %b %Y}, left out of the ranking.")
    for s, why in res.stale.items():
        notes.append(f"{s}: {why}.")
    fresh = {s: df for s, df in stock_prices.items() if s not in stale}

    signals = {s: compute_symbol_signals(df, cfg) for s, df in fresh.items()}
    calendar = trading_calendar(fresh)
    calendar = calendar[calendar <= data_ts]
    regime = regime_series(index_df, cfg)
    panels = build_panels(signals, regime, calendar)
    i = len(calendar) - 1
    data_day = calendar[i].date()
    mods = dict(cfg["modules"])
    regime_on = bool(panels.regime.iloc[i]) if mods.get("regime_filter", True) else True
    if index_df.index[-1] < data_ts:
        notes.append(f"Nifty 50 index data ends {index_df.index[-1]:%d %b}; market filter uses that day.")

    next_session = next_weekday(data_day)
    days = cfg["schedule"]["rebalance_days_of_month"]
    checkin_next = is_checkin_session(data_day, next_session, days)
    checkin_day = next_session if checkin_next else next_checkin(data_day, days)

    ftable, fwarn = load_fundamentals(cfg)
    if fwarn:
        notes.append(fwarn)
    res_cal = load_results_calendar(cfg)
    if res_cal is None:
        notes.append("No data/results_calendar.csv: check each stock's results date on Kite before buying.")
    industry = dict(zip(universe["symbol"], universe["industry"]))

    ranked = ranked_eligible(panels, i, cfg, mods)
    ranked_any = ranked_eligible(panels, i, cfg, {**mods, "trend_template": True})
    holdings = check_holdings(trades, res.prices, panels, i, ranked, cfg, checkin_next, regime_on, checkin_day)
    occupied = sum(1 for h in holdings if h.action in ("KEEP", "HOLD", "CHECK"))
    held_syms = {h.symbol for h in holdings if h.action != "STOP HIT"}
    free = max(0, cfg["portfolio"]["holdings"] - occupied)

    budget = cfg["portfolio"]["capital"] / cfg["portfolio"]["holdings"]
    today = now_ist().date()
    picks, skipped, next_in_line = [], [], []
    use_g = mods.get("fundamentals", True)
    for rank, sym in enumerate(ranked, 1):
        if sym in held_syms:
            continue
        fund = evaluate(sym, industry.get(sym, ""), ftable, cfg)
        if use_g and fund.status == "FAIL":
            if len(picks) < free:
                skipped.append((sym, fund.summary))
            continue
        if len(picks) < free:
            pk = make_pick(sym, rank, panels, i, universe, cfg, fund, res_cal, today, budget)
            if pk.qty < 1:
                skipped.append((sym, f"one share ({pk.limit:,.0f}) costs more than the {budget:,.0f} "
                                     "per-stock amount"))
                continue
            picks.append(pk)
        elif len(next_in_line) < 5:
            next_in_line.append((rank, sym, float(panels.close.iloc[i][sym]),
                                 float(panels.rs_pct.iloc[i][sym]), fund.status))
        else:
            break

    status_path = out_dir / "backtest_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else None

    ctx = {"generated": now_ist(), "data_date": data_day, "next_checkin": checkin_day,
           "checkin_next": checkin_next, "regime_on": regime_on, "backtest_status": status,
           "picks": picks, "holdings": holdings, "next_in_line": next_in_line,
           "skipped_quality": skipped, "watch_when_off": ranked_any[:5], "notes": notes}
    (out_dir / "report.html").write_text(build_report_html(ctx, cfg), encoding="utf-8")
    (out_dir / "candidates.json").write_text(candidates_json(ctx), encoding="utf-8")

    log.info("Data up to %s. Market filter %s. Next check-in %s%s.", data_day,
             "ON" if regime_on else "OFF", checkin_day, " (tomorrow)" if checkin_next else "")
    if regime_on:
        for pk in picks:
            log.info("  %-12s buy %4d at limit %10.2f, stop loss %10.2f", pk.symbol, pk.qty, pk.limit, pk.stop)
    for h in holdings:
        log.info("  holding %-12s %s", h.symbol, h.action)
    if status is not None and not status["passed"]:
        log.warning("BACKTEST FAILED OUT OF SAMPLE: do not trade these picks.")
    log.info("Wrote %s (%.0fs)", out_dir / "report.html", time.time() - t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
