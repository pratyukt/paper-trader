"""Indian equity trading charges (NSE cash segment), per round trip.

Rates are fractions of traded value. Defaults follow Dhan's published rate card
and statutory levies as checked in November 2026. They change from time to
time, so compare against a real contract note before trusting them with money.
"""
from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class CostModel:
    # Brokerage
    brokerage_pct_intraday: float = 0.0003   # 0.03% per executed order ...
    brokerage_cap: float = 20.0              # ... or Rs 20, whichever is lower
    brokerage_pct_delivery: float = 0.0      # zero on delivery
    # Securities Transaction Tax
    stt_intraday_sell: float = 0.00025       # 0.025% on the sell side only
    stt_delivery: float = 0.001              # 0.1% on buy and on sell
    # Exchange, regulator, stamp duty
    exch_txn: float = 0.0000307              # NSE transaction charge, both sides
    sebi: float = 0.000001                   # Rs 10 per crore, both sides
    stamp_intraday_buy: float = 0.00003      # 0.003% on the buy side
    stamp_delivery_buy: float = 0.00015      # 0.015% on the buy side
    gst: float = 0.18                        # on brokerage + exchange + SEBI charges
    dp_charge_per_sell: float = 14.75        # Rs per scrip per sell day (delivery), incl. GST
    # Execution friction: assumed adverse move per side versus the reference price
    slippage: float = 0.0005                 # 0.05% per side

    @classmethod
    def from_dict(cls, d: dict | None) -> "CostModel":
        d = d or {}
        known = {f.name for f in fields(cls)}
        unknown = set(d) - known
        if unknown:
            raise ValueError(f"unknown cost settings: {sorted(unknown)}")
        return cls(**d)

    def _broker(self, value: float, pct: float) -> float:
        return min(self.brokerage_cap, value * pct) if pct > 0 else 0.0

    def intraday(self, buy_value: float, sell_value: float) -> float:
        """All charges in rupees for an intraday (MIS) round trip."""
        turnover = buy_value + sell_value
        brokerage = self._broker(buy_value, self.brokerage_pct_intraday) + self._broker(
            sell_value, self.brokerage_pct_intraday
        )
        exch = turnover * self.exch_txn
        sebi = turnover * self.sebi
        stt = sell_value * self.stt_intraday_sell
        stamp = buy_value * self.stamp_intraday_buy
        gst = (brokerage + exch + sebi) * self.gst
        return brokerage + exch + sebi + stt + stamp + gst

    def delivery(self, buy_value: float, sell_value: float) -> float:
        """All charges in rupees for a delivery (CNC) round trip, incl. DP charge on the sell."""
        turnover = buy_value + sell_value
        brokerage = self._broker(buy_value, self.brokerage_pct_delivery) + self._broker(
            sell_value, self.brokerage_pct_delivery
        )
        exch = turnover * self.exch_txn
        sebi = turnover * self.sebi
        stt = turnover * self.stt_delivery
        stamp = buy_value * self.stamp_delivery_buy
        gst = (brokerage + exch + sebi) * self.gst
        dp = self.dp_charge_per_sell if sell_value > 0 else 0.0
        return brokerage + exch + sebi + stt + stamp + gst + dp
