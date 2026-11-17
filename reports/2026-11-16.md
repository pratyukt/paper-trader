# Paper trading report - data through 2026-11-16

**Status: CHECK**. Paper money only; no real orders are placed. Each account started with Rs 75,000 on 2026-11-16.

## Checks

- [OK] Price history: history downloaded.
- [CHECK] Data is behind: last session on file is Mon 16 Nov 2026, expected Tue 17 Nov 2026. Nothing after that date is settled, and the paper orders below are for the session after it.

## Accounts

| Account | Value | Since start | Last session | Sessions | Profitable days | Charges paid | Worst fall from peak |
|---|---|---|---|---|---|---|---|
| breakout_fade | Rs 75,865 | +1.15% | +1.15% | 1 | 100% | Rs 45 | +0.00% |
| momentum_intraday | Rs 74,559 | -0.59% | -0.59% | 1 | 0% | Rs 69 | -0.59% |
| NIFTYBEES buy & hold | Rs 75,254 | +0.34% | +0.34% | - | - | - | - |

## breakout_fade

Stocks that closed at a 20-day high on 1.5x volume; sell short at the open, buy back at the close.

Settled on 2026-11-16:

| Stock | Side | Shares | Entry | Exit | Exit reason | Before charges | Charges | Net |
|---|---|---|---|---|---|---|---|---|
| APOLLO | short | 31 | 476.76 | 470.84 | close | +184 | 16 | +168 |
| GVT&D | short | 3 | 4437.78 | 4339.17 | close | +296 | 14 | +282 |
| MEESHO | short | 57 | 258.87 | 251.32 | close | +431 | 16 | +415 |

Paper orders for 2026-11-17 (from the 2026-11-16 close):

| Stock | Shares (est.) | Reference close | Amount |
|---|---|---|---|
| ITC | 51 | 295.10 | Rs 15,173 |
| MAXHEALTH | 15 | 1009.90 | Rs 15,173 |

Sell short at the open (intraday order in the 9:00-9:07 pre-open window), buy back before 3:15 pm. Stop-loss 5.0% above the opening price.

## momentum_intraday

Strongest 20-day movers above their 50-day average; buy at the open, sell at the close.

Settled on 2026-11-16:

| Stock | Side | Shares | Entry | Exit | Exit reason | Before charges | Charges | Net |
|---|---|---|---|---|---|---|---|---|
| ATHERENERG | long | 7 | 1946.97 | 1938.63 | close | -58 | 14 | -73 |
| DIVISLAB | long | 1 | 11495.74 | 11311.99 | stop | -184 | 12 | -196 |
| KALYANKJIL | long | 21 | 694.35 | 707.80 | close | +282 | 16 | +267 |
| LAURUSLABS | long | 6 | 2431.21 | 2392.35 | stop | -233 | 15 | -249 |
| INDIGO | long | 2 | 5597.80 | 5508.32 | stop | -179 | 12 | -191 |

Paper orders for 2026-11-17 (from the 2026-11-16 close):

| Stock | Shares (est.) | Reference close | Amount |
|---|---|---|---|
| ATHERENERG | 7 | 1939.60 | Rs 14,912 |
| KALYANKJIL | 21 | 708.15 | Rs 14,912 |
| DIVISLAB | 1 | 11080.00 | Rs 14,912 |
| MAXHEALTH | 14 | 1009.90 | Rs 14,912 |
| INDIGO | 2 | 5544.00 | Rs 14,912 |

Buy at the open (order in the 9:00-9:07 pre-open window), sell before 3:15 pm. Stop-loss 1.5% below the opening price.

## Go-live gate (breakout_fade)

- [NOT YET] At least 60 paper sessions (so far 1)
- [PASS] Net profit after all charges (so far Rs +865)
- [PASS] Profit factor of 1.2 or better (so far inf)
- [PASS] Worst fall from peak under 10% (so far 0.0%)
- [PASS] Ahead of simply holding the Nifty 50 ETF over the same period

**Not ready for real money. Keep it on paper.**
