"""Build the check-in web page (report.html / index.html)."""
from __future__ import annotations

import json
import math
from datetime import date

from .charts import CHART_JS, LIB_URL
from .checkin import HoldingCheck, Pick, Why
from .html_common import esc, page
from .utils import inr, pct

FAILED_BANNER = "STRATEGY FAILED OUT OF SAMPLE"

SCAN_CSS = """
.hero{position:relative;border-radius:22px;padding:20px 18px 16px;margin:0 0 14px;overflow:hidden;
background:linear-gradient(160deg,rgba(255,255,255,.07),rgba(255,255,255,.02));border:1px solid var(--line)}
.hero:before{content:"";position:absolute;inset:0;border-radius:22px;padding:1px;pointer-events:none;
background:linear-gradient(135deg,var(--accent,#60a5fa),transparent 55%);
-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude}
.hero.green{--accent:#34d399}.hero.red{--accent:#fb7185}.hero.blue{--accent:#60a5fa}
.headline{font-size:clamp(32px,9vw,46px);line-height:1.05;margin:2px 0 8px;font-weight:800;letter-spacing:-.03em;
background:linear-gradient(90deg,#fff,var(--accent,#60a5fa));-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{margin:0 0 10px;color:#d6dbe6;font-size:16px}
.steps{margin:8px 0 12px;padding-left:22px}.steps li{margin:6px 0;font-weight:600}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px}
.chip{display:inline-flex;align-items:center;gap:6px;font-size:13px;padding:6px 11px;border-radius:999px;
background:rgba(255,255,255,.06);border:1px solid var(--line);color:#dfe4ee}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block}.dot.g{background:var(--green);box-shadow:0 0 10px var(--green)}
.dot.r{background:var(--red);box-shadow:0 0 10px var(--red)}
h2.sec{font-size:13px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);margin:28px 0 10px;display:flex;
align-items:center;gap:8px}h2.sec:after{content:"";flex:1;height:1px;background:var(--line)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:14px}
.chart{height:240px;margin:8px -4px 0}.chart.sm{height:110px}.chart.eq{height:220px}
.nochart{display:grid;place-items:center;height:100%;color:var(--muted);font-size:13px}
.lg{display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:var(--muted);margin-top:6px}
.lg i{display:inline-block;width:14px;height:3px;border-radius:2px;vertical-align:middle;margin-right:5px}
.say{font-size:15px;font-weight:600;margin:0 0 4px}.say .pos{color:var(--green)}.say .neg{color:var(--red)}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:10px}
.tile{background:rgba(255,255,255,.03);border:1px solid var(--line);border-radius:14px;padding:10px 12px}
.tl{font-size:11.5px;color:var(--muted)}.tv{font-size:22px;font-weight:800;letter-spacing:-.02em}
.tv.green{color:var(--green)}.tv.red{color:var(--red)}.tv.amber{color:var(--amber)}.tn{font-size:11.5px;color:var(--muted)}
@media(max-width:420px){.tiles{grid-template-columns:1fr 1fr}.tiles .tile:first-child{grid-column:1/-1}}
.more{display:inline-block;margin-top:8px;color:var(--blue);text-decoration:none;font-size:14px;font-weight:600}
.stock{background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:16px;margin:12px 0}
.shead{display:flex;align-items:center;gap:12px}
.clogo{position:relative;flex:none;width:46px;height:46px;border-radius:14px;background:#fff;display:grid;place-items:center;
overflow:hidden;font-weight:800;color:#0b1020;font-size:15px}
.clogo img{position:absolute;inset:7px;width:32px;height:32px;object-fit:contain}
.sname{flex:1;min-width:0}.sym{font-size:20px;font-weight:800;letter-spacing:-.02em;line-height:1.1}
.co{color:var(--muted);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rankb{flex:none;font-weight:800;font-size:13px;padding:5px 10px;border-radius:10px;
background:linear-gradient(135deg,var(--blue),var(--violet));color:#0b1020}
.rankb.watch{background:rgba(251,191,36,.15);color:var(--amber)}
.brands{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0 2px}
.brands span{font-size:12.5px;font-weight:600;padding:5px 10px;border-radius:999px;background:rgba(167,139,250,.12);
color:#d9d0ff;border:1px solid rgba(167,139,250,.22)}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:12px 0 0}
.kpis div{background:rgba(255,255,255,.04);border-radius:12px;padding:8px;text-align:center}
.kpis b{display:block;font-size:17px;font-weight:800}.kpis span{font-size:11px;color:var(--muted)}
.one{margin:10px 0 0;font-weight:600}
.buybox{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:12px 0}
.buybox div{background:rgba(96,165,250,.08);border:1px solid rgba(96,165,250,.18);border-radius:12px;padding:8px 10px}
.buybox .l{font-size:11px;color:var(--muted)}.buybox .v{font-size:17px;font-weight:800}.buybox .v.red{color:var(--red)}
pre.order{background:rgba(0,0,0,.35);border:1px solid var(--line);border-radius:12px;padding:12px;font-size:12.5px;
white-space:pre-wrap;word-break:break-word;margin:10px 0}
details{margin:10px 0 0}summary{cursor:pointer;color:var(--blue);font-size:13.5px;font-weight:600}
.about{font-size:13.5px;color:#c4cbd8;margin:8px 0}.meta{font-size:12.5px;color:var(--muted)}
.risk{font-size:12.5px;color:#fde68a;background:rgba(251,191,36,.08);border-radius:10px;padding:8px 10px;margin-top:8px}
.ranks{display:flex;flex-wrap:wrap;gap:8px}
.rank{display:inline-flex;align-items:center;gap:8px;padding:6px 11px 6px 6px;border-radius:12px;
background:var(--panel);border:1px solid var(--line);font-weight:600;font-size:13.5px}
.rank b{display:inline-grid;place-items:center;width:22px;height:22px;border-radius:7px;font-size:11.5px;
background:linear-gradient(135deg,var(--blue),var(--violet));color:#0b1020}
.how{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.how div{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px;font-size:13.5px}
.how b{display:block;font-size:20px;margin-bottom:2px}
.copied{color:var(--green);font-size:13px;margin-left:8px}
.notes{margin-top:22px}.notes summary{color:var(--muted)}
.verdict{display:flex;align-items:center;gap:10px;margin:12px 0 4px;padding:10px 12px;border-radius:14px;border:1px solid var(--line)}
.verdict b{font-size:20px;font-weight:900;letter-spacing:.02em}.verdict span{font-size:13px;color:var(--muted)}
.verdict.BUY{background:rgba(52,211,153,.10);border-color:rgba(52,211,153,.35)}.verdict.BUY b{color:var(--green)}
.verdict.HOLD{background:rgba(251,191,36,.10);border-color:rgba(251,191,36,.35)}.verdict.HOLD b{color:var(--amber)}
.verdict.SELL{background:rgba(251,113,133,.10);border-color:rgba(251,113,133,.35)}.verdict.SELL b{color:var(--red)}
.verdict.WAIT{background:rgba(148,163,184,.10);border-color:rgba(148,163,184,.35)}.verdict.WAIT b{color:#cbd5e1}
.plan{margin:12px 0;padding:12px;border-radius:14px;background:rgba(96,165,250,.06);border:1px solid rgba(96,165,250,.18)}
.ph{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--blue);font-weight:700;margin-bottom:8px}
.pgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.pgrid .l{font-size:11.5px;color:var(--muted)}.pgrid .v{font-size:17px;font-weight:800}.pgrid .s{font-size:11px;color:var(--muted)}
.v.blue{color:var(--blue)}.v.red{color:var(--red)}.v.green{color:var(--green)}
@media(max-width:400px){.pgrid{grid-template-columns:1fr 1fr}}
.rules{margin:0;padding-left:18px;font-size:13.5px}.rules li{margin:4px 0}
.sigt{width:100%;margin-top:8px;font-size:13px}.sigt th{background:transparent;position:static}
.sigt td{white-space:normal;vertical-align:top}.sigt td:nth-child(2){white-space:nowrap}
.hint{font-size:11px;color:var(--muted)}
.sig{display:inline-block;min-width:52px;text-align:center;font-size:11.5px;font-weight:800;padding:3px 8px;border-radius:8px}
.sig.BUY{background:rgba(52,211,153,.15);color:var(--green)}.sig.HOLD{background:rgba(251,191,36,.15);color:var(--amber)}
.sig.SELL{background:rgba(251,113,133,.15);color:var(--red)}.sig.WAIT{background:rgba(148,163,184,.15);color:#cbd5e1}
.howlink{display:flex;align-items:center;justify-content:space-between;gap:10px;text-decoration:none;color:var(--text);
background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:14px 16px;margin-top:10px}
.howlink b{font-size:15px}.howlink span{color:var(--blue);font-weight:700}
"""

COPY_JS = """
function copyText(id,btn){const t=document.getElementById(id).innerText;
const done=()=>{const s=btn.nextElementSibling;s.textContent='Copied';setTimeout(()=>s.textContent='',1500)};
if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(t).then(done,()=>fb(t,done))}else{fb(t,done)}}
function fb(t,done){const a=document.createElement('textarea');a.value=t;a.style.position='fixed';a.style.opacity='0';
document.body.appendChild(a);a.select();try{document.execCommand('copy');done()}catch(e){}a.remove()}
"""


def _sgn(v: float) -> str:
    return "N/A" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:+.0f}%"


def _cls(v: float) -> str:
    return "" if v is None or (isinstance(v, float) and math.isnan(v)) else ("pos" if v >= 0 else "neg")


def _logo(w: Why) -> str:
    initials = esc(w.symbol[:2])
    img = (f'<img alt="" loading="lazy" src="https://www.google.com/s2/favicons?domain={esc(w.domain)}&amp;sz=128" '
           f'onerror="this.remove()">') if w.domain else ""
    return f'<span class="clogo">{initials}{img}</span>'


VERDICT = {
    "BUY": ("BUY", "Strong on every check"),
    "HOLD": ("HOLD", "Keep it if you own it"),
    "SELL": ("SELL / AVOID", "One or more checks failed"),
    "WAIT": ("WAIT", "Good stock, weak market"),
}


def signal_table(w: Why) -> str:
    rows = "".join(
        f'<tr><td>{esc(name)}<div class="hint">{esc(hint)}</div></td><td>{esc(reading)}</td>'
        f'<td><span class="sig {esc(sig)}">{esc(sig)}</span></td></tr>'
        for name, reading, sig, hint in w.signals)
    return ('<table class="sigt"><thead><tr><th>Indicator</th><th>Today</th><th>Signal</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>')


def price_box(w: Why, watch: bool) -> str:
    lv = w.levels
    if not lv:
        return ""
    aim = (f'<div><div class="l">Target</div><div class="v green">{inr(lv["aim"], 2)}</div>'
           f'<div class="s">+{lv["aim_pct"]:.0f}% (typical win)</div></div>') if lv.get("aim") else ""
    head = "If the market turns strong" if watch else "Your plan"
    return (f'<div class="plan"><div class="ph">{head}</div><div class="pgrid">'
            f'<div><div class="l">Buy up to</div><div class="v blue">{inr(lv["buy"], 2)}</div>'
            f'<div class="s">{lv["qty"]} share{"" if lv["qty"] == 1 else "s"}, {inr(lv["amount"])}</div></div>'
            f'<div><div class="l">Stop loss</div><div class="v red">{inr(lv["stop"], 2)}</div>'
            f'<div class="s">-{lv["stop_pct"]:.0f}%, sell if it falls here</div></div>'
            f'{aim}</div>'
            '<div class="ph" style="margin-top:12px">Sell when any of these happens</div><ul class="rules">'
            f'<li>Price falls to <b>{inr(lv["stop"], 2)}</b> (stop loss, Kite sells it for you)</li>'
            '<li>It drops out of the <b>Top 10</b> on a check-in day (1st or 15th)</li>'
            '<li>The market turns weak on a check-in day: <b>sell everything</b></li></ul></div>')


def stock_card(w: Why, label: str, watch: bool, extra: str = "") -> str:
    brands = ("<div class=\"brands\">" + "".join(f"<span>{esc(b)}</span>" for b in w.brands) + "</div>") if w.brands else ""
    v_label, v_hint = VERDICT.get(w.overall, (w.overall, ""))
    about = ""
    if w.about or w.meta:
        about = (f'<details><summary>About the business</summary>'
                 + (f'<div class="meta">{esc(w.meta)}</div>' if w.meta else "")
                 + (f'<div class="about">{esc(w.about)} <span class="meta">(Yahoo Finance)</span></div>' if w.about else "")
                 + f'<div class="risk">{esc(w.risk)}</div></details>')
    return f"""
<div class="stock">
  <div class="shead">{_logo(w)}<div class="sname"><div class="sym">{esc(w.symbol)}</div>
  <div class="co">{esc(w.company)}</div></div><span class="rankb{' watch' if watch else ''}">{esc(label)}</span></div>
  {brands}
  <div class="verdict {esc(w.overall)}"><b>{esc(v_label)}</b><span>{esc(v_hint)}</span></div>
  <div class="chart" data-k="{esc(w.symbol)}" data-kind="price"></div>
  <div class="lg"><span><i style="background:#fbbf24"></i>50-day avg</span><span><i style="background:#a78bfa"></i>200-day avg</span>
  <span><i style="background:#60a5fa"></i>Buy up to</span><span><i style="background:#fb7185"></i>Stop loss</span></div>
  {price_box(w, watch)}
  <details open><summary>Signals ({sum(1 for r in w.signals if r[2] == 'BUY')} of {len(w.signals)} say BUY)</summary>{signal_table(w)}
  <div class="tl" style="margin-top:12px">Beating the Nifty? (line above 100 = yes)</div>
  <div class="chart sm" data-k="{esc(w.symbol)}" data-kind="rs"></div></details>
  {extra}
  {about}
</div>"""


def pick_extra(pk: Pick, k: int) -> str:
    flags = []
    if pk.results_level == "avoid":
        flags.append(f'<span class="badge red">{esc(pk.results_text)}</span> ')
    if pk.fund.status == "FAIL":
        flags.append('<span class="badge red">Quality check failed</span>')
    return (''.join(flags)
            + f'<details><summary>Kite order (copy)</summary><pre class="order" id="o{k}">{esc(pk.order_text)}</pre>'
            f'<button onclick="copyText(\'o{k}\',this)">Copy order</button><span class="copied"></span></details>')


def holding_card(h: HoldingCheck) -> str:
    colour = {"red": "red", "green": "green"}.get(h.level, "amber")
    pnl = "N/A" if h.pnl_inr != h.pnl_inr else f'<span class="{_cls(h.pnl_inr)}">{inr(h.pnl_inr)} ({pct(h.pnl_pct, signed=True)})</span>'
    return (f'<div class="stock"><div class="shead"><div class="sname"><div class="sym">{esc(h.symbol)}</div>'
            f'<div class="co">{h.qty} shares at {inr(h.buy_price, 2)}</div></div>'
            f'<span class="badge {colour}">{esc(h.action)}</span></div>'
            f'<p class="one">{esc(h.detail)}</p><div class="small muted">Profit / loss: {pnl}</div></div>')


def build_report_html(ctx: dict, cfg: dict) -> str:
    st = ctx["backtest_status"]
    data_day: date = ctx["data_date"]
    checkin_day: date = ctx["next_checkin"]
    tomorrow: bool = ctx["checkin_next"]
    regime_on: bool = ctx["regime_on"]
    picks: list[Pick] = ctx["picks"]
    holdings: list[HoldingCheck] = ctx["holdings"]
    failed = st is not None and not st["passed"]
    keep_n = cfg["portfolio"]["keep_if_rank_within"]
    brand = (cfg.get("brand", {}).get("name", "Momentum Radar"), cfg.get("brand", {}).get("tagline", ""))

    # ---- hero
    steps: list[str] = []
    if failed:
        headline, tone, sub = "Do not trade this", "red", "The 12-year test shows no edge since 2021."
    elif not regime_on:
        headline, tone = "Don't buy now", "red"
        sub = ("The overall market is weak. Tomorrow, sell any stocks from this method and keep the money aside."
               if tomorrow else
               f"The overall market is weak. Keep your money aside. If you own stocks from this method, "
               f"sell them on {checkin_day:%a %d %b}.")
    elif tomorrow:
        headline, tone, sub = "Action tomorrow", "blue", f"Before 9:15 am on {checkin_day:%a %d %b}:"
        sells = [h for h in holdings if h.action == "SELL"]
        if sells:
            steps.append("Sell " + ", ".join(esc(h.symbol) for h in sells))
        if picks:
            steps.append("Buy " + ", ".join(f"{esc(p.symbol)} ({p.qty})" for p in picks))
            steps.append("Set a stop loss on each")
        if not holdings:
            steps.append(f"Sell anything not in the Top {keep_n}")
    else:
        headline, tone, sub = "Hold, no action today", "green", f"Next check-in {checkin_day:%a %d %b}. Stop losses on Kite work on their own."
    steps_html = ('<ol class="steps">' + "".join(f"<li>{x}</li>" for x in steps) + "</ol>") if steps else ""
    hero = (f'<header class="hero {tone}"><h1 class="headline">{headline}</h1><p class="sub">{sub}</p>{steps_html}'
            f'<div class="chips"><span class="chip"><i class="dot {"g" if regime_on else "r"}"></i>Market {"strong" if regime_on else "weak"}</span>'
            f'<span class="chip">Next check-in <b>{checkin_day:%a %d %b}</b></span>'
            f'<span class="chip">Prices to {data_day:%d %b}</span></div></header>')
    banner = ""
    if failed:
        banner = (f'<div class="banner red"><span class="big">{FAILED_BANNER}</span>'
                  f'<p>{esc("; ".join(st.get("reasons", [])))}. Do not trade these picks with real money.</p></div>')

    # ---- market chart (backs up "market ON / OFF")
    nifty = ctx.get("charts", {}).get("NIFTY")
    market = ""
    if nifty:
        above, fast_ok = nifty["last"] > nifty["slow_last"], nifty["fast_last"] > nifty["slow_last"]
        if regime_on:
            say = 'Nifty 50 is <span class="pos">in an uptrend</span>: above its 200-day average, 50-day above 200-day.'
        elif above and not fast_ok:
            say = ('Nifty 50 is back above its 200-day average, but the 50-day is still '
                   '<span class="neg">below</span> it. Not a clear uptrend yet.')
        else:
            say = 'Nifty 50 is <span class="neg">below</span> its 200-day average. Downtrend.'
        market = (f'<h2 class="sec">The market</h2><div class="panel"><p class="say">{say}</p>'
                  f'<div class="small muted">Nifty {inr(nifty["last"], 0, symbol=False)} &middot; 50-day '
                  f'{inr(nifty["fast_last"], 0, symbol=False)} &middot; 200-day {inr(nifty["slow_last"], 0, symbol=False)}</div>'
                  '<div class="chart" data-k="NIFTY" data-kind="index"></div>'
                  '<div class="lg"><span><i style="background:#fbbf24"></i>50-day avg</span>'
                  '<span><i style="background:#a78bfa"></i>200-day avg</span></div></div>')

    # ---- stocks
    if regime_on:
        title = "Buy list" if tomorrow else "Buy list (preview)"
        cards = "".join(stock_card(pk.why, f"#{pk.rank}", False, pick_extra(pk, k))
                        for k, pk in enumerate(picks) if pk.why) if picks else ""
        stocks = cards or '<p class="muted">Nothing to buy right now.</p>'
        if picks and not tomorrow:
            stocks = '<p class="small muted">What the next check-in would buy. Wait for that day.</p>' + stocks
    else:
        title = "Watch list"
        ww = ctx.get("watch_why") or []
        stocks = ('<p class="small muted">Strongest stocks now. Not buying yet. These are ready for when the market turns strong.</p>'
                  + "".join(stock_card(w, f"Watch #{w.rank}", True) for w in ww)) if ww else \
            '<p class="muted">No buys until the market turns up.</p>'

    top = ctx.get("top_list", [])
    top_html = ""
    if top and regime_on:
        top_html = (f'<h2 class="sec">Top {keep_n} now</h2><div class="ranks">'
                    + "".join(f'<span class="rank"><b>{r}</b>{esc(s)}</span>' for r, s in top) + "</div>"
                    '<p class="small muted">Hold one of these? Keep it. Not in the list? Sell at the check-in.</p>')
    hold_html = ('<h2 class="sec">Your holdings</h2>' + "".join(holding_card(h) for h in holdings)) if holdings else ""

    # ---- proof
    proof = ""
    if st is not None:
        eq = st.get("equity_weekly")
        proof = (f'<h2 class="sec">Does it work?</h2><div class="panel"><div class="tiles">'
                 f'<div class="tile"><div class="tl">12-year test</div><div class="tv {"red" if failed else "green"}">'
                 f'{"FAILED" if failed else "PASSED"}</div><div class="tn">{inr(st["oos_expectancy_inr"])} avg per trade</div></div>'
                 f'<div class="tile"><div class="tl">Per year since 2021</div><div class="tv">{pct(st.get("oos_cagr"), 0, signed=True)}</div>'
                 f'<div class="tn">Nifty {pct(st.get("nifty_oos_cagr"), 0, signed=True)}</div></div>'
                 f'<div class="tile"><div class="tl">Worst fall</div><div class="tv red">{pct(st.get("oos_max_dd_pct"), 0)}</div>'
                 f'<div class="tn">Nifty {pct(st.get("nifty_oos_max_dd_pct"), 0)}</div></div></div>'
                 + ('<div class="tl">₹1,00,000 invested in 2014 (log scale)</div><div class="chart eq" data-k="EQUITY" data-kind="equity"></div>'
                    '<div class="lg"><span><i style="background:#60a5fa"></i>This method</span>'
                    '<span><i style="background:#94a3b8"></i>Nifty 50</span></div>' if eq else "")
                 + '<a class="more" href="backtest.html">Full test details &rarr;</a></div>')

    how = ('<a class="howlink" href="how.html"><div><b>How does Momentum Radar work?</b>'
           '<div class="small muted">Signals, the 50 and 200-day averages, stop loss and target, explained simply.</div></div>'
           '<span>Read &rarr;</span></a>')

    skipped = ctx.get("skipped_quality", [])
    notes = [esc(n) for n in ctx.get("notes", [])] + [esc(f"Skipped {s}: {why}") for s, why in skipped]
    notes.append("The 12-year test uses today's Nifty 100 members (survivorship bias): real results are likely lower.")
    notes.append("Charts: TradingView Lightweight Charts. Logos: company websites. Business info: Yahoo Finance.")
    notes_html = ('<details class="notes"><summary>Notes</summary><ul class="small muted">'
                  + "".join(f"<li>{n}</li>" for n in notes) + "</ul></details>")

    body = f"""{hero}{banner}{market}
<h2 class="sec">{title}</h2>{stocks}
{top_html}{hold_html}{proof}{how}{notes_html}
<div class="small muted" style="margin-top:12px">Updated {ctx["generated"]:%d %b %Y, %I:%M %p} IST</div>"""
    charts = dict(ctx.get("charts", {}))
    if st is not None and st.get("equity_weekly"):
        charts["EQUITY"] = st["equity_weekly"]
    head = f'<script src="{LIB_URL}"></script>' if charts else ""
    js = COPY_JS + ("window.__CHARTS=" + json.dumps(charts, separators=(",", ":")) + ";" + CHART_JS if charts else "")
    html = page("Dashboard", body, js, brand=brand, head_extra=head, active="index.html")
    return html.replace("</style>", SCAN_CSS + "</style>", 1)


def phone_message(ctx: dict) -> str:
    """Short plain-text summary (Telegram, if switched on)."""
    st = ctx["backtest_status"]
    lines = [f"Momentum Radar, prices to {ctx['data_date']:%a %d %b}"]
    if st is not None and not st["passed"]:
        lines.append("WARNING: STRATEGY FAILED OUT OF SAMPLE. Do not trade it.")
    lines.append("Market: " + ("strong" if ctx["regime_on"] else "weak, do not buy"))
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
