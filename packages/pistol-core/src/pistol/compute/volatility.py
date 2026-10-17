"""Volatility estimators and Hurst exponent. Returns list[float] per bar."""

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


def historical_volatility(bars, period=30, annualize=True):
    """Stddev of log returns * sqrt(252) if annualized."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    lr = np.log(df["close"] / df["close"].shift(1))
    vol = lr.rolling(period).std()
    if annualize:
        vol = vol * np.sqrt(252)
    return [None if pd.isna(v) else float(v) for v in vol]


def parkinson(bars, period=30):
    """Parkinson high-low volatility estimator. Annualized."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    hl = np.log(df["high"] / df["low"]).pow(2)
    factor = np.sqrt(hl.rolling(period).mean() / (4 * np.log(2))) * np.sqrt(252)
    return [None if pd.isna(v) else float(v) for v in factor]


def garman_klass(bars, period=30):
    """Garman-Klass OHLC volatility estimator. Annualized."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    hl = np.log(df["high"] / df["low"]).pow(2)
    co = np.log(df["close"] / df["open"]).pow(2)
    gk = (0.5 * hl - (2 * np.log(2) - 1) * co).rolling(period).mean()
    factor = np.sqrt(gk) * np.sqrt(252)
    return [None if pd.isna(v) else float(v) for v in factor]


def yang_zhang(bars, period=30):
    """Yang-Zhang overnight + intraday combined estimator. Annualized."""
    df = _bars_to_df(bars)
    if df.empty or len(df) < period + 1:
        return [None] * len(df)
    log_ho = np.log(df["high"] / df["open"])
    log_lo = np.log(df["low"] / df["open"])
    log_co = np.log(df["close"] / df["open"])
    log_oc = np.log(df["open"] / df["close"].shift(1))
    log_cc = np.log(df["close"] / df["close"].shift(1))
    rs = (log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)).rolling(period).mean()
    oc_var = log_oc.rolling(period).var()
    cc_var = log_cc.rolling(period).var()
    k = 0.34 / (1.34 + (period + 1) / (period - 1))
    yz = oc_var + k * cc_var + (1 - k) * rs
    out = np.sqrt(yz) * np.sqrt(252)
    return [None if pd.isna(v) else float(v) for v in out]


def hurst_exponent(bars, max_lag=20):
    """Rescaled range / R/S Hurst exponent. Single scalar repeated for each bar."""
    df = _bars_to_df(bars)
    n = len(df)
    if n < max_lag * 2:
        return [None] * n
    prices = df["close"].values
    lags = range(2, max_lag + 1)
    tau = []
    for lag in lags:
        rs_values = []
        for start in range(0, n - lag, lag):
            chunk = prices[start:start + lag]
            if len(chunk) < lag:
                continue
            mean = chunk.mean()
            deviations = chunk - mean
            cumulative = np.cumsum(deviations)
            r = cumulative.max() - cumulative.min()
            s = chunk.std(ddof=1)
            if s > 0:
                rs_values.append(r / s)
        if rs_values:
            tau.append(np.mean(rs_values))
        else:
            tau.append(np.nan)
    valid = [(l, t) for l, t in zip(lags, tau) if not np.isnan(t) and t > 0]
    if len(valid) < 2:
        return [None] * n
    log_lags = np.log([l for l, _ in valid])
    log_tau = np.log([t for _, t in valid])
    hurst = np.polyfit(log_lags, log_tau, 1)[0]
    return [hurst] * n
