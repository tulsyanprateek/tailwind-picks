"""Tests for the check-in report."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from screener.checkin import is_checkin_session, next_checkin, round_to_tick, tick_for
from screener.config import load_config
from screener.fundamentals import evaluate
from screener.report_scan import FAILED_BANNER, build_report_html


@pytest.fixture(scope="module")
def cfg():
    return load_config()


def test_checkin_is_first_session_on_or_after_1st_and_15th():
    # Sat 15 Nov 2026 -> check-in is Mon 16 Nov.
    assert is_checkin_session(date(2026, 11, 13), date(2026, 11, 16), [1, 15])
    assert not is_checkin_session(date(2026, 11, 16), date(2026, 11, 17), [1, 15])
    assert next_checkin(date(2026, 11, 6), [1, 15]) == date(2026, 11, 16)
    assert next_checkin(date(2026, 11, 16), [1, 15]) == date(2026, 12, 1)


def test_prices_round_to_valid_ticks():
    assert tick_for(370) == 0.05 and tick_for(1221) == 0.10 and tick_for(51710) == 5.0
    assert round_to_tick(370.43) == 370.40
    assert round_to_tick(1221.87) == 1221.80


def test_fundamentals_missing_is_na_not_pass(cfg):
    r = evaluate("TCS", "IT", None, cfg)
    assert r.status == "N/A" and r.score is None


def test_fundamentals_pass_fail_and_bank_rules(cfg):
    cols = cfg["fundamentals"]["columns"]
    table = pd.DataFrame([
        {cols["symbol"]: "GOOD", cols["roce"]: 25, cols["debt_to_equity"]: 0.2, cols["sales_growth_3y"]: 15,
         cols["qtr_profit_yoy"]: 10, cols["promoter_pledge"]: 0, cols["roe"]: 20, cols["industry"]: "IT"},
        {cols["symbol"]: "DEBT", cols["roce"]: 25, cols["debt_to_equity"]: 2.5, cols["sales_growth_3y"]: 15,
         cols["qtr_profit_yoy"]: 10, cols["promoter_pledge"]: 0, cols["roe"]: 20, cols["industry"]: "Cement"},
        {cols["symbol"]: "BANKX", cols["roce"]: 5, cols["debt_to_equity"]: 9, cols["sales_growth_3y"]: 1,
         cols["qtr_profit_yoy"]: 5, cols["promoter_pledge"]: 0, cols["roe"]: 14, cols["industry"]: "Private Bank"},
    ])
    table["_sym"] = table[cols["symbol"]]
    table = table.set_index("_sym")
    assert evaluate("GOOD", "", table, cfg).status == "PASS"
    assert evaluate("DEBT", "", table, cfg).status == "FAIL"
    assert evaluate("BANKX", "", table, cfg).status == "PASS"     # ROCE and debt skipped for banks
    assert evaluate("MISSING", "", table, cfg).status == "N/A"


def _ctx(status):
    return {"generated": pd.Timestamp("2026-11-07 18:00"), "data_date": date(2026, 11, 6),
            "next_checkin": date(2026, 11, 16), "checkin_next": False, "regime_on": True,
            "backtest_status": status, "picks": [], "holdings": [], "notes": []}


def test_report_shows_failed_banner_when_backtest_failed(cfg):
    failed = {"passed": False, "reasons": ["average profit per trade after costs is zero or negative"],
              "oos_expectancy_inr": -120.0}
    html = build_report_html(_ctx(failed), cfg)
    assert FAILED_BANNER in html and 'class="banner red"' in html
    assert "—" not in html


def test_report_has_no_failed_banner_when_backtest_passed(cfg):
    ok = {"passed": True, "reasons": [], "oos_expectancy_inr": 2300.0}
    html = build_report_html(_ctx(ok), cfg)
    assert FAILED_BANNER not in html
    assert "Not investment advice" in html
