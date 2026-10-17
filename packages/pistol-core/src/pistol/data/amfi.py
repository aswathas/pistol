"""AMFI (Association of Mutual Funds in India) adapter.

Free, official, stable. nav-all.txt gives daily NAV for every mutual fund
scheme. Portfolio disclosure PDFs (monthly) give which MFs hold which stocks.
"""

from __future__ import annotations

import io
import re
from datetime import date, datetime

import pandas as pd
import requests

from . import cache
from ..config import REQUEST_TIMEOUT, USER_AGENT


NAV_ALL_URL = "https://www.amfiindia.com/spages/NAVAll.txt"


def _fetch_nav_all_raw() -> str:
    r = requests.get(NAV_ALL_URL, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    return r.text


def nav_all(force_refresh: bool = False) -> pd.DataFrame:
    """Return full AMFI NAV table as DataFrame. Columns: scheme_code, isin, scheme_name, nav, date."""

    def _fetch():
        raw = _fetch_nav_all_raw()
        # Lines look like:
        # 119989;INF209K01KE1;Aditya Birla Sun Life Banking & PSU Debt Fund - Direct Plan - Growth;10.4567;09-Oct-2025
        rows = []
        for line in raw.splitlines():
            line = line.strip()
            if not line or ";" not in line:
                continue
            parts = line.split(";")
            if len(parts) < 5:
                continue
            try:
                scheme_code = int(parts[0])
            except ValueError:
                continue
            isin = parts[1].strip()
            name = parts[2].strip()
            try:
                nav = float(parts[3])
            except ValueError:
                continue
            date_str = parts[4].strip()
            try:
                d = datetime.strptime(date_str, "%d-%b-%Y").date()
            except ValueError:
                continue
            rows.append(
                {
                    "scheme_code": scheme_code,
                    "isin": isin,
                    "scheme_name": name,
                    "nav": nav,
                    "date": d,
                }
            )
        return rows

    cached = cache.get("amfi_nav_all")
    if cached and not force_refresh:
        return pd.DataFrame(cached)

    rows = _fetch()
    cache.set("amfi_nav_all", rows, ttl=86400)
    return pd.DataFrame(rows)


def search_schemes(query: str, limit: int = 20) -> list[dict]:
    """Fuzzy search AMFI schemes by name substring."""
    df = nav_all()
    if df.empty or not query:
        return []
    mask = df["scheme_name"].str.contains(query, case=False, regex=False)
    return df[mask].head(limit).to_dict(orient="records")


def scheme_by_code(scheme_code: int) -> dict | None:
    df = nav_all()
    if df.empty:
        return None
    row = df[df["scheme_code"] == scheme_code]
    if row.empty:
        return None
    return row.iloc[0].to_dict()
