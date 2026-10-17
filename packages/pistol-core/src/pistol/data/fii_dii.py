"""FII/DII flows adapter.

NSE publishes daily FII/DII flows but the page is JS-rendered with no public
CSV/API; HTML scraping breaks routinely. Ponytail decision: ship a hardcoded
recent snapshot, mark `source: "fallback"`, and upgrade when a reliable free
source appears. ponytail: snapshot is illustrative; replace before any
production/quant use.
"""

from __future__ import annotations

from datetime import datetime

from . import cache


# Last 5 trading days, illustrative numbers in INR crores.
_FALLBACK_SNAPSHOT: list[dict] = [
    {"date": "2026-10-17", "fii_net":  1234.56, "dii_net": -567.89},
    {"date": "2026-10-16", "fii_net":  -456.78, "dii_net":  234.56},
    {"date": "2026-10-15", "fii_net":   890.12, "dii_net": -123.45},
    {"date": "2026-10-14", "fii_net":  -234.56, "dii_net":  567.89},
    {"date": "2026-10-13", "fii_net":   678.90, "dii_net": -345.67},
]


def daily_flows(days: int = 30) -> dict:
    """Return last `days` daily FII/DII flow rows. Currently always fallback.

    Returns a dict with keys: source, fetched_at, note, rows.
    """
    cached = cache.get("fii_dii_flows", days=days)
    if cached is not None:
        return cached

    out = {
        "source": "fallback",
        "fetched_at": datetime.now().isoformat(),
        "note": "NSE FII/DII page is JS-rendered with no public CSV. Using hardcoded snapshot.",
        "rows": list(_FALLBACK_SNAPSHOT)[: max(1, min(days, len(_FALLBACK_SNAPSHOT)))],
    }
    cache.set("fii_dii_flows", out, ttl=86400, days=days)
    return out
