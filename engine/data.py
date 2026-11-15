"""Market data: load NSE end-of-day history, overlay the newest daily bhavcopies.

Two public GitHub mirrors of NSE's own daily reports are used:

* BennyThadikaran/eod2_data  - full history, adjusted for splits and bonuses,
  refreshed about once a week.
* tilak999/NSE-Data-bank     - NSE's raw "sec_bhavdata_full" file for each day,
  normally published the same evening. Used only for days the history lacks.

Both are third-party mirrors. If either stops updating, point the loaders at
any other source that produces the same columns.
"""
from __future__ import annotations

import datetime as dt
import json
import pickle
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

FIELDS = ("open", "high", "low", "close", "volume")
BENCHMARK = "NIFTYBEES"  # Nifty 50 ETF: the "just buy the index" alternative

EOD2_REPO = "https://github.com/BennyThadikaran/eod2_data.git"
# Tried in order. The NSE address is the official source and is the better choice
# on your own machine; it is blocked from some cloud environments, where the
# GitHub mirror is used instead.
BHAV_URLS = (
    "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{:%d%m%Y}.csv",
    "https://raw.githubusercontent.com/tilak999/NSE-Data-bank/main/data/"
    "sec_bhavdata_full_{:%d%m%Y}.csv",
)
_HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}


def _fetch_bhavcopy(day: dt.date) -> tuple[bytes | None, str]:
    """Body of the day's bhavcopy from the first source that has it, plus a note."""
    last_note = "no source reachable"
    for url in BHAV_URLS:
        try:
            req = urllib.request.Request(url.format(day), headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
            if body.lstrip()[:6].upper() != b"SYMBOL":
                last_note = "unexpected file content, skipped"
                continue
            # Mirrors sometimes store the previous session under today's name.
            rows = body.decode("utf-8", "replace").splitlines()
            stamp = rows[1].split(",")[2].strip() if len(rows) > 1 else ""
            if stamp != f"{day:%d-%b-%Y}":
                last_note = f"source still has {stamp or 'no data'} under this date (holiday, or not out yet)"
                continue
            return body, "bhavcopy downloaded"
        except urllib.error.HTTPError as exc:
            last_note = ("no bhavcopy published (holiday, or not out yet)" if exc.code == 404
                         else f"download failed (HTTP {exc.code})")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_note = f"download failed ({getattr(exc, 'reason', exc)})"
    return None, last_note


# --------------------------------------------------------------------------- sync
def sync_eod2(eod_dir: Path) -> str:
    """Clone or refresh the history mirror. Returns a short status line."""
    eod_dir = Path(eod_dir)
    if (eod_dir / ".git").exists():
        subprocess.run(
            ["git", "-C", str(eod_dir), "fetch", "--depth", "1", "--quiet", "origin"],
            check=True, timeout=900,
        )
        subprocess.run(
            ["git", "-C", str(eod_dir), "reset", "--hard", "--quiet", "FETCH_HEAD"],
            check=True, timeout=300,
        )
        return "history refreshed"
    eod_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--depth", "1", "--quiet", EOD2_REPO, str(eod_dir)],
        check=True, timeout=1800,
    )
    return "history downloaded"


def sync_bhavcopy(bhav_dir: Path, after: dt.date, until: dt.date) -> list[str]:
    """Download daily bhavcopies for weekdays in (after, until]. Returns notes."""
    bhav_dir = Path(bhav_dir)
    bhav_dir.mkdir(parents=True, exist_ok=True)
    notes = []
    day = after + dt.timedelta(days=1)
    while day <= until:
        if day.weekday() < 5:
            dest = bhav_dir / f"sec_bhavdata_full_{day:%d%m%Y}.csv"
            if not dest.exists():
                body, note = _fetch_bhavcopy(day)
                if body is not None:
                    dest.write_bytes(body)
                notes.append(f"{day}: {note}")
        day += dt.timedelta(days=1)
    return notes


# --------------------------------------------------------------------------- load
def load_eod2(
    eod_dir: Path,
    start: str = "2014-01-01",
    min_p90_turnover: float = 2e8,
    cache_path: Path | None = None,
) -> dict:
    """Wide date x symbol frames for liquid NSE equities, plus the benchmark ETF.

    Only ordinary shares (ISIN prefix INE) are kept, and only symbols whose
    90th-percentile daily traded value reaches `min_p90_turnover` rupees, which
    is far below what a top-100-by-liquidity universe needs.
    """
    eod_dir = Path(eod_dir)
    meta = eod_dir / "meta.json"
    key = (meta.stat().st_mtime_ns if meta.exists() else 0, start, min_p90_turnover)
    if cache_path and Path(cache_path).exists():
        with open(cache_path, "rb") as fh:
            cached = pickle.load(fh)  # written by this module only
        if cached.get("key") == key:
            return cached["market"]

    sym2isin = json.loads((eod_dir / "isin_symbol_map.json").read_text())["sym2isin"]
    start_ts = pd.Timestamp(start)
    cols: dict[str, dict] = {f: {} for f in FIELDS}
    eq: dict[str, pd.Series] = {}
    src_cols = ["Open", "High", "Low", "Close", "Volume"]

    for path in sorted((eod_dir / "daily").glob("*.csv")):
        sym = path.stem.upper()
        is_bench = sym == BENCHMARK
        if not is_bench and not str(sym2isin.get(sym, "")).startswith("INE"):
            continue
        try:
            df = pd.read_csv(path, usecols=["Date", *src_cols, "Series"])
        except (ValueError, pd.errors.ParserError, pd.errors.EmptyDataError):
            continue
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])
        df = df[df["Date"] >= start_ts]
        if len(df) < 60:
            continue
        df = df.drop_duplicates("Date", keep="last").set_index("Date").sort_index()
        num = df[src_cols].apply(pd.to_numeric, errors="coerce")
        if not is_bench and (num["Close"] * num["Volume"]).quantile(0.9) < min_p90_turnover:
            continue
        for field, col in zip(FIELDS, src_cols):
            cols[field][sym] = num[col].astype("float64")
        eq[sym] = df["Series"].astype("string").str.strip().eq("EQ").fillna(False).astype(bool)

    market = {f: pd.DataFrame(cols[f]).sort_index() for f in FIELDS}
    idx = market["close"].index
    market["eq"] = (
        pd.DataFrame(eq).reindex(idx).astype("boolean").fillna(False).astype(bool)
    )
    market["suspect"] = set()
    market["notes"] = []
    market["holidays"] = load_holidays(eod_dir)
    if cache_path:
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "wb") as fh:
            pickle.dump({"key": key, "market": market}, fh)
    return market


def read_bhavcopy(path: Path) -> tuple[pd.Timestamp, pd.DataFrame]:
    """One NSE sec_bhavdata_full file -> (date, frame indexed by symbol), EQ series only."""
    df = pd.read_csv(path, skipinitialspace=True)
    df.columns = [c.strip() for c in df.columns]
    df = df[df["SERIES"].astype(str).str.strip() == "EQ"]
    date = pd.to_datetime(str(df["DATE1"].iloc[0]).strip(), format="%d-%b-%Y")
    out = df.set_index(df["SYMBOL"].astype(str).str.strip())
    out = out[["OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE", "TTL_TRD_QNTY"]]
    out = out.apply(pd.to_numeric, errors="coerce")
    out.columns = list(FIELDS)
    return date, out[~out.index.duplicated(keep="last")]


def overlay_bhavcopy(market: dict, bhav_dir: Path, max_jump: float = 0.25) -> dict:
    """Append days that the history lacks, from raw daily bhavcopies.

    Raw bhavcopies are not adjusted for splits or bonuses. A symbol whose close
    moves more than `max_jump` against the previous close is marked suspect and
    kept out of new picks until the adjusted history catches up.
    """
    bhav_dir = Path(bhav_dir)
    if not bhav_dir.exists():
        return market
    last = market["close"].index[-1]
    days = []
    for path in bhav_dir.glob("sec_bhavdata_full_*.csv"):
        try:
            date, frame = read_bhavcopy(path)
        except (ValueError, KeyError, IndexError, pd.errors.ParserError, pd.errors.EmptyDataError):
            market["notes"].append(f"{path.name}: unreadable bhavcopy, ignored")
            continue
        if date > last:
            days.append((date, frame))
    days.sort(key=lambda x: x[0])

    symbols = market["close"].columns
    holidays = market.get("holidays", set())
    for date, frame in days:
        prev = market["close"].index[-1]
        if date <= prev:
            continue
        missing = [d for d in sessions_between(prev.date(), date.date(), holidays)]
        if missing:
            # Never skip a session: settling picks against the wrong day would
            # corrupt the ledger. Wait until the missing day shows up.
            market["notes"].append(
                f"data gap: no file for {missing[0]} - days after it are on hold until it arrives"
            )
            break
        row = frame.reindex(symbols)
        prev_close = market["close"].iloc[-1]
        jump = (row["close"] / prev_close - 1).abs()
        for sym in jump[jump > max_jump].index:
            market["suspect"].add(sym)
            market["notes"].append(
                f"{date:%Y-%m-%d} {sym}: close moved {jump[sym]:.0%} vs previous close "
                "(possible split/bonus) - excluded from new picks"
            )
        for field in FIELDS:
            market[field].loc[date] = row[field].to_numpy(dtype="float64")
        market["eq"].loc[date] = row["close"].notna().to_numpy()
        market["notes"].append(f"{date:%Y-%m-%d}: taken from raw daily bhavcopy")
    return market


def load_holidays(eod_dir: Path) -> set:
    """Exchange holidays listed in the history mirror's meta.json (current year only)."""
    try:
        raw = json.loads((Path(eod_dir) / "meta.json").read_text()).get("holidays", {})
    except (OSError, ValueError):
        return set()
    out = set()
    for key in raw:
        try:
            out.add(dt.datetime.strptime(key, "%d-%b-%Y").date())
        except ValueError:
            continue
    return out


def is_session(day: dt.date, holidays: set) -> bool:
    return day.weekday() < 5 and day not in holidays


def sessions_between(after: dt.date, before: dt.date, holidays: set) -> list:
    """Trading sessions strictly between two dates."""
    out, day = [], after + dt.timedelta(days=1)
    while day < before:
        if is_session(day, holidays):
            out.append(day)
        day += dt.timedelta(days=1)
    return out


def expected_last_session(today: dt.date, holidays: set = frozenset()) -> dt.date:
    """Most recent trading session on or before `today`."""
    day = today
    while not is_session(day, holidays):
        day -= dt.timedelta(days=1)
    return day


def next_session(after: dt.date, holidays: set = frozenset()) -> dt.date:
    day = after + dt.timedelta(days=1)
    while not is_session(day, holidays):
        day += dt.timedelta(days=1)
    return day


def as_arrays(market: dict) -> dict:
    """Numpy views used by the simulator."""
    out = {f: market[f].to_numpy(dtype="float64") for f in FIELDS}
    out["eq"] = market["eq"].to_numpy(dtype=bool)
    out["dates"] = market["close"].index
    out["symbols"] = np.array(market["close"].columns)
    return out
