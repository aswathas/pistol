"""yfinance adapter.

Primary source for EOD OHLCV (5y daily) and intraday (1m/5m/15m, 30 days).
Secondary source for live quotes (15-min delayed, used as fallback).
Zero scraping, no cookies, no rate-limit fight.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from . import cache
from ..types import Exchange, OHLC, PriceBar, Quote


# yfinance (>=0.2) ships a peewee.SqliteDatabase in yfinance.cache for the
# timezone lookup. peewee creates the underlying sqlite3 connection lazily on
# first use in whatever thread that is, and the default `check_same_thread`
# is True. So any subsequent request on a different uvicorn worker thread
# blows up with "SQLite objects created in a thread can only be used in that
# same thread." peewee's `Database.connect()` reads from
# `self.connect_params` (not kwargs), so we set the flag there for every
# peewee database that exists at import time, and override `connect` to
# inject the flag at connection time for any future ones. This is the
# most robust fix and doesn't depend on yfinance internals.
try:
    import peewee as _pw
    _orig_connect = _pw.SqliteDatabase.connect

    def _patch_connect_params():
        for _cls in (_pw.SqliteDatabase,):
            params = getattr(_cls, "connect_params", None)
            if isinstance(params, dict):
                params["check_same_thread"] = False

    _patch_connect_params()

    def _threadsafe_connect(self, *a, **kw):
        try:
            self.connect_params["check_same_thread"] = False
        except Exception:
            pass
        # Reopen with the safe flag (closes any previously bound thread).
        try:
            self.close()
        except Exception:
            pass
        return _orig_connect(self, *a, **kw)

    _pw.SqliteDatabase.connect = _threadsafe_connect

    # Force any existing instance to drop its connection so the next call
    # uses the patched connect().
    try:
        import yfinance.cache as _yfc
        for _name in ("_TzCacheManager", "_CookieCacheManager", "_ISINCacheManager"):
            _cls = getattr(_yfc, _name, None)
            if _cls is not None:
                _db = getattr(_cls, "_db", None)
                if _db is not None:
                    try:
                        _db.close()
                    except Exception:
                        pass
                    _db.connect_params["check_same_thread"] = False
    except Exception:
        pass
except Exception:
    pass


def _to_nse_symbol(symbol: str) -> str:
    """yfinance uses NSE symbols with .NS suffix (e.g. RELIANCE.NS).
    Indices like ^NSEI must be passed as-is; yfinance keys them by caret prefix.
    """
    s = symbol.upper().strip()
    if s.startswith("^"):
        return s
    if s.endswith(".NS") or s.endswith(".BO"):
        return s
    return f"{s}.NS"


def quote(symbol: str) -> Quote | None:
    """Live quote via yfinance. ~15 min delayed but always works.
    Returns None when yfinance has no data for the symbol.
    """
    sym = _to_nse_symbol(symbol)

    def _fetch():
        import yfinance as yf

        try:
            t = yf.Ticker(sym)
            info = t.fast_info if hasattr(t, "fast_info") else {}
        except Exception:
            return None
        if not info:
            return None
        # yfinance raises KeyError on missing keys; treat any access failure as None.
        def _safe(key, default=None):
            try:
                v = info.get(key)
                return v if v is not None else default
            except Exception:
                return default
        price = _safe("lastPrice") or _safe("regularMarketPreviousClose") or _safe("previousClose")
        if price is None:
            return None
        prev_close = _safe("previousClose") or _safe("regularMarketPreviousClose") or price
        vol = _safe("lastVolume") or _safe("volume") or 0
        ltp = float(price)
        pv = float(prev_close)
        change = ltp - pv
        pct = (change / pv * 100) if pv else 0.0
        return Quote(
            symbol=symbol.upper(),
            exchange=Exchange.NSE,
            name=symbol.upper(),
            ltp=ltp,
            change=change,
            pct_change=pct,
            volume=int(vol),
            ohlc=OHLC(
                open=float(_safe("open") or ltp),
                high=float(_safe("dayHigh") or ltp),
                low=float(_safe("dayLow") or ltp),
                close=ltp,
                volume=int(vol),
            ),
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

        try:
            t = yf.Ticker(sym)
            df = t.history(period=period, interval=interval, auto_adjust=False)
        except Exception:
            return []
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
    This is a placeholder returning empty list; use nse.search() instead.
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
