#!/usr/bin/env python3
"""Backtest every daily in/out rule with real charges and write backtest/summary.md.

    python run_backtest.py --data-dir ../market_data/eod2_data --start 2016-01-01
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from engine.costs import CostModel  # noqa: E402
from engine.data import as_arrays, load_eod2  # noqa: E402
from engine.signals import STRATEGIES, build_indicators  # noqa: E402
from engine.sim import Simulator, summarise  # noqa: E402


def pct(x, digits=1):
    return "n/a" if x is None or not np.isfinite(x) else f"{x * 100:.{digits}f}%"


def bp(x):
    return "n/a" if x is None or not np.isfinite(x) else f"{x * 1e4:+.1f}"


def fell_below(curve: pd.Series, level: float) -> str:
    hit = curve[curve <= level]
    return f"{hit.index[0]:%b %Y}" if len(hit) else "never"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(HERE.parent / "market_data" / "eod2_data"))
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--out", default=str(HERE / "backtest"))
    args = ap.parse_args()

    cfg = json.loads((HERE / "config.json").read_text())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    market = load_eod2(Path(args.data_dir), cache_path=HERE / ".cache" / "market.pkl")
    arrays = as_arrays(market)
    ind = build_indicators(market, cfg["universe_size"], cfg["min_price"])
    capital, k = float(cfg["capital"]), int(cfg["positions"])
    real = CostModel.from_dict(cfg.get("costs"))
    free = CostModel(**{f: 0.0 for f in CostModel.__dataclass_fields__})
    stops = cfg.get("stop_pct", {})

    def run(name, stop, costs, start=args.start, end=None):
        return Simulator(arrays, ind, costs, k, stop).run(name, start, end, capital)

    # ---------------------------------------------------------------- main table
    rows, curves, yearly = [], {}, {}
    bench_curve = None
    for name, spec in STRATEGIES.items():
        stop = stops.get(name, stops.get("default")) if spec["kind"] == "intraday" else None
        net, gross = run(name, stop, real), run(name, stop, free)
        s, g = summarise(net), summarise(gross)
        eq = net.daily["equity"]
        rows.append({
            "strategy": name, "stop": stop, **s, "gross_avg_day": g["avg_day"],
            "half_gone": fell_below(eq, capital * 0.5), "ninety_gone": fell_below(eq, capital * 0.1),
        })
        curves[name] = eq
        yr = eq.groupby(eq.index.year).last()
        start_of_year = yr.shift(1).fillna(capital)
        yearly[name] = (yr / start_of_year - 1).where(start_of_year >= 0.02 * capital)
        bench_curve = net.daily["bench"]
    curves["NIFTYBEES buy & hold"] = bench_curve
    by = bench_curve.groupby(bench_curve.index.year).last()
    yearly["NIFTYBEES buy & hold"] = by / by.shift(1).fillna(capital) - 1
    table = pd.DataFrame(rows).set_index("strategy")
    bench_cagr, bench_ret = table["bench_cagr"].iloc[0], table["bench_return"].iloc[0]
    bench_dd = float((bench_curve / np.maximum.accumulate(np.r_[capital, bench_curve.to_numpy()])[1:] - 1).min())

    # ------------------------------------------- sensitivity of the fade rules
    sens = []
    fades = [n for n, s in STRATEGIES.items() if s.get("side") == "short"]
    for name in fades:
        for stop in (None, 0.05, 0.015):
            for slip in (0.0, 0.0002, 0.0005, 0.001):
                s = summarise(run(name, stop, replace(real, slippage=slip)))
                sens.append({"strategy": name, "stop": stop, "slippage": slip,
                             "cagr": s["cagr"], "max_drawdown": s["max_drawdown"],
                             "worst_day": s["worst_day"], "profit_factor": s["profit_factor"]})
    sens = pd.DataFrame(sens)

    # ------------------------------------------------------ first half vs second
    halves = []
    last = arrays["dates"][-1]
    mid = pd.Timestamp(args.start) + (last - pd.Timestamp(args.start)) / 2
    mid = pd.Timestamp(mid.date())
    for name in fades:
        stop = stops.get(name, stops.get("default"))
        a = summarise(run(name, stop, real, args.start, mid))
        b = summarise(run(name, stop, real, mid + pd.Timedelta(days=1), None))
        halves.append({"strategy": name, "first_half_cagr": a["cagr"], "second_half_cagr": b["cagr"],
                       "first_bench": a["bench_cagr"], "second_bench": b["bench_cagr"]})
    halves = pd.DataFrame(halves)

    # ----------------------- where returns come from: overnight gap vs the day
    c, o = market["close"], market["open"]
    uni = pd.DataFrame(ind["universe"], index=c.index, columns=c.columns)
    window = c.index >= pd.Timestamp(args.start)
    member = uni.shift(1).fillna(False).astype(bool)      # universe known the evening before
    overnight = (o / c.shift(1) - 1).where(member)[window]
    intraday = (c / o - 1).where(member)[window]
    decomp = {
        "overnight_avg_bp": float(overnight.mean(axis=1).mean() * 1e4),
        "intraday_avg_bp": float(intraday.mean(axis=1).mean() * 1e4),
        "share_of_stock_days_up_intraday": float(
            (intraday.to_numpy() > 0).sum() / np.isfinite(intraday.to_numpy()).sum()),
        "by_year": {
            int(y): {"overnight_bp": float(overnight.mean(axis=1)[overnight.index.year == y].mean() * 1e4),
                     "intraday_bp": float(intraday.mean(axis=1)[intraday.index.year == y].mean() * 1e4)}
            for y in sorted(set(overnight.index.year))
        },
    }

    # -------------------------------------------------------------------- write
    table.to_csv(out / "summary.csv")
    pd.DataFrame(curves).to_csv(out / "equity_curves.csv")
    pd.DataFrame(yearly).to_csv(out / "yearly_returns.csv")
    sens.to_csv(out / "fade_sensitivity.csv", index=False)
    halves.to_csv(out / "fade_halves.csv", index=False)
    (out / "decomposition.json").write_text(json.dumps(decomp, indent=2))

    # Round-trip cost on one position, as a share of the position
    pos = capital / k
    rt_intraday = real.intraday(pos, pos) / pos + 2 * real.slippage
    rt_delivery = real.delivery(pos, pos) / pos + 2 * real.slippage

    L = [
        f"# Backtest of daily in/out rules, {args.start} to {last:%Y-%m-%d}",
        "",
        f"Rs {capital:,.0f} starting capital, {k} equal positions, no leverage. Universe: the "
        f"{cfg['universe_size']} most traded NSE shares, re-ranked monthly. Every trade pays the charges "
        f"in config.json plus {real.slippage * 100:.2f}% slippage per side.",
        "",
        f"One round trip on a Rs {pos:,.0f} position costs about {rt_intraday * 100:.2f}% intraday and "
        f"{rt_delivery * 100:.2f}% on delivery. Traded every session, that is roughly "
        f"{rt_intraday * 250 * 100:.0f}% of capital a year intraday before the strategy earns anything.",
        "",
        "| Rule | What it does | Avg day before costs (bp) | Avg day after costs (bp) | Net result per year "
        "| Rs 75,000 became | Half the money gone by | Profitable days | Profit factor | Charges paid |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, r in table.iterrows():
        L.append(
            f"| {name} | {STRATEGIES[name]['plain']} | {bp(r['gross_avg_day'])} | {bp(r['avg_day'])} | "
            f"{'wiped out' if r['end_equity'] < 0.02 * capital else pct(r['cagr'])} | "
            f"Rs {r['end_equity']:,.0f} | {r['half_gone']} | "
            f"{pct(r['profitable_days'])} | {r['profit_factor']:.2f} | Rs {r['costs_paid']:,.0f} |"
        )
    L += [
        f"| NIFTYBEES buy & hold | Buy the Nifty 50 ETF once and do nothing. | - | - | {pct(bench_cagr)} | "
        f"Rs {capital * (1 + bench_ret):,.0f} | never (worst fall {pct(bench_dd)}) | - | - | negligible |",
        "",
        "1 bp = 0.01%. Averages are over every session the account still had money. A profit factor "
        "below 1 means losing trades outweighed winning ones. An account under Rs 1,000 stops trading.",
        "",
        "## Where stock returns come from",
        "",
        f"Average stock in the universe: {decomp['overnight_avg_bp']:+.1f} bp from the previous close to "
        f"the open, {decomp['intraday_avg_bp']:+.1f} bp from the open to the close. Stocks finished "
        f"above their opening price on only {pct(decomp['share_of_stock_days_up_intraday'])} of stock-days.",
        "",
        "| Year | Overnight (bp/day) | Open to close (bp/day) |",
        "|---|---|---|",
    ]
    for y, d in decomp["by_year"].items():
        L.append(f"| {y} | {d['overnight_bp']:+.1f} | {d['intraday_bp']:+.1f} |")
    L += [
        "",
        "## Short-at-the-open rules: how fragile the result is",
        "",
        "Net result per year for different stop-losses and slippage assumptions.",
        "",
        "| Rule | Stop | 0.00% slip | 0.02% slip | 0.05% slip | 0.10% slip | Worst day (0.05%) | Max drawdown (0.05%) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for (name, stop), grp in sens.groupby(["strategy", "stop"], dropna=False, sort=False):
        g = grp.set_index("slippage")
        L.append(
            f"| {name} | {'none' if pd.isna(stop) else pct(stop)} | {pct(g.loc[0.0, 'cagr'])} | "
            f"{pct(g.loc[0.0002, 'cagr'])} | {pct(g.loc[0.0005, 'cagr'])} | {pct(g.loc[0.001, 'cagr'])} | "
            f"{pct(g.loc[0.0005, 'worst_day'])} | {pct(g.loc[0.0005, 'max_drawdown'])} |"
        )
    L += [
        "",
        f"First half ({args.start} to {mid:%Y-%m-%d}) versus second half, at the configured stop and slippage:",
        "",
        "| Rule | First half | Second half | Index ETF first half | Index ETF second half |",
        "|---|---|---|---|---|",
    ]
    for _, r in halves.iterrows():
        L.append(f"| {r['strategy']} | {pct(r['first_half_cagr'])} | {pct(r['second_half_cagr'])} | "
                 f"{pct(r['first_bench'])} | {pct(r['second_bench'])} |")
    L += [
        "",
        "## Year by year (net)",
        "",
        "| Year | " + " | ".join(yearly) + " |",
        "|---|" + "---|" * len(yearly),
    ]
    ydf = pd.DataFrame(yearly)
    for y, r in ydf.iterrows():
        L.append(f"| {y} | " + " | ".join("wiped out" if pd.isna(v) else pct(v) for v in r) + " |")
    L += [
        "",
        "## Limits of this backtest",
        "",
        "- Fills are assumed at NSE's official open and close. The official open is the pre-open auction "
        "price; an order placed after 9:15 gets a different price, and daily data cannot say which way.",
        "- The history mirror drops delisted stocks after a year, which flatters long rules.",
        f"- {len(STRATEGIES)} rules were tried with conventional settings. The best of several is partly luck.",
        "- Short selling intraday needs the stock to be available for MIS shorting on the day; that is assumed.",
        "- Prices are adjusted for splits and bonuses, not dividends (irrelevant for same-day trades).",
    ]
    (out / "summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
