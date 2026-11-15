"""Day-by-day simulator. The backtest and the paper ledger are the same code:
the paper ledger is simply this simulator replayed from the paper start date
with whole-share sizing.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .costs import CostModel
from .signals import STRATEGIES, pick


@dataclass
class Result:
    strategy: str
    capital: float
    daily: pd.DataFrame            # index=date: equity, pnl, gross, costs, trades, bench
    trades: pd.DataFrame
    pending: list = field(default_factory=list)   # picks for the next session
    open_positions: list = field(default_factory=list)
    signal_date: pd.Timestamp | None = None


class Simulator:
    def __init__(self, arrays: dict, ind: dict, costs: CostModel, positions: int = 5,
                 stop_pct: float | None = 0.015, suspect: frozenset = frozenset(),
                 bench_symbol: str = "NIFTYBEES"):
        self.a, self.ind, self.costs = arrays, ind, costs
        self.k, self.stop = positions, stop_pct
        self.suspect = frozenset(suspect)
        self.dates = arrays["dates"]
        syms = list(arrays["symbols"])
        self.bench_j = syms.index(bench_symbol) if bench_symbol in syms else None

    # ------------------------------------------------------------------ helpers
    def _picks(self, i: int, select: str, max_price: float | None, exclude=None) -> list[int]:
        # Suspect symbols are known only for the newest overlaid days, so the
        # exclusion applies only to the latest signal date.
        ex = self.suspect if i == len(self.dates) - 1 else frozenset()
        if exclude:
            ex = ex | frozenset(exclude)
        return pick(self.a, self.ind, i, select, self.k, ex, max_price)

    def _qty(self, alloc: float, price: float, whole: bool) -> float:
        q = alloc / price
        return float(math.floor(q)) if whole else q

    # --------------------------------------------------------------------- run
    def run(self, strategy: str, start, end=None, capital: float = 100000.0,
            whole_shares: bool = False) -> Result:
        spec = STRATEGIES[strategy]
        kind, select = spec["kind"], spec["select"]
        a, cm, dates = self.a, self.costs, self.dates
        O, H, L, C = a["open"], a["high"], a["low"], a["close"]
        slip = cm.slippage
        n = len(dates)
        i0 = int(dates.searchsorted(pd.Timestamp(start)))
        i1 = n - 1 if end is None else int(dates.searchsorted(pd.Timestamp(end), side="right")) - 1
        i0 = max(i0, 1)

        equity = cash = float(capital)
        held: dict[int, dict] = {}       # swing positions by column index
        rows, trades = [], []
        bench0 = C[i0 - 1, self.bench_j] if (self.bench_j is not None and i0 - 1 < n) else np.nan

        def cap_price(eq_now: float) -> float | None:
            return (eq_now / self.k) * 0.97 if whole_shares else None

        for i in range(i0, i1 + 1):
            date = dates[i]
            start_equity = equity
            alloc = start_equity / self.k
            gross = costs = 0.0
            count = 0
            picks = self._picks(i - 1, select, cap_price(start_equity),
                                exclude=[a["symbols"][j] for j in held] if kind == "swing" else None)

            if start_equity < 1000:
                picks = []          # account effectively wiped out: stop trading

            if kind in ("intraday", "overnight"):
                short = spec.get("side") == "short"
                for j in picks:
                    if kind == "intraday":
                        ref_in, ref_out = O[i, j], C[i, j]
                        if not a["eq"][i, j]:
                            continue
                    else:
                        ref_in, ref_out = C[i - 1, j], O[i, j]
                    if not (np.isfinite(ref_in) and np.isfinite(ref_out) and ref_in > 0):
                        continue
                    sign = -1.0 if short else 1.0
                    entry = ref_in * (1 + sign * slip)         # pay up to buy, give up to sell
                    qty = self._qty(alloc, entry, whole_shares)
                    if qty <= 0:
                        continue
                    reason = "close" if kind == "intraday" else "next open"
                    exit_px = ref_out * (1 - sign * slip)
                    if kind == "intraday" and self.stop:
                        stop_px = ref_in * (1 - sign * self.stop)
                        hit = (np.isfinite(H[i, j]) and H[i, j] >= stop_px) if short else (
                            np.isfinite(L[i, j]) and L[i, j] <= stop_px)
                        if hit:
                            exit_px, reason = stop_px * (1 - sign * slip), "stop"
                    if short:
                        sell, buy = qty * entry, qty * exit_px
                    else:
                        buy, sell = qty * entry, qty * exit_px
                    fee = cm.intraday(buy, sell) if kind == "intraday" else cm.delivery(buy, sell)
                    gross += sell - buy
                    costs += fee
                    count += 1
                    trades.append({
                        "date": date, "symbol": a["symbols"][j], "side": "short" if short else "long",
                        "qty": qty, "entry": round(entry, 2), "exit": round(exit_px, 2),
                        "exit_reason": reason,
                        "gross": sell - buy, "costs": fee, "net": sell - buy - fee,
                        "entry_date": dates[i - 1] if kind == "overnight" else date,
                    })
                equity = start_equity + gross - costs
                cash = equity

            else:  # swing
                max_hold = spec.get("max_hold", 5)
                for j in picks:
                    if len(held) >= self.k or j in held:
                        continue
                    if not (np.isfinite(O[i, j]) and O[i, j] > 0):
                        continue
                    entry = O[i, j] * (1 + slip)
                    qty = self._qty(min(alloc, cash), entry, whole_shares)
                    if qty <= 0:
                        continue
                    cash -= qty * entry
                    held[j] = {"qty": qty, "entry": entry, "entry_i": i, "last": entry}
                for j in list(held):
                    pos = held[j]
                    px = C[i, j]
                    if np.isfinite(px):
                        pos["last"] = px
                    sessions = i - pos["entry_i"] + 1
                    recovered = np.isfinite(px) and px > self.ind["sma5"][i, j]
                    if np.isfinite(px) and (recovered or sessions >= max_hold):
                        exit_px = px * (1 - slip)
                        buy, sell = pos["qty"] * pos["entry"], pos["qty"] * exit_px
                        fee = cm.delivery(buy, sell)
                        cash += sell - fee
                        gross += sell - buy
                        costs += fee
                        count += 1
                        trades.append({
                            "date": date, "symbol": a["symbols"][j], "side": "long",
                            "qty": pos["qty"],
                            "entry": round(pos["entry"], 2), "exit": round(exit_px, 2),
                            "exit_reason": "recovered" if recovered else "time",
                            "gross": sell - buy, "costs": fee, "net": sell - buy - fee,
                            "entry_date": dates[pos["entry_i"]],
                        })
                        del held[j]
                equity = cash + sum(p["qty"] * p["last"] for p in held.values())

            bench = (capital * C[i, self.bench_j] / bench0
                     if self.bench_j is not None and np.isfinite(bench0) else np.nan)
            rows.append({"date": date, "equity": equity, "pnl": equity - start_equity,
                         "gross": gross, "costs": costs, "trades": count, "bench": bench})

        daily = pd.DataFrame(rows).set_index("date") if rows else pd.DataFrame(
            columns=["equity", "pnl", "gross", "costs", "trades", "bench"])
        if not daily.empty:
            daily["bench"] = daily["bench"].ffill()
        tr = pd.DataFrame(trades)

        # Picks for the session after the last simulated day
        last_i = min(i1, n - 1)
        pending = []
        if last_i >= 0 and last_i == n - 1:
            held_syms = [a["symbols"][j] for j in held] if kind == "swing" else None
            for j in self._picks(last_i, select, cap_price(equity), exclude=held_syms):
                ref = C[last_i, j]
                alloc_now = equity / self.k
                pending.append({
                    "symbol": str(a["symbols"][j]), "ref_close": round(float(ref), 2),
                    "alloc": round(alloc_now, 2),
                    "est_qty": int(alloc_now // ref) if whole_shares else round(alloc_now / ref, 2),
                })
        open_positions = [
            {"symbol": str(a["symbols"][j]), "qty": p["qty"], "entry": round(p["entry"], 2),
             "last": round(p["last"], 2), "entry_date": str(dates[p["entry_i"]].date())}
            for j, p in held.items()
        ]
        return Result(strategy, float(capital), daily, tr, pending, open_positions,
                      dates[last_i] if last_i >= 0 else None)


# ------------------------------------------------------------------------ stats
def summarise(res: Result) -> dict:
    d, cap = res.daily, res.capital
    if d.empty:
        return {"days": 0}
    eq = d["equity"]
    prev = eq.shift(1).fillna(cap)
    ret = eq / prev - 1
    span_years = max((d.index[-1] - d.index[0]).days / 365.25, 1 / 365.25)
    peak = np.maximum.accumulate(np.r_[cap, eq.to_numpy()])[1:]
    alive = prev >= 1000                      # still had money to trade with
    active = (d["trades"] > 0) & alive
    t = res.trades
    wins = t.loc[t["net"] > 0, "net"].sum() if not t.empty else 0.0
    losses = -t.loc[t["net"] <= 0, "net"].sum() if not t.empty else 0.0
    bench_end = d["bench"].iloc[-1]
    out = {
        "days": int(len(d)),
        "years": span_years,
        "end_equity": float(eq.iloc[-1]),
        "total_return": float(eq.iloc[-1] / cap - 1),
        "cagr": float((eq.iloc[-1] / cap) ** (1 / span_years) - 1) if eq.iloc[-1] > 0 else -1.0,
        "max_drawdown": float((eq.to_numpy() / peak - 1).min()),
        "days_traded": int(active.sum()),
        "profitable_days": float((d.loc[active, "pnl"] > 0).mean()) if active.any() else float("nan"),
        "avg_day": float(ret[alive].mean()) if alive.any() else float("nan"),
        "worst_day": float(ret.min()),
        "best_day": float(ret.max()),
        "vol_annual": float(ret.std(ddof=0) * math.sqrt(252)),
        "trades": int(len(t)),
        "win_rate": float((t["net"] > 0).mean()) if not t.empty else float("nan"),
        "profit_factor": float(wins / losses) if losses > 0 else float("inf"),
        "gross_pnl": float(d["gross"].sum()),
        "costs_paid": float(d["costs"].sum()),
        "net_pnl": float(eq.iloc[-1] - cap),
        "bench_return": float(bench_end / cap - 1) if np.isfinite(bench_end) else float("nan"),
        "bench_cagr": float((bench_end / cap) ** (1 / span_years) - 1) if np.isfinite(bench_end) else float("nan"),
    }
    out["sharpe"] = (float(ret.mean() / ret.std(ddof=0) * math.sqrt(252))
                     if ret.std(ddof=0) > 0 else float("nan"))
    return out
