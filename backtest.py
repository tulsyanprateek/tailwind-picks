"""Run the 12-year backtest and write output/backtest.html.

Usage:  python backtest.py
"""
from __future__ import annotations

import copy
import json
import random
import sys
import time

import numpy as np
import pandas as pd

from screener.config import load_config
from screener.data import load_prices, load_universe
from screener.metrics import benchmark, summarize, verdict
from screener.portfolio import build_ohlc, simulate
from screener.report_backtest import build_backtest_html
from screener.signals import build_panels, compute_symbol_signals, regime_series, trading_calendar
from screener.utils import now_ist, setup_logging

ABLATIONS = [
    ("Full system", {}),
    ("Without market filter (A)", {"regime_filter": False}),
    ("Without trend template (B)", {"trend_template": False}),
    ("Without momentum filter (C)", {"relative_strength": False}),
    ("Without stop loss and target", {"stop_and_target": False}),
]


# In-sample stop loss check (2014 to 2020 only). The selection rule was fixed before the
# check was run: pick the version with the best in-sample return per unit of worst fall
# (CAGR / |max drawdown|). The out-of-sample period is never used to choose.
STOP_CHECK = [
    ("No stop loss", None),
    ("Tight stop: 2 x ATR, max 8%, target 3R", {"stop_mode": "atr", "use_target": True}),
    ("Safety net 10%, fixed", {"stop_mode": "percent", "stop_pct": 10, "trail_stop_at_checkin": False}),
    ("Safety net 15%, fixed", {"stop_mode": "percent", "stop_pct": 15, "trail_stop_at_checkin": False}),
    ("Safety net 20%, fixed", {"stop_mode": "percent", "stop_pct": 20, "trail_stop_at_checkin": False}),
    ("Safety net 10%, raised at check-ins", {"stop_mode": "percent", "stop_pct": 10, "trail_stop_at_checkin": True}),
    ("Safety net 15%, raised at check-ins", {"stop_mode": "percent", "stop_pct": 15, "trail_stop_at_checkin": True}),
    ("Safety net 20%, raised at check-ins", {"stop_mode": "percent", "stop_pct": 20, "trail_stop_at_checkin": True}),
]


def matches_config(override: dict | None, cfg: dict) -> bool:
    t = cfg["trade"]
    if override is None:
        return not cfg["modules"].get("stop_and_target", True)
    if not cfg["modules"].get("stop_and_target", True):
        return False
    if override["stop_mode"] != t["stop_mode"]:
        return False
    if override["stop_mode"] == "atr":
        return bool(t.get("use_target")) == override["use_target"]
    return (override["stop_pct"] == t["stop_pct"]
            and override["trail_stop_at_checkin"] == bool(t.get("trail_stop_at_checkin"))
            and not t.get("use_target"))


def stop_check(panels, ohlc, cfg, start, is_end, base_modules, capital) -> list[dict]:
    rows = []
    for name, override in STOP_CHECK:
        c = copy.deepcopy(cfg)
        mods = dict(base_modules)
        if override is None:
            mods["stop_and_target"] = False
        else:
            mods["stop_and_target"] = True
            c["trade"].update({"use_target": False, **override})
        m = summarize(simulate(panels, ohlc, c, start, is_end, mods), capital)
        ratio = m["cagr"] / abs(m["max_dd_pct"]) if m["max_dd_pct"] < 0 else float("nan")
        rows.append({"name": name, "m": m, "ratio": ratio, "in_use": matches_config(override, cfg)})
    best = max(rows, key=lambda r: (r["ratio"], 0))
    for r in rows:
        r["best"] = r is best
    return rows


def lookahead_spot_checks(prices, signals, cfg, n_checks, seed) -> int:
    """Recompute signals on data cut off at a random day and compare with the full run.

    If any value for that day changes, the calculation used data from after that day.
    """
    rng = random.Random(seed)
    syms = sorted(signals)
    checked = 0
    cols = ["trend_ok", "rs_score", "atr", "close"]
    for _ in range(n_checks):
        sym = rng.choice(syms)
        idx = signals[sym].index
        if len(idx) < 300:
            continue
        day = idx[rng.randrange(260, len(idx) - 1)]
        cut = compute_symbol_signals(prices[sym].loc[:day], cfg).iloc[-1]
        full = signals[sym].loc[day]
        for c in cols:
            a, b = full[c], cut[c]
            same = (pd.isna(a) and pd.isna(b)) or a == b or (
                isinstance(a, float) and abs(a - b) <= 1e-9 * max(1.0, abs(a)))
            assert same, f"Lookahead detected: {sym} {day.date()} column {c}: {a} vs {b}"
        checked += 1
    return checked


def main() -> int:
    cfg = load_config()
    log = setup_logging(cfg["paths"]["log_dir"], "backtest")
    t0 = time.time()
    out_dir = cfg["paths"]["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    universe, uinfo = load_universe(cfg)
    if uinfo.warning:
        log.warning(uinfo.warning)
    res = load_prices(list(universe["symbol"]), cfg)
    bench_sym = cfg["prices"]["benchmark_symbol"]
    if bench_sym not in res.prices:
        log.error("Nifty 50 index (%s) could not be loaded; the backtest needs it.", bench_sym)
        return 1
    index_df = res.prices.pop(bench_sym)

    log.info("Computing indicators for %d stocks", len(res.prices))
    signals = {s: compute_symbol_signals(df, cfg) for s, df in res.prices.items()}
    calendar = trading_calendar(res.prices)
    regime = regime_series(index_df, cfg)
    panels = build_panels(signals, regime, calendar)
    ohlc = build_ohlc(res.prices, list(signals), calendar)

    n_checks = lookahead_spot_checks(res.prices, signals, cfg, cfg["backtest"]["lookahead_spot_checks"],
                                     cfg["backtest"]["random_seed"])
    log.info("Lookahead spot checks passed: %d", n_checks)

    bt = cfg["backtest"]
    start = pd.Timestamp(bt["start"])
    is_end = pd.Timestamp(bt["in_sample_end"])
    oos_start = pd.Timestamp(bt["out_of_sample_start"])
    end = calendar[-1]
    capital = cfg["portfolio"]["capital"]
    base_modules = {k: v for k, v in cfg["modules"].items()}
    base_modules["fundamentals"] = False   # no historical fundamentals

    periods = {"full": (start, end), "is": (start, is_end), "oos": (oos_start, end)}
    runs = {}
    ablation_rows = []
    for name, override in ABLATIONS:
        mods = {**base_modules, **override}
        row = {"name": name}
        for key in ("full", "oos") if override else ("full", "is", "oos"):
            a, b = periods[key]
            r = simulate(panels, ohlc, cfg, a, b, mods)
            row[key] = summarize(r, capital)
            if not override:
                runs[key] = r
        ablation_rows.append(row)
        log.info("%-32s full CAGR %6.1f%%  maxDD %6.1f%%  trades %4d | 2021+ CAGR %6.1f%%",
                 name, row["full"]["cagr"], row["full"]["max_dd_pct"], row["full"]["trades"],
                 row["oos"]["cagr"])

    stop_rows = stop_check(panels, ohlc, cfg, start, is_end, base_modules, capital)
    for r in stop_rows:
        log.info("Stop check 2014-2020: %-40s CAGR %6.1f%%  maxDD %6.1f%%  ratio %.2f%s%s", r["name"],
                 r["m"]["cagr"], r["m"]["max_dd_pct"], r["ratio"], "  <- best" if r["best"] else "",
                 "  (in use)" if r["in_use"] else "")
    if not any(r["best"] and r["in_use"] for r in stop_rows):
        log.warning("The stop loss in config.yaml is not the one with the best in-sample ratio "
                    "(see the Stop loss check section of the report).")

    full_m, is_m, oos_m = (ablation_rows[0][k] for k in ("full", "is", "oos"))
    bclose = index_df["Close"]
    bfull, beq_full = benchmark(bclose, start, end, capital)
    bis, _ = benchmark(bclose, start, is_end, capital)
    boos, _ = benchmark(bclose, oos_start, end, capital)
    v = verdict(oos_m, boos)

    trades_full = runs["full"].trades
    missing = [f"{s} ({why})" for s, why in {**res.failed, **res.short, **res.stale}.items()]
    first_dates = {s: df.index[0] for s, df in res.prices.items()}
    late = [f"{s} (data from {d:%b %Y})" for s, d in sorted(first_dates.items(), key=lambda x: x[1])
            if d > start - pd.Timedelta(days=400)]
    missing_text = "; ".join(missing) if missing else "none"
    if late:
        missing_text += ". Listed later, so only tested from their listing: " + ", ".join(late)

    ctx = {
        "generated": now_ist(), "verdict": v,
        "full": full_m, "is": is_m, "oos": oos_m,
        "bench_full": bfull, "bench_is": bis, "bench_oos": boos,
        "equity_full": runs["full"].equity, "bench_eq_full": beq_full,
        "trades_full": trades_full, "ablation": ablation_rows, "stop_check": stop_rows,
        "sanity": {
            "symbols_tested": len(signals), "universe_size": len(universe),
            "universe_source": uinfo.source,
            "data_start": min(first_dates.values()), "data_end": end,
            "missing_text": missing_text,
            "lookahead_text": (f"every trade is entered after its signal day (checked by an assert on all "
                               f"{len(trades_full)} trades), and {n_checks} random stock-days gave identical "
                               f"values when recomputed with all later data removed."),
            **runs["full"].stats,
        },
    }
    (out_dir / "backtest.html").write_text(build_backtest_html(ctx, cfg), encoding="utf-8")
    trades_full.to_csv(out_dir / "backtest_trades.csv", index=False, date_format="%Y-%m-%d")
    status = {
        "passed": v["passed"], "reasons": v["reasons"], "generated": now_ist().isoformat(timespec="seconds"),
        "oos_expectancy_inr": v["oos_expectancy_inr"], "oos_expectancy_r": v["oos_expectancy_r"],
        "oos_cagr": v["oos_cagr"], "oos_max_dd_pct": v["oos_max_dd_pct"],
        "nifty_oos_cagr": v["bench_oos_cagr"], "nifty_oos_max_dd_pct": v["bench_oos_max_dd_pct"],
        "data_end": f"{end:%Y-%m-%d}",
    }
    eqw = runs["full"].equity.resample("W-FRI").last().dropna()
    bw = beq_full.resample("W-FRI").last().reindex(eqw.index).ffill()
    status["equity_weekly"] = {"t": [f"{d:%Y-%m-%d}" for d in eqw.index],
                               "s": [round(float(v)) for v in eqw], "n": [round(float(v)) for v in bw]}
    # Plain-language numbers for the dashboard and the "How it works" page (full 12 years).
    tf = trades_full
    move = (tf["exit"] / tf["entry"] - 1) * 100 if len(tf) else pd.Series(dtype=float)
    wins = tf["net_pnl"] > 0 if len(tf) else pd.Series(dtype=bool)
    status["summary"] = {
        "trades": int(len(tf)),
        "win_rate": float(wins.mean() * 100) if len(tf) else None,
        "avg_win_pct": float(move[wins].mean()) if wins.any() else None,
        "avg_loss_pct": float(move[~wins].mean()) if (~wins).any() else None,
        "avg_hold_days": full_m.get("avg_holding_days"),
        "pct_time_in_cash": full_m.get("pct_time_in_cash"),
        "full_cagr": full_m["cagr"], "full_max_dd_pct": full_m["max_dd_pct"],
        "nifty_full_cagr": bfull["cagr"], "nifty_full_max_dd_pct": bfull["max_dd_pct"],
        "final_value": full_m["final_value"], "nifty_final_value": bfull["final_value"],
        "start": f"{start:%Y}",
    }
    (out_dir / "backtest_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")

    log.info("Verdict: %s", "PASSED" if v["passed"] else "STRATEGY FAILED OUT OF SAMPLE")
    log.info("Out of sample: CAGR %.1f%% (Nifty %.1f%%), max fall %.1f%% (Nifty %.1f%%), "
             "expectancy Rs %.0f per trade", oos_m["cagr"], boos["cagr"], oos_m["max_dd_pct"],
             boos["max_dd_pct"], oos_m["expectancy_inr"])
    log.info("Wrote %s (%.0fs)", out_dir / "backtest.html", time.time() - t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
