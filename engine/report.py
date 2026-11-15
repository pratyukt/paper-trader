"""Daily report: checks, account values, settled paper trades, next session's paper orders."""
from __future__ import annotations

import math

from .signals import STRATEGIES

LEVEL_TAG = {"ok": "OK", "info": "NOTE", "warn": "CHECK", "alert": "ALERT"}


def _pct(x, digits=2):
    return "n/a" if x is None or not math.isfinite(x) else f"{x * 100:+.{digits}f}%"


def _rs(x):
    return f"Rs {x:,.0f}"


def how_to_trade(name: str, stop: float | None) -> str:
    spec = STRATEGIES[name]
    stop_txt = ""
    if spec["kind"] == "intraday" and stop:
        where = "above" if spec.get("side") == "short" else "below"
        stop_txt = f" Stop-loss {stop * 100:.1f}% {where} the opening price."
    if spec["kind"] == "intraday" and spec.get("side") == "short":
        return ("Sell short at the open (intraday order in the 9:00-9:07 pre-open window), "
                "buy back before 3:15 pm." + stop_txt)
    if spec["kind"] == "intraday":
        return ("Buy at the open (order in the 9:00-9:07 pre-open window), sell before 3:15 pm."
                + stop_txt)
    if spec["kind"] == "overnight":
        return "Buy just before the close, sell at the next open."
    return "Buy at the open, hold until the close recovers above the 5-day average or 5 sessions pass."


def render(ledger: dict) -> str:
    L = [
        f"# Paper trading report - data through {ledger['data_through']}",
        "",
        f"**Status: {ledger['status']}**. Paper money only; no real orders are placed. "
        f"Each account started with {_rs(ledger['capital'])} on {ledger['paper_start']}.",
        "",
        "## Checks",
        "",
    ]
    for chk in ledger["checks"]:
        L.append(f"- [{LEVEL_TAG[chk['level']]}] {chk['text']}")

    L += ["", "## Accounts", "",
          "| Account | Value | Since start | Last session | Sessions | Profitable days | "
          "Charges paid | Worst fall from peak |",
          "|---|---|---|---|---|---|---|---|"]
    for name, acc in ledger["accounts"].items():
        s = acc["summary"]
        if s.get("days", 0) == 0:
            L.append(f"| {name} | {_rs(ledger['capital'])} | - | - | 0 | - | - | - |")
            continue
        L.append(
            f"| {name} | {_rs(s['end_equity'])} | {_pct(s['total_return'])} | {_pct(acc['last_day_return'])} | "
            f"{s['days']} | {_pct(s['profitable_days'], 0).lstrip('+')} | {_rs(s['costs_paid'])} | "
            f"{_pct(s['max_drawdown'])} |"
        )
    b = ledger["benchmark"]
    if b.get("value") is not None:
        L.append(f"| {b['symbol']} buy & hold | {_rs(b['value'])} | {_pct(b['return'])} | "
                 f"{_pct(b['last_day_return'])} | - | - | - | - |")
    else:
        L.append(f"| {b['symbol']} buy & hold | {_rs(ledger['capital'])} | - | - | - | - | - | - |")

    for name, acc in ledger["accounts"].items():
        last = acc["last_trades"]
        L += ["", f"## {name}", "", STRATEGIES[name]["plain"], ""]
        if last:
            L += [f"Settled on {acc['last_trade_date']}:", "",
                  "| Stock | Side | Shares | Entry | Exit | Exit reason | Before charges | Charges | Net |",
                  "|---|---|---|---|---|---|---|---|---|"]
            for t in last:
                L.append(f"| {t['symbol']} | {t['side']} | {t['qty']:.0f} | {t['entry']:.2f} | {t['exit']:.2f} | "
                         f"{t['exit_reason']} | {t['gross']:+,.0f} | {t['costs']:,.0f} | {t['net']:+,.0f} |")
            L.append("")
        else:
            L += ["No paper trades settled yet.", ""]
        if acc["pending"]:
            L += [f"Paper orders for {ledger['next_session']} (from the {ledger['data_through']} close):", "",
                  "| Stock | Shares (est.) | Reference close | Amount |", "|---|---|---|---|"]
            for p in acc["pending"]:
                L.append(f"| {p['symbol']} | {p['est_qty']} | {p['ref_close']:.2f} | {_rs(p['alloc'])} |")
            L += ["", how_to_trade(name, acc["stop_pct"])]
        else:
            L.append(f"No stock qualified for {ledger['next_session']}; the account stays in cash.")

    g = ledger["gate"]
    L += ["", f"## Go-live gate ({g['strategy']})", ""]
    for item in g["items"]:
        L.append(f"- [{'PASS' if item['pass'] else 'NOT YET'}] {item['text']}")
    L += ["", f"**{g['verdict']}**", ""]
    return "\n".join(L)
