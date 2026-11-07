"""Build how.html: how Momentum Radar works, in plain language."""
from __future__ import annotations

import json

from .charts import CHART_JS, LIB_URL
from .html_common import esc, page
from .utils import inr, pct

HOW_CSS = """
.lead{font-size:17px;color:#d6dbe6;margin:0 0 6px}
.sec2{font-size:20px;font-weight:800;letter-spacing:-.02em;margin:30px 0 8px}
.step{display:flex;gap:12px;align-items:flex-start;background:var(--panel);border:1px solid var(--line);border-radius:16px;
padding:14px;margin:8px 0}.step b{flex:none;width:34px;height:34px;border-radius:12px;display:grid;place-items:center;
background:linear-gradient(135deg,var(--blue),var(--violet));color:#0b1020;font-size:16px}
.step p{margin:2px 0 0;color:#c4cbd8;font-size:14px}.step h4{margin:0;font-size:15.5px}
.box{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:14px;margin:10px 0}
.box p{margin:6px 0;color:#c4cbd8}
.chart{height:240px;margin:8px -4px 0}
.lg{display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:var(--muted);margin-top:6px}
.lg i{display:inline-block;width:14px;height:3px;border-radius:2px;vertical-align:middle;margin-right:5px}
.sig{display:inline-block;min-width:52px;text-align:center;font-size:11.5px;font-weight:800;padding:3px 8px;border-radius:8px}
.sig.BUY{background:rgba(52,211,153,.15);color:var(--green)}.sig.HOLD{background:rgba(251,191,36,.15);color:var(--amber)}
.sig.SELL{background:rgba(251,113,133,.15);color:var(--red)}.sig.WAIT{background:rgba(148,163,184,.15);color:#cbd5e1}
.sigt td{white-space:normal;vertical-align:top}.sigt th{position:static}
.nums{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
.nums div{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px}
.nums b{display:block;font-size:22px;font-weight:800}.nums span{font-size:12px;color:var(--muted)}
.pos{color:var(--green)}.neg{color:var(--red)}
"""


def build_how_html(cfg: dict, status: dict | None, nifty_chart: dict | None) -> str:
    p, t = cfg["portfolio"], cfg["trade"]
    n_hold, keep = p["holdings"], p["keep_if_rank_within"]
    stop = f"{t['stop_pct']:g}%" if t.get("stop_mode") == "percent" else "2 x ATR"
    sm = (status or {}).get("summary") or {}
    brand = (cfg.get("brand", {}).get("name", "Momentum Radar"), cfg.get("brand", {}).get("tagline", ""))

    steps = [
        ("📅", "Two check-in days a month", "On the 1st and the 15th (or the next trading day). Nothing to do on other days."),
        ("🚦", "First, check the whole market", "If the Nifty 50 is weak, we don't buy anything and keep the money aside."),
        ("🏁", f"Pick the {n_hold} fastest runners", f"Out of the Nifty 100, the {n_hold} stocks that rose the most over the "
                                               "last 3, 6 and 12 months, and are still in a steady uptrend."),
        ("🛡️", f"Protect each one with a {stop} stop loss", "Set once on Kite. If the price falls that far, Kite sells it for you."),
        ("🔁", "Keep the winners, swap the losers", f"On each check-in, keep stocks still in the Top {keep}. Sell the rest and "
                                                     "buy new leaders."),
    ]
    steps_html = "".join(f'<div class="step"><b>{i}</b><div><h4>{esc(h)}</h4><p>{esc(d)}</p></div></div>'
                         for i, h, d in steps)

    signals = [
        ("Market (Nifty 50)", "Is the whole market rising? (Nifty above its 200-day average, and 50-day above 200-day)",
         "BUY", "WAIT"),
        ("Price vs 50-day average", "Is the stock above its average price of the last 50 days?", "BUY", "SELL"),
        ("50-day vs 200-day average", "Is the short-term average above the long-term one?", "BUY", "SELL"),
        ("200-day average", "Is the long-term average itself going up?", "BUY", "SELL"),
        ("Distance from 1-year high", "Is the price within 25% of its highest price of the year?", "BUY", "SELL"),
        ("1 year vs Nifty 50", "Did the stock rise more than the market over the year?", "BUY", "SELL"),
        ("Momentum rank", f"Its place among Nifty 100 stocks by recent rise. Top {n_hold} buy, top {keep} hold.",
         "BUY", "SELL"),
    ]
    sig_rows = "".join(f'<tr><td><b>{esc(n)}</b><div class="small muted">{esc(q)}</div></td>'
                       f'<td><span class="sig {y}">{y}</span></td><td><span class="sig {no}">{no}</span></td></tr>'
                       for n, q, y, no in signals)

    nifty_html = ""
    if nifty_chart:
        nifty_html = ('<div class="box"><b>Live example: the Nifty 50 today</b>'
                      '<div class="chart" data-k="NIFTY" data-kind="index"></div>'
                      '<div class="lg"><span><i style="background:#fbbf24"></i>50-day average</span>'
                      '<span><i style="background:#a78bfa"></i>200-day average</span></div>'
                      '<p class="small">When the yellow line is above the purple line and the price is above both, '
                      'the market is strong. When the price drops below the purple line, the market is weak.</p></div>')

    nums = ""
    if sm:
        nums = (f'<div class="nums">'
                f'<div><b class="pos">{pct(sm.get("full_cagr"), 0, signed=True)}</b><span>per year since {esc(sm.get("start", ""))} '
                f'(Nifty 50: {pct(sm.get("nifty_full_cagr"), 0, signed=True)})</span></div>'
                f'<div><b>{inr(sm.get("final_value"))}</b><span>from ₹1,00,000 (Nifty 50: {inr(sm.get("nifty_final_value"))})</span></div>'
                f'<div><b>{sm.get("win_rate", 0):.0f}%</b><span>of trades made money</span></div>'
                f'<div><b class="pos">+{sm.get("avg_win_pct", 0):.0f}%</b><span>typical winning trade '
                f'(losing trade: {sm.get("avg_loss_pct", 0):.0f}%)</span></div>'
                f'<div><b class="neg">{pct(sm.get("full_max_dd_pct"), 0)}</b><span>worst fall from a peak '
                f'(Nifty 50: {pct(sm.get("nifty_full_max_dd_pct"), 0)})</span></div>'
                f'<div><b>{sm.get("pct_time_in_cash", 0):.0f}%</b><span>of the time the money waited aside</span></div>'
                f'</div>')
    aim = f"+{sm['avg_win_pct']:.0f}%" if sm.get("avg_win_pct") else "the typical win"

    body = f"""
<h1>How Momentum Radar works</h1>
<p class="lead">A simple, rule-based way to own the strongest Nifty 100 stocks, only when the market is healthy.</p>

<div class="sec2">In one minute</div>
{steps_html}

<div class="sec2">Why buy stocks that already went up?</div>
<div class="box"><p>It sounds odd, but it is one of the most studied patterns in markets: stocks that rose the most over
the last 3 to 12 months tend to keep doing better than the rest for a few more months. Big investors move money slowly, good
news takes time to sink in, and people chase what is working. The NSE even runs an index built on this idea
(Nifty200 Momentum 30).</p><p>It stops working sometimes, usually when the whole market turns. That is why we check the market
first.</p></div>

<div class="sec2">What are the 50-day and 200-day averages?</div>
<div class="box"><p><b>The 50-day average</b> is the average closing price of the last 50 trading days (about 2.5 months).
It shows the <b>short-term</b> direction.</p>
<p><b>The 200-day average</b> is the same over 200 trading days (about 10 months). It shows the <b>long-term</b> direction.</p>
<p><b>Why these two?</b> They are the most widely watched trend lines in the world, so many buyers and sellers react around
them. A price above both, with the 50-day above the 200-day, means both the short and the long trend are up. A price
below the 200-day often means the trend has broken.</p></div>
{nifty_html}

<div class="sec2">The signals on each stock</div>
<div class="scroll"><table class="sigt"><thead><tr><th>Indicator</th><th>If yes</th><th>If no</th></tr></thead>
<tbody>{sig_rows}</tbody></table></div>
<div class="box"><p><span class="sig BUY">BUY</span> every check passes and the stock is in the Top {n_hold}.</p>
<p><span class="sig HOLD">HOLD</span> still healthy and in the Top {keep}: keep it if you own it, don't add.</p>
<p><span class="sig SELL">SELL</span> a check failed or it fell out of the Top {keep}: sell on the next check-in day.</p>
<p><span class="sig WAIT">WAIT</span> the stock looks good but the market is weak: don't buy yet.</p></div>

<div class="sec2">Buy price, stop loss and target</div>
<div class="box"><p><b>Buy up to:</b> last closing price + {t['max_gap_pct']}%. Place a limit order at this price before 9:15 am.
If the stock opens higher and never comes back, skip it. Chasing a jump usually hurts.</p>
<p><b>Stop loss:</b> {stop} below your buy price, set as a GTT order on Kite. It caps the loss on one stock and works even when
you are not watching.</p>
<p><b>Target:</b> {aim} is the typical gain of a winning trade in the 12-year test. It is a guide, not a sell order: winners are
kept as long as they stay in the Top {keep}, and some go much further.</p>
<p><b>Sell everything</b> when the market turns weak on a check-in day.</p></div>

<div class="sec2">Did it work in the past?</div>
<p class="small muted">Tested on 12 years of real prices with all Zerodha charges, starting with ₹1,00,000.</p>
{nums}
<div class="box"><p><b>Be realistic.</b> Fewer than half the trades make money; the method works because winners are much
bigger than losers. There will be months and even years of losses. The test also uses today's Nifty 100 list for all years,
which flatters the result, so expect less in real life.</p></div>
<a class="howlink" href="backtest.html" style="display:flex;justify-content:space-between;text-decoration:none;color:var(--text);
background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:14px 16px;margin-top:10px">
<b>See the full 12-year test</b><span style="color:var(--blue);font-weight:700">Open &rarr;</span></a>
"""
    charts = {"NIFTY": nifty_chart} if nifty_chart else {}
    head = f'<script src="{LIB_URL}"></script>' if charts else ""
    js = ("window.__CHARTS=" + json.dumps(charts, separators=(",", ":")) + ";" + CHART_JS) if charts else ""
    html = page("How it works", body, js, brand=brand, head_extra=head, active="how.html")
    return html.replace("</style>", HOW_CSS + "</style>", 1)
