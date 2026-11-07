"""Build the check-in web page (report.html / index.html)."""
from __future__ import annotations

import json

from .checkin import HoldingCheck, Pick
from .dashboard import build_dashboard_html

FAILED_BANNER = "STRATEGY FAILED OUT OF SAMPLE"

def build_report_html(ctx: dict, cfg: dict) -> str:
    """The dashboard page (index.html / report.html)."""
    return build_dashboard_html(ctx, cfg)


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
