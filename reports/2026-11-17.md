# Paper trading report - data through 2026-11-17

**Status: CHECK**. Paper money only; no real orders are placed. Each account started with Rs 75,000 on 2026-11-16.

## Checks

- [OK] Price history: history downloaded.
- [CHECK] Data is behind: last session on file is Tue 17 Nov 2026, expected Wed 18 Nov 2026. Nothing after that date is settled, and the paper orders below are for the session after it.

## Accounts

| Account | Value | Since start | Last session | Sessions | Profitable days | Charges paid | Worst fall from peak |
|---|---|---|---|---|---|---|---|
| breakout_fade | Rs 75,746 | +0.99% | -0.16% | 2 | 50% | Rs 76 | -0.16% |
| momentum_intraday | Rs 74,246 | -1.01% | -0.42% | 2 | 0% | Rs 138 | -1.01% |
| NIFTYBEES buy & hold | Rs 75,774 | +1.03% | +0.69% | - | - | - | - |

## breakout_fade

Stocks that closed at a 20-day high on 1.5x volume; sell short at the open, buy back at the close.

Settled on 2026-11-17:

| Stock | Side | Shares | Entry | Exit | Exit reason | Before charges | Charges | Net |
|---|---|---|---|---|---|---|---|---|
| ITC | short | 51 | 295.00 | 293.45 | close | +79 | 16 | +63 |
| MAXHEALTH | short | 14 | 1019.49 | 1031.42 | close | -167 | 15 | -182 |

Paper orders for 2026-11-18 (from the 2026-11-17 close):

| Stock | Shares (est.) | Reference close | Amount |
|---|---|---|---|
| VAML | 38 | 397.00 | Rs 15,149 |
| GROWW | 66 | 227.53 | Rs 15,149 |

Sell short at the open (intraday order in the 9:00-9:07 pre-open window), buy back before 3:15 pm. Stop-loss 5.0% above the opening price.

## momentum_intraday

Strongest 20-day movers above their 50-day average; buy at the open, sell at the close.

Settled on 2026-11-17:

| Stock | Side | Shares | Entry | Exit | Exit reason | Before charges | Charges | Net |
|---|---|---|---|---|---|---|---|---|
| ATHERENERG | long | 7 | 1940.97 | 1909.94 | stop | -217 | 14 | -231 |
| KALYANKJIL | long | 21 | 707.80 | 696.49 | stop | -238 | 16 | -253 |
| DIVISLAB | long | 1 | 11092.54 | 11144.42 | close | +52 | 12 | +40 |
| MAXHEALTH | long | 14 | 1020.51 | 1030.38 | close | +138 | 15 | +123 |
| INDIGO | long | 2 | 5597.80 | 5608.19 | close | +21 | 12 | +9 |

Paper orders for 2026-11-18 (from the 2026-11-17 close):

| Stock | Shares (est.) | Reference close | Amount |
|---|---|---|---|
| ATHERENERG | 7 | 1908.60 | Rs 14,849 |
| MAXHEALTH | 14 | 1030.90 | Rs 14,849 |
| KALYANKJIL | 21 | 682.75 | Rs 14,849 |
| DIVISLAB | 1 | 11150.00 | Rs 14,849 |
| CHOLAFIN | 7 | 1884.70 | Rs 14,849 |

Buy at the open (order in the 9:00-9:07 pre-open window), sell before 3:15 pm. Stop-loss 1.5% below the opening price.

## Go-live gate (breakout_fade)

- [NOT YET] At least 60 paper sessions (so far 2)
- [PASS] Net profit after all charges (so far Rs +746)
- [PASS] Profit factor of 1.2 or better (so far 5.10)
- [PASS] Worst fall from peak under 10% (so far 0.2%)
- [NOT YET] Ahead of simply holding the Nifty 50 ETF over the same period

**Not ready for real money. Keep it on paper.**
