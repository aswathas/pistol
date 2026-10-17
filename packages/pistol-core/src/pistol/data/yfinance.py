"""yfinance adapter.

Primary source for EOD OHLCV (5y daily) and intraday (1m/5m/15m, 30 days).
Secondary source for live quotes (15-min delayed, used as fallback).
Zero scraping, no cookies, no rate-limit fight.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd

from . import cache
from ..types import Exchange, OHLC, PriceBar, Quote


def _to_nse_symbol(symbol: str) -> str:
    """yfinance uses NSE symbols with .NS suffix (e.g. RELIANCE.NS)."""
    s = symbol.upper().strip()
    if s.endswith(".NS") or s.endswith(".BO"):
        return s
    return f"{s}.NS"


def quote(symbol: str) -> Quote | None:
    """Live quote via yfinance. ~15 min delayed but always works."""
    sym = _to_nse_symbol(symbol)

    def _fetch():
        import yfinance as yf

        t = yf.Ticker(sym)
        info = t.fast_info if hasattr(t, "fast_info") else {}
        price = info.get("last_price") or info.get("previous_close")
        prev_close = info.get("previous_close")
        if price is None:
            return None
        ltp = float(price)
        change = ltp - float(prev_close) if prev_close else 0.0
        pct = (change / float(prev_close) * 100) if prev_close else 0.0
        vol = int(info.get("volume") or 0)
        day_high = float(info.get("day_high") or ltp)
        day_low = float(info.get("day_low") or ltp)
        day_open = float(info.get("open") or ltp)
        name = info.get("short_name") or info.get("long_name") or symbol
        return Quote(
            symbol=symbol.upper(),
            exchange=Exchange.NSE,
            name=name,
            ltp=ltp,
            change=change,
            pct_change=pct,
            volume=vol,
            bid=None,
            ask=None,
            bid_qty=None,
            ask_qty=None,
            ohlc=OHLC(open=day_open, high=day_high, low=day_low, close=ltp, volume=vol),
            timestamp=datetime.now(),
            source="yfinance",
        ).model_dump(mode="json")

    raw = cache.get_or_set("quote", _fetch, symbol=sym)
    return Quote(**raw) if raw else None


def price_history(
    symbol: str,
    period: str = "1y",
    interval: str = "1d",
) -> list[PriceBar]:
    """OHLCV history. period: 1d/5d/1mo/3mo/6mo/1y/2y/5y/10y/ytd/max.
    interval: 1m/2m/5m/15m/30m/60m/90m/1h/1d/5d/1wk/1mo/3mo.
    """
    sym = _to_nse_symbol(symbol)
    cache_key = f"ohlcv_{interval}"

    def _fetch():
        import yfinance as yf

        t = yf.Ticker(sym)
        df = t.history(period=period, interval=interval, auto_adjust=False)
        if df is None or df.empty:
            return []
        bars = []
        for idx, row in df.iterrows():
            ts = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
            bars.append(
                {
                    "timestamp": ts.date().isoformat() if hasattr(ts, "date") else str(ts),
                    "open": float(row.get("Open", 0) or 0),
                    "high": float(row.get("High", 0) or 0),
                    "low": float(row.get("Low", 0) or 0),
                    "close": float(row.get("Close", 0) or 0),
                    "volume": int(row.get("Volume", 0) or 0),
                    "adj_close": float(row.get("Adj Close", 0) or 0) if "Adj Close" in row else None,
                    "delivery_pct": None,
                    "delivery_volume": None,
                }
            )
        return bars

    raw = cache.get_or_set(cache_key, _fetch, symbol=sym, period=period, interval=interval)
    return [PriceBar(**b) for b in (raw or [])]


def search(query: str, limit: int = 20) -> list[dict]:
    """yfinance doesn't expose a search API. Use NSE for that.
    This is a placeholder returning empty list — use nse.search() instead.
    """
    return []


def is_market_open() -> bool:
    """Heuristic: NSE hours are 9:15-15:30 IST, Mon-Fri."""
    from datetime import datetime
    import pytz
    try:
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist)
    except Exception:
        return False
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close
