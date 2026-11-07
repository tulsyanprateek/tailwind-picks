"""Quality filter (module G) from a Screener.in export, and the results calendar."""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

log = logging.getLogger("screener.fundamentals")


@dataclass
class FundResult:
    status: str                      # "PASS", "FAIL" or "N/A"
    score: float | None              # share of checks passed, 0-100 (None when N/A)
    summary: str
    checks: list[tuple[str, bool]] = field(default_factory=list)


def _to_float(v) -> float:
    if v is None:
        return math.nan
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("%", "").replace("₹", "")
    if s in ("", "-", "--", "NA", "N/A", "nan"):
        return math.nan
    try:
        return float(s)
    except ValueError:
        return math.nan


def load_fundamentals(cfg: dict) -> tuple[pd.DataFrame | None, str | None]:
    """Return (table indexed by NSE symbol, warning)."""
    fcfg = cfg["fundamentals"]
    path = cfg["paths"]["data_dir"] / fcfg["file"]
    if not path.exists():
        return None, (f"No fundamentals file ({path.name}). The quality filter was not applied: "
                      "every stock shows fundamentals N/A.")
    try:
        raw = pd.read_csv(path)
    except Exception as exc:
        return None, f"Could not read {path.name} ({exc}). Fundamentals shown as N/A."
    cols = fcfg["columns"]
    if cols["symbol"] not in raw.columns:
        return None, (f"{path.name} has no '{cols['symbol']}' column. Set fundamentals.columns.symbol "
                      "in config.yaml to the column holding the NSE symbol.")
    missing = [v for k, v in cols.items() if k not in ("symbol", "name") and v not in raw.columns]
    warning = (f"Columns not found in {path.name}: {', '.join(missing)}. Those checks show as N/A. "
               "Fix the names under fundamentals.columns in config.yaml.") if missing else None
    raw = raw.copy()
    raw["_sym"] = raw[cols["symbol"]].astype(str).str.strip().str.upper()
    return raw.drop_duplicates("_sym").set_index("_sym"), warning


def is_financial(industry: str, cfg: dict) -> bool:
    text = (industry or "").lower()
    return any(k in text for k in cfg["fundamentals"]["financial_keywords"])


def evaluate(symbol: str, universe_industry: str, table: pd.DataFrame | None, cfg: dict) -> FundResult:
    if table is None or symbol not in table.index:
        return FundResult("N/A", None, "Fundamentals N/A (not in your Screener export). Check before buying.")
    fcfg, cols = cfg["fundamentals"], cfg["fundamentals"]["columns"]
    row = table.loc[symbol]

    def val(key):
        c = cols.get(key)
        return _to_float(row[c]) if c in row.index else math.nan

    industry = str(row[cols["industry"]]) if cols.get("industry") in row.index else universe_industry
    fin = is_financial(industry, cfg) or is_financial(universe_industry, cfg)
    checks: list[tuple[str, float, bool]] = []
    if fin:
        t = fcfg["financial"]
        checks += [(f"ROE >= {t['min_roe']}%", val("roe"), val("roe") >= t["min_roe"]),
                   (f"Latest quarter profit YoY > {t['min_qtr_profit_yoy']}%", val("qtr_profit_yoy"),
                    val("qtr_profit_yoy") > t["min_qtr_profit_yoy"])]
    else:
        t = fcfg["non_financial"]
        checks += [(f"ROCE >= {t['min_roce']}%", val("roce"), val("roce") >= t["min_roce"]),
                   (f"Debt to equity <= {t['max_debt_to_equity']}", val("debt_to_equity"),
                    val("debt_to_equity") <= t["max_debt_to_equity"]),
                   (f"Sales growth 3Y >= {t['min_sales_growth_3y']}%", val("sales_growth_3y"),
                    val("sales_growth_3y") >= t["min_sales_growth_3y"]),
                   (f"Latest quarter profit YoY > {t['min_qtr_profit_yoy']}%", val("qtr_profit_yoy"),
                    val("qtr_profit_yoy") > t["min_qtr_profit_yoy"]),
                   (f"Promoter pledge <= {t['max_promoter_pledge']}%", val("promoter_pledge"),
                    val("promoter_pledge") <= t["max_promoter_pledge"])]
    known = [(n, ok) for n, v, ok in checks if not math.isnan(v)]
    if not known:
        return FundResult("N/A", None, "Fundamentals N/A (values missing in your export). Check before buying.")
    passed = sum(ok for _, ok in known)
    unknown = [n for n, v, _ in checks if math.isnan(v)]
    status = "PASS" if passed == len(known) else "FAIL"
    if unknown and status == "PASS":
        status = "N/A"
    kind = "Bank / NBFC" if fin else "Company"
    summary = f"{kind}: {passed} of {len(checks)} quality checks passed"
    if unknown:
        summary += f" ({len(unknown)} not in your export)"
    return FundResult(status, passed / len(checks) * 100, summary, [(n, ok) for n, ok in known])


def load_results_calendar(cfg: dict) -> dict[str, list[date]] | None:
    path = cfg["paths"]["data_dir"] / cfg["results_calendar"]["file"]
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
        df.columns = [c.strip().lower() for c in df.columns]
        df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()
        df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
        out: dict[str, list[date]] = {}
        for sym, d in df.dropna(subset=["date"]).itertuples(index=False):
            out.setdefault(sym, []).append(d.date())
        return out
    except Exception as exc:
        log.warning("Could not read the results calendar (%s)", exc)
        return None


def results_flag(symbol: str, calendar: dict[str, list[date]] | None, today: date, cfg: dict
                 ) -> tuple[str, str]:
    """(level, text): level is 'avoid', 'ok' or 'unknown'."""
    if calendar is None:
        return "unknown", "Check results date on Kite"
    days = cfg["results_calendar"]["avoid_within_days"]
    upcoming = sorted(d for d in calendar.get(symbol, []) if d >= today)
    if upcoming and (upcoming[0] - today).days <= days:
        return "avoid", f"Results soon ({upcoming[0]:%d %b}), avoid"
    if upcoming:
        return "ok", f"Next results {upcoming[0]:%d %b %Y}"
    return "unknown", "Results date not in your calendar: check on Kite"
