"""Technical indicators. Pure-pandas, take list[PriceBar], return list[IndicatorPoint]."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..types import IndicatorPoint, PriceBar, Signal


def _bars_to_df(bars):
    if not bars:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    return pd.DataFrame([
        {"timestamp": pd.Timestamp(b.timestamp), "open": b.open, "high": b.high,
         "low": b.low, "close": b.close, "volume": b.volume}
        for b in bars
    ])


def _to_points(dates, values, signals=None):
    out = []
    for i, ts in enumerate(dates):
        v = values.iloc[i]
        s = signals.iloc[i] if signals is not None else None
        out.append(IndicatorPoint(
            timestamp=ts.date() if hasattr(ts, "date") else ts,
            value=None if pd.isna(v) else float(v),
            signal=s if s is not None and not (isinstance(s, float) and pd.isna(s)) else None,
        ))
    return out


def sma(bars, period=20):
    """Simple moving average of close."""
    df = _bars_to_df(bars)
    s = df["close"].rolling(period).mean() if not df.empty else pd.Series(dtype=float)
    return _to_points(df["timestamp"], s)


def ema(bars, period=20):
    """Exponential moving average of close."""
    df = _bars_to_df(bars)
    s = df["close"].ewm(span=period, adjust=False).mean() if not df.empty else pd.Series(dtype=float)
    return _to_points(df["timestamp"], s)


def macd(bars, fast=12, slow=26, signal=9):
    """MACD line. v1 returns macd only; signal/histogram is wrapper concern."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    return _to_points(df["timestamp"], macd_line)


def rsi(bars, period=14):
    """Wilder RSI on close."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_val = 100 - (100 / (1 + rs))
    return _to_points(df["timestamp"], rsi_val)


def bollinger(bars, period=20, stddev=2.0):
    """Bollinger middle band (SMA). Upper/lower/%B in wrapper."""
    df = _bars_to_df(bars)
    s = df["close"].rolling(period).mean() if not df.empty else pd.Series(dtype=float)
    return _to_points(df["timestamp"], s)


def atr(bars, period=14):
    """Average True Range."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    atr_val = tr.ewm(alpha=1 / period, adjust=False).mean()
    return _to_points(df["timestamp"], atr_val)


def adx(bars, period=14):
    """ADX only. +DI/-DI in wrapper."""
    df = _bars_to_df(bars)
    if df.empty or len(df) < period * 2:
        return _to_points(df["timestamp"], pd.Series([np.nan] * len(df)))
    high = df["high"]
    low = df["low"]
    close = df["close"]
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    cond = plus_dm > minus_dm
    plus_dm = plus_dm.where(cond, 0.0)
    minus_dm = minus_dm.where(~cond, 0.0)
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr_v = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr_v.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr_v.replace(0, np.nan)
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)).abs()
    adx_val = dx.ewm(alpha=1 / period, adjust=False).mean()
    return _to_points(df["timestamp"], adx_val)


def stochastic(bars, k_period=14, d_period=3):
    """%K of stochastic. %D smoothing is wrapper concern."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    low_min = df["low"].rolling(k_period).min()
    high_max = df["high"].rolling(k_period).max()
    k = 100 * (df["close"] - low_min) / (high_max - low_min).replace(0, np.nan)
    return _to_points(df["timestamp"], k)


def cci(bars, period=20):
    """Commodity Channel Index."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    tp = (df["high"] + df["low"] + df["close"]) / 3
    sma_tp = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    cci_val = (tp - sma_tp) / (0.015 * mad.replace(0, np.nan))
    return _to_points(df["timestamp"], cci_val)


def williams_r(bars, period=14):
    """Williams percentR."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    high_max = df["high"].rolling(period).max()
    low_min = df["low"].rolling(period).min()
    wr = -100 * (high_max - df["close"]) / (high_max - low_min).replace(0, np.nan)
    return _to_points(df["timestamp"], wr)


def roc(bars, period=10):
    """Rate of change percent, close-based."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    roc_val = df["close"].pct_change(periods=period) * 100
    return _to_points(df["timestamp"], roc_val)


def mfi(bars, period=14):
    """Money Flow Index. Uses typical price + volume."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    tp = (df["high"] + df["low"] + df["close"]) / 3
    raw_mf = tp * df["volume"]
    delta = tp.diff()
    pos_mf = raw_mf.where(delta > 0, 0.0)
    neg_mf = raw_mf.where(delta < 0, 0.0)
    pos_sum = pos_mf.rolling(period).sum()
    neg_sum = neg_mf.rolling(period).sum()
    mf_ratio = pos_sum / neg_sum.replace(0, np.nan)
    mfi_val = 100 - (100 / (1 + mf_ratio))
    return _to_points(df["timestamp"], mfi_val)


def obv(bars):
    """On-balance volume. Returns cumulative volume series."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    direction = np.sign(df["close"].diff()).fillna(0)
    obv_val = (direction * df["volume"]).cumsum()
    return _to_points(df["timestamp"], obv_val)


def vwap(bars):
    """Cumulative VWAP. ponytail: yfinance daily bars are EOD; for true intraday VWAP pass one session only."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    tp = (df["high"] + df["low"] + df["close"]) / 3
    cum_pv = (tp * df["volume"]).cumsum()
    cum_v = df["volume"].cumsum()
    vwap_val = cum_pv / cum_v.replace(0, np.nan)
    return _to_points(df["timestamp"], vwap_val)


def ichimoku(bars, tenkan=9, kijun=26, senkou_b=52):
    """Tenkan-sen only. Kijun, Senkou A/B, Chikou in wrapper."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    tenkan_val = (df["high"].rolling(tenkan).max() + df["low"].rolling(tenkan).min()) / 2
    return _to_points(df["timestamp"], tenkan_val)


def parabolic_sar(bars, af_start=0.02, af_increment=0.02, af_max=0.2):
    """Parabolic SAR."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    high = df["high"].values
    low = df["low"].values
    sar = np.full(len(df), np.nan)
    if len(df) < 2:
        return _to_points(df["timestamp"], pd.Series(sar))
    af = af_start
    bull = True
    ep = high[0]
    sar[0] = low[0]
    for i in range(1, len(df)):
        sar[i] = sar[i - 1] + af * (ep - sar[i - 1])
        if bull:
            if low[i] < sar[i]:
                bull = False
                sar[i] = ep
                ep = low[i]
                af = af_start
            else:
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + af_increment, af_max)
                sar[i] = min(sar[i], low[i - 1])
                if i >= 2:
                    sar[i] = min(sar[i], low[i - 2])
        else:
            if high[i] > sar[i]:
                bull = True
                sar[i] = ep
                ep = high[i]
                af = af_start
            else:
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + af_increment, af_max)
                sar[i] = max(sar[i], high[i - 1])
                if i >= 2:
                    sar[i] = max(sar[i], high[i - 2])
    return _to_points(df["timestamp"], pd.Series(sar))


def keltner(bars, period=20, multiplier=2.0):
    """Keltner middle band (EMA)."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    mid = df["close"].ewm(span=period, adjust=False).mean()
    return _to_points(df["timestamp"], mid)


def donchian(bars, period=20):
    """Donchian middle band."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    mid = (df["high"].rolling(period).max() + df["low"].rolling(period).min()) / 2
    return _to_points(df["timestamp"], mid)


def aroon(bars, period=25):
    """Aroon Up only."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    roll_high_idx = df["high"].rolling(period + 1).apply(lambda x: np.argmax(x), raw=True)
    aroon_up = 100 * (period - roll_high_idx) / period
    return _to_points(df["timestamp"], aroon_up)


def supertrend(bars, period=10, multiplier=3.0):
    """Supertrend line + direction encoded as Signal.BUY/SELL."""
    df = _bars_to_df(bars)
    if df.empty:
        return []
    high = df["high"]
    low = df["low"]
    close = df["close"]
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr_v = tr.ewm(alpha=1 / period, adjust=False).mean()
    hl2 = (high + low) / 2
    upper = hl2 + multiplier * atr_v
    lower = hl2 - multiplier * atr_v
    st = np.full(len(df), np.nan)
    direction = np.ones(len(df), dtype=int)
    for i in range(1, len(df)):
        if close.iloc[i] > upper.iloc[i - 1]:
            direction[i] = 1
        elif close.iloc[i] < lower.iloc[i - 1]:
            direction[i] = -1
        else:
            direction[i] = direction[i - 1]
        if direction[i] == 1:
            st[i] = lower.iloc[i]
        else:
            st[i] = upper.iloc[i]
    sig = pd.Series([Signal.BUY if d == 1 else Signal.SELL for d in direction])
    return _to_points(df["timestamp"], pd.Series(st), signals=sig)
