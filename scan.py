"""Check-in report. Run any evening after 4 pm IST (needed the evening before a check-in).

Usage:  python scan.py
Writes output/report.html and output/candidates.json.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, timedelta

import pandas as pd

from screener import notify
from screener.checkin import (check_holdings, is_checkin_session, load_open_trades, make_pick,
                              load_brands, next_checkin, next_weekday, round_to_tick, why_stock)
from screener.charts import index_payload, stock_payload
from screener.confirm import second_opinion
from screener.profiles import get_logo, get_profile
from screener.config import load_config
from screener.data import load_prices, load_universe
from screener.fundamentals import evaluate, load_fundamentals, load_results_calendar
from screener.report_how import build_how_html
from screener.report_scan import build_report_html, candidates_json, phone_message
from screener.signals import build_panels, compute_symbol_signals, ranked_eligible, regime_series, trading_calendar
from screener.utils import now_ist, setup_logging


def _last_weekday_before(d: date) -> date:
    d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def main() -> int:
    """Run the scan; on any crash, still try to tell the phone."""
    cfg = load_config()
    log = setup_logging(cfg["paths"]["log_dir"], "scan")
    try:
        return run(cfg, log)
    except Exception as exc:
        log.exception("Scan failed")
        notify.send(cfg, f"Stock check FAILED tonight: {type(exc).__name__}: {exc}. "
                         "See logs/scan.log on the computer.")
        return 1


def run(cfg: dict, log) -> int:
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

    # The next session follows the last completed weekday, even if Yahoo has not published
    # today's prices yet (NSE holidays are not known).
    now = now_ist()
    hh, mm = (int(x) for x in cfg["prices"]["session_complete_time_ist"].split(":"))
    if now.weekday() < 5 and (now.hour, now.minute) >= (hh, mm):
        last_done = now.date()
    else:
        last_done = _last_weekday_before(now.date())
    ref_day = max(data_day, last_done)
    phone_notes = []
    if data_day < ref_day:
        msg = f"Prices for {ref_day:%d %b} are not available yet; this report uses {data_day:%d %b}."
        notes.append(msg)
        phone_notes.append(msg)
    next_session = next_weekday(ref_day)
    days = cfg["schedule"]["rebalance_days_of_month"]
    checkin_next = is_checkin_session(ref_day, next_session, days)
    checkin_day = next_session if checkin_next else next_checkin(ref_day, days)

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
    aim_pct = ((status or {}).get("summary") or {}).get("avg_win_pct")

    # Signals, prices and plain-language reasons for each stock shown.
    brands = load_brands(cfg)

    def why_for(sym: str, rank: int, pick=None):
        fund = evaluate(sym, industry.get(sym, ""), ftable, cfg) if ftable is not None else None
        w = why_stock(sym, rank, float(panels.rs_pct.iloc[i][sym]), bool(panels.trend_ok.iloc[i][sym]),
                      fresh[sym], index_df, data_ts, get_profile(sym, cfg), fund, cfg, brands.get(sym),
                      market_on=regime_on)
        if pick is None:
            pick = make_pick(sym, rank, panels, i, universe, cfg, fund or evaluate(sym, "", None, cfg),
                             res_cal, today, budget)
        w.levels = {"buy": pick.limit, "stop": pick.stop, "qty": pick.qty, "amount": pick.qty * pick.last_close,
                    "close": pick.last_close, "stop_pct": pick.stop_pct,
                    "aim": round_to_tick(pick.last_close * (1 + aim_pct / 100), "nearest") if aim_pct else None,
                    "aim_pct": aim_pct}
        return w

    # Watchlist on the dashboard: the Top 10 (picks marked), each with signals, prices and charts.
    pick_map = {pk.symbol: pk for pk in picks}
    for pk in picks:
        pk.why = why_for(pk.symbol, pk.rank, pk)
    keep_n = cfg["portfolio"]["keep_if_rank_within"]
    list_syms = list((ranked if regime_on else ranked_any)[:keep_n])
    list_syms += [s for s in pick_map if s not in list_syms]
    watch_why = []
    for r, s in enumerate(list_syms, 1):
        w = pick_map[s].why if s in pick_map else why_for(s, (ranked if regime_on else ranked_any).index(s) + 1)
        watch_why.append(w)
    charts = {"NIFTY": index_payload(index_df, data_ts, cfg, sessions=250)}
    for w in watch_why:
        charts[w.symbol] = stock_payload(fresh[w.symbol], index_df, data_ts, sessions=250,
                                         stop=w.levels["stop"], limit=w.levels["buy"])
        charts[w.symbol]["aim"] = w.levels.get("aim")
        w.second, w.second_agree, extra = second_opinion(fresh[w.symbol], data_ts, sessions=250)
        w.logo = get_logo(w.domain, cfg)
        charts[w.symbol].update(extra)

    # How the radar was built today (the funnel), for the dashboard.
    sc = panels.rs_score.iloc[i].notna()
    funnel = {"scanned": int(sc.sum()),
              "uptrend": int((panels.trend_ok.iloc[i] & sc).sum()),
              "momentum": int(((panels.rs_pct.iloc[i] >= cfg["relative_strength"]["min_percentile"]) & sc).sum()),
              "both": len(ranked_any), "top": min(keep_n, len(ranked_any)),
              "buy": len(picks) if regime_on else 0, "market_on": regime_on}

    ctx = {"generated": now_ist(), "data_date": data_day, "next_checkin": checkin_day,
           "checkin_next": checkin_next, "regime_on": regime_on, "backtest_status": status,
           "picks": picks, "holdings": holdings, "next_in_line": next_in_line,
           "skipped_quality": skipped, "watch_when_off": ranked_any[:5], "notes": notes,
           "phone_notes": phone_notes, "watch_why": watch_why, "charts": charts, "pick_map": pick_map, "funnel": funnel,
           "top_list": list(enumerate(ranked[:cfg["portfolio"]["keep_if_rank_within"]], 1))}
    (out_dir / "report.html").write_text(build_report_html(ctx, cfg), encoding="utf-8")
    (out_dir / "candidates.json").write_text(candidates_json(ctx), encoding="utf-8")
    (out_dir / "how.html").write_text(build_how_html(cfg, status, charts.get("NIFTY"), funnel), encoding="utf-8")
    (out_dir / "index.html").write_text((out_dir / "report.html").read_text(encoding="utf-8"), encoding="utf-8")
    text = phone_message(ctx)
    log.info("Phone message:\n%s", text)
    notify.send(cfg, text, out_dir / "report.html")

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
