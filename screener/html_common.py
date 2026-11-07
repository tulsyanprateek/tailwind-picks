"""Shared HTML pieces: dark mobile-first CSS and inline SVG charts (no libraries)."""
from __future__ import annotations

import html
import math

import pandas as pd

from .utils import inr

CSS = """
:root{--bg:#0b0e14;--panel:#121722;--panel2:#171d2a;--line:#1f2736;--text:#e6e9f0;--muted:#8a94a7;
--green:#22c55e;--green-bg:rgba(34,197,94,.12);--red:#ef4444;--red-bg:rgba(239,68,68,.12);--amber:#f5b942;
--amber-bg:rgba(245,185,66,.12);--blue:#3b82f6;--violet:#a78bfa;--grey:#7d8696}
*{box-sizing:border-box}
html,body{margin:0;color:var(--text);
font:15px/1.55 Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
-webkit-font-smoothing:antialiased}
html{background:var(--bg)}
body{background:var(--bg);min-height:100vh;font-feature-settings:"tnum" 1}
.wrap{max-width:1280px;margin:0 auto;padding:12px 14px 28px}
h1,h2,h3{font-family:"Space Grotesk",Inter,sans-serif}h1{font-size:24px;margin:4px 0 2px;letter-spacing:-.02em}h2{font-size:18px;margin:30px 0 12px;letter-spacing:-.01em}h3{font-size:15px;margin:16px 0 6px}
.muted{color:var(--muted)}.small{font-size:13px}
.banner{border-radius:16px;padding:14px 16px;margin:12px 0;font-weight:600}
.banner.red{background:var(--red-bg);border:1px solid var(--red);color:#ffd6d6}
.banner.green{background:var(--green-bg);border:1px solid var(--green);color:#d4f5e4}
.banner.amber{background:var(--amber-bg);border:1px solid var(--amber);color:#fbe6b8}
.banner .big{font-size:20px;display:block;margin-bottom:4px}
.banner p{margin:6px 0 0;font-weight:400}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin:12px 0}
.badge{display:inline-block;border-radius:999px;padding:2px 10px;font-size:13px;font-weight:600}
.badge.green{background:var(--green-bg);color:var(--green)}.badge.red{background:var(--red-bg);color:var(--red)}
.badge.amber{background:var(--amber-bg);color:var(--amber)}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;border:1px solid var(--line);border-radius:14px;background:var(--panel)}
table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}
th,td{padding:7px 10px;text-align:right;white-space:nowrap;border-bottom:1px solid var(--line)}
th:first-child,td:first-child{text-align:left}
thead th{background:var(--panel2);color:var(--muted);font-weight:600;position:sticky;top:0}
td.hl,th.hl{background:rgba(59,130,246,.10)}
.pos{color:var(--green)}.neg{color:var(--red)}
.kv{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px}
.kv div{display:flex;justify-content:space-between;gap:8px;border-bottom:1px dashed var(--line);padding:3px 0}
.kv span:first-child{color:var(--muted)}
@media(max-width:560px){.kv{grid-template-columns:1fr}}
svg text{fill:var(--muted);font-size:14px}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:13px;color:var(--muted);margin:6px 0}
.legend i{display:inline-block;width:12px;height:3px;vertical-align:middle;margin-right:5px}
button{background:var(--blue);color:#fff;border:0;border-radius:8px;
padding:9px 16px;font-size:14px;font-weight:700;cursor:pointer}
button:active{transform:translateY(1px)}
ul{padding-left:20px}li{margin:3px 0}
footer{margin:32px 0 12px;color:var(--muted);font-size:13px;border-top:1px solid var(--line);padding-top:12px}
"""

FOOTER = ("Screening tool for personal use. Not investment advice. "
          "Past backtest results do not guarantee future returns.")

DISCLAIMER = ("Momentum Radar is a free personal experiment. Not investment advice and not a "
              "recommendation to buy or sell. The author is not registered with SEBI as an investment "
              "adviser or research analyst. Stocks can lose money; past results do not guarantee future "
              "returns. Do your own research or ask a SEBI-registered adviser.")

BRAND_CSS = """
.topbar{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:0 0 14px}
.brand{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--text)}
.logo{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;
background:conic-gradient(from 200deg,#60a5fa,#a78bfa,#34d399,#60a5fa);box-shadow:0 0 24px rgba(96,165,250,.35)}
.logo i{width:12px;height:12px;border-radius:50%;background:#070b14;box-shadow:0 0 0 3px rgba(7,11,20,.35)}
.bname{font-family:"Space Grotesk",Inter,sans-serif;font-weight:700;font-size:17px;letter-spacing:-.02em;line-height:1.1}.btag{font-size:11.5px;color:var(--muted)}
.exp{font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:4px 9px;border-radius:999px;
color:#fbbf24;background:rgba(251,191,36,.10);border:1px solid rgba(251,191,36,.25);white-space:nowrap}
.nav{display:flex;gap:4px;margin:0 0 12px;padding:4px;border-radius:12px;background:var(--panel);border:1px solid var(--line)}
.nav a{flex:1;text-align:center;font-size:13.5px;font-weight:700;color:var(--muted);text-decoration:none;padding:8px 6px;border-radius:10px}
.nav a.on{color:#fff;background:var(--panel2);box-shadow:inset 0 -2px 0 var(--blue)}
.disc{font-size:12px;color:#c9b98a;background:rgba(251,191,36,.06);border:1px solid rgba(251,191,36,.16);
border-radius:12px;padding:10px 12px;margin:0 0 10px}
"""


def esc(s) -> str:
    return html.escape(str(s))


FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900'
         '&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">')
NAV = [("index.html", "Dashboard"), ("how.html", "How it works"), ("backtest.html", "12-year test")]


def page(title: str, body: str, extra_js: str = "", brand: tuple[str, str] | None = None,
         head_extra: str = "", active: str = "") -> str:
    name, tagline = brand or ("Momentum Radar", "Nifty 100 trend tracker")
    top = (f'<div class="topbar"><a class="brand" href="index.html"><span class="logo"><i></i></span>'
           f'<span><div class="bname">{esc(name)}</div><div class="btag">{esc(tagline)}</div></span></a>'
           f'<span class="exp">Free experiment</span></div>'
           + '<nav class="nav">' + "".join(f'<a href="{h}" class="{"on" if h == active else ""}">{t}</a>'
                                          for h, t in NAV) + "</nav>")
    return (f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<meta name=\"robots\" content=\"noindex,nofollow\"><meta name=\"theme-color\" content=\"#070b14\">"
            f"<title>{esc(name)} | {esc(title)}</title>{FONTS}<style>{CSS}{BRAND_CSS}</style>{head_extra}</head>"
            f"<body><div class=\"wrap\">{top}{body}<footer><div class=\"disc\">{esc(DISCLAIMER)}</div>"
            f"{esc(name)}. {esc(FOOTER)}</footer></div>"
            f"{'<script>' + extra_js + '</script>' if extra_js else ''}</body></html>")


def _nice_ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    if hi <= lo:
        return [lo]
    raw = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(raw))
    step = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw), default=raw)
    first = math.ceil(lo / step) * step
    ticks, v = [], first
    while v <= hi + 1e-9:
        ticks.append(v)
        v += step
    return ticks


def line_chart(series: list[tuple[str, pd.Series, str]], y_fmt=lambda v: inr(v),
               height: int = 260, vline: pd.Timestamp | None = None, vline_label: str = "",
               fill_below_zero: bool = False) -> str:
    """series: [(label, values indexed by date, css colour)]. Weekly points are plenty."""
    W, H, L, R, T, B = 600, height, 78, 10, 12, 28
    s0 = [s.resample("W-FRI").last().dropna() for _, s, _ in series]
    x0 = min(s.index[0] for s in s0)
    x1 = max(s.index[-1] for s in s0)
    lo = min(float(s.min()) for s in s0)
    hi = max(float(s.max()) for s in s0)
    if fill_below_zero:
        hi = max(hi, 0)
    pad = (hi - lo) * 0.05 or 1
    lo, hi = lo - pad, hi + (0 if fill_below_zero else pad)
    span = (x1 - x0).days or 1

    def X(d):
        return L + (W - L - R) * (d - x0).days / span

    def Y(v):
        return T + (H - T - B) * (1 - (v - lo) / (hi - lo))

    parts = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" '
             f'style="display:block;height:auto">']
    for v in _nice_ticks(lo, hi):
        y = Y(v)
        parts.append(f'<line x1="{L}" x2="{W - R}" y1="{y:.1f}" y2="{y:.1f}" stroke="#2a2f3a"/>')
        parts.append(f'<text x="{L - 6}" y="{y + 4:.1f}" text-anchor="end">{esc(y_fmt(v))}</text>')
    for yr in range(x0.year + 1, x1.year + 1):
        d = pd.Timestamp(year=yr, month=1, day=1)
        x = X(d)
        if (yr - x0.year) % max(1, (x1.year - x0.year) // 8 + 1) == 0:
            parts.append(f'<text x="{x:.1f}" y="{H - 8}" text-anchor="middle">{yr}</text>')
        parts.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{T}" y2="{H - B}" stroke="#1f232c"/>')
    if vline is not None and x0 <= vline <= x1:
        x = X(vline)
        parts.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{T}" y2="{H - B}" stroke="#f5b942" '
                     f'stroke-dasharray="4 4"/>')
        parts.append(f'<text x="{x + 4:.1f}" y="{T + 12}" style="fill:#f5b942">{esc(vline_label)}</text>')
    for (label, _, colour), s in zip(series, s0):
        pts = " ".join(f"{X(d):.1f},{Y(v):.1f}" for d, v in s.items())
        if fill_below_zero:
            area = f"{X(s.index[0]):.1f},{Y(0):.1f} {pts} {X(s.index[-1]):.1f},{Y(0):.1f}"
            parts.append(f'<polygon points="{area}" fill="{colour}" fill-opacity="0.18"/>')
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{colour}" stroke-width="1.8"/>')
    parts.append("</svg>")
    legend = "".join(f'<span><i style="background:{c}"></i>{esc(lab)}</span>' for lab, _, c in series)
    return f'<div class="legend">{legend}</div>' + "".join(parts)


def bar_chart(bins: list[tuple[str, int]], height: int = 220) -> str:
    W, H, L, R, T, B = 600, height, 36, 6, 14, 32
    n = len(bins)
    top = max((c for _, c in bins), default=1) or 1
    bw = (W - L - R) / n
    parts = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" style="display:block;height:auto">']
    for v in _nice_ticks(0, top, 4):
        y = T + (H - T - B) * (1 - v / top)
        parts.append(f'<line x1="{L}" x2="{W - R}" y1="{y:.1f}" y2="{y:.1f}" stroke="#2a2f3a"/>')
        parts.append(f'<text x="{L - 6}" y="{y + 4:.1f}" text-anchor="end">{int(v)}</text>')
    for k, (label, c) in enumerate(bins):
        h = (H - T - B) * c / top
        x = L + k * bw
        neg = label.startswith("<") or label.startswith("-")
        colour = "#ff5d5d" if neg else "#3fbf7f"
        parts.append(f'<rect x="{x + 2:.1f}" y="{H - B - h:.1f}" width="{bw - 4:.1f}" height="{h:.1f}" '
                     f'fill="{colour}" fill-opacity="0.8"><title>{esc(label)}R: {c}</title></rect>')
        parts.append(f'<text x="{x + bw / 2:.1f}" y="{H - 10}" text-anchor="middle">{esc(label)}</text>')
    parts.append("</svg>")
    return "".join(parts)
