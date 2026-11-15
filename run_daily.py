#!/usr/bin/env python3
"""Daily paper-trading run. Execute once after the market closes (data is usually up by ~7:30 pm IST).

    python run_daily.py                 # refresh data, settle today's paper trades, pick tomorrow's
    python run_daily.py --no-sync       # use data already on disk

It places no real orders. It rebuilds the paper ledger from `paper_start` in
config.json every time, so the same data always gives the same ledger.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pandas as pd  # noqa: E402

from engine import data as D  # noqa: E402
from engine.costs import CostModel  # noqa: E402
from engine.report import render  # noqa: E402
from engine.signals import STRATEGIES, build_indicators  # noqa: E402
from engine.sim import Simulator, summarise  # noqa: E402

IST = ZoneInfo("Asia/Kolkata")
DATA_READY = dt.time(18, 30)     # before this, today's file is not expected yet


def clean(obj):
    """JSON-safe copy: NaN/inf -> None, timestamps -> ISO dates."""
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (pd.Timestamp, dt.date)):
        return str(obj)[:10]
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    if hasattr(obj, "item"):
        return clean(obj.item())
    return obj


def trade_key(t: dict) -> tuple:
    return (str(t["date"])[:10], t["symbol"], t.get("side", "long"),
            round(float(t["qty"]), 4), round(float(t["entry"]), 2), round(float(t["exit"]), 2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=str(HERE / "data"))
    ap.add_argument("--state-dir", default=str(HERE / "state"))
    ap.add_argument("--reports-dir", default=str(HERE / "reports"))
    ap.add_argument("--config", default=str(HERE / "config.json"))
    ap.add_argument("--no-sync", action="store_true")
    ap.add_argument("--now", default=None, help="override the clock, e.g. 2026-11-16T20:00 (IST)")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text())
    root, state_dir, reports_dir = Path(args.data_root), Path(args.state_dir), Path(args.reports_dir)
    eod_dir, bhav_dir = root / "eod2_data", root / "bhavcopy"
    now = dt.datetime.fromisoformat(args.now).replace(tzinfo=IST) if args.now else dt.datetime.now(IST)
    checks: list[dict] = []

    # ------------------------------------------------------------------- data
    if not args.no_sync:
        try:
            checks.append({"level": "ok", "text": f"Price history: {D.sync_eod2(eod_dir)}."})
        except Exception as exc:  # network trouble must not stop the report
            checks.append({"level": "warn", "text": f"Could not refresh price history ({exc}); using the copy on disk."})
    market = D.load_eod2(eod_dir, cache_path=HERE / ".cache" / "market.pkl")
    history_end = market["close"].index[-1].date()
    if not args.no_sync:
        for note in D.sync_bhavcopy(bhav_dir, history_end, now.date()):
            if "failed" in note or "unexpected" in note:
                checks.append({"level": "warn", "text": note})
    market["suspect"], market["notes"] = set(), []
    market = D.overlay_bhavcopy(market, bhav_dir)
    for note in market["notes"]:
        level = "warn" if ("gap" in note or "excluded" in note or "unreadable" in note) else "info"
        if level == "warn":
            checks.append({"level": level, "text": note})
    holidays = market["holidays"]
    last = market["close"].index[-1]
    today = now.date()
    expected = D.expected_last_session(today, holidays)
    if expected == today and now.time() < DATA_READY:
        expected = D.expected_last_session(today - dt.timedelta(days=1), holidays)
    if last.date() >= expected:
        checks.append({"level": "ok", "text": f"Data is current: last session on file is {last:%a %d %b %Y}."})
    else:
        checks.append({"level": "warn", "text":
                       f"Data is behind: last session on file is {last:%a %d %b %Y}, expected {expected:%a %d %b %Y}. "
                       "Nothing after that date is settled, and the paper orders below are for the session after it."})
    next_day = D.next_session(last.date(), holidays)

    # ------------------------------------------------------------- simulation
    arrays = D.as_arrays(market)
    ind = build_indicators(market, cfg["universe_size"], cfg["min_price"])
    costs = CostModel.from_dict(cfg.get("costs"))
    capital, k = float(cfg["capital"]), int(cfg["positions"])
    stops = cfg.get("stop_pct", {})
    names = cfg["paper_strategies"]
    primary = names[0]

    prev_path = state_dir / "ledger.json"
    prev = json.loads(prev_path.read_text()) if prev_path.exists() else None

    accounts, bench = {}, {"symbol": D.BENCHMARK, "value": None, "return": None, "last_day_return": None}
    for name in names:
        stop = stops.get(name, stops.get("default")) if STRATEGIES[name]["kind"] == "intraday" else None
        sim = Simulator(arrays, ind, costs, k, stop, frozenset(market["suspect"]))
        res = sim.run(name, cfg["paper_start"], None, capital, whole_shares=True)
        s = summarise(res)
        trades = res.trades.to_dict("records") if not res.trades.empty else []
        last_date = str(res.daily.index[-1].date()) if not res.daily.empty else None
        eq = res.daily["equity"] if not res.daily.empty else None
        accounts[name] = {
            "plain": STRATEGIES[name]["plain"], "stop_pct": stop, "summary": s,
            "last_day_return": (float(eq.iloc[-1] / (eq.iloc[-2] if len(eq) > 1 else capital) - 1)
                                if eq is not None else None),
            "equity": [{"date": str(d.date()), **{c: float(r[c]) for c in ("equity", "pnl", "costs", "trades")}}
                       for d, r in res.daily.iterrows()],
            "trades": trades,
            "last_trade_date": last_date,
            "last_trades": [t for t in trades if str(t["date"])[:10] == last_date],
            "pending": res.pending,
            "open_positions": res.open_positions,
        }
        if eq is not None and res.daily["bench"].notna().any():
            b = res.daily["bench"]
            bench.update(value=float(b.iloc[-1]), **{"return": float(b.iloc[-1] / capital - 1)},
                         last_day_return=float(b.iloc[-1] / (b.iloc[-2] if len(b) > 1 else capital) - 1))

        # Did the settled history change since the previous run?
        if prev and name in prev.get("accounts", {}):
            cutoff = prev["data_through"]
            old = {trade_key(t) for t in prev["accounts"][name]["trades"]}
            new = {trade_key(t) for t in trades if str(t["date"])[:10] <= cutoff}
            if old != new:
                checks.append({"level": "alert", "text":
                               f"{name}: {len(old ^ new)} previously settled paper trade(s) changed after a data "
                               "revision. Compare state/ledger.json with its previous copy before trusting the record."})
            announced = {p["symbol"] for p in prev["accounts"][name].get("pending", [])}
            traded = {t["symbol"] for t in trades if str(t["date"])[:10] == prev.get("next_session")}
            if prev.get("next_session", "") <= str(last.date()) and announced != traded:
                checks.append({"level": "warn", "text":
                               f"{name}: stocks traded on {prev['next_session']} differ from the orders announced "
                               f"(announced {sorted(announced)}, traded {sorted(traded)})."})

    # ------------------------------------------------------- guard rails, gate
    ps = accounts[primary]["summary"]
    pause = float(cfg.get("pause_drawdown", 0.08))
    if ps.get("days", 0) and ps["max_drawdown"] <= -pause:
        checks.append({"level": "alert", "text":
                       f"{primary} has fallen {abs(ps['max_drawdown']) * 100:.1f}% from its peak, past the "
                       f"{pause * 100:.0f}% pause line. If this were real money, trading would stop here."})
    gate_cfg = cfg["go_live_gate"]
    days = ps.get("days", 0)
    items = [
        {"pass": days >= gate_cfg["min_sessions"],
         "text": f"At least {gate_cfg['min_sessions']} paper sessions (so far {days})"},
        {"pass": days > 0 and ps["net_pnl"] > 0,
         "text": f"Net profit after all charges (so far Rs {ps.get('net_pnl', 0):+,.0f})"},
        {"pass": days > 0 and ps["profit_factor"] >= gate_cfg["min_profit_factor"],
         "text": f"Profit factor of {gate_cfg['min_profit_factor']} or better "
                 f"(so far {ps['profit_factor']:.2f})" if days else
                 f"Profit factor of {gate_cfg['min_profit_factor']} or better (no trades yet)"},
        {"pass": days > 0 and ps["max_drawdown"] > -gate_cfg["max_drawdown"],
         "text": f"Worst fall from peak under {gate_cfg['max_drawdown'] * 100:.0f}% "
                 f"(so far {abs(ps.get('max_drawdown', 0)) * 100:.1f}%)"},
        {"pass": days > 0 and bench["return"] is not None and ps["total_return"] > bench["return"],
         "text": "Ahead of simply holding the Nifty 50 ETF over the same period"},
    ]
    ready = all(i["pass"] for i in items)
    gate = {"strategy": primary, "items": items,
            "verdict": ("Gate passed on paper. Paper results still assume ideal fills; start with a small "
                        "amount if you go live." if ready else "Not ready for real money. Keep it on paper.")}

    worst = {"ok": 0, "info": 0, "warn": 1, "alert": 2}
    rank = max(worst[c["level"]] for c in checks)
    ledger = clean({
        "generated_at": now.strftime("%Y-%m-%d %H:%M IST"),
        "data_through": str(last.date()), "next_session": str(next_day),
        "paper_start": cfg["paper_start"], "capital": capital,
        "status": ["OK", "CHECK", "ALERT"][rank], "checks": checks,
        "accounts": accounts, "benchmark": bench, "gate": gate,
    })

    # ------------------------------------------------------------------ write
    state_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    if prev_path.exists():
        (state_dir / "ledger.previous.json").write_text(prev_path.read_text())
    prev_path.write_text(json.dumps(ledger, indent=1))
    text = render(ledger)
    (reports_dir / f"{last.date()}.md").write_text(text)
    (reports_dir / "latest.md").write_text(text)
    print(text)
    return 0 if rank < 2 else 2


if __name__ == "__main__":
    sys.exit(main())
