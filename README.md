# Daily paper trader (NSE)

A paper-trading engine for daily in/out rules on NSE shares. It picks stocks after each close,
"trades" them the next session at the official open and close, charges every real cost, and
keeps score against simply holding the Nifty 50 ETF. **It places no real orders and contains no
broker code.**

## What the backtest says (read this first)

`backtest/summary.md` has the full tables. In short, over 2016 to November 2026 with Rs 75,000:

- Every "buy in the morning, sell by the close" rule lost almost everything, before costs as well as after.
- The reverse (sell short at the open, buy back at the close) made money before costs and roughly
  broke even after them: about -6% to +4% a year depending on the rule.
- Buying the Nifty 50 ETF once and doing nothing made about 12% a year.
- No rule was profitable on much more than half of its days. "Profit every day" does not exist.

The reason is structural: in this data the average liquid stock gains overnight and loses a little
between the open and the close, and a daily round trip costs about 0.2% of the position.

## Run it

Needs Python 3.10+, `pandas`, `numpy` and `git`.

```
python run_daily.py          # after ~7:30 pm IST on a trading day
```

The first run downloads about 570 MB of price history into `data/`. Each run:

1. refreshes prices (history mirror, plus the day's NSE bhavcopy);
2. rebuilds the paper ledger from `paper_start` and settles the latest session;
3. picks the next session's paper orders;
4. writes `reports/<date>.md`, `reports/latest.md` and `state/ledger.json`, and prints the report.

Exit code 2 means a check raised an ALERT.

Other commands:

```
python run_backtest.py --data-dir data/eod2_data     # redo the backtest
EOD2_DIR=data/eod2_data python tests/test_engine.py  # self-checks
```

## What the daily report checks

- **Data is current.** If the day's file is missing, nothing is settled against the wrong day.
- **Possible split or bonus** in the newest raw data: that stock is kept out of new picks.
- **Settled history unchanged** since the last run (a data revision would change it).
- **Announced orders match what was traded.**
- **Pause line:** the main account falling more than `pause_drawdown` from its peak.
- **Go-live gate:** 60+ sessions, net profit, profit factor 1.2+, fall under 10%, ahead of the ETF.

## Settings (`config.json`)

| Key | Meaning |
|---|---|
| `capital` | Paper money per account |
| `paper_strategies` | Rules to run side by side; the first is the main one the gate judges |
| `positions` | Equal slots per account |
| `stop_pct` | Intraday stop-loss per rule (`default` for the rest) |
| `universe_size`, `min_price` | The N most traded shares above a minimum price |
| `paper_start` | First paper session; change it to start a fresh ledger |
| `costs` | Brokerage, STT, exchange, SEBI, stamp duty, GST, DP charge, slippage |
| `go_live_gate`, `pause_drawdown` | Thresholds described above |

Rules available: `momentum_intraday`, `dip_intraday`, `breakout_intraday`, `momentum_fade`,
`breakout_fade`, `attention_fade`, `momentum_overnight`, `dip_swing` (see `engine/signals.py`).

## Limits you should know

- Paper fills are the official open and close minus an assumed slippage. Real fills differ, and for
  the short-at-open rules a few hundredths of a percent decide between profit and loss.
- The cost rates were checked in November 2026. Compare them with a real contract note.
- Price data comes from two third-party GitHub mirrors of NSE's daily reports
  (BennyThadikaran/eod2_data and tilak999/NSE-Data-bank), with NSE's own archive tried first for the
  daily file. The direct NSE download was not testable where this was built.
- Exchange holidays are known only for the current year (from the history mirror).
- Shorting intraday assumes the stock is available to short that day.
- This is a research tool, not investment advice.
