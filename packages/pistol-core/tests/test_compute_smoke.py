"""Smoke tests: import each compute module, run on synthetic 30-bar series."""

from __future__ import annotations

from datetime import date, timedelta

from pistol.compute import indicators, patterns, portfolio, screeners, signals, statistics, volatility
from pistol.types import PriceBar


def _bars(n=30, start_price=100.0):
    bars = []
    price = start_price
    for i in range(n):
        price *= 1.001
        o = price - 0.5
        c = price + 0.5
        h = c + 1.0
        l = o - 1.0
        bars.append(PriceBar(timestamp=date(2024, 1, 1) + timedelta(days=i),
                             open=o, high=h, low=l, close=c, volume=10000 + i * 100))
    return bars


BARS = _bars()


def test_indicators_sma():
    out = indicators.sma(BARS, 14)
    assert isinstance(out, list) and len(out) == 30


def test_indicators_ema():
    out = indicators.ema(BARS, 14)
    assert isinstance(out, list) and len(out) == 30


def test_indicators_rsi():
    out = indicators.rsi(BARS, 14)
    assert isinstance(out, list) and len(out) == 30


def test_indicators_macd():
    out = indicators.macd(BARS)
    assert isinstance(out, list) and len(out) == 30


def test_indicators_bollinger():
    out = indicators.bollinger(BARS)
    assert isinstance(out, list) and len(out) == 30


def test_indicators_atr():
    out = indicators.atr(BARS, 14)
    assert isinstance(out, list) and len(out) == 30


def test_indicators_adx():
    out = indicators.adx(BARS, 14)
    assert isinstance(out, list) and len(out) == 30


def test_indicators_stochastic():
    out = indicators.stochastic(BARS)
    assert isinstance(out, list) and len(out) == 30


def test_indicators_cci():
    out = indicators.cci(BARS)
    assert isinstance(out, list) and len(out) == 30


def test_indicators_williams_r():
    out = indicators.williams_r(BARS)
    assert isinstance(out, list) and len(out) == 30


def test_indicators_roc():
    out = indicators.roc(BARS)
    assert isinstance(out, list) and len(out) == 30


def test_indicators_mfi():
    out = indicators.mfi(BARS)
    assert isinstance(out, list) and len(out) == 30


def test_indicators_obv():
    out = indicators.obv(BARS)
    assert isinstance(out, list) and len(out) == 30


def test_indicators_vwap():
    out = indicators.vwap(BARS)
    assert isinstance(out, list) and len(out) == 30


def test_indicators_ichimoku():
    out = indicators.ichimoku(BARS)
    assert isinstance(out, list) and len(out) == 30


def test_indicators_parabolic_sar():
    out = indicators.parabolic_sar(BARS)
    assert isinstance(out, list) and len(out) == 30


def test_indicators_keltner():
    out = indicators.keltner(BARS)
    assert isinstance(out, list) and len(out) == 30


def test_indicators_donchian():
    out = indicators.donchian(BARS)
    assert isinstance(out, list) and len(out) == 30


def test_indicators_aroon():
    out = indicators.aroon(BARS)
    assert isinstance(out, list) and len(out) == 30


def test_indicators_supertrend():
    out = indicators.supertrend(BARS)
    assert isinstance(out, list) and len(out) == 30


def test_patterns_detect_all():
    out = patterns.detect_all(BARS)
    assert isinstance(out, dict) and len(out) >= 12
    assert "doji" in out and "marubozu" in out


def test_patterns_doji():
    out = patterns.doji(BARS)
    assert isinstance(out, list)


def test_volatility_hv():
    out = volatility.historical_volatility(BARS)
    assert isinstance(out, list) and len(out) == 30


def test_volatility_parkinson():
    out = volatility.parkinson(BARS)
    assert isinstance(out, list)


def test_volatility_garman_klass():
    out = volatility.garman_klass(BARS)
    assert isinstance(out, list)


def test_volatility_yang_zhang():
    out = volatility.yang_zhang(BARS)
    assert isinstance(out, list)


def test_volatility_hurst():
    out = volatility.hurst_exponent(BARS, max_lag=10)
    assert isinstance(out, list)


def test_statistics_z_score():
    out = statistics.z_score(BARS)
    assert isinstance(out, list) and len(out) == 30


def test_statistics_correlation():
    out = statistics.correlation(BARS, "close", BARS, "close", period=10)
    assert isinstance(out, list)


def test_statistics_beta():
    out = statistics.beta(BARS, BARS, period=10)
    assert isinstance(out, list)


def test_statistics_pair_corr():
    out = statistics.pair_correlation_matrix({"A": BARS, "B": BARS})
    assert hasattr(out, "shape")


def test_signals_golden_cross():
    out = signals.golden_cross(BARS)
    assert isinstance(out, list)


def test_signals_death_cross():
    out = signals.death_cross(BARS)
    assert isinstance(out, list)


def test_signals_macd_crossover():
    out = signals.macd_crossover(BARS)
    assert isinstance(out, list)


def test_signals_rsi_oversold():
    out = signals.rsi_oversold(BARS)
    assert isinstance(out, list)


def test_signals_volume_spike():
    out = signals.volume_spike(BARS)
    assert isinstance(out, list)


def test_screeners_preset():
    presets = screeners.preset_screens()
    assert isinstance(presets, dict) and len(presets) >= 10


def test_screeners_screen_by_indicator():
    out = screeners.screen_by_indicator({"A": BARS}, indicators.rsi, ">", 0, period=14)
    assert isinstance(out, list)


def test_portfolio_var():
    out = portfolio.var([0.01, -0.02, 0.03, -0.01, 0.02])
    assert isinstance(out, float)


def test_portfolio_cvar():
    out = portfolio.cvar([0.01, -0.02, 0.03, -0.01, 0.02])
    assert isinstance(out, float)


def test_portfolio_sharpe():
    out = portfolio.sharpe([0.01, -0.02, 0.03, -0.01, 0.02])
    assert isinstance(out, float)


def test_portfolio_max_drawdown():
    dd, s, e = portfolio.max_drawdown([100, 110, 90, 95, 105])
    assert isinstance(dd, float) and s == 1 and e == 2


def test_portfolio_correlation_matrix():
    out = portfolio.correlation_matrix({"A": [0.01, 0.02, -0.01], "B": [0.02, -0.01, 0.01]})
    assert hasattr(out, "shape")


def test_portfolio_backtest():
    long_bars = _bars(300)
    out = portfolio.backtest_sma_crossover(long_bars, fast=20, slow=50)
    assert "equity_curve" in out and "trades" in out
