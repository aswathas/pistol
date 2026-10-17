"""BSE public site adapter.

BSE is more permissive than NSE. Used for BSE-listed scrips and as fallback
when NSE blocks. The bseindia.com quote endpoint is JSON over HTTP.
"""

from __future__ import annotations

import json
from datetime import datetime

import requests

from . import cache
from ..config import BROWSER_USER_AGENT, REQUEST_TIMEOUT
from ..types import Exchange, OHLC, Quote


_BASE = "https://www.bseindia.com"


def quote(symbol: str) -> Quote | None:
    """BSE live quote. Stub: defer to yfinance for now (BSE API requires scrip code, not symbol)."""
    return None


def scrip_search(query: str) -> list[dict]:
    """BSE scrip code lookup. Stub."""
    return []
