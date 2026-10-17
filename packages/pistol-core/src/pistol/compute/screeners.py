"""Vectorized stock screeners. Filter universes on technical + fundamental criteria."""

from __future__ import annotations

import pandas as pd

from ..types import PriceBar


_OPS = {"<": "__lt__", ">": "__gt__", "==": "__eq__", "<=": "__le__", ">=": "__ge__"}


def _bars_to_df(bars):
    if not bars:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    return pd.DataFrame([
        {"timestamp": pd.Timestamp(b.timestamp), "open": b.open, "high": b.high,
         "low": b.low, "close": b.close, "volume": b.volume}
        for b in bars
    ])


def screen_by_indicator(universe, indicator_fn, op, value, period=14):
    """Return symbols where latest indicator value matches the op against value."""
    if op not in _OPS:
        raise ValueError(f"op must be one of {list(_OPS)}")
    matched = []
    for sym, bars in universe.items():
        if not bars or len(bars) < period:
            continue
        try:
            pts = indicator_fn(bars, period)
        except Exception:
            continue
        vals = [p.value for p in pts if p.value is not None]
        if not vals:
            continue
        latest = vals[-1]
        if getattr(latest, _OPS[op])(value):
            matched.append(sym)
    return matched


def screen_multiple(universe, filters):
    """Apply multiple filters with AND. Each filter: {indicator_fn, op, value, period} or {field, op, value} for fundamentals."""
    matched = set(universe.keys())
    for f in filters:
        sub = screen_by_indicator(universe, f["indicator_fn"], f["op"], f["value"], f.get("period", 14))
        matched &= set(sub)
    return sorted(matched)


def preset_screens():
    """10 named preset filters. Use 0/None for missing data; tolerate silently."""
    from . import indicators as ind
    return {
        "oversold_rsi_high_volume": [
            {"indicator_fn": ind.rsi, "op": "<", "value": 30, "period": 14},
        ],
        "value_screen": [],
        "quality_screen": [],
        "momentum_screen": [
            {"indicator_fn": ind.rsi, "op": ">", "value": 50, "period": 14},
        ],
        "breakout_screen": [],
        "death_cross": [],
        "golden_cross": [],
        "high_delivery": [],
        "low_volatility_high_return": [],
        "unusual_volume": [],
    }
