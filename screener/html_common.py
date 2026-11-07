"""Shared HTML pieces: dark mobile-first CSS and inline SVG charts (no libraries)."""
from __future__ import annotations

import html
import math

import pandas as pd

from .utils import inr

CSS = """
:root{--bg:#0f1115;--panel:#171a21;--panel2:#1d212a;--line:#2a2f3a;--text:#e7e9ee;--muted:#9aa3b2;
--green:#3fbf7f;--green-bg:#123524;--red:#ff5d5d;--red-bg:#3a1414;--amber:#f5b942;--amber-bg:#3a2d10;
--blue:#6aa8ff;--grey:#7d8696}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--text);
font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:16px}
h1{font-size:22px;margin:4px 0 2px}h2{font-size:18px;margin:28px 0 10px}h3{font-size:15px;margin:16px 0 6px}
.muted{color:var(--muted)}.small{font-size:13px}
.banner{border-radius:10px;padding:14px 16px;margin:12px 0;font-weight:600}
.banner.red{background:var(--red-bg);border:1px solid var(--red);color:#ffd6d6}
.banner.green{background:var(--green-bg);border:1px solid var(--green);color:#d4f5e4}
.banner.amber{background:var(--amber-bg);border:1px solid var(--amber);color:#fbe6b8}
.banner .big{font-size:20px;display:block;margin-bottom:4px}
.banner p{margin:6px 0 0;font-weight:400}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:12px 0}
.badge{display:inline-block;border-radius:999px;padding:2px 10px;font-size:13px;font-weight:600}
.badge.green{background:var(--green-bg);color:var(--green)}.badge.red{background:var(--red-bg);color:var(--red)}
.badge.amber{background:var(--amber-bg);color:var(--amber)}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}
th,td{padding:7px 10px;text-align:right;white-space:nowrap;border-bottom:1px solid var(--line)}
th:first-child,td:first-child{text-align:left}
thead th{background:var(--panel2);color:var(--muted);font-weight:600;position:sticky;top:0}
td.hl,th.hl{background:#1b2533}
.pos{color:var(--green)}.neg{color:var(--red)}
.kv{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px}
.kv div{display:flex;justify-content:space-between;gap:8px;border-bottom:1px dashed var(--line);padding:3px 0}
.kv span:first-child{color:var(--muted)}
@media(max-width:560px){.kv{grid-template-columns:1fr}}
svg text{fill:var(--muted);font-size:14px}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:13px;color:var(--muted);margin:6px 0}
.legend i{display:inline-block;width:12px;height:3px;vertical-align:middle;margin-right:5px}
button{background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:8px;
padding:8px 14px;font-size:14px;cursor:pointer}
button:active{transform:translateY(1px)}
ul{padding-left:20px}li{margin:3px 0}
footer{margin:32px 0 12px;color:var(--muted);font-size:13px;border-top:1px solid var(--line);padding-top:12px}
"""

FOOTER = ("Screening tool for personal use. Not investment advice. "
          "Past backtest results do not guarantee future returns.")


def esc(s) -> str:
    return html.escape(str(s))


def page(title: str, body: str, extra_js: str = "") -> str:
    return (f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{esc(title)}</title><style>{CSS}</style></head><body><div class=\"wrap\">"
            f"{body}<footer>{esc(FOOTER)}</footer></div>"
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
