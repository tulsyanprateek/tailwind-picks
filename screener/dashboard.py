"""Tailwind Picks dashboard: one simple scrolling page (approved wireframe).

1 header  2 today's answer  3 market card  4 stock cards (top 5)
5 rest of the Top 10  6 does it work?  7 disclaimer (page footer)
"""
from __future__ import annotations

import json
import math

from .charts import LIB_URL
from .html_common import esc, page
from .live_js import LIVE_CSS, LIVE_JS
from .utils import inr, pct

FAILED_BANNER = "STRATEGY FAILED OUT OF SAMPLE"
WORD = {"BUY": "BUY", "HOLD": "HOLD", "SELL": "SELL", "WAIT": "WAIT"}
HINT = {"BUY": "All rules pass, top 5", "HOLD": "Keep if you own it", "SELL": "A rule failed",
        "WAIT": "Good stock, weak market"}

CSS = """
.page{max-width:1100px;margin:0 auto}
.answer{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px}
.answer .big{font-family:"Space Grotesk",Inter,sans-serif;font-size:clamp(30px,7vw,44px);font-weight:700;line-height:1.05;margin:0 0 6px}
.answer.red .big{color:#fda4af}.answer.green .big{color:#86efac}.answer.blue .big{color:#93c5fd}
.answer p{margin:0 0 10px;color:#c7cedb;font-size:15.5px}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;font-weight:600;padding:5px 10px;border-radius:999px;
background:var(--panel2);border:1px solid var(--line);color:#d5dbe6}
.dot{width:7px;height:7px;border-radius:50%}.dot.g{background:var(--green)}.dot.r{background:var(--red)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:16px;margin:0}
.muted2{color:var(--muted);font-size:13px}
.sec{font-family:"Space Grotesk",Inter,sans-serif;font-size:19px;font-weight:700;margin:26px 0 10px}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.card{min-width:0}
.mchart{height:170px;margin:8px -4px 0}.schart{height:200px;margin:10px -4px 0}.eqchart{height:190px;margin-top:10px}
.sh{display:flex;align-items:center;gap:10px}
.logo2{position:relative;flex:none;width:40px;height:40px;border-radius:10px;background:#fff;display:grid;place-items:center;
overflow:hidden;font:800 13px Inter;color:#0b1020}
.logo2 img{position:absolute;inset:5px;width:30px;height:30px;object-fit:contain}
.sname{flex:1;min-width:0}.sname b{display:block;font-family:"Space Grotesk";font-size:19px;line-height:1.1}
.sname span{display:block;font-size:12.5px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.px2{text-align:right}.px2 b{display:block;font-size:16px;font-weight:700}.px2 span{font-size:12px;font-weight:600}
.up{color:var(--green)}.dn{color:var(--red)}
.vd{flex:none;font:700 13px "Space Grotesk";padding:6px 11px;border-radius:8px;letter-spacing:.04em}
.vd.BUY{background:rgba(34,197,94,.15);color:var(--green)}.vd.HOLD{background:rgba(245,185,66,.15);color:var(--amber)}
.vd.SELL{background:rgba(239,68,68,.15);color:var(--red)}.vd.WAIT{background:rgba(148,163,184,.15);color:#cbd5e1}
.brands{display:flex;flex-wrap:wrap;gap:5px;margin-top:10px}
.brands span{font-size:11.5px;font-weight:600;padding:3px 9px;border-radius:999px;background:rgba(167,139,250,.12);color:#d9d0ff}
.lv{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px}
.lv>div{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:8px 10px}
.lv .l{font-size:11px;color:var(--muted)}.lv .v{font:700 17px "Space Grotesk"}.lv .s{font-size:11px;color:var(--muted)}
.v.blue{color:#60a5fa}.v.red{color:#f87171}.v.green{color:#4ade80}
.strip{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px;font-size:12.5px}
.strip span{padding:4px 9px;border-radius:8px;background:var(--panel2);color:#d5dbe6}.strip b{color:#fff}
.qty{font-size:12.5px;color:var(--muted);margin-top:8px}
details.more{margin-top:12px;border-top:1px solid var(--line);padding-top:10px}
details.more summary{cursor:pointer;font-weight:600;font-size:14px;color:#93c5fd;list-style:none}
details.more summary::-webkit-details-marker{display:none}
details.more summary:after{content:" +"}details.more[open] summary:after{content:" -"}
.t2{width:100%;font-size:13px;margin:10px 0}.t2 td{padding:6px 4px;border-bottom:1px solid var(--line);white-space:normal;text-align:left}
.t2 td:nth-child(2){white-space:nowrap;color:#d5dbe6}.t2 td:last-child{text-align:right}
.hint{font-size:11px;color:var(--muted)}
.sig{display:inline-block;min-width:48px;text-align:center;font-size:11px;font-weight:800;padding:3px 7px;border-radius:6px}
.sig.BUY{background:rgba(34,197,94,.15);color:var(--green)}.sig.HOLD{background:rgba(245,185,66,.15);color:var(--amber)}
.sig.SELL{background:rgba(239,68,68,.15);color:var(--red)}.sig.WAIT{background:rgba(148,163,184,.15);color:#cbd5e1}
.ichart{height:120px;margin:4px -4px 10px}
.about{font-size:13.5px;color:#c7cedb}
.risk{font-size:12.5px;color:#fde68a;background:rgba(245,185,66,.08);border-radius:10px;padding:8px 10px;margin-top:8px}
pre.order{background:#000;border:1px solid var(--line);border-radius:10px;padding:10px;font-size:12px;white-space:pre-wrap;margin:10px 0 6px}
.copied{color:var(--green);font-size:12px;margin-left:8px}
.list{background:var(--panel);border:1px solid var(--line);border-radius:16px;overflow:hidden}
.row{display:grid;grid-template-columns:28px minmax(0,1fr) auto 64px 56px;gap:10px;align-items:center;padding:10px 14px;
border-bottom:1px solid var(--line);font-size:13.5px}.row:last-child{border-bottom:0}
.row .r{color:var(--muted);font-weight:700}.row .nm b{display:block}.row .nm span{font-size:11.5px;color:var(--muted);white-space:nowrap;
overflow:hidden;text-overflow:ellipsis;display:block}.row .p{text-align:right;font-weight:600}.row .c{text-align:right;font-weight:600}
.nums{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.nums>div{background:var(--panel2);border-radius:10px;padding:10px}.nums b{display:block;font:700 20px "Space Grotesk"}
.nums span{font-size:11.5px;color:var(--muted)}
.lg{display:flex;flex-wrap:wrap;gap:12px;font-size:11.5px;color:var(--muted);margin-top:6px}
.lg i{display:inline-block;width:12px;height:3px;border-radius:2px;vertical-align:middle;margin-right:5px}
.link{color:#93c5fd;text-decoration:none;font-weight:600;font-size:14px}
@media(max-width:860px){.grid{grid-template-columns:minmax(0,1fr)}}
@media(max-width:420px){.row{grid-template-columns:22px minmax(0,1fr) auto 52px;padding:10px 12px}.row .c{display:none}
.nums{grid-template-columns:1fr 1fr}.nums div:first-child{grid-column:1/-1}.lv .v{font-size:15px}.px2 b{font-size:14px}}
"""

JS = r"""
(function(){
var A=window.__APP||{};var L=window.LightweightCharts;
if(!L){document.querySelectorAll('[data-chart]').forEach(function(e){e.innerHTML='<div class="muted2" style="padding:20px;text-align:center">Charts need an internet connection.</div>'});return;}
function mk(el){return L.createChart(el,{width:el.clientWidth,height:el.clientHeight,handleScroll:false,handleScale:false,
 layout:{background:{type:'solid',color:'transparent'},textColor:'#8a94a7',fontSize:11,fontFamily:'Inter, sans-serif'},
 grid:{vertLines:{visible:false},horzLines:{color:'rgba(255,255,255,0.04)'}},rightPriceScale:{borderVisible:false},
 timeScale:{borderVisible:false},crosshair:{mode:1,vertLine:{labelBackgroundColor:'#1f2736'},horzLine:{labelBackgroundColor:'#1f2736'}},
 localization:{priceFormatter:function(p){return Number(p).toLocaleString('en-IN',{maximumFractionDigits:2})}}});}
function pts(a){return a.map(function(x){return{time:x[0],value:x[1]}})}
function ln(ch,a,c,w){var s=ch.addLineSeries({color:c,lineWidth:w||1.5,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});s.setData(pts(a));return s}
var made=[];
function price(el,d){var ch=mk(el);
 var c=ch.addCandlestickSeries({upColor:'#22c55e',downColor:'#ef4444',borderVisible:false,wickUpColor:'#22c55e',wickDownColor:'#ef4444'});
 c.setData(d.c.map(function(x){return{time:x[0],open:x[1],high:x[2],low:x[3],close:x[4]}}));
 ln(ch,d.ma50,'#f5b942');ln(ch,d.ma200,'#a78bfa',2);
 function pl(v,col,t){if(v)c.createPriceLine({price:v,color:col,lineWidth:1,lineStyle:2,axisLabelVisible:true,title:t})}
 pl(d.limit,'#3b82f6','Buy');pl(d.stop,'#ef4444','Stop');pl(d.aim,'#22c55e','Target');
 ch.timeScale().fitContent();return ch}
function draw(el){var d=A[el.dataset.chart];if(!d||el.dataset.done||!el.clientWidth)return;el.dataset.done=1;var k=el.dataset.kind,ch;
 if(k==='price'){ch=price(el,d)}
 else if(k==='eq'){ch=mk(el);ch.applyOptions({rightPriceScale:{mode:1},localization:{priceFormatter:function(p){return '₹'+Math.round(p).toLocaleString('en-IN')}}});
  var a=ch.addAreaSeries({lineColor:'#3b82f6',topColor:'rgba(59,130,246,0.3)',bottomColor:'rgba(59,130,246,0)',lineWidth:2,priceLineVisible:false});
  a.setData(d.t.map(function(t,i){return{time:t,value:d.s[i]}}));
  ln(ch,d.t.map(function(t,i){return[t,d.n[i]]}),'#8a94a7');ch.timeScale().fitContent()}
 else if(k==='rsi'){ch=mk(el);var r=ln(ch,d.rsi,'#a78bfa');
  [[70,'rgba(239,68,68,0.6)'],[50,'rgba(148,163,184,0.5)'],[30,'rgba(34,197,94,0.6)']].forEach(function(p){r.createPriceLine({price:p[0],color:p[1],lineWidth:1,lineStyle:2,axisLabelVisible:false,title:''})});
  ch.timeScale().fitContent()}
 else if(k==='macd'){ch=mk(el);var h=ch.addHistogramSeries({priceLineVisible:false,lastValueVisible:false});
  h.setData(d.macdh.map(function(x){return{time:x[0],value:x[1],color:x[1]>=0?'rgba(34,197,94,0.5)':'rgba(239,68,68,0.5)'}}));
  ln(ch,d.macd,'#3b82f6');ln(ch,d.macds,'#f5b942');ch.timeScale().fitContent()}
 made.push([ch,el]);}
document.querySelectorAll('[data-chart]').forEach(function(el){if(!el.closest('details'))draw(el)});
document.querySelectorAll('details.more').forEach(function(dt){dt.addEventListener('toggle',function(){if(dt.open)dt.querySelectorAll('[data-chart]').forEach(draw)})});
var t;window.addEventListener('resize',function(){clearTimeout(t);t=setTimeout(function(){made.forEach(function(m){if(m[1].clientWidth){m[0].applyOptions({width:m[1].clientWidth});m[0].timeScale().fitContent()}})},150)});
})();
function copyText(id,btn){var t=document.getElementById(id).innerText;var s=btn.nextElementSibling;
function done(){s.textContent='Copied';setTimeout(function(){s.textContent=''},1500)}
if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(t).then(done)}else{var a=document.createElement('textarea');
a.value=t;document.body.appendChild(a);a.select();try{document.execCommand('copy');done()}catch(e){}a.remove()}}
"""


def _last_chg(c: list) -> tuple[float, float]:
    if not c or len(c) < 2:
        return math.nan, math.nan
    return c[-1][4], (c[-1][4] / c[-2][4] - 1) * 100


def _logo(sym: str, logo: str) -> str:
    img = f'<img alt="" src="{logo}">' if logo else ""
    return f'<span class="logo2">{esc(sym[:2])}{img}</span>'


def _rows(rows) -> str:
    return '<table class="t2">' + "".join(
        f'<tr><td>{esc(n)}<div class="hint">{esc(h)}</div></td><td>{esc(r)}</td>'
        f'<td><span class="sig {esc(s)}">{esc(s)}</span></td></tr>' for n, r, s, h in rows) + "</table>"


def stock_card(w, d: dict, pick, market_on: bool) -> str:
    last, chg = _last_chg(d.get("c", []))
    lv = w.levels or {}
    sid = esc(w.symbol)
    brands = ('<div class="brands">' + "".join(f"<span>{esc(b)}</span>" for b in w.brands) + "</div>") if w.brands else ""
    if lv.get("aim"):
        aim = (f'<div><div class="l">Target</div><div class="v green">{inr(lv["aim"], 0)}</div>'
               f'<div class="s">+{lv["aim_pct"]:.0f}% typical win</div></div>')
    else:
        aim = '<div><div class="l">Target</div><div class="v">N/A</div></div>'
    qty = lv.get("qty", 0)
    if qty:
        qty_txt = (("If the market turns strong: " if not market_on else "")
                   + f'buy {qty} share{"" if qty == 1 else "s"} (about {inr(lv.get("amount", 0))}). Sell if it hits the stop loss, '
                     'drops out of the Top 10, or the market turns weak on a check-in day.')
    else:
        qty_txt = "One share costs more than your per-stock amount, so skip it."
    rules_buy = sum(1 for r in w.signals if r[2] == "BUY")
    order = ""
    if pick is not None:
        order = (f'<pre class="order" id="o-{sid}">{esc(pick.order_text)}</pre>'
                 f'<button onclick="copyText(\'o-{sid}\',this)">Copy Kite order</button><span class="copied"></span>')
    about = ((f'<div class="muted2" style="margin-top:12px">{esc(w.meta)}</div>' if w.meta else "")
             + (f'<p class="about">{esc(w.about)} <span class="muted2">(Yahoo Finance)</span></p>' if w.about else ""))
    chg_cls = "up" if chg >= 0 else "dn"
    return f"""
<div class="card">
  <div class="sh">{_logo(w.symbol, w.logo)}<div class="sname"><b>{sid}</b><span>{esc(w.company)}</span></div>
  <div class="px2"><b data-lp="{sid}" data-d="2" data-s="1">{inr(last, 2)}</b><span data-lc="{sid}" data-d="2" class="{chg_cls}">{chg:+.2f}%</span></div>
  <span class="vd {esc(w.overall)}">{WORD.get(w.overall, w.overall)}</span></div>
  {brands}
  <div class="schart" data-chart="{sid}" data-kind="price"></div>
  <div class="lg"><span><i style="background:#f5b942"></i>50-day</span><span><i style="background:#a78bfa"></i>200-day</span>
  <span><i style="background:#3b82f6"></i>Buy</span><span><i style="background:#ef4444"></i>Stop</span><span><i style="background:#22c55e"></i>Target</span></div>
  <div class="lv">
    <div><div class="l">Buy up to</div><div class="v blue">{inr(lv.get("buy"), 0)}</div><div class="s">limit order</div></div>
    <div><div class="l">Stop loss</div><div class="v red">{inr(lv.get("stop"), 0)}</div><div class="s">-{lv.get("stop_pct", 0):.0f}%</div></div>
    {aim}
  </div>
  <div class="strip"><span>Rules <b>{rules_buy}/{len(w.signals)}</b></span><span>Indicators <b>{w.second_agree}/{len(w.second)}</b></span>
  <span>Rank <b>#{w.rank}</b></span><span>{esc(HINT.get(w.overall, ""))}</span></div>
  <div class="qty">{esc(qty_txt)}</div>
  <details class="more"><summary>Show details</summary>
    <div class="muted2" style="margin-top:10px">Tailwind Picks rules (these decide the signal)</div>{_rows(w.signals)}
    <div class="muted2">Second-opinion indicators (for checking only)</div>{_rows(w.second)}
    <div class="hint">RSI (14): above 70 stretched, below 50 weak</div><div class="ichart" data-chart="{sid}" data-kind="rsi"></div>
    <div class="hint">MACD: bars above zero = rising momentum</div><div class="ichart" data-chart="{sid}" data-kind="macd"></div>
    {about}<div class="risk">{esc(w.risk)}</div>{order}
  </details>
</div>"""


def build_dashboard_html(ctx: dict, cfg: dict) -> str:
    st = ctx["backtest_status"]
    regime_on, tomorrow = ctx["regime_on"], ctx["checkin_next"]
    checkin_day, data_day = ctx["next_checkin"], ctx["data_date"]
    picks, holdings = ctx["picks"], ctx["holdings"]
    failed = st is not None and not st["passed"]
    charts = ctx.get("charts", {}) or {}
    rows = [w for w in (ctx.get("watch_why") or []) if w.symbol in charts]
    pick_map = ctx.get("pick_map") or {p.symbol: p for p in picks}
    brand = (cfg.get("brand", {}).get("name", "Tailwind Picks"), cfg.get("brand", {}).get("tagline", ""))
    n_hold, keep_n = cfg["portfolio"]["holdings"], cfg["portfolio"]["keep_if_rank_within"]

    # 2. today's answer
    if failed:
        big, tone, why = "Do not trade this", "red", "The 12-year test shows no edge since 2021."
    elif not regime_on:
        big, tone = "Don't buy now", "red"
        if tomorrow:
            why = "The overall market is weak. Tomorrow, sell stocks you bought with Tailwind Picks and keep the money aside."
        else:
            why = ("The overall market is weak, so keep your money aside. If you own stocks from Tailwind Picks, "
                   f"sell them on {checkin_day:%a %d %b}.")
    elif tomorrow:
        big, tone = "Action tomorrow", "blue"
        sells = [h.symbol for h in holdings if h.action == "SELL"]
        parts = (["Sell " + ", ".join(sells)] if sells else []) + (
            ["Buy " + ", ".join(f"{p.symbol} ({p.qty})" for p in picks)] if picks else [])
        if not holdings:
            parts.append(f"Sell anything not in the Top {keep_n}")
        why = f"Before 9:15 am on {checkin_day:%a %d %b}: " + ". ".join(parts) + "."
    else:
        big, tone, why = "Hold, no action today", "green", "Your stop losses on Kite work on their own."
    fn = ctx.get("funnel")
    scan_txt = f'<span class="chip">{fn["scanned"]} scanned, {fn["both"]} qualify</span>' if fn else ""
    answer = (f'<div class="answer {tone}"><div class="big">{esc(big)}</div><p>{esc(why)}</p><div class="chips">'
              f'<span class="chip"><i class="dot {"g" if regime_on else "r"}"></i>Market {"strong" if regime_on else "weak"}</span>'
              f'<span class="chip">Next check-in {checkin_day:%a %d %b}</span><span class="chip">Signals from {data_day:%d %b} close</span>'
              f'{scan_txt}</div></div>')
    banner = ""
    if failed:
        banner = (f'<div class="banner red"><span class="big">{FAILED_BANNER}</span>'
                  f'<p>{esc("; ".join(st.get("reasons", [])))}. Do not trade these picks with real money.</p></div>')

    # 3. market card
    market = ""
    nifty = charts.get("NIFTY")
    if nifty:
        last, chg = _last_chg(nifty["c"])
        fast_ok = nifty["fast_last"] > nifty["slow_last"]
        above = nifty["last"] > nifty["slow_last"]
        if regime_on:
            say = "Market strong: Nifty above its 200-day average, 50-day above 200-day."
        elif above and not fast_ok:
            say = "Market weak: Nifty is back above its 200-day average, but the 50-day is still below it."
        else:
            say = "Market weak: Nifty is below its 200-day average."
        market = (f'<div class="card"><div class="sh"><span class="logo2" style="background:var(--panel2);color:#fff">N50</span>'
                  f'<div class="sname"><b>Nifty 50</b><span>{esc(say)}</span></div>'
                  f'<div class="px2"><b data-lp="NIFTY" data-d="0">{inr(last, 0, symbol=False)}</b><span data-lc="NIFTY" data-d="2" class="{"up" if chg >= 0 else "dn"}">{chg:+.2f}%</span></div></div>'
                  '<div class="mchart" data-chart="NIFTY" data-kind="price"></div>'
                  '<div class="lg"><span><i style="background:#f5b942"></i>50-day average</span>'
                  '<span><i style="background:#a78bfa"></i>200-day average</span></div></div>')

    # 4. stock cards (top 5) and 5. rest of the Top 10
    top, rest = rows[:n_hold], rows[n_hold:]
    if regime_on:
        title = "Buy list" if tomorrow else "Top 5 right now"
    else:
        title = "Top 5 to watch (not buying yet)"
    cards = "".join(stock_card(w, charts[w.symbol], pick_map.get(w.symbol), regime_on) for w in top) \
        or '<p class="muted2">No stocks qualify today.</p>'
    rest_html = ""
    if rest:
        rest_cards = "".join(stock_card(w, charts[w.symbol], pick_map.get(w.symbol), regime_on) for w in rest)
        rest_html = (f'<div class="sec">Rest of the Top {keep_n}</div><p class="muted2" style="margin:-4px 0 10px">'
                     f'Not for new buying. Own one of these? Keep it. Not in the Top {keep_n} on a check-in day? Sell it.</p>'
                     f'<div class="grid">{rest_cards}</div>')

    hold = ""
    if holdings:
        hold = ('<div class="sec">Your holdings</div><div class="list">' + "".join(
            f'<div class="row" style="grid-template-columns:minmax(0,1fr) auto"><span class="nm"><b>{esc(h.symbol)}</b>'
            f'<span>{esc(h.detail)}</span></span><span class="sig {"SELL" if h.action in ("SELL", "STOP HIT") else "HOLD"}">'
            f'{esc(h.action)}</span></div>' for h in holdings) + "</div>")

    # 6. does it work?
    proof = ""
    if st is not None:
        eq = ""
        if st.get("equity_weekly"):
            eq = ('<div class="eqchart" data-chart="EQUITY" data-kind="eq"></div><div class="lg">'
                  '<span><i style="background:#3b82f6"></i>₹1,00,000 with Tailwind Picks since 2014</span>'
                  '<span><i style="background:#8a94a7"></i>Nifty 50</span></div>')
        proof = ('<div class="sec">Does it work?</div><div class="card"><div class="nums">'
                 f'<div><b class="{"dn" if failed else "up"}">{"FAILED" if failed else "PASSED"}</b><span>12-year test, '
                 f'{inr(st["oos_expectancy_inr"])} avg per trade</span></div>'
                 f'<div><b>{pct(st.get("oos_cagr"), 0, signed=True)}</b><span>per year since 2021 '
                 f'(Nifty {pct(st.get("nifty_oos_cagr"), 0, signed=True)})</span></div>'
                 f'<div><b class="dn">{pct(st.get("oos_max_dd_pct"), 0)}</b><span>worst fall '
                 f'(Nifty {pct(st.get("nifty_oos_max_dd_pct"), 0)})</span></div></div>'
                 + eq + '<p style="margin:10px 0 0"><a class="link" href="how.html">How it works</a> &middot; '
                   '<a class="link" href="backtest.html">Full 12-year test</a></p></div>')

    notes = [esc(n) for n in ctx.get("notes", [])]
    notes.append("The 12-year test uses today's Nifty 100 members (survivorship bias): real results are likely lower.")
    notes.append("Charts by TradingView Lightweight Charts (open source). Business info from Yahoo Finance.")
    notes_html = ('<details class="more" style="border:0"><summary>Notes</summary><ul class="muted2">'
                  + "".join(f"<li>{n}</li>" for n in notes) + "</ul></details>")

    fresh = ('<div class="fresh" id="fresh"><i class="fdot"></i><div class="ftxt"><b id="fresh-a">Checking for the latest prices...</b>'
             f'<span>Signals updated {ctx["generated"]:%d %b, %I:%M %p} IST. They change only after the market closes.</span></div>'
             '<button class="fbtn" onclick="location.replace(location.pathname+&quot;?v=&quot;+Date.now())">Refresh</button></div>')
    body = (f'<div class="page">{fresh}{answer}{banner}'
            + (f'<div class="sec">The market</div>{market}' if market else "")
            + f'<div class="sec">{esc(title)}</div><div class="grid">{cards}</div>{rest_html}{hold}{proof}{notes_html}'
            f'<div class="muted2" style="margin-top:10px">Updated {ctx["generated"]:%d %b %Y, %I:%M %p} IST</div></div>')

    app = {k: v for k, v in charts.items() if k == "NIFTY" or any(w.symbol == k for w in rows)}
    if st is not None and st.get("equity_weekly"):
        app["EQUITY"] = st["equity_weekly"]
    head = f'<script src="{LIB_URL}"></script>' if app else ""
    live = {"url": cfg.get("live", {}).get("url", ""), "gen": ctx["generated"].isoformat(timespec="seconds"),
            "close": f"{data_day:%d %b}"}
    js = ("window.__APP=" + json.dumps(app, separators=(",", ":")) + ";window.__LIVE=" + json.dumps(live) + ";"
          + JS + LIVE_JS)
    html = page("Dashboard", body, js, brand=brand, head_extra=head, active="index.html")
    return html.replace("</style>", CSS + LIVE_CSS + "</style>", 1)
