"""Build output/report.html: the check-in report."""
from __future__ import annotations

import json
from datetime import date

from .checkin import HoldingCheck, Pick
from .html_common import esc, page
from .utils import inr, pct

FAILED_BANNER = "STRATEGY FAILED OUT OF SAMPLE"

SCAN_CSS = """
.top{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0 4px}
.todo{background:var(--panel);border:2px solid var(--blue);border-radius:12px;padding:14px 16px;margin:14px 0}
.todo h2{margin:0 0 8px;font-size:18px}
.todo ol{margin:6px 0 0;padding-left:22px}.todo li{margin:6px 0}
.pick{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;margin:12px 0}
.pick .head{display:flex;justify-content:space-between;align-items:baseline;gap:8px;flex-wrap:wrap}
.pick .sym{font-size:20px;font-weight:700}.pick .co{color:var(--muted);font-size:13px}
.big3{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:12px 0}
.big3 div{background:var(--panel2);border-radius:10px;padding:8px 10px}
.big3 .l{font-size:12px;color:var(--muted)}.big3 .v{font-size:17px;font-weight:700}
.big3 .v.red{color:var(--red)}.big3 .v.blue{color:var(--blue)}
@media(max-width:380px){.big3{grid-template-columns:1fr 1fr}}
.flags{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.chk{list-style:none;padding:0;margin:6px 0;font-size:13px}.chk li{margin:2px 0}
.ok{color:var(--green)}.no{color:var(--red)}
pre.order{background:#0b0d11;border:1px solid var(--line);border-radius:8px;padding:10px;font-size:12.5px;
white-space:pre-wrap;word-break:break-word;margin:8px 0}
details{margin:8px 0}summary{cursor:pointer;color:var(--muted);font-size:13px}
.spark{display:block;width:100%;height:auto;margin:6px 0}
.copied{color:var(--green);font-size:13px;margin-left:8px}
"""

COPY_JS = """
function copyText(id,btn){const t=document.getElementById(id).innerText;
const done=()=>{const s=btn.nextElementSibling;s.textContent='Copied';setTimeout(()=>s.textContent='',1500)};
if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(t).then(done,()=>fb(t,done))}else{fb(t,done)}}
function fb(t,done){const a=document.createElement('textarea');a.value=t;a.style.position='fixed';a.style.opacity='0';
document.body.appendChild(a);a.select();try{document.execCommand('copy');done()}catch(e){}a.remove()}
"""


def sparkline(closes: list[float], stop: float, limit: float) -> str:
    if len(closes) < 2:
        return ""
    W, H, P = 320, 80, 4
    lo = min(min(closes), stop)
    hi = max(max(closes), limit)
    span = (hi - lo) or 1

    def Y(v):
        return P + (H - 2 * P) * (1 - (v - lo) / span)

    n = len(closes)
    pts = " ".join(f"{P + (W - 2 * P) * k / (n - 1):.1f},{Y(v):.1f}" for k, v in enumerate(closes))
    return (f'<svg class="spark" viewBox="0 0 {W} {H}" role="img" aria-label="Last {n} sessions">'
            f'<line x1="{P}" x2="{W - P}" y1="{Y(stop):.1f}" y2="{Y(stop):.1f}" stroke="#ff5d5d" '
            f'stroke-dasharray="4 3" stroke-width="1"/>'
            f'<line x1="{P}" x2="{W - P}" y1="{Y(limit):.1f}" y2="{Y(limit):.1f}" stroke="#6aa8ff" '
            f'stroke-dasharray="4 3" stroke-width="1"/>'
            f'<polyline points="{pts}" fill="none" stroke="#e7e9ee" stroke-width="1.5"/></svg>'
            f'<div class="legend"><span><i style="background:#e7e9ee"></i>last {n} sessions</span>'
            f'<span><i style="background:#6aa8ff"></i>buy limit</span>'
            f'<span><i style="background:#ff5d5d"></i>stop loss</span></div>')


def _badge(text: str, colour: str) -> str:
    return f'<span class="badge {colour}">{esc(text)}</span>'


def pick_card(pk: Pick, k: int, cfg: dict) -> str:
    fund_colour = {"PASS": "green", "FAIL": "red"}.get(pk.fund.status, "amber")
    res_colour = {"avoid": "red", "ok": "green"}.get(pk.results_level, "amber")
    checks = "".join(f'<li class="{"ok" if ok else "no"}">{"✓" if ok else "✗"} {esc(n)}</li>'
                     for n, ok in pk.filters)
    fund_checks = "".join(f'<li class="{"ok" if ok else "no"}">{"✓" if ok else "✗"} {esc(n)}</li>'
                          for n, ok in pk.fund.checks)
    target_cell = (f'<div><div class="l">Target</div><div class="v">{inr(pk.target, 2)}</div></div>'
                   if pk.target else
                   '<div><div class="l">Target</div><div class="v" style="font-size:14px">sell at a check-in</div></div>')
    return f"""
<div class="pick">
  <div class="head"><div><span class="sym">{esc(pk.symbol)}</span> <span class="co">{esc(pk.company)}</span></div>
  <span class="badge green">Rank {pk.rank}</span></div>
  <div class="big3">
    <div><div class="l">Buy (shares)</div><div class="v blue">{pk.qty}</div></div>
    <div><div class="l">Limit price</div><div class="v blue">{inr(pk.limit, 2)}</div></div>
    <div><div class="l">Stop loss</div><div class="v red">{inr(pk.stop, 2)}</div></div>
    <div><div class="l">Amount</div><div class="v">{inr(pk.position_value)}</div></div>
    <div><div class="l">Loss if stop hit</div><div class="v red">{inr(-pk.risk_inr)}</div></div>
    {target_cell}
  </div>
  <div class="flags">{_badge(pk.results_text, res_colour)} {_badge("Quality: " + pk.fund.status, fund_colour)}</div>
  {sparkline(pk.closes, pk.stop, pk.limit)}
  <pre class="order" id="o{k}">{esc(pk.order_text)}</pre>
  <button onclick="copyText('o{k}',this)">Copy order</button><span class="copied"></span>
  <details><summary>Details</summary>
    <div class="kv small" style="margin-top:8px">
      <div><span>Last close</span><span>{inr(pk.last_close, 2)}</span></div>
      <div><span>Stop distance</span><span>{pct(pk.stop_pct)}</span></div>
      <div><span>Momentum percentile</span><span>{pk.rs_pct:.0f}</span></div>
      <div><span>Round-trip charges (est.)</span><span>{inr(pk.round_trip_cost)}</span></div>
      <div><span>Industry</span><span>{esc(pk.industry)}</span></div>
      <div><span>GTT stop limit</span><span>{inr(pk.gtt_stop_limit, 2)}</span></div>
    </div>
    <ul class="chk">{checks}</ul>
    <div class="small muted">{esc(pk.fund.summary)}</div><ul class="chk">{fund_checks}</ul>
  </details>
</div>"""


def holding_card(h: HoldingCheck) -> str:
    colour = {"red": "red", "green": "green"}.get(h.level, "amber")
    pnl = "" if h.pnl_inr != h.pnl_inr else (
        f'<span class="{"pos" if h.pnl_inr >= 0 else "neg"}">{inr(h.pnl_inr)} ({pct(h.pnl_pct, signed=True)})</span>')
    return f"""
<div class="pick">
  <div class="head"><div><span class="sym">{esc(h.symbol)}</span>
  <span class="co">{h.qty} shares bought at {inr(h.buy_price, 2)}{f" on {h.buy_date:%d %b %Y}" if h.buy_date else ""}</span></div>
  <span class="badge {colour}">{esc(h.action)}</span></div>
  <p style="margin:8px 0">{esc(h.detail)}</p>
  <div class="kv small">
    <div><span>Last close</span><span>{inr(h.last_close, 2) if h.last_close == h.last_close else "N/A"}</span></div>
    <div><span>Profit / loss</span>{pnl or "<span>N/A</span>"}</div>
    <div><span>Stop loss (GTT)</span><span>{inr(h.stop, 2) if h.stop == h.stop else "not set"}</span></div>
    <div><span>Sessions held</span><span>{h.sessions}</span></div>
  </div>
</div>"""


def build_report_html(ctx: dict, cfg: dict) -> str:
    st = ctx["backtest_status"]
    data_day: date = ctx["data_date"]
    checkin_day: date = ctx["next_checkin"]
    tomorrow_checkin: bool = ctx["checkin_next"]
    regime_on: bool = ctx["regime_on"]
    picks: list[Pick] = ctx["picks"]
    holdings: list[HoldingCheck] = ctx["holdings"]

    badges = [_badge("Market filter ON" if regime_on else "Market filter OFF", "green" if regime_on else "red")]
    if st is None:
        badges.append(_badge("Backtest not run yet", "amber"))
    elif st["passed"]:
        badges.append(_badge(f"Backtest PASSED: {inr(st['oos_expectancy_inr'])} per trade after costs (2021+)", "green"))
    else:
        badges.append(_badge(f"Backtest FAILED: {inr(st['oos_expectancy_inr'])} per trade after costs (2021+)", "red"))

    banners = []
    if st is not None and not st["passed"]:
        banners.append(f'<div class="banner red"><span class="big">{FAILED_BANNER}</span>'
                       f'<p>The backtest shows no edge after costs on 2021+ data '
                       f'({esc("; ".join(st.get("reasons", [])))}). Do not trade these picks with real money.</p></div>')
    elif st is None:
        banners.append('<div class="banner amber"><span class="big">Backtest not run</span>'
                       '<p>Run <b>python backtest.py</b> first, so you know whether this method has an edge.</p></div>')
    if not regime_on:
        banners.append('<div class="banner red"><span class="big">Market filter OFF: no new buys, stay in cash</span>'
                       '<p>The Nifty 50 is not in an uptrend. At the next check-in, sell all holdings '
                       'and keep the money in cash until the filter turns ON again.</p></div>')

    sells = [h for h in holdings if h.action == "SELL"]
    raises = [h for h in holdings if h.new_stop]
    if tomorrow_checkin:
        steps = []
        if sells:
            steps.append("<li><b>Sell</b> at the open: " + ", ".join(esc(h.symbol) for h in sells)
                         + ". Cancel their GTT orders.</li>")
        if raises:
            steps.append("<li><b>Raise the GTT stop loss</b>: " + ", ".join(
                f"{esc(h.symbol)} to {inr(h.new_stop, 2)}" for h in raises) + ".</li>")
        if regime_on and picks:
            steps.append(f"<li><b>Buy</b> {len(picks)} stock{'s' if len(picks) > 1 else ''} with the limit orders "
                         "below: " + ", ".join(f"{esc(p.symbol)} ({p.qty} shares)" for p in picks) + ".</li>")
            steps.append("<li>After each buy fills, <b>set its GTT stop loss</b> (in the order text) and add "
                         "the trade to <b>data/open_trades.csv</b>.</li>")
        if not steps:
            steps.append("<li>Nothing to buy or sell. Your holdings stay as they are.</li>")
        todo = (f'<div class="todo"><h2>Check-in on {checkin_day:%A %d %b}: before 9:15 am</h2>'
                f'<ol>{"".join(steps)}</ol></div>')
    else:
        todo = (f'<div class="todo"><h2>No action needed today</h2>'
                f'<p style="margin:0">Next check-in: <b>{checkin_day:%A %d %b %Y}</b>. Run this report again '
                f'the evening before. Your GTT stop losses work on their own until then.</p>'
                + ('<p class="small muted" style="margin:8px 0 0">The list below is a preview of what the '
                   'check-in would buy if it were tomorrow. Starting fresh? Wait for the check-in.</p>'
                   if regime_on else "") + '</div>')

    pick_title = "Buy list" if tomorrow_checkin else "Preview: buy list"
    if not regime_on:
        pick_html = "<p>No buys while the market filter is OFF.</p>"
        watch = ctx.get("watch_when_off", [])
        if watch:
            pick_html += ('<p class="small muted">Strongest stocks right now (watch only): '
                          + ", ".join(esc(s) for s in watch) + "</p>")
    elif picks:
        pick_html = "".join(pick_card(pk, k, cfg) for k, pk in enumerate(picks))
    else:
        pick_html = "<p>No free slots or no qualifying stocks.</p>"

    hold_html = ("".join(holding_card(h) for h in holdings) if holdings else
                 '<p class="small muted">No holdings recorded. After you buy, add a row to '
                 '<b>data/open_trades.csv</b>: <code>symbol,buy_date,buy_price,qty,stop_loss</code>, for '
                 'example <code>TCS,17-11-2026,3450.50,5,2933.00</code>.</p>')

    nxt = ctx.get("next_in_line", [])
    nxt_html = ""
    if nxt and regime_on:
        rows = "".join(f"<tr><td>{r}</td><td>{esc(s)}</td><td>{inr(c, 2)}</td><td>{rp:.0f}</td>"
                       f"<td>{esc(fs)}</td></tr>" for r, s, c, rp, fs in nxt)
        nxt_html = ('<h2>Next in line</h2><p class="small muted">If a pick above is flagged (results soon, '
                    'quality fail) and you skip it, these come next.</p><div class="scroll"><table><thead><tr>'
                    '<th>Rank</th><th>Stock</th><th>Last close</th><th>Momentum pct</th><th>Quality</th>'
                    f'</tr></thead><tbody>{rows}</tbody></table></div>')

    skipped = ctx.get("skipped_quality", [])
    skip_html = ""
    if skipped:
        skip_html = ('<h2>Skipped</h2><ul class="small">' + "".join(
            f"<li>{esc(s)}: {esc(why)}</li>" for s, why in skipped) + "</ul>")

    notes = [esc(n) for n in ctx.get("notes", [])]
    notes.append("The backtest uses today's Nifty 100 members for all years (survivorship bias), so real "
                 "results are likely worse than the backtest.")
    notes_html = '<h2>Data notes</h2><ul class="small muted">' + "".join(f"<li>{n}</li>" for n in notes) + "</ul>"

    body = f"""
<h1>Check-in report</h1>
<div class="muted small">Prices up to the close of {data_day:%A %d %b %Y}. Generated {ctx["generated"]:%d %b %Y %H:%M} IST.</div>
<div class="top">{" ".join(badges)}</div>
{"".join(banners)}
{todo}
<h2>{pick_title}</h2>
{pick_html}
<h2>Your holdings</h2>
{hold_html}
{nxt_html}
{skip_html}
{notes_html}
"""
    html = page("Check-in report", body, COPY_JS)
    return html.replace("</style>", SCAN_CSS + "</style>", 1)


def candidates_json(ctx: dict) -> str:
    def pick(pk: Pick) -> dict:
        return {"symbol": pk.symbol, "company": pk.company, "rank": pk.rank, "qty": pk.qty,
                "limit_price": pk.limit, "stop_loss": pk.stop, "gtt_stop_limit": pk.gtt_stop_limit,
                "target": pk.target, "last_close": pk.last_close, "position_value": round(pk.position_value, 2),
                "loss_if_stopped": round(pk.risk_inr, 2), "round_trip_cost": round(pk.round_trip_cost, 2),
                "momentum_percentile": round(pk.rs_pct, 1), "fundamentals": pk.fund.status,
                "fundamentals_summary": pk.fund.summary, "results": pk.results_text,
                "filters": {n: ok for n, ok in pk.filters}}

    def hold(h: HoldingCheck) -> dict:
        return {"symbol": h.symbol, "action": h.action, "detail": h.detail, "last_close": h.last_close,
                "pnl": None if h.pnl_inr != h.pnl_inr else round(h.pnl_inr, 2), "new_stop": h.new_stop}

    st = ctx["backtest_status"]
    return json.dumps({
        "data_date": f"{ctx['data_date']:%Y-%m-%d}", "next_checkin": f"{ctx['next_checkin']:%Y-%m-%d}",
        "checkin_next_session": ctx["checkin_next"], "market_filter_on": ctx["regime_on"],
        "backtest_passed": None if st is None else st["passed"],
        "picks": [pick(p) for p in ctx["picks"]] if ctx["regime_on"] else [],
        "holdings": [hold(h) for h in ctx["holdings"]],
        "next_in_line": [{"rank": r, "symbol": s} for r, s, *_ in ctx.get("next_in_line", [])],
        "notes": ctx.get("notes", []),
    }, indent=2, default=str)
