#!/usr/bin/env python3
"""Self-checks. Run:  python tests/test_engine.py   (set EOD2_DIR to also run the real-data checks)"""
from __future__ import annotations

import datetime as dt
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from engine import data as D  # noqa: E402
from engine import sim as S  # noqa: E402
from engine.costs import CostModel  # noqa: E402
from engine.signals import build_indicators, pick  # noqa: E402


def approx(a, b, tol=1e-6):
    assert abs(a - b) <= tol, f"{a} != {b}"


def test_costs_by_hand():
    cm = CostModel()
    # Rs 15,000 bought and sold intraday:
    # brokerage 2 x 4.50 = 9.00; exchange 30,000 x 0.00307% = 0.921; SEBI 0.03;
    # STT 15,000 x 0.025% = 3.75; stamp 15,000 x 0.003% = 0.45; GST 18% x 9.951 = 1.79118
    approx(cm.intraday(15000, 15000), 9.0 + 0.921 + 0.03 + 3.75 + 0.45 + 1.79118, 1e-4)
    # Brokerage cap: Rs 2,00,000 each way -> Rs 20 per order, not 0.03%
    big = cm.intraday(200000, 200000)
    approx(big, 40 + 12.28 + 0.4 + 50 + 6 + 0.18 * (40 + 12.28 + 0.4), 1e-6)
    # Delivery: STT 0.1% both sides, stamp 0.015% on buy, DP charge on the sell
    approx(cm.delivery(15000, 15000), 0.921 + 0.03 + 30 + 2.25 + 0.18 * 0.951 + 14.75, 1e-4)


def tiny_market():
    dates = pd.bdate_range("2025-01-01", periods=4)
    #            day0   day1   day2   day3
    o = np.array([[100, 100, 100, 100.0], [50, 50, 50, 50.0]]).T
    h = np.array([[101, 103, 108, 101.0], [51, 51, 51, 51.0]]).T
    l = np.array([[99, 97, 99, 99.0], [49, 49, 49, 49.0]]).T
    c = np.array([[100, 102, 106, 100.0], [50, 50, 50, 50.0]]).T
    arrays = {"open": o, "high": h, "low": l, "close": c, "volume": np.ones_like(o),
              "eq": np.ones_like(o, dtype=bool), "dates": dates, "symbols": np.array(["AAA", "NIFTYBEES"])}
    return arrays


def test_intraday_long_short_and_stops(monkeypatch_pick=None):
    arrays = tiny_market()
    free = CostModel(**{f: 0.0 for f in CostModel.__dataclass_fields__})
    orig = S.pick
    S.pick = lambda a, ind, i, select, k, ex, mp: [0]      # always pick AAA
    try:
        # Long, 2% stop, one slot, Rs 10,000: day1 low 97 -> stopped at 98 (-2%);
        # day2 +6%; day3 flat.
        sim = S.Simulator(arrays, {}, free, positions=1, stop_pct=0.02)
        res = sim.run("momentum_intraday", arrays["dates"][1], None, 10000.0)
        eq = res.daily["equity"].to_numpy()
        approx(eq[0], 9800.0)
        approx(eq[1], 9800.0 * 1.06)
        approx(eq[2], 9800.0 * 1.06)
        assert list(res.trades["exit_reason"]) == ["stop", "close", "close"]
        # Short, 5% stop: day1 -2% for a long = +2% for the short; day2 high 108 -> stopped at 105 (-5%).
        sim = S.Simulator(arrays, {}, free, positions=1, stop_pct=0.05)
        res = sim.run("momentum_fade", arrays["dates"][1], None, 10000.0)
        eq = res.daily["equity"].to_numpy()
        approx(eq[0], 10000.0 * 0.98)
        approx(eq[1], 9800.0 * 0.95)
        assert list(res.trades["exit_reason"]) == ["close", "stop", "close"]
        # Whole shares: Rs 10,000 at Rs 100 -> exactly 100 shares; with costs the net is lower.
        real = CostModel()
        res2 = S.Simulator(arrays, {}, real, positions=1, stop_pct=None).run(
            "momentum_intraday", arrays["dates"][1], arrays["dates"][1], 10000.0, whole_shares=True)
        t = res2.trades.iloc[0]
        assert t["qty"] == 99.0          # entry is 100.05 after slippage, so 99 whole shares
        assert t["net"] < t["gross"] and t["costs"] > 0
    finally:
        S.pick = orig


def test_bhavcopy_overlay_gap_and_split_flag():
    dates = pd.to_datetime(["2026-11-05", "2026-11-06"])
    cols = ["AAA", "BBB"]
    frame = lambda v: pd.DataFrame(v, index=dates, columns=cols, dtype="float64")  # noqa: E731
    market = {f: frame([[10, 20], [11, 21]]) for f in D.FIELDS}
    market["eq"] = pd.DataFrame(True, index=dates, columns=cols)
    market.update(suspect=set(), notes=[], holidays={dt.date(2026, 11, 10)})
    head = ("SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, "
            "CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, DELIV_PER\n")
    row = lambda s, d, c: f"{s}, EQ, {d}, 0, {c}, {c}, {c}, {c}, {c}, {c}, 1000, 1, 1, -, -\n"  # noqa: E731
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # 9 Nov present, 10 Nov is a holiday, 11 Nov missing, 12 Nov present -> stop before 12 Nov
        (tmp / "sec_bhavdata_full_09112026.csv").write_text(
            head + row("AAA", "09-Nov-2026", 11.5) + row("BBB", "09-Nov-2026", 10.0) + "CCC, BE, 09-Nov-2026, 0,1,1,1,1,1,1,1,1,1,-,-\n")
        (tmp / "sec_bhavdata_full_12112026.csv").write_text(head + row("AAA", "12-Nov-2026", 12.0))
        out = D.overlay_bhavcopy(market, tmp)
    idx = out["close"].index
    assert str(idx[-1].date()) == "2026-11-09", idx
    approx(out["close"].loc["2026-11-09", "AAA"], 11.5)
    assert "BBB" in out["suspect"]                      # 21 -> 10 is a >25% jump
    assert any("data gap" in n and "2026-11-11" in n for n in out["notes"])
    assert out["eq"].dtypes.eq(bool).all()


def test_real_data_no_lookahead():
    eod = os.environ.get("EOD2_DIR")
    if not eod:
        print("  (skipped: EOD2_DIR not set)")
        return
    market = D.load_eod2(Path(eod), cache_path=ROOT / ".cache" / "market.pkl")
    arrays = D.as_arrays(market)
    full = build_indicators(market, 100, 50)
    n = len(arrays["dates"])
    for cut in (n - 400, n - 137, n - 21):
        part = {f: market[f].iloc[: cut + 1] for f in D.FIELDS}
        part["eq"] = market["eq"].iloc[: cut + 1]
        ind_cut = build_indicators(part, 100, 50)
        arr_cut = D.as_arrays(part)
        for select in ("momentum", "dip", "breakout", "attention"):
            a = pick(arrays, full, cut, select, 5)
            b = pick(arr_cut, ind_cut, cut, select, 5)
            assert a == b, f"look-ahead in {select} at row {cut}: {a} vs {b}"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all checks passed")
