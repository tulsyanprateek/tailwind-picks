"""Build how.html: the method, the philosophy and every indicator, in plain language."""
from __future__ import annotations

import json

from .charts import CHART_JS, LIB_URL
from .html_common import esc, page
from .utils import inr, pct

HOW_CSS = """
.hwrap{max-width:900px;margin:0 auto}
.hero2{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}
.hero2 h1{margin:0 0 6px;font-size:28px}.lead{font-size:16px;color:#c7cedb;margin:0}
.toc{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0 0}
.toc a{font-size:12.5px;font-weight:600;color:#93c5fd;text-decoration:none;padding:5px 10px;border-radius:999px;
background:var(--panel2);border:1px solid var(--line)}
.h2{font-family:"Space Grotesk",Inter,sans-serif;font-size:21px;font-weight:700;margin:30px 0 10px;scroll-margin-top:12px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.pp{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px}
.pp h4{margin:0 0 4px;font-family:"Space Grotesk";font-size:15.5px}.pp p{margin:4px 0;color:#c7cedb;font-size:14px}
.pp .tag{display:inline-block;font-size:10.5px;font-weight:800;letter-spacing:.06em;padding:2px 7px;border-radius:6px;margin-bottom:6px}
.tag.rule{background:rgba(59,130,246,.15);color:#93c5fd}.tag.second{background:rgba(167,139,250,.15);color:#d9d0ff}
.flow{display:grid;gap:8px}
.flow div{display:flex;gap:12px;align-items:center;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px 14px}
.flow b{flex:none;min-width:46px;text-align:center;font-family:"Space Grotesk";font-size:20px;color:#fff}
.flow span{font-size:14px;color:#c7cedb}.flow div:last-child{border-color:rgba(59,130,246,.5);background:rgba(59,130,246,.08)}
.chart{height:260px;margin:8px -4px 0}
.lg{display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:var(--muted);margin-top:6px}
.lg i{display:inline-block;width:12px;height:3px;border-radius:2px;vertical-align:middle;margin-right:5px}
.sig{display:inline-block;min-width:52px;text-align:center;font-size:11px;font-weight:800;padding:3px 8px;border-radius:6px}
.sig.BUY{background:rgba(34,197,94,.15);color:var(--green)}.sig.HOLD{background:rgba(245,185,66,.15);color:var(--amber)}
.sig.SELL{background:rgba(239,68,68,.15);color:var(--red)}.sig.WAIT{background:rgba(148,163,184,.15);color:#cbd5e1}
.nums{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.nums div{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px}
.nums b{display:block;font-family:"Space Grotesk";font-size:22px}.nums span{font-size:12px;color:var(--muted)}
.pos{color:var(--green)}.neg{color:var(--red)}
table.it td{white-space:normal}
@media(max-width:700px){.grid2,.nums{grid-template-columns:1fr}}
"""

INDICATORS = [
    ("Market filter (Nifty 50)", "rule",
     "Whether the whole market is in an uptrend: the Nifty 50 above its 200-day average, and its 50-day average above the 200-day.",
     "When the market is weak, most stocks fall together, even good ones. So no new buys, and everything is sold at the next check-in."),
    ("Moving averages (50-day and 200-day)", "rule",
     "The average closing price of the last 50 days (about 2.5 months) and the last 200 days (about 10 months).",
     "Price above both, 50-day above 200-day, and the 200-day rising = a healthy uptrend. These are the most watched trend lines in the "
     "world, so many buyers and sellers act around them."),
    ("52-week high and low", "rule",
     "The highest and lowest prices of the last year.",
     "A strong stock trades close to its 1-year high (within 25%) and well above its low (at least 30% higher)."),
    ("Momentum (relative strength)", "rule",
     "How much a stock rose over 3, 6 and 12 months (40%, 30%, 30% weight), skipping the last week, compared with every other Nifty 100 stock.",
     "This is the main engine. Only the top 30% qualify, and the highest ranked are bought. The last week is skipped because very "
     "short-term moves tend to reverse."),
    ("ATR (average true range)", "rule",
     "How much a stock typically moves in a day.",
     "Used only in the 12-year test to compare stop loss choices. The live stop loss is a simple 15% below the buy price."),
    ("RSI (14)", "second",
     "Relative Strength Index: compares recent up days with down days, on a scale of 0 to 100.",
     "50 to 70 = healthy momentum. Above 70 = very strong but stretched, may pause. Below 50 = momentum fading."),
    ("MACD (12, 26, 9)", "second",
     "Moving Average Convergence Divergence: the gap between a fast and a slow average, with its own signal line.",
     "Above zero and above its signal line = momentum rising. Above zero but below the signal line = cooling. Below zero = downtrend."),
    ("ADX (14)", "second",
     "Average Directional Index: how strong the trend is, with +DI and -DI showing whether buyers or sellers are in control.",
     "Above 25 with buyers in control = strong uptrend. Below 20 = no clear trend."),
    ("Volume and OBV", "second",
     "On-Balance Volume adds volume on up days and subtracts it on down days.",
     "Rising OBV = buyers are stepping in and the move has support. Falling OBV = more selling than buying."),
]


def build_how_html(cfg: dict, status: dict | None, nifty_chart: dict | None, funnel: dict | None = None) -> str:
    p, t = cfg["portfolio"], cfg["trade"]
    n_hold, keep = p["holdings"], p["keep_if_rank_within"]
    stop = f"{t['stop_pct']:g}%" if t.get("stop_mode") == "percent" else "2 x ATR"
    sm = (status or {}).get("summary") or {}
    brand = (cfg.get("brand", {}).get("name", "Momentum Radar"), cfg.get("brand", {}).get("tagline", ""))
    aim = f"+{sm['avg_win_pct']:.0f}%" if sm.get("avg_win_pct") else "the typical win"

    principles = [
        ("Follow the trend, don't predict", "We don't guess what a company will earn. We buy what the market is already proving strong."),
        ("Winners keep winning, for a while", "Stocks that rose the most over 3 to 12 months tend to keep beating the rest for a few "
                                              "months. It is one of the most researched patterns in markets."),
        ("Market first, stock second", "Even great stocks fall in a falling market. We only buy when the whole market is rising."),
        ("Cut losers, let winners run", f"Every stock gets a {stop} stop loss. Winners are kept as long as they stay in the Top {keep}."),
        ("Rules, not feelings", "The same rules every time, tested on 12 years of prices. No tips, no news, no excitement."),
        ("Few decisions, low cost", "Check twice a month only. Fewer trades means lower charges and less stress."),
    ]
    phil = "".join(f'<div class="pp"><h4>{esc(h)}</h4><p>{esc(d)}</p></div>' for h, d in principles)

    fn = funnel or {}
    flow = ""
    if fn:
        flow = ('<div class="flow">'
                f'<div><b>{fn["scanned"]}</b><span>Nifty 100 stocks scanned today (stocks with under a year of prices are skipped)</span></div>'
                f'<div><b>{fn["uptrend"]}</b><span>are in a healthy uptrend (moving averages and 52-week checks)</span></div>'
                f'<div><b>{fn["momentum"]}</b><span>are in the top 30% for momentum</span></div>'
                f'<div><b>{fn["both"]}</b><span>pass both, ranked by momentum</span></div>'
                f'<div><b>{fn["top"]}</b><span>make the watchlist (Top {keep}): hold these if you own them</span></div>'
                f'<div><b>{fn["buy"]}</b><span>to buy now (Top {n_hold}, only when the market is strong)</span></div></div>')

    inds = "".join(
        f'<div class="pp"><span class="tag {kind}">{"USED IN THE RULES" if kind == "rule" else "SECOND OPINION"}</span>'
        f'<h4>{esc(n)}</h4><p><b>What it is:</b> {esc(w)}</p><p><b>How to read it:</b> {esc(r)}</p></div>'
        for n, kind, w, r in INDICATORS)

    nifty_html = ""
    if nifty_chart:
        nifty_html = ('<div class="pp" style="margin-top:10px"><b>Live example: the Nifty 50 with its 50-day and 200-day averages</b>'
                      '<div class="chart" data-k="NIFTY" data-kind="index"></div>'
                      '<div class="lg"><span><i style="background:#fbbf24"></i>50-day average</span>'
                      '<span><i style="background:#a78bfa"></i>200-day average</span></div>'
                      '<p>Yellow above purple, and the price above both = strong market. Price below purple = weak market.</p></div>')

    iv = (status or {}).get("interval_check") or []
    iv_html = ""
    if iv:
        rows = "".join(f'<tr><td>{esc(r["name"])}{" (used)" if r["name"] == "Every 2 weeks" else ""}</td>'
                       f'<td>{r["cagr_min"]:.0f}% to {r["cagr_max"]:.0f}%</td><td>{r["dd_max"]:.0f}% to {r["dd_min"]:.0f}%</td>'
                       f'<td>{r["trades"]}</td></tr>' for r in iv)
        iv_html = ('<div class="scroll" style="margin-top:10px"><table class="it"><thead><tr><th>Check-in</th><th>Return per year</th>'
                   f'<th>Worst fall</th><th>Trades</th></tr></thead><tbody>{rows}</tbody></table></div>')

    nums = ""
    if sm:
        nums = ('<div class="nums">'
                f'<div><b class="pos">{pct(sm.get("full_cagr"), 0, signed=True)}</b><span>per year since {esc(sm.get("start", ""))} '
                f'(Nifty 50: {pct(sm.get("nifty_full_cagr"), 0, signed=True)})</span></div>'
                f'<div><b>{inr(sm.get("final_value"))}</b><span>from ₹1,00,000 (Nifty 50: {inr(sm.get("nifty_final_value"))})</span></div>'
                f'<div><b>{sm.get("win_rate", 0):.0f}%</b><span>of trades made money</span></div>'
                f'<div><b class="pos">+{sm.get("avg_win_pct", 0):.0f}%</b><span>typical winning trade</span></div>'
                f'<div><b class="neg">{sm.get("avg_loss_pct", 0):.0f}%</b><span>typical losing trade</span></div>'
                f'<div><b class="neg">{pct(sm.get("full_max_dd_pct"), 0)}</b><span>worst fall from a peak '
                f'(Nifty 50: {pct(sm.get("nifty_full_max_dd_pct"), 0)})</span></div></div>')

    body = f"""<div class="hwrap">
<div class="hero2"><h1>How Momentum Radar works</h1>
<p class="lead">A rule-based way to own the strongest Nifty 100 stocks, only while the market is healthy. Every number on the
dashboard comes from the rules below.</p>
<div class="toc"><a href="#philosophy">Philosophy</a><a href="#radar">How stocks get on the radar</a><a href="#indicators">Indicators</a>
<a href="#averages">50 and 200-day averages</a><a href="#signals">Signals</a><a href="#interval">Why every 15 days</a>
<a href="#plan">Buy, stop loss, target</a><a href="#results">Past results</a></div></div>

<div class="h2" id="philosophy">The philosophy</div>
<div class="grid2">{phil}</div>

<div class="h2" id="radar">How a stock gets on the radar</div>
<p class="muted">Every evening all Nifty 100 stocks go through the same filters. Today's numbers:</p>
{flow}

<div class="h2" id="indicators">The technical indicators</div>
<p class="muted">Blue tags are the tested rules that decide what to buy and sell. Purple tags are popular indicators shown as a
second opinion, so you can cross-check each stock on the dashboard (Indicators tab). They don't change the picks, because adding
untested rules to a tested method makes it less reliable, not more.</p>
<div class="grid2">{inds}</div>

<div class="h2" id="averages">Why the 50-day and 200-day averages?</div>
<div class="pp"><p>An average smooths out daily noise and shows the direction. <b>50 days</b> (about 2.5 months) captures the
current move; <b>200 days</b> (about 10 months) captures the big trend. They are the trend lines most funds and traders watch, so
prices often react around them, which makes them more reliable than unusual settings.</p></div>
{nifty_html}

<div class="h2" id="signals">What the signals mean</div>
<div class="pp"><p><span class="sig BUY">BUY</span> every rule passes and the stock is in the Top {n_hold}.</p>
<p><span class="sig HOLD">HOLD</span> still healthy and in the Top {keep}: keep it if you own it, don't add.</p>
<p><span class="sig SELL">SELL</span> a rule failed or it dropped out of the Top {keep}: sell on the next check-in day.</p>
<p><span class="sig WAIT">WAIT</span> the stock is strong but the market is weak: don't buy yet.</p></div>

<div class="h2" id="interval">Why check every 15 days?</div>
<div class="pp"><p>We tested different check-in intervals on 2014 to 2020 only, each with different calendar dates. The less often
you check, the more the result depends on lucky or unlucky dates: checking every 3 months gave anything from a weak to a great
return depending only on which months were chosen. Every 2 weeks gave steady results with fewer trades than weekly, so that is what
the radar uses.</p></div>
{iv_html}

<div class="h2" id="plan">Buy price, stop loss and target</div>
<div class="pp"><p><b>Buy up to:</b> last close + {t['max_gap_pct']}%, as a limit order before 9:15 am. If it opens higher and never
comes back, skip it.</p>
<p><b>Stop loss:</b> {stop} below your buy price, set once as a GTT order on Kite.</p>
<p><b>Target:</b> {aim}, the typical winning trade in the test. A guide only: winners are kept while they stay in the Top {keep}.</p>
<p><b>Sell everything</b> when the market turns weak on a check-in day.</p></div>

<div class="h2" id="results">Did it work in the past?</div>
<p class="muted">12 years of real prices, all Zerodha charges included, starting with ₹1,00,000.</p>
{nums}
<div class="pp" style="margin-top:10px"><p><b>Be realistic.</b> Fewer than half the trades make money; the method works because
winners are bigger than losers. Expect losing months and years. The test uses today's Nifty 100 list for all years, which flatters
the result, so expect less in real life.</p><p><a href="backtest.html" style="color:#93c5fd;font-weight:600">See the full 12-year test &rarr;</a></p></div>
</div>"""
    charts = {"NIFTY": nifty_chart} if nifty_chart else {}
    head = f'<script src="{LIB_URL}"></script>' if charts else ""
    js = ("window.__CHARTS=" + json.dumps(charts, separators=(",", ":")) + ";" + CHART_JS) if charts else ""
    html = page("How it works", body, js, brand=brand, head_extra=head, active="how.html")
    return html.replace("</style>", HOW_CSS + "</style>", 1)
