"""Statistical computations: z-score, correlation, beta, correlation matrix."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..types import PriceBar


def _bars_to_df(bars):
    if not bars:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    return pd.DataFrame([
        {"timestamp": pd.Timestamp(b.timestamp), "open": b.open, "high": b.high,
         "low": b.low, "close": b.close, "volume": b.volume}
        for b in bars
    ])


def _field_series(bars, field):
    df = _bars_to_df(bars)
    if field not in df.columns:
        return pd.Series(dtype=float)
    return df[field]


def z_score(bars, period=20):
    """Z-score of close vs rolling mean/std."""
    s = _field_series(bars, "close")
    if s.empty:
        return []
    mean = s.rolling(period).mean()
    std = s.rolling(period).std()
    z = (s - mean) / std.replace(0, np.nan)
    return [None if pd.isna(v) else float(v) for v in z]


def correlation(bars_a, bars_a_field, bars_b, bars_b_field, period=60):
    """Rolling correlation between two series."""
    a = _field_series(bars_a, bars_a_field)
    b = _field_series(bars_b, bars_b_field)
    if a.empty or b.empty:
        return []
    n = min(len(a), len(b))
    a, b = a.iloc[-n:], b.iloc[-n:]
    corr = a.rolling(period).corr(b)
    return [None if pd.isna(v) else float(v) for v in corr]


def beta(stock_bars, index_bars, period=60):
    """Beta of stock vs index from log returns."""
    stock = _field_series(stock_bars, "close")
    index = _field_series(index_bars, "close")
    if stock.empty or index.empty:
        return []
    n = min(len(stock), len(index))
    stock, index = stock.iloc[-n:], index.iloc[-n:]
    stock_lr = np.log(stock / stock.shift(1))
    index_lr = np.log(index / index.shift(1))
    cov = stock_lr.rolling(period).cov(index_lr)
    var = index_lr.rolling(period).var()
    b = cov / var.replace(0, np.nan)
    return [None if pd.isna(v) else float(v) for v in b]


def pair_correlation_matrix(symbols_to_bars, period=60):
    """NxN correlation matrix of close returns."""
    syms = list(symbols_to_bars.keys())
    rets = {}
    for sym in syms:
        bars = symbols_to_bars[sym]
        s = _field_series(bars, "close")
        if s.empty:
            rets[sym] = pd.Series(dtype=float)
            continue
        rets[sym] = np.log(s / s.shift(1))
    df = pd.DataFrame(rets)
    df = df.tail(period) if len(df) > period else df
    return df.corr()
