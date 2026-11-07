"""Check-in dates, the buy list and the holdings check for the live report."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd

from . import costs
from .fundamentals import FundResult, evaluate, results_flag
from .signals import Panels, ranked_eligible
from .trade import limit_price, plan_trade, quantity, raised_stop
from .utils import inr


# --------------------------------------------------------------------------- dates

def next_weekday(d: date) -> date:
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def is_checkin_session(prev_session: date, session: date, days_of_month: list[int]) -> bool:
    """True when `session` is the first trading day on or after the 1st or 15th."""
    for d in days_of_month:
        anchor = date(session.year, session.month, d)
        if prev_session < anchor <= session:
            return True
    return False


def next_checkin(after: date, days_of_month: list[int]) -> date:
    """First weekday on or after the next anchor date that is later than `after`.
    (NSE holidays are not known; if that day is a holiday, use the next trading day.)"""
    d = after
    while True:
        d = next_weekday(d)
        if is_checkin_session(_prev_weekday(d), d, days_of_month):
            return d


def _prev_weekday(d: date) -> date:
    d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def tick_for(price: float) -> float:
    """A tick size that is valid on NSE at this price whichever tick table applies
    (multiples of a larger tick are always valid for a smaller one)."""
    if price < 1000:
        return 0.05
    if price < 5000:
        return 0.10
    if price < 10000:
        return 0.50
    if price < 20000:
        return 1.00
    return 5.00


def round_to_tick(price: float, mode: str = "down") -> float:
    tick = tick_for(price)
    steps = price / tick
    steps = math.floor(steps + 1e-9) if mode == "down" else math.ceil(steps - 1e-9) if mode == "up" else round(steps)
    return round(steps * tick, 2)


# --------------------------------------------------------------------------- why this stock

@dataclass
class Why:
    symbol: str
    company: str
    rank: int
    reasons: list[str]
    meta: str
    about: str
    risk: str
    oneliner: str = ""
    stats: dict = field(default_factory=dict)
    brands: list[str] = field(default_factory=list)
    domain: str = ""
    signals: list = field(default_factory=list)   # (indicator, reading, BUY/HOLD/SELL/WAIT, meaning)
    overall: str = ""                             # BUY, HOLD, SELL or WAIT
    levels: dict = field(default_factory=dict)    # buy, stop, aim, qty, amount
    second: list = field(default_factory=list)    # second-opinion indicators (not used for picking)
    second_agree: int = 0
    logo: str = ""                                # embedded logo image (data URI)


def load_brands(cfg: dict) -> dict[str, tuple[str, list[str]]]:
    """symbol -> (website domain for the logo, everyday brands people know)."""
    path = cfg["paths"]["data_dir"] / "brands.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path).fillna("")
    return {str(r.symbol).upper(): (str(r.domain), [b.strip() for b in str(r.known_for).split(";") if b.strip()])
            for r in df.itertuples(index=False)}


def _ret(c: pd.Series, n: int) -> float:
    return float(c.iloc[-1] / c.iloc[-1 - n] - 1) * 100 if len(c) > n else math.nan


def why_stock(sym: str, rank: int, rs_pct: float, trend_ok: bool, df: pd.DataFrame,
              index_df: pd.DataFrame, data_ts: pd.Timestamp, profile: dict,
              fund: FundResult | None, cfg: dict,
              brand_info: tuple[str, list[str]] | None = None, market_on: bool = True) -> Why:
    """Plain-language reasons. These are the real reasons the method picked the stock
    (price strength and trend), plus what the company does for context."""
    c = df["Close"].loc[:data_ts]
    nc = index_df["Close"].loc[:data_ts]
    r12, r6, r3 = _ret(c, 252), _ret(c, 126), _ret(c, 63)
    n12 = _ret(nc, 252)
    reasons = []
    if not math.isnan(r12):
        reasons.append(f"Up {r12:+.0f}% in the last 12 months, while the Nifty 50 moved {n12:+.0f}%.")
    if not math.isnan(r3):
        if r6 > 0 and r3 > 0:
            reasons.append(f"Still rising lately: {r6:+.0f}% in 6 months and {r3:+.0f}% in 3 months.")
        else:
            reasons.append(f"Has cooled off lately ({r3:+.0f}% in 3 months), but is still strong over the year.")
    if rs_pct >= 99.5:
        reasons.append(f"The strongest Nifty 100 stock over the last 3 to 12 months (rank #{rank} on the list).")
    else:
        reasons.append(f"Stronger than {rs_pct:.0f}% of Nifty 100 stocks over the last 3 to 12 months "
                       f"(rank #{rank} on the list).")
    hi = float(df["High"].loc[:data_ts].iloc[-252:].max())
    gap = (1 - c.iloc[-1] / hi) * 100
    where = "at its 52-week high" if gap < 1 else f"{gap:.0f}% below its 52-week high"
    if trend_ok:
        reasons.append(f"Trading {where} and above its 50, 150 and 200-day averages: a steady uptrend.")
    else:
        reasons.append(f"Trading {where}.")
    if fund is not None and fund.status != "N/A":
        reasons.append(fund.summary + ".")
    meta_parts = [x for x in (profile.get("sector"), profile.get("industry")) if x]
    mc = profile.get("market_cap")
    if mc:
        meta_parts.append(f"Market value {inr(mc / 1e7)} crore")
    t = cfg["trade"]
    stop_txt = f"the {t['stop_pct']:g}% stop loss" if t.get("stop_mode") == "percent" else "the stop loss"
    risk = ("Picked for its price strength, not because of a forecast about the business. Strong stocks "
            f"can fall quickly; {stop_txt} limits the loss.")
    if rs_pct >= 90 and trend_ok:
        one = "One of the fastest-rising Nifty 100 stocks, still in a steady uptrend."
    elif trend_ok:
        one = "Rising faster than most Nifty 100 stocks, in a steady uptrend."
    else:
        one = "Strong over the year, but its trend is not clean right now."
    domain, brands = brand_info or ("", [])
    stats = {"r12": r12, "n12": n12, "r3": r3, "gap": gap, "rs_pct": rs_pct}
    signals, overall = indicator_signals(c, hi, r12, n12, rank, market_on, cfg)
    return Why(sym, profile.get("name") or sym, rank, reasons, " · ".join(meta_parts),
               profile.get("summary") or "", risk, one, stats, brands, domain, signals, overall)


def indicator_signals(c: pd.Series, hi52: float, r12: float, n12: float, rank: int, market_on: bool,
                      cfg: dict) -> tuple[list, str]:
    """Each rule of the method as one row: what it reads today and what it says."""
    from . import indicators as ind
    close = float(c.iloc[-1])
    s50, s200 = float(ind.sma(c, 50).iloc[-1]), float(ind.sma(c, 200).iloc[-1])
    s200_prev = float(ind.sma(c, 200).iloc[-21]) if len(c) > 221 else math.nan
    n_hold, keep = cfg["portfolio"]["holdings"], cfg["portfolio"]["keep_if_rank_within"]
    rows = [
        ("Market (Nifty 50)", "Strong" if market_on else "Weak", "BUY" if market_on else "WAIT",
         "Buy only when the whole market is rising"),
        ("Price vs 50-day average", f"{(close / s50 - 1) * 100:+.0f}%", "BUY" if close > s50 else "SELL",
         "Above = short-term trend is up"),
        ("50-day vs 200-day average", "Above" if s50 > s200 else "Below", "BUY" if s50 > s200 else "SELL",
         "Above = long-term trend is up"),
        ("200-day average", "Rising" if s200 > s200_prev else "Falling", "BUY" if s200 > s200_prev else "SELL",
         "Rising = the big trend is healthy"),
        ("Distance from 1-year high", "At high" if close >= hi52 * 0.99 else f"{(close / hi52 - 1) * 100:.0f}%",
         "BUY" if close >= 0.75 * hi52 else "SELL", "Within 25% of the high = still strong"),
        ("1 year vs Nifty 50", f"{r12:+.0f}% vs {n12:+.0f}%", "BUY" if r12 > n12 else "SELL",
         "Rising faster than the market"),
        ("Momentum rank", f"#{rank}", "BUY" if rank <= n_hold else "HOLD" if rank <= keep else "SELL",
         f"Top {n_hold} = buy, top {keep} = hold, below = sell"),
    ]
    stock_rows = [r[2] for r in rows[1:]]
    if not market_on:
        overall = "WAIT"
    elif "SELL" in stock_rows:
        overall = "SELL"
    elif rank <= n_hold:
        overall = "BUY"
    else:
        overall = "HOLD"
    return rows, overall


# --------------------------------------------------------------------------- buy list

@dataclass
class Pick:
    symbol: str
    company: str
    industry: str
    rank: int
    rs_pct: float
    rs_score: float
    last_close: float
    limit: float
    qty: int
    position_value: float
    stop: float
    stop_pct: float
    target: float | None
    gtt_stop_limit: float
    round_trip_cost: float
    risk_inr: float
    fund: FundResult
    results_level: str
    results_text: str
    filters: list[tuple[str, bool]]
    closes: list[float] = field(default_factory=list)
    order_text: str = ""
    why: "Why | None" = None


def _filters_for(p: Panels, i: int, sym: str, cfg: dict, fund: FundResult) -> list[tuple[str, bool]]:
    out = [("Nifty 50 uptrend (market filter)", bool(p.regime.iloc[i])),
           ("Stock in a healthy uptrend (trend template)", bool(p.trend_ok.iloc[i][sym])),
           (f"Momentum in the top {100 - cfg['relative_strength']['min_percentile']}%",
            bool(p.rs_pct.iloc[i][sym] >= cfg["relative_strength"]["min_percentile"]))]
    if cfg["modules"].get("fundamentals", True):
        out.append((f"Quality filter: {fund.status}", fund.status == "PASS"))
    return out


def make_pick(sym: str, rank: int, p: Panels, i: int, universe: pd.DataFrame, cfg: dict,
              fund: FundResult, res_cal, today: date, budget: float) -> Pick:
    t = cfg["trade"]
    close = float(p.close.iloc[i][sym])
    lim = round_to_tick(limit_price(close, cfg), "down")
    qty = quantity(budget, lim)
    plan = plan_trade(close, float(p.atr.iloc[i][sym]), cfg)   # stop from the last close
    stop = round_to_tick(plan.stop, "nearest")
    stop_limit = round_to_tick(stop * (1 - t["gtt_stop_limit_below_pct"] / 100), "down")
    target = round_to_tick(plan.target, "nearest") if math.isfinite(plan.target) else None
    value = qty * close
    rt = costs.round_trip_charges(value, value, cfg) + 2 * costs.slippage_amount(value, cfg)
    row = universe.set_index("symbol").loc[sym] if sym in set(universe["symbol"]) else None
    company = str(row["company"]) if row is not None else sym
    industry = str(row["industry"]) if row is not None else ""
    level, text = results_flag(sym, res_cal, today, cfg)
    closes = p.close[sym].iloc[max(0, i - 119):i + 1].dropna().tolist()
    pk = Pick(symbol=sym, company=company, industry=industry, rank=rank,
              rs_pct=float(p.rs_pct.iloc[i][sym]), rs_score=float(p.rs_score.iloc[i][sym]),
              last_close=close, limit=lim, qty=qty, position_value=value, stop=stop,
              stop_pct=(close - stop) / close * 100, target=target, gtt_stop_limit=stop_limit,
              round_trip_cost=rt, risk_inr=qty * (close - stop), fund=fund,
              results_level=level, results_text=text,
              filters=_filters_for(p, i, sym, cfg, fund), closes=closes)
    pk.order_text = order_sheet(pk, cfg)
    return pk


def order_sheet(pk: Pick, cfg: dict) -> str:
    lines = [f"{pk.symbol} (NSE)",
             f"1. BUY  CNC  LIMIT  Qty {pk.qty}  Price {pk.limit:.2f}",
             "   (Place before 9:15 am on check-in day. If it does not fill that day, do not chase.)"]
    if pk.target is None:
        lines.append(f"2. GTT single, SELL, Qty {pk.qty}: trigger {pk.stop:.2f}, limit {pk.gtt_stop_limit:.2f}")
    else:
        lines.append(f"2. GTT OCO, SELL, Qty {pk.qty}: stop trigger {pk.stop:.2f}, stop limit "
                     f"{pk.gtt_stop_limit:.2f}; target {pk.target:.2f}")
    pct_ = cfg["trade"]["stop_pct"] if cfg["trade"].get("stop_mode") == "percent" else None
    if pct_:
        lines.append(f"   (Set after the buy fills. If you paid much more or less than {pk.last_close:.2f}, "
                     f"use your buy price minus {pct_:g}%.)")
    return "\n".join(lines)


# --------------------------------------------------------------------------- holdings

@dataclass
class HoldingCheck:
    symbol: str
    buy_date: date | None
    buy_price: float
    qty: int
    stop: float
    last_close: float
    pnl_inr: float
    pnl_pct: float
    sessions: int
    action: str          # SELL, KEEP, HOLD, STOP HIT, CHECK
    level: str           # red, green, amber
    detail: str
    new_stop: float | None = None
    rank: int | None = None


def load_open_trades(cfg: dict) -> tuple[pd.DataFrame, str | None]:
    path = cfg["paths"]["data_dir"] / "open_trades.csv"
    cols = ["symbol", "buy_date", "buy_price", "qty", "stop_loss"]
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(columns=cols).to_csv(path, index=False)
        return pd.DataFrame(columns=cols), None
    try:
        df = pd.read_csv(path)
        df.columns = [c.strip().lower() for c in df.columns]
        missing = [c for c in cols if c not in df.columns]
        if missing:
            return pd.DataFrame(columns=cols), f"open_trades.csv is missing columns: {', '.join(missing)}"
        df = df.dropna(subset=["symbol"])
        df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()
        df["buy_date"] = pd.to_datetime(df["buy_date"], dayfirst=True, errors="coerce")
        for c in ("buy_price", "qty", "stop_loss"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df[cols], None
    except Exception as exc:
        return pd.DataFrame(columns=cols), f"Could not read open_trades.csv ({exc})"


def check_holdings(trades: pd.DataFrame, prices: dict[str, pd.DataFrame], p: Panels, i: int,
                   ranked_keep: list[str], cfg: dict, checkin_next: bool, regime_on: bool,
                   next_checkin_day: date) -> list[HoldingCheck]:
    out = []
    keep_rank = cfg["portfolio"]["keep_if_rank_within"]
    keep = ranked_keep[:keep_rank]
    data_day = p.calendar[i]
    for r in trades.itertuples(index=False):
        sym = r.symbol
        bd = r.buy_date.date() if isinstance(r.buy_date, pd.Timestamp) else None
        df = prices.get(sym)
        if df is None or df.empty or math.isnan(r.buy_price) or math.isnan(r.qty):
            out.append(HoldingCheck(sym, bd, r.buy_price, int(r.qty) if not math.isnan(r.qty) else 0,
                                    r.stop_loss, math.nan, math.nan, math.nan, 0, "CHECK", "amber",
                                    "No price data or incomplete row in open_trades.csv. Check this one on Kite."))
            continue
        df = df.loc[:data_day]
        since = df.loc[pd.Timestamp(bd):] if bd else df.iloc[-1:]
        last = float(df["Close"].iloc[-1])
        qty = int(r.qty)
        pnl = (last - r.buy_price) * qty
        hc = HoldingCheck(sym, bd, float(r.buy_price), qty, float(r.stop_loss), last, pnl,
                          (last / r.buy_price - 1) * 100, len(since), "HOLD", "green", "")
        if not math.isnan(r.stop_loss) and len(since) and float(since["Low"].min()) <= r.stop_loss:
            hit_day = since.index[since["Low"] <= r.stop_loss][0]
            hc.action, hc.level = "STOP HIT", "red"
            hc.detail = (f"The price fell to your stop loss on {hit_day:%d %b}. Your GTT should have sold it. "
                         "Check Kite, then delete this row from open_trades.csv.")
            out.append(hc)
            continue
        rank = keep.index(sym) + 1 if sym in keep else None
        hc.rank = rank
        if checkin_next:
            if not regime_on:
                hc.action, hc.level = "SELL", "red"
                hc.detail = ("Market filter is OFF. Sell at tomorrow's open (market order, or cancel the GTT "
                             "and sell), then keep the money aside.")
            elif rank is None:
                hc.action, hc.level = "SELL", "red"
                hc.detail = (f"No longer in the top {keep_rank} qualifying stocks. Sell at tomorrow's open "
                             "and cancel its GTT.")
            else:
                hc.action, hc.level = "KEEP", "green"
                hc.detail = f"Still ranks {rank} of the qualifying stocks. Keep it."
                atr_v = float(p.atr.iloc[i][sym]) if sym in p.atr.columns else math.nan
                ns = raised_stop(hc.stop, hc.buy_price, hc.buy_price - hc.stop, last, atr_v, cfg)
                if ns > hc.stop + 1e-9:
                    hc.new_stop = round_to_tick(ns, "nearest")
                    hc.detail += f" Raise the GTT stop loss to {hc.new_stop:.2f}."
        else:
            hc.detail = f"Hold. Nothing to do until the check-in on {next_checkin_day:%a %d %b}."
            if not regime_on:
                hc.level = "amber"
                hc.detail += " The market filter is OFF now: if it is still OFF then, you will sell."
            elif rank is None:
                hc.level = "amber"
                hc.detail += f" It is currently outside the top {keep_rank}, so it may be sold then."
        out.append(hc)
    return out
