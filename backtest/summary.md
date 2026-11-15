# Backtest of daily in/out rules, 2016-01-01 to 2026-11-13

Rs 75,000 starting capital, 5 equal positions, no leverage. Universe: the 100 most traded NSE shares, re-ranked monthly. Every trade pays the charges in config.json plus 0.05% slippage per side.

One round trip on a Rs 15,000 position costs about 0.21% intraday and 0.42% on delivery. Traded every session, that is roughly 52% of capital a year intraday before the strategy earns anything.

| Rule | What it does | Avg day before costs (bp) | Avg day after costs (bp) | Net result per year | Rs 75,000 became | Half the money gone by | Profitable days | Profit factor | Charges paid |
|---|---|---|---|---|---|---|---|---|---|
| momentum_intraday | Strongest 20-day movers above their 50-day average; buy at the open, sell at the close. | -11.7 | -34.1 | wiped out | Rs 989 | Nov 2016 | 32.2% | 0.63 | Rs 21,894 |
| dip_intraday | Uptrending stocks that just sold off hard (2-day RSI under 10); buy at the open, sell at the close. | -4.0 | -16.6 | wiped out | Rs 991 | Sep 2017 | 35.3% | 0.64 | Rs 26,354 |
| breakout_intraday | Stocks closing at a 20-day high on 1.5x volume; buy at the open, sell at the close. | -10.3 | -21.8 | wiped out | Rs 1,000 | Oct 2016 | 30.2% | 0.54 | Rs 16,988 |
| momentum_fade | Strongest 20-day movers above their 50-day average; sell short at the open, buy back at the close. | +19.3 | -1.1 | -5.8% | Rs 39,029 | Aug 2022 | 48.5% | 0.98 | Rs 171,900 |
| breakout_fade | Stocks that closed at a 20-day high on 1.5x volume; sell short at the open, buy back at the close. | +14.4 | +2.2 | 4.0% | Rs 114,438 | never | 51.1% | 1.03 | Rs 173,160 |
| attention_fade | Yesterday's biggest movers on heavy volume; sell short at the open, buy back at the close. | +23.0 | +3.0 | 4.4% | Rs 119,392 | never | 50.0% | 1.02 | Rs 322,474 |
| momentum_overnight | Strongest 20-day movers; buy at the close, sell at the next open. | +23.0 | -66.6 | wiped out | Rs 996 | Dec 2016 | 20.2% | 0.35 | Rs 92,788 |
| dip_swing | Uptrending stocks that just sold off hard; buy at the next open, sell when the close recovers above the 5-day average or after 5 sessions. | -0.7 | -23.5 | wiped out | Rs 978 | Sep 2018 | 52.6% | 0.65 | Rs 56,632 |
| NIFTYBEES buy & hold | Buy the Nifty 50 ETF once and do nothing. | - | - | 12.4% | Rs 267,721 | never (worst fall -36.3%) | - | - | negligible |

1 bp = 0.01%. Averages are over every session the account still had money. A profit factor below 1 means losing trades outweighed winning ones. An account under Rs 1,000 stops trading.

## Where stock returns come from

Average stock in the universe: +16.3 bp from the previous close to the open, -11.3 bp from the open to the close. Stocks finished above their opening price on only 45.4% of stock-days.

| Year | Overnight (bp/day) | Open to close (bp/day) |
|---|---|---|
| 2016 | +16.3 | -16.0 |
| 2017 | +22.8 | -7.6 |
| 2018 | +9.3 | -13.8 |
| 2019 | +13.1 | -14.0 |
| 2020 | +17.7 | -9.0 |
| 2021 | +24.9 | -13.7 |
| 2022 | +12.1 | -9.8 |
| 2023 | +19.8 | -8.5 |
| 2024 | +24.3 | -16.7 |
| 2025 | +9.7 | -9.1 |
| 2026 | +8.3 | -5.8 |

## Short-at-the-open rules: how fragile the result is

Net result per year for different stop-losses and slippage assumptions.

| Rule | Stop | 0.00% slip | 0.02% slip | 0.05% slip | 0.10% slip | Worst day (0.05%) | Max drawdown (0.05%) |
|---|---|---|---|---|---|---|---|
| momentum_fade | none | 20.2% | 7.9% | -6.9% | -27.3% | -9.4% | -69.3% |
| momentum_fade | 5.0% | 22.3% | 9.2% | -5.8% | -26.4% | -5.2% | -66.8% |
| momentum_fade | 1.5% | 9.7% | -0.6% | -14.2% | -32.8% | -1.7% | -85.0% |
| breakout_fade | none | 20.1% | 12.6% | 3.1% | -11.0% | -8.2% | -46.9% |
| breakout_fade | 5.0% | 21.3% | 13.5% | 4.0% | -10.2% | -5.2% | -42.0% |
| breakout_fade | 1.5% | 11.3% | 5.0% | -3.9% | -17.0% | -1.7% | -52.2% |
| attention_fade | none | 34.1% | 17.4% | 0.9% | -20.7% | -12.5% | -46.6% |
| attention_fade | 5.0% | 39.9% | 23.1% | 4.4% | -18.0% | -5.2% | -44.3% |
| attention_fade | 1.5% | 19.1% | 7.0% | -7.4% | -27.3% | -1.7% | -67.2% |

First half (2016-01-01 to 2021-06-07) versus second half, at the configured stop and slippage:

| Rule | First half | Second half | Index ETF first half | Index ETF second half |
|---|---|---|---|---|
| momentum_fade | -6.8% | -4.9% | 14.6% | 10.3% |
| breakout_fade | 3.9% | 4.0% | 14.6% | 10.3% |
| attention_fade | 3.4% | 5.4% | 14.6% | 10.3% |

## Year by year (net)

| Year | momentum_intraday | dip_intraday | breakout_intraday | momentum_fade | breakout_fade | attention_fade | momentum_overnight | dip_swing | NIFTYBEES buy & hold |
|---|---|---|---|---|---|---|---|---|---|
| 2016 | -60.0% | -37.2% | -56.9% | 4.6% | 54.4% | 58.1% | -51.5% | -30.5% | 4.0% |
| 2017 | -55.8% | -35.7% | -53.2% | -9.8% | -4.2% | -12.0% | -60.8% | 6.5% | 29.9% |
| 2018 | -65.6% | -37.5% | -40.2% | 25.1% | 9.2% | 23.7% | -93.0% | -39.9% | 4.8% |
| 2019 | -61.1% | -30.9% | -27.9% | -2.3% | -13.5% | -23.8% | wiped out | -33.9% | 13.6% |
| 2020 | -43.4% | -21.9% | -36.4% | -33.7% | -7.7% | -9.6% | wiped out | -30.3% | 15.4% |
| 2021 | wiped out | -46.8% | -42.6% | -15.2% | -9.8% | 12.6% | wiped out | -49.2% | 26.0% |
| 2022 | wiped out | -34.7% | -34.7% | -26.1% | -3.2% | 25.8% | wiped out | -72.1% | 5.5% |
| 2023 | wiped out | -31.6% | -35.7% | 31.3% | 10.1% | -5.1% | wiped out | -55.1% | 21.0% |
| 2024 | wiped out | -38.3% | wiped out | 13.3% | 29.3% | 40.5% | wiped out | wiped out | 10.4% |
| 2025 | wiped out | -24.3% | wiped out | -22.8% | -2.9% | -23.3% | wiped out | wiped out | 11.7% |
| 2026 | wiped out | wiped out | wiped out | -5.5% | -2.1% | -7.5% | wiped out | wiped out | -2.9% |

## Limits of this backtest

- Fills are assumed at NSE's official open and close. The official open is the pre-open auction price; an order placed after 9:15 gets a different price, and daily data cannot say which way.
- The history mirror drops delisted stocks after a year, which flatters long rules.
- 8 rules were tried with conventional settings. The best of several is partly luck.
- Short selling intraday needs the stock to be available for MIS shorting on the day; that is assumed.
- Prices are adjusted for splits and bonuses, not dividends (irrelevant for same-day trades).
