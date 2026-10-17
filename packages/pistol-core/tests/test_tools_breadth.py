"""Smoke tests for breadth + market-data + FII/DII + news tools.

Network via yfinance/Google News where needed; offline for stubs and FII/DII
fallback. Generous timeouts (network may be slow).
"""

from __future__ import annotations

import signal

import pytest

from pistol.data import fii_dii
from pistol.tools import (
    TOOL_REGISTRY,
    get_fii_dii_flows,
    get_india_market_news,
    get_india_vix,
    get_index_performance,
    get_market_breadth,
    get_market_pulse,
    get_market_pulse_with_flows,
    get_market_heatmap,
    get_new_highs_lows,
    get_sector_rotation,
    get_stock_news_with_sentiment,
    get_top_movers,
    list_indices,
)


def _timeout(seconds=60):
    def handler(signum, frame):
        raise TimeoutError(f"test exceeded {seconds}s")
    signal.signal(signal.SIGBREAK if hasattr(signal, "SIGBREAK") else signal.SIGALRM, handler)
    if hasattr(signal, "alarm"):
        signal.alarm(seconds)


def test_registry_grew_with_breadth_tools():
    # 15 existing + 12 new + 1 from poc = at least 27
    assert len(TOOL_REGISTRY) >= 27


def test_fii_dii_fallback_data():
    d = fii_dii.daily_flows(days=5)
    assert d["source"] == "fallback"
    assert isinstance(d["rows"], list)
    assert len(d["rows"]) >= 1
    assert "fii_net" in d["rows"][0] and "dii_net" in d["rows"][0]


def test_get_fii_dii_flows():
    _timeout(30)
    r = get_fii_dii_flows(period="5d")
    assert r.tool == "get_fii_dii_flows"
    assert r.source == "fallback"
    assert isinstance(r.data["rows"], list)


def test_get_market_pulse():
    _timeout(90)
    r = get_market_pulse(limit=5)
    assert r.tool == "get_market_pulse"
    assert r.chart is not None
    assert r.data["count"] >= 1


def test_get_top_movers_direction_gainers():
    _timeout(90)
    r = get_top_movers(limit=5, direction="gainers")
    assert r.tool == "get_top_movers"
    assert r.data["direction"] == "gainers"
    assert isinstance(r.data["movers"], list)


def test_get_top_movers_direction_losers():
    _timeout(90)
    r = get_top_movers(limit=5, direction="losers")
    assert r.data["direction"] == "losers"


def test_get_top_movers_backcompat():
    _timeout(90)
    r = get_top_movers(limit=5)  # default direction=mixed
    assert r.data["direction"] == "mixed"


def test_get_index_performance():
    _timeout(60)
    r = get_index_performance(index="^NSEI", period="6mo")
    assert r.tool == "get_index_performance"
    assert r.chart is not None


def test_get_market_heatmap():
    _timeout(120)
    r = get_market_heatmap()
    assert r.tool == "get_market_heatmap"
    assert r.chart is not None
    assert "y_labels" in r.data and "x_labels" in r.data


def test_get_sector_rotation():
    _timeout(120)
    r = get_sector_rotation(period="1m")
    assert r.tool == "get_sector_rotation"
    assert r.chart is not None
    assert isinstance(r.data["sectors"], list)


def test_list_indices():
    _timeout(120)
    r = list_indices()
    assert r.tool == "list_indices"
    assert len(r.data["indices"]) >= 10


def test_get_india_vix():
    _timeout(60)
    r = get_india_vix()
    assert r.tool == "get_india_vix"


def test_get_market_breadth():
    _timeout(120)
    r = get_market_breadth()
    assert r.tool == "get_market_breadth"
    assert r.chart is not None
    total = r.data["total"]
    assert total >= 0


def test_get_new_highs_lows():
    _timeout(180)
    r = get_new_highs_lows()
    assert r.tool == "get_new_highs_lows"
    assert "near_high_count" in r.data
    assert "near_low_count" in r.data


def test_get_market_pulse_with_flows():
    _timeout(120)
    r = get_market_pulse_with_flows(limit=5, period="5d")
    assert r.tool == "get_market_pulse_with_flows"
    assert "pulse" in r.data and "flows" in r.data


def test_get_india_market_news():
    _timeout(60)
    r = get_india_market_news(limit=5)
    assert r.tool == "get_india_market_news"
    assert "items" in r.data


def test_get_stock_news_with_sentiment():
    _timeout(60)
    r = get_stock_news_with_sentiment("RELIANCE", limit=5)
    assert r.tool == "get_stock_news_with_sentiment"
    assert "aggregate" in r.data
    assert r.data["aggregate"]["label"] in {"positive", "negative", "neutral"}
