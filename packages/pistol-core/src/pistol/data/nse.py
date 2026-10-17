"""NSE public site adapter.

NSE blocks aggressive scrapers and rotates endpoint shapes. We:
1. Maintain a session with proper cookies + browser UA
2. Hit the public quote API
3. On any failure, fall back to yfinance (handled in tools layer)

Coverage: NSE-listed equities. BSE-listed covered by bse.py.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

import requests

from . import cache
from ..config import BROWSER_USER_AGENT, REQUEST_TIMEOUT
from ..types import Exchange, OHLC, PriceBar, Quote


_BASE = "https://www.nseindia.com"
_QUOTE_API = f"{_BASE}/api/quote-equity"
_QUOTE_FALLBACK = f"{_BASE}/api/quote-equity?symbol={}"
_HISTORY_API = f"{_BASE}/api/historical/cm/equity"


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": _BASE,
        }
    )
    return s


_session_cache: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session_cache
    if _session_cache is None:
        _session_cache = _session()
    return _session_cache


def _bootstrap_cookies() -> None:
    """Hit homepage once to seed cookies. NSE requires this before quote API."""
    s = _get_session()
    try:
        s.get(_BASE, timeout=REQUEST_TIMEOUT)
    except requests.RequestException:
        pass


def quote(symbol: str) -> Quote | None:
    """Live NSE quote. Returns None on any failure (caller falls back)."""
    sym = symbol.upper().strip()

    def _fetch():
        s = _get_session()
        # First call: seed cookies if needed
        if not s.cookies:
            _bootstrap_cookies()
        try:
            r = s.get(f"{_QUOTE_API}?symbol={sym}", timeout=REQUEST_TIMEOUT)
        except requests.RequestException:
            return None
        if r.status_code != 200:
            return None
        try:
            data = r.json()
        except json.JSONDecodeError:
            return None
        if not data or "priceInfo" not in data:
            return None
        info = data["priceInfo"]
        meta = data.get("info", {}) or {}
        ltp = float(info.get("lastPrice", 0) or 0)
        prev_close = float(info.get("previousClose", 0) or 0)
        change = float(info.get("change", 0) or 0)
        pct = float(info.get("pChange", 0) or 0)
        vol = int(info.get("totalTradedVolume", 0) or 0)
        ohlc = OHLC(
            open=float(info.get("open", 0) or 0),
            high=float(info.get("intraDayHighLow", {}).get("high", {}).get("value", 0) or info.get("open", 0)),
            low=float(info.get("intraDayHighLow", {}).get("low", {}).get("value", 0) or info.get("open", 0)),
            close=ltp,
            volume=vol,
        )
        return Quote(
            symbol=sym,
            exchange=Exchange.NSE,
            name=meta.get("companyName"),
            ltp=ltp,
            change=change,
            pct_change=pct,
            volume=vol,
            bid=float(info.get("bid", 0) or 0) or None,
            ask=float(info.get("ask", 0) or 0) or None,
            bid_qty=None,
            ask_qty=None,
            ohlc=ohlc,
            timestamp=datetime.now(),
            source="nse",
        ).model_dump(mode="json")

    return _fetch()  # don't cache NSE direct, too flaky


def search(query: str, limit: int = 20) -> list[dict]:
    """NSE has no public search API. Use yfinance for search by symbol.
    Returns empty list — caller should use a different approach.
    """
    return []


def price_history(symbol: str, days: int = 365) -> list[PriceBar]:
    """NSE historical data via bhavcopy download. Stub: defer to yfinance."""
    return []


def corporate_actions(symbol: str) -> list[dict]:
    """NSE corporate actions via JSON endpoint. Stub."""
    return []


def shareholding(symbol: str) -> list[dict]:
    """NSE shareholding pattern. Stub."""
    return []


def indices_list() -> list[dict]:
    """NSE indices. Stub."""
    return []
