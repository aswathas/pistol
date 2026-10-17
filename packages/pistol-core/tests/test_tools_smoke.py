"""Smoke tests for the tool registry. Hits network via yfinance; 30s timeout each."""

from __future__ import annotations

import signal

import pytest

from pistol.tools import (
    TOOL_REGISTRY,
    claude_tool_schema,
    get_advanced_chart,
    get_candlestick_patterns,
    get_company_profile,
    get_financials,
    get_indicator,
    get_market_news,
    get_price_history,
    get_shareholding,
    get_signals,
    get_stock_news,
    get_stock_quote,
    get_top_movers,
)


def _timeout(seconds=30):
    def handler(signum, frame):
        raise TimeoutError(f"test exceeded {seconds}s")
    signal.signal(signal.SIGBREAK if hasattr(signal, "SIGBREAK") else signal.SIGALRM, handler)
    if hasattr(signal, "alarm"):
        signal.alarm(seconds)


def test_registry_has_tools():
    assert len(TOOL_REGISTRY) >= 15


def test_schema_generation():
    schemas = claude_tool_schema(TOOL_REGISTRY)
    assert len(schemas) == len(TOOL_REGISTRY)
    for s in schemas:
        assert "name" in s and "description" in s and "input_schema" in s


def test_get_stock_quote():
    _timeout(30)
    r = get_stock_quote("RELIANCE")
    assert r.tool == "get_stock_quote"
    assert r.data is not None


def test_get_price_history():
    _timeout(30)
    r = get_price_history("RELIANCE", period="1mo")
    assert r.tool == "get_price_history"
    assert r.chart is not None


def test_get_indicator_rsi():
    _timeout(30)
    r = get_indicator("RELIANCE", "rsi", 14)
    assert r.tool == "get_indicator"
    assert r.chart is not None


def test_get_candlestick_patterns():
    _timeout(30)
    r = get_candlestick_patterns("RELIANCE", days=30)
    assert r.tool == "get_candlestick_patterns"


def test_get_signals():
    _timeout(30)
    r = get_signals("RELIANCE")
    assert r.tool == "get_signals"


def test_get_market_news():
    _timeout(30)
    r = get_market_news(limit=5)
    assert r.tool == "get_market_news"


def test_get_stock_news():
    _timeout(30)
    r = get_stock_news("RELIANCE", limit=5)
    assert r.tool == "get_stock_news"


def test_get_shareholding_stub():
    r = get_shareholding("RELIANCE")
    assert r.source == "stub"


def test_get_financials_stub():
    r = get_financials("RELIANCE")
    assert r.source == "stub"


def test_get_company_profile():
    _timeout(30)
    r = get_company_profile("RELIANCE")
    assert r.tool == "get_company_profile"


def test_get_top_movers():
    _timeout(30)
    r = get_top_movers(limit=5)
    assert r.tool == "get_top_movers"


def test_get_advanced_chart():
    _timeout(30)
    r = get_advanced_chart("RELIANCE", period="1mo")
    assert r.tool == "get_advanced_chart"
    assert r.chart is not None
