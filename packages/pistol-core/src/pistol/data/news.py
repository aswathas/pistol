"""Google News RSS adapter.

Free, no auth, generous rate limits. Used for market news and stock-specific
news. hl=en-IN&gl=IN&ceid=IN:en for Indian English results.
"""

from __future__ import annotations

import re
from datetime import datetime

import feedparser
import requests

from . import cache
from ..config import REQUEST_TIMEOUT, USER_AGENT


_BASE = "https://news.google.com/rss"


def search(query: str, limit: int = 20, when: str = "7d") -> list[dict]:
    """Search news for query. when: 1h/1d/7d/30d or empty for all-time."""

    def _fetch():
        params = {
            "q": query,
            "hl": "en-IN",
            "gl": "IN",
            "ceid": "IN:en",
        }
        if when:
            params["q"] = f"{query} when:{when}"
        try:
            r = requests.get(_BASE, params=params, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
            r.raise_for_status()
        except requests.RequestException:
            return []
        feed = feedparser.parse(r.text)
        items = []
        for entry in feed.entries[:limit]:
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            ts = datetime(*published[:6]) if published else datetime.now()
            source = ""
            if hasattr(entry, "source") and hasattr(entry.source, "title"):
                source = entry.source.title
            items.append(
                {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "published": ts.isoformat(),
                    "source": source,
                    "summary": re.sub("<[^>]+>", "", entry.get("summary", ""))[:500],
                }
            )
        return items

    return cache.get_or_set("news_search", _fetch, query=query, when=when, limit=limit)


def market_news(limit: int = 30) -> list[dict]:
    """Top Indian market news."""
    return search("Indian stock market NSE BSE", limit=limit, when="1d")
