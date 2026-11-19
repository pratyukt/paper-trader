# Paper trading report - data through 2026-11-18

**Status: CHECK**. Paper money only; no real orders are placed. Each account started with Rs 75,000 on 2026-11-16.

## Checks

- [OK] Price history: history downloaded.
- [CHECK] Data is behind: last session on file is Wed 18 Nov 2026, expected Thu 19 Nov 2026. Nothing after that date is settled, and the paper orders below are for the session after it.

## Accounts

| Account | Value | Since start | Last session | Sessions | Profitable days | Charges paid | Worst fall from peak |
|---|---|---|---|---|---|---|---|
| breakout_fade | Rs 76,851 | +2.47% | +1.46% | 3 | 67% | Rs 108 | -0.16% |
| momentum_intraday | Rs 73,298 | -2.27% | -1.28% | 3 | 0% | Rs 208 | -2.27% |
| NIFTYBEES buy & hold | Rs 75,327 | +0.44% | -0.59% | - | - | - | - |

## breakout_fade

Stocks that closed at a 20-day high on 1.5x volume; sell short at the open, buy back at the close.

Settled on 2026-11-18:

| Stock | Side | Shares | Entry | Exit | Exit reason | Before charges | Charges | Net |
|---|---|---|---|---|---|---|---|---|
| VAML | short | 38 | 395.80 | 374.69 | close | +802 | 16 | +787 |
| GROWW | short | 66 | 228.69 | 223.63 | close | +334 | 16 | +318 |

Paper orders for 2026-11-19 (from the 2026-11-18 close):

| Stock | Shares (est.) | Reference close | Amount |
|---|---|---|---|
| SBIN | 13 | 1135.00 | Rs 15,370 |

Sell short at the open (intraday order in the 9:00-9:07 pre-open window), buy back before 3:15 pm. Stop-loss 5.0% above the opening price.

## momentum_intraday

Strongest 20-day movers above their 50-day average; buy at the open, sell at the close.

Settled on 2026-11-18:

| Stock | Side | Shares | Entry | Exit | Exit reason | Before charges | Charges | Net |
|---|---|---|---|---|---|---|---|---|
| ATHERENERG | long | 7 | 1909.55 | 1900.15 | close | -66 | 14 | -80 |
| MAXHEALTH | long | 14 | 1032.52 | 1016.01 | stop | -231 | 15 | -246 |
| KALYANKJIL | long | 21 | 683.09 | 672.17 | stop | -229 | 15 | -244 |
| DIVISLAB | long | 1 | 11185.59 | 11043.48 | close | -142 | 12 | -154 |
| CHOLAFIN | long | 7 | 1870.73 | 1840.83 | stop | -209 | 14 | -223 |

Paper orders for 2026-11-19 (from the 2026-11-18 close):

| Stock | Shares (est.) | Reference close | Amount |
|---|---|---|---|
| ATHERENERG | 7 | 1901.10 | Rs 14,660 |
| MAXHEALTH | 14 | 1022.85 | Rs 14,660 |
| CHOLAFIN | 7 | 1875.00 | Rs 14,660 |
| DIVISLAB | 1 | 11049.00 | Rs 14,660 |
| INDIGO | 2 | 5499.30 | Rs 14,660 |

Buy at the open (order in the 9:00-9:07 pre-open window), sell before 3:15 pm. Stop-loss 1.5% below the opening price.

## Go-live gate (breakout_fade)

- [NOT YET] At least 60 paper sessions (so far 3)
- [PASS] Net profit after all charges (so far Rs +1,851)
- [PASS] Profit factor of 1.2 or better (so far 11.16)
- [PASS] Worst fall from peak under 10% (so far 0.2%)
- [PASS] Ahead of simply holding the Nifty 50 ETF over the same period

**Not ready for real money. Keep it on paper.**
