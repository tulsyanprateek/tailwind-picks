"""Build output/report.html: the check-in report."""
from __future__ import annotations

import json
from datetime import date

from .checkin import HoldingCheck, Pick
from .html_common import esc, page
from .utils import inr, pct

FAILED_BANNER = "STRATEGY FAILED OUT OF SAMPLE"

SCAN_CSS = """
.hero{position:relative;border-radius:22px;padding:22px 20px 18px;margin:4px 0 16px;overflow:hidden;
background:linear-gradient(160deg,rgba(255,255,255,.07),rgba(255,255,255,.02));border:1px solid var(--line)}
.hero:before{content:"";position:absolute;inset:0;border-radius:22px;padding:1px;pointer-events:none;
background:linear-gradient(135deg,var(--accent,#60a5fa),transparent 55%);
-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude}
.hero.green{--accent:#34d399}.hero.red{--accent:#fb7185}.hero.blue{--accent:#60a5fa}
.eyebrow{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:600}
.headline{font-size:clamp(30px,8vw,44px);line-height:1.05;margin:8px 0 8px;font-weight:800;letter-spacing:-.03em;
background:linear-gradient(90deg,#fff,var(--accent,#60a5fa));-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{margin:0 0 10px;color:#d6dbe6;font-size:16px}
.steps{margin:8px 0 12px;padding-left:22px}.steps li{margin:6px 0;font-weight:600}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px}
.chip{display:inline-flex;align-items:center;gap:6px;font-size:13px;padding:6px 11px;border-radius:999px;
background:rgba(255,255,255,.06);border:1px solid var(--line);color:#dfe4ee}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block}.dot.g{background:var(--green);box-shadow:0 0 10px var(--green)}
.dot.r{background:var(--red);box-shadow:0 0 10px var(--red)}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
@media(max-width:560px){.tiles{grid-template-columns:1fr 1fr}.tiles .tile:first-child{grid-column:1/-1}}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:12px 14px}
.tl{font-size:12px;color:var(--muted)}.tv{font-size:24px;font-weight:800;letter-spacing:-.02em;margin:2px 0}
.tv.green{color:var(--green)}.tv.red{color:var(--red)}.tv.amber{color:var(--amber)}.tn{font-size:12px;color:var(--muted)}
.more{display:inline-block;margin:10px 2px 0;color:var(--blue);text-decoration:none;font-size:14px;font-weight:600}
h2.sec{font-size:13px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);margin:30px 0 10px}
.ranks{display:flex;flex-wrap:wrap;gap:8px}
.rank{display:inline-flex;align-items:center;gap:8px;padding:7px 12px 7px 7px;border-radius:12px;
background:var(--panel);border:1px solid var(--line);font-weight:600;font-size:14px}
.rank b{display:inline-grid;place-items:center;width:24px;height:24px;border-radius:8px;font-size:12px;
background:linear-gradient(135deg,var(--blue),var(--violet));color:#0b1020}
.how{display:grid;gap:8px}
.how div{display:flex;gap:12px;align-items:flex-start;background:var(--panel);border:1px solid var(--line);
border-radius:14px;padding:12px 14px}
.how b{flex:none;display:grid;place-items:center;width:28px;height:28px;border-radius:50%;
background:rgba(96,165,250,.15);color:var(--blue)}
.notes{margin-top:22px}.notes summary{cursor:pointer;color:var(--muted);font-size:13px}
.pick{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:16px;margin:12px 0}
.pick .head{display:flex;justify-content:space-between;align-items:baseline;gap:8px;flex-wrap:wrap}
.pick .sym{font-size:22px;font-weight:800;letter-spacing:-.02em}.pick .co{color:var(--muted);font-size:13px}
.big3{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:12px 0}
.big3 div{background:rgba(255,255,255,.04);border-radius:12px;padding:9px 11px}
.big3 .l{font-size:12px;color:var(--muted)}.big3 .v{font-size:18px;font-weight:800}
.big3 .v.red{color:var(--red)}.big3 .v.blue{color:var(--blue)}
@media(max-width:380px){.big3{grid-template-columns:1fr 1fr}}
.flags{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.chk{list-style:none;padding:0;margin:6px 0;font-size:13px}.chk li{margin:2px 0}
.ok{color:var(--green)}.no{color:var(--red)}
pre.order{background:rgba(0,0,0,.35);border:1px solid var(--line);border-radius:12px;padding:12px;font-size:12.5px;
white-space:pre-wrap;word-break:break-word;margin:10px 0}
details{margin:8px 0}summary{cursor:pointer;color:var(--muted);font-size:13px}
.spark{display:block;width:100%;height:auto;margin:6px 0}
.copied{color:var(--green);font-size:13px;margin-left:8px}
.why{margin:12px 0 6px;padding:12px 14px;border-radius:14px;background:rgba(96,165,250,.06);border:1px solid rgba(96,165,250,.18)}
.why-h{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--blue);font-weight:700;margin:2px 0 6px}
.why .why-h+ul{margin-top:0}.reasons{margin:0 0 10px;padding-left:18px}.reasons li{margin:4px 0}
.meta{font-size:13px;color:#cfd6e4;font-weight:600;margin-bottom:4px}
.about{margin:0 0 10px;font-size:14px;color:#c4cbd8}.src{font-size:11px;color:var(--muted)}
.risk{font-size:13px;color:#fde68a;background:rgba(251,191,36,.08);border-radius:10px;padding:8px 10px}
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


def why_block(w) -> str:
    if w is None:
        return ""
    about = ""
    if w.meta or w.about:
        about = (f'<div class="why-h">About the business</div>'
                 + (f'<div class="meta">{esc(w.meta)}</div>' if w.meta else "")
                 + (f'<p class="about">{esc(w.about)} <span class="src">Source: Yahoo Finance</span></p>' if w.about else ""))
    return (f'<div class="why"><div class="why-h">Why this stock</div><ul class="reasons">'
            + "".join(f"<li>{esc(r)}</li>" for r in w.reasons) + "</ul>"
            + about + f'<div class="risk">{esc(w.risk)}</div></div>')


def watch_card(w) -> str:
    return (f'<div class="pick"><div class="head"><div><span class="sym">{esc(w.symbol)}</span> '
            f'<span class="co">{esc(w.company)}</span></div><span class="badge amber">Watch #{w.rank}</span></div>'
            f'{why_block(w)}</div>')


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
  {why_block(pk.why)}
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

    failed = st is not None and not st["passed"]
    sells = [h for h in holdings if h.action == "SELL"]
    raises = [h for h in holdings if h.new_stop]
    keep_n = cfg["portfolio"]["keep_if_rank_within"]

    # ---- hero: the one thing to know today
    steps: list[str] = []
    if failed:
        headline, tone = "Do not trade this", "red"
        sub = "The 12-year test shows no edge after costs since 2021. The picks below are for information only."
    elif not regime_on:
        headline, tone = "Stay in cash", "red"
        sub = ("The Nifty 50 is not in an uptrend (market filter OFF: no new trades). "
               + ("At tomorrow's check-in, sell everything you hold." if tomorrow_checkin else
                  f"No new buys. If it is still OFF on {checkin_day:%a %d %b}, sell everything then."))
    elif tomorrow_checkin:
        headline, tone = "Check-in tomorrow", "blue"
        sub = f"Before 9:15 am on {checkin_day:%A %d %b}:"
        if sells:
            steps.append("Sell " + ", ".join(esc(h.symbol) for h in sells) + " at the open and cancel their GTT.")
        if raises:
            steps.append("Raise the stop loss: " + ", ".join(
                f"{esc(h.symbol)} to {inr(h.new_stop, 2)}" for h in raises) + ".")
        if picks:
            steps.append("Buy " + ", ".join(f"{esc(p.symbol)} ({p.qty})" for p in picks)
                         + " with the limit orders below.")
            steps.append("After each buy fills, set its GTT stop loss (in the order text).")
        if not holdings:
            steps.append(f"Sell anything you hold that is not in the Top {keep_n} below.")
        if not steps:
            steps.append("Nothing to change.")
    else:
        headline, tone = "No action today", "green"
        sub = f"Next check-in is {checkin_day:%A %d %b}. Stop losses on Kite work on their own until then."
    steps_html = ('<ol class="steps">' + "".join(f"<li>{x}</li>" for x in steps) + "</ol>") if steps else ""

    chips = [f'<span class="chip"><i class="dot {"g" if regime_on else "r"}"></i>Market {"ON" if regime_on else "OFF"}</span>',
             f'<span class="chip">Next check-in <b>{checkin_day:%a %d %b}</b></span>',
             f'<span class="chip">Prices to {data_day:%a %d %b}</span>']
    hero = (f'<header class="hero {tone}"><div class="eyebrow">Nifty 100 Momentum &middot; Check-in report</div>'
            f'<h1 class="headline">{headline}</h1><p class="sub">{sub}</p>{steps_html}'
            f'<div class="chips">{"".join(chips)}</div></header>')

    # ---- proof tiles from the 12-year test
    if st is None:
        tiles = ('<div class="tile"><div class="tl">12-year test</div><div class="tv amber">Not run</div>'
                 '<div class="tn">Run python backtest.py</div></div>')
    else:
        tiles = (f'<div class="tile"><div class="tl">12-year test</div>'
                 f'<div class="tv {"red" if failed else "green"}">{"FAILED" if failed else "PASSED"}</div>'
                 f'<div class="tn">{inr(st["oos_expectancy_inr"])} per trade after costs</div></div>'
                 f'<div class="tile"><div class="tl">Yearly return since 2021</div>'
                 f'<div class="tv">{pct(st.get("oos_cagr"), signed=True)}</div>'
                 f'<div class="tn">Nifty 50: {pct(st.get("nifty_oos_cagr"), signed=True)}</div></div>'
                 f'<div class="tile"><div class="tl">Worst fall since 2021</div>'
                 f'<div class="tv red">{pct(st.get("oos_max_dd_pct"))}</div>'
                 f'<div class="tn">Nifty 50: {pct(st.get("nifty_oos_max_dd_pct"))}</div></div>')
    tiles_html = (f'<div class="tiles">{tiles}</div>'
                  '<a class="more" href="backtest.html">See the full 12-year test &rarr;</a>')

    banner = ""
    if failed:
        banner = (f'<div class="banner red"><span class="big">{FAILED_BANNER}</span>'
                  f'<p>{esc("; ".join(st.get("reasons", [])))}. Do not trade these picks with real money.</p></div>')

    # ---- buy list
    if not regime_on:
        watch = ctx.get("watch_when_off", [])
        pick_title = "Watch list"
        pick_html = '<p class="muted">No buys while the market filter is OFF.</p>'
        watch_why = ctx.get("watch_why") or []
        if watch_why:
            pick_html += ('<p class="small muted">The strongest stocks right now, to watch only. '
                          'Do not buy until the market filter is ON.</p>' + "".join(watch_card(w) for w in watch_why))
        elif watch:
            pick_html += ('<div class="ranks">' + "".join(f'<span class="rank"><b>{k}</b>{esc(s)}</span>'
                                                      for k, s in enumerate(watch, 1)) + "</div>"
                          '<p class="small muted">Strongest stocks right now, to watch only.</p>')
    else:
        pick_title = "Buy list" if tomorrow_checkin else "Buy list (preview)"
        pick_html = ("".join(pick_card(pk, k, cfg) for k, pk in enumerate(picks)) if picks
                     else '<p class="muted">No free slots or no qualifying stocks.</p>')
        if picks and not tomorrow_checkin:
            pick_html = ('<p class="small muted">What the check-in would buy if it were tomorrow. '
                         'Starting fresh? Wait for the check-in.</p>') + pick_html

    # ---- top list and holdings
    top = ctx.get("top_list", [])
    top_html = ""
    if top and regime_on:
        top_html = (f'<h2 class="sec">Top {keep_n} right now</h2><div class="ranks">'
                    + "".join(f'<span class="rank"><b>{r}</b>{esc(s)}</span>' for r, s in top) + "</div>"
                    '<p class="small muted">On a check-in day, keep what you hold if it is in this list '
                    'and sell it if not.</p>')
    hold_html = ('<h2 class="sec">Your holdings</h2>' + "".join(holding_card(h) for h in holdings)) if holdings else ""

    nxt = ctx.get("next_in_line", [])
    nxt_html = ""
    if nxt and regime_on:
        rows = "".join(f"<tr><td>{r}</td><td>{esc(s)}</td><td>{inr(c, 2)}</td><td>{rp:.0f}</td>"
                       f"<td>{esc(fs)}</td></tr>" for r, s, c, rp, fs in nxt)
        nxt_html = ('<h2 class="sec">Next in line</h2><p class="small muted">If you skip a pick (results soon, '
                    'quality fail), use these in order.</p><div class="scroll"><table><thead><tr>'
                    '<th>Rank</th><th>Stock</th><th>Last close</th><th>Momentum</th><th>Quality</th>'
                    f'</tr></thead><tbody>{rows}</tbody></table></div>')

    skipped = ctx.get("skipped_quality", [])
    skip_html = ""
    if skipped:
        skip_html = ('<h2 class="sec">Skipped</h2><ul class="small muted">' + "".join(
            f"<li>{esc(s)}: {esc(why)}</li>" for s, why in skipped) + "</ul>")

    p_ = cfg["portfolio"]
    stop_txt = (f"{cfg['trade']['stop_pct']:g}% below the buy price"
                if cfg["trade"].get("stop_mode") == "percent" else "2 x the daily range below the buy price")
    how = ('<h2 class="sec">How it works</h2><div class="how">'
           f'<div><b>1</b><span>Twice a month (1st and 15th), pick the {p_["holdings"]} Nifty 100 stocks that '
           'have risen the most over the last year and are still in a steady uptrend.</span></div>'
           '<div><b>2</b><span>Only when the Nifty 50 itself is rising. When it is not, sell and wait in cash.</span></div>'
           f'<div><b>3</b><span>Put equal money in each, with a safety-net stop loss {stop_txt}.</span></div>'
           f'<div><b>4</b><span>At the next check-in, keep what is still in the Top {keep_n} and replace the rest.</span></div>'
           '</div><p class="small muted">Losing trades are normal: in the test, fewer than half the trades made '
           'money. It worked because the winners were much bigger than the losers. Nothing here is guaranteed.</p>')

    notes = [esc(n) for n in ctx.get("notes", [])]
    notes.append("The 12-year test uses today's Nifty 100 members for all years (survivorship bias), so real "
                 "results are likely worse than the test.")
    notes_html = ('<details class="notes"><summary>Data notes</summary><ul class="small muted">'
                  + "".join(f"<li>{n}</li>" for n in notes) + "</ul></details>")

    body = f"""
{hero}
{banner}
{tiles_html}
<h2 class="sec">{pick_title}</h2>
{pick_html}
{top_html}
{hold_html}
{nxt_html}
{skip_html}
{how}
{notes_html}
<div class="small muted" style="margin-top:14px">Updated {ctx["generated"]:%d %b %Y, %I:%M %p} IST</div>
"""
    html = page("Check-in report", body, COPY_JS)
    return html.replace("</style>", SCAN_CSS + "</style>", 1)


def phone_message(ctx: dict) -> str:
    """Short plain-text summary for Telegram."""
    st = ctx["backtest_status"]
    lines = [f"Stock check, prices to {ctx['data_date']:%a %d %b}"]
    if st is not None and not st["passed"]:
        lines.append("WARNING: STRATEGY FAILED OUT OF SAMPLE. Do not trade it.")
    lines.append("Market: " + ("ON" if ctx["regime_on"] else "OFF, stay in cash"))
    stops = [h for h in ctx["holdings"] if h.action == "STOP HIT"]
    for h in stops:
        lines.append(f"Stop loss hit: {h.symbol}. Check Kite sold it, then remove it from open_trades.csv.")
    if ctx["checkin_next"]:
        lines.append(f"CHECK-IN tomorrow ({ctx['next_checkin']:%a %d %b}), before 9:15 am:")
        acts = 0
        for h in ctx["holdings"]:
            if h.action == "SELL":
                lines.append(f"  SELL {h.symbol} {h.qty} at open, cancel its GTT")
                acts += 1
            elif h.new_stop:
                lines.append(f"  RAISE stop {h.symbol} to {h.new_stop:.2f}")
                acts += 1
        if ctx["regime_on"]:
            for p in ctx["picks"]:
                lines.append(f"  BUY {p.symbol} {p.qty} @ limit {p.limit:.2f}, then GTT stop {p.stop:.2f}")
                acts += 1
        if not acts:
            lines.append("  Nothing to change.")
    elif not stops:
        lines.append(f"No action. Next check-in {ctx['next_checkin']:%a %d %b}.")
    for n in ctx.get("phone_notes", []):
        lines.append(n)
    return "\n".join(lines)


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
