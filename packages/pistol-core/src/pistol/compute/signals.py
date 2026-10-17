"""Trading signal detectors. Return list of (date, signal_str, value) tuples."""

from __future__ import annotations

from datetime import date

import pandas as pd

from . import indicators as ind
from ..types import PriceBar


def _bars_to_df(bars):
    if not bars:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    return pd.DataFrame([
        {"timestamp": pd.Timestamp(b.timestamp), "open": b.open, "high": b.high,
         "low": b.low, "close": b.close, "volume": b.volume}
        for b in bars
    ])


def _cross_above(fast, slow):
    prev = fast.shift(1) <= slow.shift(1)
    now = fast > slow
    return (prev & now).fillna(False)


def _cross_below(fast, slow):
    prev = fast.shift(1) >= slow.shift(1)
    now = fast < slow
    return (prev & now).fillna(False)


def golden_cross(bars, fast=50, slow=200):
    """Fast SMA crosses above slow SMA."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    sma_f = df["close"].rolling(fast).mean()
    sma_s = df["close"].rolling(slow).mean()
    cross = _cross_above(sma_f, sma_s)
    out = []
    for i in range(len(df)):
        if cross.iloc[i]:
            ts = df["timestamp"].iloc[i]
            out.append((ts.date() if hasattr(ts, "date") else ts, "golden_cross", float(sma_f.iloc[i])))
    return out


def death_cross(bars, fast=50, slow=200):
    """Fast SMA crosses below slow SMA."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    sma_f = df["close"].rolling(fast).mean()
    sma_s = df["close"].rolling(slow).mean()
    cross = _cross_below(sma_f, sma_s)
    out = []
    for i in range(len(df)):
        if cross.iloc[i]:
            ts = df["timestamp"].iloc[i]
            out.append((ts.date() if hasattr(ts, "date") else ts, "death_cross", float(sma_f.iloc[i])))
    return out


def macd_crossover(bars):
    """MACD line crosses signal line (bullish or bearish)."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    ema_fast = df["close"].ewm(span=12, adjust=False).mean()
    ema_slow = df["close"].ewm(span=26, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    bull = _cross_above(macd_line, signal_line)
    bear = _cross_below(macd_line, signal_line)
    out = []
    for i in range(len(df)):
        if bull.iloc[i]:
            ts = df["timestamp"].iloc[i]
            out.append((ts.date() if hasattr(ts, "date") else ts, "macd_bullish_cross", float(macd_line.iloc[i])))
        elif bear.iloc[i]:
            ts = df["timestamp"].iloc[i]
            out.append((ts.date() if hasattr(ts, "date") else ts, "macd_bearish_cross", float(macd_line.iloc[i])))
    return out


def rsi_oversold(bars, period=14, threshold=30):
    """RSI drops below threshold."""
    pts = ind.rsi(bars, period)
    out = []
    prev_val = None
    for p in pts:
        v = p.value
        if v is not None and prev_val is not None and prev_val >= threshold and v < threshold:
            out.append((p.timestamp, "rsi_oversold", float(v)))
        prev_val = v
    return out


def rsi_overbought(bars, period=14, threshold=70):
    """RSI rises above threshold."""
    pts = ind.rsi(bars, period)
    out = []
    prev_val = None
    for p in pts:
        v = p.value
        if v is not None and prev_val is not None and prev_val <= threshold and v > threshold:
            out.append((p.timestamp, "rsi_overbought", float(v)))
        prev_val = v
    return out


def volume_spike(bars, period=20, multiplier=2.0):
    """Volume > multiplier * rolling avg."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    avg = df["volume"].rolling(period).mean()
    spikes = df["volume"] > (multiplier * avg)
    out = []
    for i in range(len(df)):
        if spikes.iloc[i] and not pd.isna(avg.iloc[i]):
            ts = df["timestamp"].iloc[i]
            out.append((ts.date() if hasattr(ts, "date") else ts, "volume_spike", float(df["volume"].iloc[i])))
    return out


def breakout_52w_high(bars):
    """Close > max of prior 252 bars."""
    df = _bars_to_df(bars)
    if df.empty or len(df) < 253:
        return []
    prior_max = df["close"].rolling(252).max().shift(1)
    bo = df["close"] > prior_max
    out = []
    for i in range(len(df)):
        if bo.iloc[i]:
            ts = df["timestamp"].iloc[i]
            out.append((ts.date() if hasattr(ts, "date") else ts, "breakout_52w_high", float(df["close"].iloc[i])))
    return out


def breakdown_52w_low(bars):
    """Close < min of prior 252 bars."""
    df = _bars_to_df(bars)
    if df.empty or len(df) < 253:
        return []
    prior_min = df["close"].rolling(252).min().shift(1)
    bo = df["close"] < prior_min
    out = []
    for i in range(len(df)):
        if bo.iloc[i]:
            ts = df["timestamp"].iloc[i]
            out.append((ts.date() if hasattr(ts, "date") else ts, "breakdown_52w_low", float(df["close"].iloc[i])))
    return out
