"""Build output/backtest.html."""
from __future__ import annotations

import json
import math

import pandas as pd

from .html_common import bar_chart, esc, line_chart, page
from .metrics import drawdown, r_histogram
from .utils import inr, num, pct

FAILED_TEXT = "STRATEGY FAILED OUT OF SAMPLE"


def _f(v, kind):
    if v is None or (isinstance(v, float) and (math.isnan(v))):
        return "N/A"
    if isinstance(v, float) and math.isinf(v):
        return "no losses"
    return {"inr": lambda: inr(v), "pct": lambda: pct(v), "spct": lambda: pct(v, signed=True),
            "n": lambda: f"{int(v):,}".replace(",", ","), "r": lambda: f"{v:+.2f}R",
            "x": lambda: f"{v:.2f}", "d": lambda: f"{v:.1f}"}[kind]()


def _cls(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    return "pos" if v > 0 else "neg" if v < 0 else ""


METRIC_ROWS = [
    ("Final value of ₹1,00,000", "final_value", "inr"),
    ("Net profit after all costs", "net_pnl", "inr"),
    ("Yearly return (CAGR)", "cagr", "spct"),
    ("Worst fall from a peak (max drawdown)", "max_dd_pct", "pct"),
    ("Worst fall in rupees", "max_dd_inr", "inr"),
    ("Number of trades", "trades", "n"),
    ("Winning trades", "win_rate", "pct"),
    ("Average win", "avg_win", "inr"),
    ("Average loss", "avg_loss", "inr"),
    ("Average result per trade (expectancy)", "expectancy_inr", "inr"),
    ("Average result in R (expectancy)", "expectancy_r", "r"),
    ("Profit factor (gross wins / gross losses)", "profit_factor", "x"),
    ("Longest run of losing trades", "longest_losing_streak", "n"),
    ("Months that ended up", "pct_months_positive", "pct"),
    ("Average holding (trading sessions)", "avg_holding_sessions", "d"),
    ("Average holding (calendar days)", "avg_holding_days", "d"),
    ("Time fully in cash", "pct_time_in_cash", "pct"),
    ("Total charges and slippage paid", "total_charges", "inr"),
]


def _metrics_table(cols: list[tuple[str, dict, bool]], bench: list[dict]) -> str:
    head = "".join(f'<th class="{"hl" if hl else ""}">{esc(n)}</th>' for n, _, hl in cols)
    rows = []
    for label, key, kind in METRIC_ROWS:
        cells = "".join(f'<td class="{"hl " if hl else ""}{_cls(m.get(key)) if kind in ("inr", "spct", "r") else ""}">'
                        f'{_f(m.get(key), kind)}</td>' for _, m, hl in cols)
        rows.append(f"<tr><td>{esc(label)}</td>{cells}</tr>")
    rows.append('<tr><td colspan="4" style="text-align:left;color:var(--muted)">'
                'Nifty 50 buy and hold, same periods</td></tr>')
    for label, key, kind in [("Nifty 50: final value of ₹1,00,000", "final_value", "inr"),
                             ("Nifty 50: yearly return (CAGR)", "cagr", "spct"),
                             ("Nifty 50: worst fall (max drawdown)", "max_dd_pct", "pct")]:
        cells = "".join(f'<td class="{"hl" if cols[k][2] else ""}">{_f(b.get(key), kind)}</td>'
                        for k, b in enumerate(bench))
        rows.append(f"<tr><td>{esc(label)}</td>{cells}</tr>")
    return (f'<div class="scroll"><table><thead><tr><th></th>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def _ablation_table(rows: list[dict]) -> str:
    head = ("<th>Version</th><th>Trades</th><th>Win %</th><th>Expectancy</th><th>CAGR</th>"
            "<th>Max fall</th><th class=\"hl\">2021+ CAGR</th><th class=\"hl\">2021+ max fall</th>"
            "<th class=\"hl\">2021+ expectancy</th>")
    body = []
    for r in rows:
        f, o = r["full"], r["oos"]
        body.append(
            f"<tr><td>{esc(r['name'])}</td><td>{_f(f['trades'], 'n')}</td><td>{_f(f['win_rate'], 'pct')}</td>"
            f"<td class=\"{_cls(f['expectancy_inr'])}\">{_f(f['expectancy_inr'], 'inr')}</td>"
            f"<td class=\"{_cls(f['cagr'])}\">{_f(f['cagr'], 'spct')}</td><td>{_f(f['max_dd_pct'], 'pct')}</td>"
            f"<td class=\"hl {_cls(o['cagr'])}\">{_f(o['cagr'], 'spct')}</td>"
            f"<td class=\"hl\">{_f(o['max_dd_pct'], 'pct')}</td>"
            f"<td class=\"hl {_cls(o['expectancy_inr'])}\">{_f(o['expectancy_inr'], 'inr')}</td></tr>")
    return (f'<div class="scroll"><table><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def _trade_table(trades: pd.DataFrame) -> str:
    cols = ["symbol", "entry_date", "exit_date", "qty", "entry", "initial_stop", "target",
            "exit", "exit_reason", "sessions", "charges", "net_pnl", "r_multiple"]
    head = "".join(f"<th>{esc(c.replace('_', ' '))}</th>" for c in cols)
    body = []
    for _, t in trades.sort_values("entry_date", ascending=False).iterrows():
        body.append(
            f"<tr><td>{esc(t['symbol'])}</td><td>{t['entry_date']:%d %b %Y}</td>"
            f"<td>{t['exit_date']:%d %b %Y}</td><td>{int(t['qty'])}</td><td>{num(t['entry'])}</td>"
            f"<td>{num(t['initial_stop'])}</td><td>{num(t['target'])}</td><td>{num(t['exit'])}</td>"
            f"<td style=\"text-align:left\">{esc(t['exit_reason'])}</td><td>{int(t['sessions'])}</td>"
            f"<td>{inr(t['charges'] + t['slippage'])}</td>"
            f"<td class=\"{_cls(t['net_pnl'])}\">{inr(t['net_pnl'])}</td>"
            f"<td class=\"{_cls(t['r_multiple'])}\">{t['r_multiple']:+.2f}</td></tr>")
    return (f'<div class="scroll" style="max-height:520px;overflow:auto"><table><thead><tr>{head}'
            f'</tr></thead><tbody>{"".join(body)}</tbody></table></div>')


def _stop_rule_text(cfg: dict) -> str:
    t = cfg["trade"]
    if not cfg["modules"].get("stop_and_target", True):
        return "<li>No stop loss and no target: holdings are only sold at a check-in.</li>"
    if t.get("stop_mode") == "percent":
        s = (f"<li>Safety-net stop loss {t['stop_pct']}% below the buy price, as a GTT order on Kite"
             + (", raised at each check-in to last close minus the same %" if t.get("trail_stop_at_checkin") else "")
             + ".")
    else:
        s = (f"<li>Stop loss: entry minus {t['atr_stop_multiple']} x ATR(14), never more than "
             f"{t['max_stop_pct']}% below entry, raised at each check-in (never lowered).")
    if t.get("use_target", True):
        s += f" Target: entry + {t['target_r']} x the risk, in the same GTT order."
    else:
        s += " No target: holdings are sold at a check-in when they drop off the list."
    return s + "</li>"


def _stop_check_section(rows: list[dict] | None) -> str:
    if not rows:
        return ""
    body = []
    for r in rows:
        m = r["m"]
        tag = []
        if r["best"]:
            tag.append("best ratio")
        if r["in_use"]:
            tag.append("in use")
        name = esc(r["name"]) + (f' <span class="badge amber">{esc(", ".join(tag))}</span>' if tag else "")
        hl = ' class="hl"' if r["in_use"] else ""
        body.append(f"<tr{hl}><td>{name}</td><td class=\"{_cls(m['cagr'])}\">{_f(m['cagr'], 'spct')}</td>"
                    f"<td>{_f(m['max_dd_pct'], 'pct')}</td><td>{r['ratio']:.2f}</td>"
                    f"<td>{_f(m['trades'], 'n')}</td><td>{_f(m['win_rate'], 'pct')}</td></tr>")
    in_use_best = any(r["best"] and r["in_use"] for r in rows)
    note = "" if in_use_best else (
        '<p class="small"><b>Why the setting in use is not the best ratio:</b> the test only contains '
        "stocks that are in the Nifty 100 today. Companies that collapsed and left the index (the "
        "situations a safety-net stop exists for) are missing, so the test cannot show what the stop "
        "protects against. The difference in the 2014 to 2020 results is small, so the safety net is kept "
        "as insurance. This was decided before looking at any 2021+ results for these versions.</p>")
    return (
        "<h2>Stop loss check (2014 to 2020 only)</h2>"
        '<p class="muted small">The only parameter check allowed: done on the in-sample years only, so the '
        "2021+ results stay a fair test. Rule fixed in advance: prefer the best yearly return per unit of "
        "worst fall (ratio = CAGR / worst fall). Only the version in use is shown after 2020.</p>"
        '<div class="scroll"><table><thead><tr><th>Version</th><th>CAGR</th><th>Worst fall</th>'
        f'<th>Ratio</th><th>Trades</th><th>Win %</th></tr></thead><tbody>{"".join(body)}</tbody></table></div>'
        f"{note}")


def build_backtest_html(ctx: dict, cfg: dict) -> str:
    v = ctx["verdict"]
    full, ins, oos = ctx["full"], ctx["is"], ctx["oos"]
    bfull, bis, boos = ctx["bench_full"], ctx["bench_is"], ctx["bench_oos"]
    oos_start = pd.Timestamp(cfg["backtest"]["out_of_sample_start"])
    p = cfg["portfolio"]

    if v["passed"]:
        banner = (f'<div class="banner green"><span class="big">PASSED out of sample (2021 to now)</span>'
                  f'<p>On data the rules were never adjusted on, ₹1,00,000 became {inr(oos["final_value"])} '
                  f'({pct(oos["cagr"], signed=True)} a year) against {inr(boos["final_value"])} for the Nifty 50 '
                  f'({pct(boos["cagr"], signed=True)} a year). Worst fall: {pct(oos["max_dd_pct"])} '
                  f'against {pct(boos["max_dd_pct"])} for the Nifty 50. Average result per trade after costs: '
                  f'{inr(oos["expectancy_inr"])}.</p><p>Passing a backtest is not a promise. '
                  f'Expect losing trades, losing months and falls of this size or worse.</p></div>')
    else:
        banner = (f'<div class="banner red"><span class="big">{FAILED_TEXT}</span>'
                  f'<p>From 2021 to now: {"; ".join(esc(r) for r in v["reasons"])}. '
                  f'₹1,00,000 became {inr(oos["final_value"])} against {inr(boos["final_value"])} for the '
                  f'Nifty 50. Average result per trade after costs: {inr(oos["expectancy_inr"])}.</p>'
                  f'<p>Do not trade this system with real money.</p></div>')

    warn = (
        '<div class="banner amber"><span class="big">Read before trusting these numbers</span>'
        '<p><b>Survivorship bias.</b> The test uses today\'s Nifty 100 members for all 12 years. '
        'Stocks that fell out of the index (often after falling a lot) are missing, and today\'s '
        'winners are included from the start. Real results would likely be worse than shown.</p>'
        '<p><b>Fundamentals filter not tested.</b> Historical fundamentals are not available, so the '
        'backtest runs without the quality filter (module G). The live report can apply it.</p>'
        '<p><b>Costs.</b> Zerodha delivery charges and 0.1% slippage per side are included. '
        'Verify the rates at zerodha.com/charges.</p></div>')

    sc = ctx["sanity"]
    sanity = (
        '<div class="card"><h3 style="margin-top:0">Sanity checks</h3><ul class="small">'
        f'<li>Stocks tested: <b>{sc["symbols_tested"]}</b> of {sc["universe_size"]} in the Nifty 100 list '
        f'({esc(sc["universe_source"])}).</li>'
        f'<li>Price data from {sc["data_start"]:%d %b %Y} to {sc["data_end"]:%d %b %Y}; '
        f'backtest from {full["start"]:%d %b %Y} to {full["end"]:%d %b %Y}.</li>'
        f'<li>Missing or skipped stocks: {esc(sc["missing_text"])}</li>'
        f'<li>No future data: {esc(sc["lookahead_text"])}</li>'
        f'<li>Check-ins simulated: {sc["checkins"]}, of which {sc["checkins_regime_off"]} had the '
        f'market filter OFF (everything sold, stayed in cash).</li>'
        f'<li>Buy orders not filled because the stock opened more than '
        f'{cfg["trade"]["max_gap_pct"]}% above the last close and never came back: {sc["gap_skipped"]}.</li>'
        '</ul></div>')

    rules = (
        '<div class="card small"><h3 style="margin-top:0">The rules that were tested</h3><ul>'
        f'<li>Check-in on the first trading day on or after the '
        f'{" and ".join(str(d) + ("st" if d == 1 else "th") for d in cfg["schedule"]["rebalance_days_of_month"])} '
        'of each month. Picks use prices up to the previous close; orders go in at that day\'s open.</li>'
        '<li>Only when the Nifty 50 is above its 200-day average and its 50-day average is above its '
        '200-day average. Otherwise everything is sold and the money stays in cash.</li>'
        '<li>Each stock must be in a healthy uptrend (above its 50, 150 and 200-day averages, the '
        '200-day average rising, at least 30% above its 52-week low and within 25% of its 52-week high) '
        f'and in the top {100 - cfg["relative_strength"]["min_percentile"]}% of the universe for '
        '3, 6 and 12-month momentum.</li>'
        f'<li>Hold the {p["holdings"]} strongest. A holding is kept while it still qualifies and ranks in '
        f'the top {p["keep_if_rank_within"]}.</li>'
        f'<li>Each new holding gets 1/{p["holdings"]} of the portfolio, bought with a limit order at last '
        f'close + {cfg["trade"]["max_gap_pct"]}%.</li>'
        f'{_stop_rule_text(cfg)}'
        '<li>If the stop and the target are both touched on the same day, the test assumes the stop '
        'was hit first.</li></ul></div>')

    eq_chart = line_chart(
        [("This system", ctx["equity_full"], "#6aa8ff"), ("Nifty 50 buy and hold", ctx["bench_eq_full"], "#9aa3b2")],
        vline=oos_start, vline_label="out of sample")
    dd_chart = line_chart(
        [("This system", drawdown(ctx["equity_full"]), "#ff5d5d"),
         ("Nifty 50", drawdown(ctx["bench_eq_full"]), "#9aa3b2")],
        y_fmt=lambda x: f"{x:.0f}%", height=200, fill_below_zero=True, vline=oos_start)
    hist = bar_chart(r_histogram(ctx["trades_full"]["r_multiple"])) if len(ctx["trades_full"]) else ""

    csv_text = ctx["trades_full"].to_csv(index=False, date_format="%Y-%m-%d")
    js = ("const CSV=" + json.dumps(csv_text) + ";"
          "function dl(){const b=new Blob([CSV],{type:'text/csv'});const a=document.createElement('a');"
          "a.href=URL.createObjectURL(b);a.download='backtest_trades.csv';document.body.appendChild(a);"
          "a.click();a.remove();}")

    body = f"""
<h1>Tailwind Picks: 12-year test</h1>
<div class="muted small">Nifty 100 stocks, ₹{inr(p["capital"], symbol=False)} start, {p["holdings"]} stocks held,
check-in every 2 weeks. Generated {ctx["generated"]:%d %b %Y %H:%M} IST.</div>
{banner}
{warn}
{sanity}
<h2>Results</h2>
<p class="muted small">In sample: {ins["start"]:%b %Y} to {ins["end"]:%b %Y}. Out of sample (highlighted): {oos["start"]:%b %Y}
to {oos["end"]:%b %Y}. Each period starts again with ₹1,00,000. The rules were fixed before the test and not tuned.</p>
{_metrics_table([("Full period", full, False), ("In sample", ins, False), ("Out of sample", oos, True)], [bfull, bis, boos])}
<h2>Growth of ₹1,00,000</h2>
<div class="card">{eq_chart}</div>
<h2>Falls from the previous peak</h2>
<div class="card">{dd_chart}</div>
<h2>Trade results in R</h2>
<p class="muted small">R is the money at risk on a trade (entry minus stop loss, times quantity). A trade at -1R lost
what was planned; +3R hit the target.</p>
<div class="card">{hist}</div>
<h2>Which parts add value</h2>
<p class="muted small">The same test with one part switched off at a time. If a version without a part does as well,
that part is not earning its place.</p>
{_ablation_table(ctx["ablation"])}
{_stop_check_section(ctx.get("stop_check"))}
{rules}
<h2>All trades ({len(ctx["trades_full"])})</h2>
<p><button onclick="dl()">Download CSV</button></p>
{_trade_table(ctx["trades_full"]) if len(ctx["trades_full"]) else "<p>No trades.</p>"}
"""
    return page("12-year test", body, js, active="backtest.html", brand=(cfg.get("brand", {}).get("name", "Tailwind Picks"), cfg.get("brand", {}).get("tagline", "")))
