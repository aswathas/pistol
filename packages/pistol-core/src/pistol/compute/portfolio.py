"""Portfolio analytics: concentration, VaR/CVaR, Sharpe/Sortino, drawdown, backtest."""

from __future__ import annotations

from datetime import date
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


def sector_concentration(holdings, sector_map):
    """Each holding: {symbol, value}. Returns sector -> pct of portfolio."""
    total = sum(h.get("value", 0) for h in holdings)
    if total <= 0:
        return {}
    buckets = {}
    for h in holdings:
        sym = h["symbol"]
        sec = sector_map.get(sym, "Unknown")
        buckets[sec] = buckets.get(sec, 0.0) + h.get("value", 0)
    return {k: v / total for k, v in buckets.items()}


def var(returns, confidence=0.95):
    """Historical Value-at-Risk. Returns negative number (loss)."""
    if not returns:
        return 0.0
    s = pd.Series(returns).dropna()
    if s.empty:
        return 0.0
    return float(-s.quantile(1 - confidence))


def cvar(returns, confidence=0.95):
    """Expected Shortfall: mean of returns worse than VaR threshold."""
    if not returns:
        return 0.0
    s = pd.Series(returns).dropna()
    if s.empty:
        return 0.0
    threshold = s.quantile(1 - confidence)
    tail = s[s <= threshold]
    if tail.empty:
        return float(-threshold)
    return float(-tail.mean())


def sharpe(returns, risk_free=0.06, annualize=True):
    """Sharpe ratio. Assumes daily returns if annualize=True."""
    if not returns or len(returns) < 2:
        return 0.0
    s = pd.Series(returns).dropna()
    if s.std() == 0:
        return 0.0
    daily_rf = risk_free / 252 if annualize else risk_free
    excess = s - daily_rf
    sr = excess.mean() / s.std()
    if annualize:
        sr = sr * np.sqrt(252)
    return float(sr)


def sortino(returns, risk_free=0.06):
    """Sortino ratio: like Sharpe but uses downside deviation only."""
    if not returns or len(returns) < 2:
        return 0.0
    s = pd.Series(returns).dropna()
    daily_rf = risk_free / 252
    excess = s - daily_rf
    downside = s[s < 0]
    if downside.empty or downside.std() == 0:
        return 0.0
    return float(excess.mean() / downside.std() * np.sqrt(252))


def max_drawdown(equity_curve):
    """Returns (max_dd_pct, start_idx, end_idx) where pct is positive number."""
    if not equity_curve:
        return (0.0, 0, 0)
    s = pd.Series(equity_curve)
    running_max = s.cummax()
    drawdown = (running_max - s) / running_max
    idx = int(drawdown.idxmax())
    peak_idx = int(s.iloc[: idx + 1].idxmax()) if idx >= 0 else 0
    return (float(drawdown.iloc[idx]), peak_idx, idx)


def correlation_matrix(returns_by_symbol):
    """NxN pandas DataFrame of correlations."""
    df = pd.DataFrame(returns_by_symbol)
    return df.corr()


def backtest_sma_crossover(bars, fast=50, slow=200, initial_cash=100000.0):
    """All-in/out SMA crossover backtest. Returns equity_curve, trades, sharpe, max_dd, total_return, years."""
    df = _bars_to_df(bars)
    if df.empty or len(df) < slow + 2:
        return {
            "equity_curve": [],
            "trades": [],
            "sharpe": 0.0,
            "max_dd": 0.0,
            "total_return": 0.0,
            "years": 0.0,
        }
    sma_f = df["close"].rolling(fast).mean()
    sma_s = df["close"].rolling(slow).mean()
    cross_up = (sma_f.shift(1) <= sma_s.shift(1)) & (sma_f > sma_s)
    cross_dn = (sma_f.shift(1) >= sma_s.shift(1)) & (sma_f < sma_s)
    cash = initial_cash
    shares = 0
    equity = []
    trades = []
    for i in range(len(df)):
        price = float(df["close"].iloc[i])
        if cross_up.iloc[i] and shares == 0:
            shares = int(cash // price)
            if shares > 0:
                cash -= shares * price
                trades.append({"date": str(df["timestamp"].iloc[i].date()), "action": "buy", "price": price, "shares": shares})
        elif cross_dn.iloc[i] and shares > 0:
            cash += shares * price
            trades.append({"date": str(df["timestamp"].iloc[i].date()), "action": "sell", "price": price, "shares": shares})
            shares = 0
        equity.append(cash + shares * price)
    if shares > 0:
        last_price = float(df["close"].iloc[-1])
        cash += shares * last_price
        equity[-1] = cash
        trades.append({"date": str(df["timestamp"].iloc[-1].date()), "action": "sell", "price": last_price, "shares": shares})
    final = equity[-1] if equity else initial_cash
    total_return = (final - initial_cash) / initial_cash if initial_cash else 0.0
    daily_returns = pd.Series(equity).pct_change().dropna().tolist()
    sh = sharpe(daily_returns) if daily_returns else 0.0
    dd, _, _ = max_drawdown(equity)
    days = (df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]).days if len(df) > 1 else 0
    years = days / 365.25 if days > 0 else 0.0
    return {
        "equity_curve": equity,
        "trades": trades,
        "sharpe": sh,
        "max_dd": dd,
        "total_return": total_return,
        "years": years,
    }
