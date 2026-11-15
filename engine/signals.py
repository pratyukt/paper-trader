"""Indicators, the liquid universe, and the pick rules.

Everything at row t uses data up to and including day t only, so picks made
after day t's close can be traded on day t+1 without look-ahead.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def rsi(close: pd.DataFrame, n: int) -> pd.DataFrame:
    delta = close.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / down.replace(0, np.nan))


def build_indicators(market: dict, universe_size: int = 100, min_price: float = 50.0) -> dict:
    c, v = market["close"], market["volume"]
    ind = {
        "sma5": c.rolling(5, min_periods=5).mean(),
        "sma50": c.rolling(50, min_periods=40).mean(),
        "sma200": c.rolling(200, min_periods=150).mean(),
        "ret20": c / c.shift(20) - 1,
        "rsi2": rsi(c, 2),
        "hi20": c.rolling(20, min_periods=20).max(),
        "vol20": v.rolling(20, min_periods=15).mean(),
    }
    # Universe: the `universe_size` most traded ordinary shares, re-ranked on the
    # first trading day of each month using the prior 60 sessions' median traded
    # value. Ranking on a fixed calendar trigger keeps replays deterministic.
    dates = c.index
    med60 = (c * v).rolling(60, min_periods=40).median()
    month = dates.year * 12 + dates.month
    first_of_month = np.r_[True, month[1:] != month[:-1]]
    eligible = market["eq"] & (c >= min_price)
    rank = med60.where(eligible)[first_of_month].rank(axis=1, ascending=False, method="first")
    member = (rank <= universe_size).astype("float64")
    ind["universe"] = member.reindex(dates).ffill().fillna(0.0) > 0.5
    ind["volume"] = v
    return {k: frame.to_numpy() for k, frame in ind.items()}


# Each rule returns (mask, score); higher score is picked first.
def _momentum(a, ind, i):
    mask = ind["universe"][i] & a["eq"][i] & (a["close"][i] > ind["sma50"][i])
    return mask, ind["ret20"][i]


def _dip(a, ind, i):
    mask = (
        ind["universe"][i] & a["eq"][i]
        & (a["close"][i] > ind["sma200"][i]) & (ind["rsi2"][i] < 10)
    )
    return mask, -ind["rsi2"][i]


def _breakout(a, ind, i):
    rel_vol = ind["volume"][i] / ind["vol20"][i]
    mask = (
        ind["universe"][i] & a["eq"][i]
        & (a["close"][i] >= ind["hi20"][i]) & (a["close"][i] > ind["sma50"][i])
        & (rel_vol > 1.5)
    )
    return mask, rel_vol


def _attention(a, ind, i):
    # Stocks everyone was watching yesterday: big move on unusually heavy volume.
    rel_vol = ind["volume"][i] / ind["vol20"][i]
    move = np.abs(a["close"][i] / a["close"][i - 1] - 1) if i > 0 else np.full_like(rel_vol, np.nan)
    mask = ind["universe"][i] & a["eq"][i] & (rel_vol > 1.5)
    return mask, rel_vol * move


SELECTORS = {"momentum": _momentum, "dip": _dip, "breakout": _breakout, "attention": _attention}

# kind: intraday  = enter at the next open, exit at the same day's close (MIS, intraday charges)
#                   side "short" sells first and buys back (intraday short selling)
#       overnight = buy today's close, sell next open (delivery charges)
#       swing     = buy next open, hold up to `max_hold` sessions (delivery charges)
STRATEGIES = {
    "momentum_intraday": {
        "kind": "intraday", "select": "momentum",
        "plain": "Strongest 20-day movers above their 50-day average; buy at the open, sell at the close.",
    },
    "dip_intraday": {
        "kind": "intraday", "select": "dip",
        "plain": "Uptrending stocks that just sold off hard (2-day RSI under 10); buy at the open, sell at the close.",
    },
    "breakout_intraday": {
        "kind": "intraday", "select": "breakout",
        "plain": "Stocks closing at a 20-day high on 1.5x volume; buy at the open, sell at the close.",
    },
    "momentum_fade": {
        "kind": "intraday", "select": "momentum", "side": "short",
        "plain": "Strongest 20-day movers above their 50-day average; sell short at the open, buy back at the close.",
    },
    "breakout_fade": {
        "kind": "intraday", "select": "breakout", "side": "short",
        "plain": "Stocks that closed at a 20-day high on 1.5x volume; sell short at the open, buy back at the close.",
    },
    "attention_fade": {
        "kind": "intraday", "select": "attention", "side": "short",
        "plain": "Yesterday's biggest movers on heavy volume; sell short at the open, buy back at the close.",
    },
    "momentum_overnight": {
        "kind": "overnight", "select": "momentum",
        "plain": "Strongest 20-day movers; buy at the close, sell at the next open.",
    },
    "dip_swing": {
        "kind": "swing", "select": "dip", "max_hold": 5,
        "plain": "Uptrending stocks that just sold off hard; buy at the next open, sell when the close "
                 "recovers above the 5-day average or after 5 sessions.",
    },
}


def pick(a: dict, ind: dict, i: int, select: str, k: int,
         exclude: frozenset = frozenset(), max_price: float | None = None) -> list[int]:
    """Column indices of up to k picks made after the close of row i."""
    mask, score = SELECTORS[select](a, ind, i)
    mask = mask & np.isfinite(score) & np.isfinite(a["close"][i])
    if max_price is not None:
        mask = mask & (a["close"][i] <= max_price)
    idx = np.flatnonzero(mask)
    if exclude:
        idx = np.array([j for j in idx if a["symbols"][j] not in exclude], dtype=int)
    if idx.size == 0:
        return []
    order = idx[np.argsort(-score[idx], kind="stable")]
    return [int(j) for j in order[:k]]
