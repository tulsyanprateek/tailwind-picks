# NSE Momentum Rotation Screener (personal use)

Every 2 weeks this tool picks up to 5 Nifty 100 stocks to hold. For each one it gives the
quantity, buy price, stop loss and target. You set the stop loss and target as a GTT order
on Kite, so nothing needs watching between check-ins. It also backtests itself on 12 years
of prices, including all Zerodha charges, so you can see whether the method has an edge.

It runs on your own computer, uses free Yahoo Finance data, and has no paid APIs and no
AI at runtime.

**No method wins every trade. This is a screening tool, not investment advice.**

## Setup

You need Python 3.11 or newer.

### Windows

```bat
cd D:\claude_code\stock_screener
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Mac

```bash
cd ~/stock_screener
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Commands

| Command | When | Output |
|---|---|---|
| `python backtest.py` | Once, and again whenever you change a rule in `config.yaml` | `output/backtest.html` |
| `python scan.py` | Not built yet (step 5, after you review the backtest) | `output/report.html`, `output/candidates.json` |
| `python -m pytest -q` | After any code change | Test results |

The first run downloads about 14 years of daily prices (about 2 minutes). Later runs only
download the new days. Prices are cached in `data/cache/`.

## Files you maintain

| File | What | Needed for |
|---|---|---|
| `data/nifty100.csv` | Index members (symbol, company, industry). Downloaded automatically from niftyindices.com; if that fails the local copy is used. **Update every March and September.** | Everything |
| `data/fundamentals.csv` | Your Screener.in export. Column names are set in `config.yaml` under `fundamentals.columns`. | Live report (quality filter) |
| `data/results_calendar.csv` | Columns `symbol,date`. Flags stocks with results due within 7 days. | Live report |
| `data/open_trades.csv` | Your current holdings. | Live report |

## Settings

Every rule parameter is in `config.yaml`, with a comment for each one. To put the reports
in a synced cloud folder (to open them on your phone), set `paths.output_dir` to that folder.

## Honest limits

- **Survivorship bias.** The backtest uses today's Nifty 100 members for all 12 years.
  Stocks that dropped out of the index are missing, so real results are likely worse.
- **No historical fundamentals.** The quality filter cannot be backtested.
- **Data.** Yahoo Finance data for NSE can have occasional bad prices. Cross-check a pick
  on Kite before you buy.
