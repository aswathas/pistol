"""Config: env, source priority, cache TTLs."""

from __future__ import annotations

import os
from pathlib import Path


def _cache_dir() -> Path:
    d = Path(os.environ.get("PISTOL_CACHE_DIR", Path.home() / ".cache" / "pistol"))
    d.mkdir(parents=True, exist_ok=True)
    return d


CACHE_DIR = _cache_dir()
DB_PATH = CACHE_DIR / "pistol.sqlite"

# Source priority: lower number = tried first.
# Fallback chain per data type. Failure of one source cascades to the next.
SOURCE_PRIORITY: dict[str, list[str]] = {
    "quote_nse": ["nse", "yfinance"],
    "quote_bse": ["bse", "yfinance"],
    "ohlcv_daily": ["yfinance", "nse_bhavcopy", "bse_bhavcopy"],
    "ohlcv_intraday": ["nse", "yfinance"],
    "delivery": ["nse_bhavcopy"],
    "corporate_actions": ["nse_corporate_rss", "bse_corporate_rss"],
    "fundamentals": ["nse_xbrl", "bse_xbrl", "amfi"],
    "shareholding": ["nse_shareholding", "bse_shareholding"],
    "fii_dii": ["nsdl", "nse_pdf"],
    "macro": ["rbi", "data_gov_in"],
    "news": ["google_news_rss"],
    "mf_holdings": ["amfi"],
    "indices": ["nse_indices", "bse_indices"],
}

# Cache TTLs (seconds). Different data has different freshness needs.
CACHE_TTLS: dict[str, int] = {
    "quote": 60,            # 60s during market hours
    "quote_after_hours": 3600,  # 1h after market close
    "ohlcv_daily": 86400,  # 1 day
    "ohlcv_intraday": 300,  # 5 min
    "delivery": 86400,
    "corporate_actions": 604800,  # 1 week
    "fundamentals": 21600,  # 6h
    "shareholding": 604800,
    "fii_dii": 3600,
    "macro": 86400,
    "news": 900,            # 15 min
    "mf_holdings": 86400,
    "indices": 300,
    "compute": 300,         # 5 min for derived values
}

# Network politeness
REQUEST_TIMEOUT = 15
USER_AGENT = "pistol/0.1 (https://github.com/aswathas13/pistol)"

# NSE/BSE specifically want a browser UA
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
