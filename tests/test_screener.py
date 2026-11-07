"""Acceptance tests. Run with:  python -m pytest -q"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from screener import costs
from screener import indicators as ind
from screener.config import load_config
from screener.metrics import verdict
from screener.portfolio import build_ohlc, simulate
from screener.report_backtest import FAILED_TEXT, build_backtest_html
from screener.signals import (build_panels, compute_symbol_signals, ranked_eligible,
                              rebalance_indices, regime_series)
from screener.trade import gap_too_large, limit_fill, limit_price, plan_trade, quantity, raised_stop


@pytest.fixture(scope="module")
def cfg():
    return load_config()


@pytest.fixture(scope="module")
def atr_cfg():
    """The original tight ATR stop with a 3R target (the spec's stop and target maths)."""
    c = load_config()
    c["trade"].update({"stop_mode": "atr", "use_target": True})
    return c


def _fixture_ohlc():
    idx = pd.bdate_range("2024-01-01", periods=6)
    return pd.DataFrame({
        "Open":  [10, 11, 12, 11, 13, 14],
        "High":  [11, 12, 13, 12, 14, 15],
        "Low":   [9, 10, 11, 10, 12, 13],
        "Close": [10, 12, 12, 11, 14, 14],
    }, index=idx, dtype=float)


def _trending_prices(n=600, seed=0, drift=0.0008, start="2020-01-01"):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start, periods=n)
    close = 100 * np.exp(np.cumsum(drift + rng.normal(0, 0.012, n)))
    op = close * (1 + rng.normal(0, 0.003, n))
    high = np.maximum(op, close) * (1 + np.abs(rng.normal(0, 0.006, n)))
    low = np.minimum(op, close) * (1 - np.abs(rng.normal(0, 0.006, n)))
    return pd.DataFrame({"Open": op, "High": high, "Low": low, "Close": close,
                         "Volume": rng.integers(1e5, 1e6, n).astype(float)}, index=idx)


# 1. Indicators ------------------------------------------------------------------------

def test_sma_matches_hand_calculation():
    s = _fixture_ohlc()["Close"]
    out = ind.sma(s, 3)
    assert out.iloc[:2].isna().all()
    # (10+12+12)/3, (12+12+11)/3, (12+11+14)/3, (11+14+14)/3
    assert out.iloc[2:].round(6).tolist() == [round(34 / 3, 6), round(35 / 3, 6), round(37 / 3, 6), 13.0]


def test_atr_matches_hand_calculation():
    d = _fixture_ohlc()
    # True ranges: day1 H-L=2; day2 max(2,|12-10|,|10-10|)=2; day3 max(2,|13-12|,|11-12|)=2;
    # day4 max(2,|12-12|,|10-12|)=2; day5 max(2,|14-11|,|12-11|)=3; day6 max(2,|15-14|,|13-14|)=2
    assert ind.true_range(d["High"], d["Low"], d["Close"]).tolist() == [2, 2, 2, 2, 3, 2]
    a = ind.atr(d["High"], d["Low"], d["Close"], 3)
    # Wilder: first = mean(2,2,2)=2; then (2*2+2)/3=2; (2*2+3)/3=7/3; (7/3*2+2)/3=20/9
    assert a.iloc[:2].isna().all()
    assert a.iloc[2:].tolist() == pytest.approx([2, 2, 7 / 3, 20 / 9])


def test_52_week_high_low_rolling():
    d = _fixture_ohlc()
    assert ind.rolling_high(d["High"], 3).iloc[2:].tolist() == [13, 13, 14, 15]
    assert ind.rolling_low(d["Low"], 3).iloc[2:].tolist() == [9, 10, 10, 10]


# 2. Filters and schedule --------------------------------------------------------------

def test_trend_template_passes_uptrend_and_fails_downtrend(cfg):
    up = compute_symbol_signals(_trending_prices(drift=0.002, seed=1), cfg)
    down = compute_symbol_signals(_trending_prices(drift=-0.002, seed=1), cfg)
    assert up["trend_ok"].iloc[-60:].mean() > 0.8
    assert not down["trend_ok"].iloc[-60:].any()


def test_rebalance_days_are_first_session_on_or_after_1st_and_15th():
    cal = pd.bdate_range("2025-03-01", "2025-04-30")   # 1 Mar 2025 is a Saturday
    days = [cal[i] for i in rebalance_indices(cal, [1, 15])]
    assert [d.strftime("%Y-%m-%d") for d in days] == ["2025-03-03", "2025-03-17", "2025-04-01", "2025-04-15"]


# 3. Stop and target maths -------------------------------------------------------------

def test_stop_target_and_quantity(atr_cfg):
    plan = plan_trade(1000.0, 25.0, atr_cfg)           # entry 1,000, ATR(14) 25
    assert plan.stop == pytest.approx(950)          # 1000 - 2 x 25 (within the 8% cap)
    assert plan.risk_per_share == pytest.approx(50)
    assert plan.breakeven_level == pytest.approx(1050)   # +1R: stop moves to entry
    assert plan.target == pytest.approx(1150)            # +3R
    assert quantity(20000, 1000.0) == 20                 # 1/5 of 1,00,000 at 1,000


# 4. Stop never wider than 8% ----------------------------------------------------------

def test_stop_is_capped_at_8_percent(atr_cfg):
    plan = plan_trade(1000.0, 60.0, atr_cfg)            # 2 x ATR = 120 = 12%, too wide
    assert plan.stop == pytest.approx(920)
    assert plan.target == pytest.approx(1240)


def test_stop_is_only_ever_raised(atr_cfg):
    assert raised_stop(950, 1000, 50, 980, 25, atr_cfg) == 950          # 980 - 50 = 930 < 950: unchanged
    assert raised_stop(950, 1000, 50, 1060, 25, atr_cfg) == 1010        # 1060 - 50
    assert raised_stop(950, 1000, 50, 1050, 40, atr_cfg) == 1000        # +1R reached: at least entry


def test_percent_safety_net_stop(cfg):
    c = {**cfg, "trade": {**cfg["trade"], "stop_mode": "percent", "stop_pct": 15,
                          "use_target": False, "trail_stop_at_checkin": False}}
    plan = plan_trade(1000.0, 25.0, c)
    assert plan.stop == pytest.approx(850)
    assert math.isinf(plan.target)
    assert raised_stop(850, 1000, 150, 1300, 25, c) == 850        # fixed: never moves
    c["trade"]["trail_stop_at_checkin"] = True
    assert raised_stop(850, 1000, 150, 1300, 25, c) == pytest.approx(1105)   # 1300 x 0.85
    assert raised_stop(850, 1000, 150, 900, 25, c) == 850         # never lowered


# 5. Gap rule --------------------------------------------------------------------------

def test_gap_above_2_percent_means_no_entry(cfg):
    last_close = 1000.0
    assert limit_price(last_close, cfg) == pytest.approx(1020)
    assert gap_too_large(1025.0, last_close, cfg)                 # opens 2.5% up
    assert limit_fill(1025.0, 1022.0, limit_price(last_close, cfg)) is None   # never back to limit
    assert limit_fill(1025.0, 1015.0, 1020.0) == 1020.0          # dips to the limit: fills there
    assert limit_fill(1010.0, 1000.0, 1020.0) == 1010.0          # opens below the limit: fills at open


# 6. No lookahead ----------------------------------------------------------------------

def test_signals_shift_with_the_data(cfg):
    df = _trending_prices(seed=3, drift=0.001)
    base = compute_symbol_signals(df, cfg)
    shifted_df = df.shift(1).dropna()            # same prices, each one day later
    shifted = compute_symbol_signals(shifted_df, cfg)
    for col in ("trend_ok", "rs_score", "atr", "close"):
        a = base[col].iloc[:-1].to_numpy()
        b = shifted[col].to_numpy()
        if a.dtype == bool:
            assert (a[260:] == b[260:]).all(), col
        else:
            assert np.allclose(a[260:], b[260:], equal_nan=True), col


def test_signals_do_not_change_when_future_data_is_removed(cfg):
    df = _trending_prices(seed=4)
    full = compute_symbol_signals(df, cfg)
    for cut in (300, 420, 550):
        part = compute_symbol_signals(df.iloc[:cut + 1], cfg)
        pd.testing.assert_series_equal(part.iloc[-1], full.iloc[cut], check_names=False)


def test_entry_is_always_after_signal_day(cfg):
    prices = {f"S{k}": _trending_prices(n=700, seed=10 + k, drift=0.0004 + 0.0002 * k) for k in range(8)}
    index_df = _trending_prices(n=700, seed=99, drift=0.0006)
    signals = {s: compute_symbol_signals(d, cfg) for s, d in prices.items()}
    cal = index_df.index
    panels = build_panels(signals, regime_series(index_df, cfg), cal)
    ohlc = build_ohlc(prices, list(signals), cal)
    mods = {**cfg["modules"], "fundamentals": False}
    res = simulate(panels, ohlc, cfg, cal[300], cal[-1], mods)
    assert len(res.trades) > 0
    assert (res.trades["entry_date"] > res.trades["signal_date"]).all()
    # Picks on a check-in only use the previous close: ranking at day i-1 is unaffected by day i.
    i = 400
    before = ranked_eligible(panels, i - 1, cfg, mods)
    panels.rs_score.iloc[i] = np.nan
    assert ranked_eligible(panels, i - 1, cfg, mods) == before


# 7. Costs -----------------------------------------------------------------------------

def test_round_trip_costs(cfg):
    buy, sell = 5 * 4980, 5 * 5450
    total = costs.round_trip_charges(buy, sell, cfg)
    # STT 52.15 + txn 1.60 + SEBI 0.05 + stamp 3.74 + GST 0.30 + DP 15.93 = 73.77
    assert total == pytest.approx(73.77, abs=0.05)
    assert round(total) == 74


# 8. Failure banner --------------------------------------------------------------------

def _summary(**kw):
    base = {"start": pd.Timestamp("2021-01-01"), "end": pd.Timestamp("2025-01-01"), "final_value": 90000.0,
            "net_pnl": -10000.0, "cagr": -2.0, "max_dd_pct": -25.0, "max_dd_inr": -25000.0, "trades": 10,
            "win_rate": 30.0, "avg_win": 2000.0, "avg_loss": -1500.0, "avg_r": -0.2, "expectancy_inr": -400.0,
            "expectancy_r": -0.2, "profit_factor": 0.6, "longest_losing_streak": 5, "pct_months_positive": 40.0,
            "avg_holding_sessions": 12.0, "avg_holding_days": 17.0, "pct_time_in_cash": 30.0,
            "total_charges": 900.0}
    base.update(kw)
    return base


def test_negative_expectancy_shows_failed_banner(cfg):
    oos = _summary()
    bench = {"start": oos["start"], "end": oos["end"], "final_value": 140000.0, "net_pnl": 40000.0,
             "cagr": 9.0, "max_dd_pct": -15.0, "max_dd_inr": -15000.0}
    v = verdict(oos, bench)
    assert not v["passed"]
    idx = pd.bdate_range("2021-01-01", "2025-01-01")
    eq = pd.Series(np.linspace(100000, 90000, len(idx)), index=idx)
    trades = pd.DataFrame({"symbol": ["X"], "entry_date": [idx[5]], "exit_date": [idx[9]], "qty": [10],
                           "entry": [100.0], "initial_stop": [95.0], "target": [115.0], "exit": [95.0],
                           "exit_reason": ["stop loss"], "sessions": [4], "charges": [20.0], "slippage": [2.0],
                           "net_pnl": [-72.0], "r_multiple": [-1.44]})
    ctx = {"generated": pd.Timestamp("2025-01-02"), "verdict": v, "full": oos, "is": oos, "oos": oos,
           "bench_full": bench, "bench_is": bench, "bench_oos": bench, "equity_full": eq,
           "bench_eq_full": eq * 1.1, "trades_full": trades,
           "ablation": [{"name": "Full system", "full": oos, "oos": oos}],
           "sanity": {"symbols_tested": 1, "universe_size": 1, "universe_source": "test", "data_start": idx[0],
                      "data_end": idx[-1], "missing_text": "none", "lookahead_text": "ok", "checkins": 1,
                      "checkins_regime_off": 0, "gap_skipped": 0}}
    out = build_backtest_html(ctx, cfg)
    assert FAILED_TEXT in out
    assert 'class="banner red"' in out
    assert "—" not in out          # no em dashes


def test_passing_case_has_no_failed_banner(cfg):
    oos = _summary(expectancy_inr=500.0, cagr=15.0, max_dd_pct=-20.0)
    bench = {"cagr": 10.0, "max_dd_pct": -15.0}
    assert verdict(oos, bench)["passed"]
