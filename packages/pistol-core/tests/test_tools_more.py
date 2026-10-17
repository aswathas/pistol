"""Smoke tests for the new tools (volatility, stats, portfolio, search, batch, intraday, advanced chart)."""

from __future__ import annotations

import json
import signal

import pytest

from pistol.tools import (
    TOOL_REGISTRY,
    backtest_sma_crossover,
    get_advanced_chart,
    get_batch_quotes,
    get_beta,
    get_correlation,
    get_garman_klass_volatility,
    get_historical_volatility,
    get_hurst_exponent,
    get_intraday_ticks,
    get_parkinson_volatility,
    get_yang_zhang_volatility,
    get_z_score,
    portfolio_correlation_matrix,
    portfolio_max_drawdown,
    portfolio_sector_concentration,
    portfolio_sharpe,
    portfolio_var,
    screen_by_indicator,
    search_stocks,
)


def _timeout(seconds=30):
    def handler(signum, frame):
        raise TimeoutError(f"test exceeded {seconds}s")
    signal.signal(signal.SIGBREAK if hasattr(signal, "SIGBREAK") else signal.SIGALRM, handler)
    if hasattr(signal, "alarm"):
        signal.alarm(seconds)


def test_registry_has_new_tools():
    expected = {
        "get_historical_volatility", "get_parkinson_volatility",
        "get_garman_klass_volatility", "get_yang_zhang_volatility",
        "get_hurst_exponent", "get_z_score", "get_correlation", "get_beta",
        "screen_by_indicator", "portfolio_sector_concentration",
        "portfolio_var", "portfolio_sharpe", "portfolio_max_drawdown",
        "portfolio_correlation_matrix", "backtest_sma_crossover",
        "search_stocks", "get_batch_quotes", "get_intraday_ticks",
        "get_advanced_chart",
    }
    missing = expected - set(TOOL_REGISTRY)
    assert not missing, f"missing tools: {missing}"


def test_get_historical_volatility():
    _timeout(30)
    r = get_historical_volatility("RELIANCE", period=30)
    assert r.tool == "get_historical_volatility"
    assert r.data is not None
    assert r.chart is not None


def test_get_parkinson_volatility():
    _timeout(30)
    r = get_parkinson_volatility("RELIANCE", period=30)
    assert r.tool == "get_parkinson_volatility"
    assert r.chart is not None


def test_get_garman_klass_volatility():
    _timeout(30)
    r = get_garman_klass_volatility("RELIANCE", period=30)
    assert r.tool == "get_garman_klass_volatility"
    assert r.chart is not None


def test_get_yang_zhang_volatility():
    _timeout(30)
    r = get_yang_zhang_volatility("RELIANCE", period=30)
    assert r.tool == "get_yang_zhang_volatility"
    assert r.chart is not None


def test_get_hurst_exponent():
    _timeout(30)
    r = get_hurst_exponent("RELIANCE", max_lag=20)
    assert r.tool == "get_hurst_exponent"
    assert r.data is not None
    assert "interpretation" in r.data


def test_get_z_score():
    _timeout(30)
    r = get_z_score("RELIANCE", period=20)
    assert r.tool == "get_z_score"
    assert r.chart is not None


def test_get_correlation():
    _timeout(30)
    r = get_correlation("RELIANCE", "TCS", period=60)
    assert r.tool == "get_correlation"
    assert r.data is not None


def test_get_beta():
    _timeout(30)
    r = get_beta("RELIANCE", index_symbol="^NSEI", period=60)
    assert r.tool == "get_beta"
    assert r.chart is not None


def test_screen_by_indicator_rsi():
    _timeout(60)
    r = screen_by_indicator(["RELIANCE", "TCS", "INFY"], "rsi", "<", 30, period=14)
    assert r.tool == "screen_by_indicator"
    assert "matched" in r.data


def test_portfolio_sector_concentration():
    holdings = json.dumps([{"symbol": "RELIANCE", "value": 60000}, {"symbol": "TCS", "value": 40000}])
    sectors = json.dumps({"RELIANCE": "Energy", "TCS": "IT"})
    r = portfolio_sector_concentration(holdings, sectors)
    assert r.tool == "portfolio_sector_concentration"
    assert r.chart is not None
    assert abs(r.data["Energy"] - 0.6) < 1e-6


def test_portfolio_var():
    rets = json.dumps([0.01, -0.02, 0.005, -0.03, 0.02, -0.01, 0.015])
    r = portfolio_var(rets, confidence=0.95)
    assert r.tool == "portfolio_var"
    assert "value_at_risk" in r.data


def test_portfolio_sharpe():
    rets = json.dumps([0.01, -0.02, 0.005, -0.03, 0.02, -0.01, 0.015])
    r = portfolio_sharpe(rets, risk_free=0.06)
    assert r.tool == "portfolio_sharpe"
    assert "sharpe" in r.data


def test_portfolio_max_drawdown():
    eq = json.dumps([100, 110, 105, 95, 100, 120, 90, 110])
    r = portfolio_max_drawdown(eq)
    assert r.tool == "portfolio_max_drawdown"
    assert "max_drawdown" in r.data
    assert r.data["max_drawdown"] > 0


def test_portfolio_correlation_matrix():
    rets = json.dumps({
        "A": [0.01, -0.02, 0.005, -0.03, 0.02],
        "B": [0.015, -0.018, 0.003, -0.025, 0.022],
        "C": [-0.005, 0.012, -0.008, 0.015, -0.010],
    })
    r = portfolio_correlation_matrix(rets)
    assert r.tool == "portfolio_correlation_matrix"
    assert r.chart is not None


def test_backtest_sma_crossover():
    _timeout(60)
    r = backtest_sma_crossover("RELIANCE", fast=50, slow=200, years=5)
    assert r.tool == "backtest_sma_crossover"
    assert r.chart is not None
    assert "equity_curve" in r.data


def test_search_stocks():
    r = search_stocks("RELI")
    assert r.tool == "search_stocks"
    assert "RELIANCE" in r.data["matched"]


def test_get_batch_quotes():
    _timeout(30)
    r = get_batch_quotes(["RELIANCE", "TCS"])
    assert r.tool == "get_batch_quotes"
    assert r.data is not None


def test_get_intraday_ticks():
    _timeout(30)
    r = get_intraday_ticks("RELIANCE", interval="5m")
    assert r.tool == "get_intraday_ticks"
    assert r.data is not None


def test_get_advanced_chart_with_indicators():
    _timeout(30)
    r = get_advanced_chart("RELIANCE", chart_type="candlestick", period="1mo", indicators=["rsi"])
    assert r.tool == "get_advanced_chart"
    assert r.chart is not None
    assert "rsi" in r.data.get("indicators", {})
