"""Unified tool registry. Each tool returns a ToolResult with data + chart + source."""

from __future__ import annotations

import inspect

from . import charts, compute
from .compute import indicators as ind, volatility, statistics, portfolio, screeners
from .data import news, yfinance
from .types import ChartSpec, PriceBar, Quote, ToolResult


NIFTY_50 = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "SBIN",
    "BHARTIARTL", "ITC", "KOTAKBANK", "LT", "AXISBANK", "ASIANPAINT", "MARUTI",
    "SUNPHARMA", "BAJFINANCE", "BAJAJFINSV", "WIPRO", "HCLTECH", "TECHM",
    "ULTRACEMCO", "TITAN", "NESTLEIND", "POWERGRID", "NTPC", "M&M", "TATASTEEL",
    "JSWSTEEL", "ADANIENT", "ADANIPORTS", "COALINDIA", "ONGC", "BPCL", "GRASIM",
    "INDUSINDBK", "CIPLA", "DRREDDY", "EICHERMOT", "HEROMOTOCO", "BAJAJ-AUTO",
    "DIVISLAB", "BRITANNIA", "APOLLOHOSP", "HINDALCO", "TATACONSUM", "SBILIFE",
    "HDFCLIFE", "UPL", "LTIM", "SHRIRAMFIN",
]


def _bars_from_yfinance(symbol, period="6mo", interval="1d"):
    return yfinance.price_history(symbol, period=period, interval=interval)


def get_stock_quote(symbol):
    """Fetch live quote for an Indian stock (NSE default)."""
    sym = symbol.upper()
    q = yfinance.quote(sym)
    if q is None:
        return ToolResult(tool="get_stock_quote", symbol=sym, data={"error": "no quote"}, source="yfinance", note="No data returned")
    return ToolResult(tool="get_stock_quote", symbol=sym, data=q.model_dump(mode="json") if hasattr(q, "model_dump") else q, source="yfinance")


def get_price_history(symbol, period="6mo", interval="1d"):
    """Fetch OHLCV price history and return a line chart of close prices."""
    sym = symbol.upper()
    bars = _bars_from_yfinance(sym, period, interval)
    if not bars:
        return ToolResult(tool="get_price_history", symbol=sym, data={"error": "no bars"}, source="yfinance")
    chart = charts.line_chart(
        title=f"{sym} close ({period})",
        x=[b.timestamp.isoformat() for b in bars],
        y=[b.close for b in bars],
        y_name="close",
    )
    return ToolResult(tool="get_price_history", symbol=sym, data={"bars": [b.model_dump(mode="json") for b in bars]}, chart=chart, source="yfinance")


_INDICATOR_DISPATCH = {
    "rsi": ind.rsi, "ema": ind.ema, "sma": ind.sma, "macd": ind.macd,
    "bollinger": ind.bollinger, "atr": ind.atr, "adx": ind.adx,
    "stochastic": ind.stochastic, "cci": ind.cci, "williams_r": ind.williams_r,
    "roc": ind.roc, "mfi": ind.mfi, "obv": ind.obv, "vwap": ind.vwap,
    "ichimoku": ind.ichimoku, "parabolic_sar": ind.parabolic_sar,
    "keltner": ind.keltner, "donchian": ind.donchian, "aroon": ind.aroon,
    "supertrend": ind.supertrend,
}


def get_indicator(symbol, indicator, period=14):
    """Compute a technical indicator. Returns data + line chart."""
    sym = symbol.upper()
    bars = _bars_from_yfinance(sym, period="6mo")
    if not bars:
        return ToolResult(tool="get_indicator", symbol=sym, data={"error": "no bars"}, source="compute")
    indicator = indicator.lower()
    if indicator not in _INDICATOR_DISPATCH:
        return ToolResult(tool="get_indicator", symbol=sym, data={"error": f"unsupported indicator {indicator}"}, source="compute")
    fn = _INDICATOR_DISPATCH[indicator]
    pts = fn(bars, period)
    chart = charts.line_chart(
        title=f"{sym} {indicator}({period})",
        x=[p.timestamp.isoformat() for p in pts],
        y=[p.value for p in pts],
        y_name=indicator,
        thresholds=[30, 70] if indicator == "rsi" else None,
    )
    return ToolResult(tool="get_indicator", symbol=sym, data={"indicator": indicator, "values": [p.model_dump(mode="json") for p in pts]}, chart=chart, source="compute")


def get_candlestick_patterns(symbol, days=100):
    """Detect 12 candlestick patterns in the last `days` bars."""
    sym = symbol.upper()
    bars = _bars_from_yfinance(sym, period="6mo")
    if not bars:
        return ToolResult(tool="get_candlestick_patterns", symbol=sym, data={"error": "no bars"}, source="compute")
    sub = bars[-days:] if len(bars) > days else bars
    detected = compute.patterns.detect_all(sub)
    return ToolResult(tool="get_candlestick_patterns", symbol=sym, data=detected, source="compute")


def get_signals(symbol):
    """Run all 8 trading signal detectors on the symbol."""
    sym = symbol.upper()
    bars = _bars_from_yfinance(sym, period="1y")
    if not bars:
        return ToolResult(tool="get_signals", symbol=sym, data={"error": "no bars"}, source="compute")
    out = {
        "golden_cross": compute.signals.golden_cross(bars),
        "death_cross": compute.signals.death_cross(bars),
        "macd_crossover": compute.signals.macd_crossover(bars),
        "rsi_oversold": compute.signals.rsi_oversold(bars),
        "rsi_overbought": compute.signals.rsi_overbought(bars),
        "volume_spike": compute.signals.volume_spike(bars),
        "breakout_52w_high": compute.signals.breakout_52w_high(bars),
        "breakdown_52w_low": compute.signals.breakdown_52w_low(bars),
    }
    return ToolResult(tool="get_signals", symbol=sym, data=out, source="compute")


def screen_stocks(universe, filters):
    """Run a preset screen. filters is a list of {indicator_fn, op, value, period} dicts."""
    matched = screeners.screen_multiple(universe, filters)
    return ToolResult(tool="screen_stocks", symbol=None, data={"matched": matched, "total_scanned": len(universe)}, source="compute")


def backtest_sma(symbol, fast=50, slow=200, years=5):
    """Run an SMA crossover backtest over `years` of daily bars."""
    sym = symbol.upper()
    bars = _bars_from_yfinance(sym, period=f"{years}y")
    if not bars:
        return ToolResult(tool="backtest_sma", symbol=sym, data={"error": "no bars"}, source="compute")
    res = portfolio.backtest_sma_crossover(bars, fast, slow)
    chart = charts.line_chart(
        title=f"{sym} SMA({fast}/{slow}) backtest equity",
        x=list(range(len(res["equity_curve"]))),
        y=res["equity_curve"],
        y_name="equity",
    )
    return ToolResult(tool="backtest_sma", symbol=sym, data=res, chart=chart, source="compute")


def get_market_news(limit=20):
    """Top Indian market news from Google News RSS."""
    items = news.market_news(limit=limit)
    return ToolResult(tool="get_market_news", symbol=None, data={"items": items}, source="google_news")


def get_stock_news(symbol, limit=10):
    """Stock-specific news search."""
    sym = symbol.upper()
    items = news.search(sym, limit=limit, when="7d")
    return ToolResult(tool="get_stock_news", symbol=sym, data={"items": items}, source="google_news")


def get_shareholding(symbol):
    """Stub. Real shareholding API is paid; deferred to v0.2."""
    return ToolResult(tool="get_shareholding", symbol=symbol.upper(), data={"error": "shareholding coming in v0.2"}, source="stub")


def get_financials(symbol):
    """Stub. Real XBRL fundamentals parsing is heavy; deferred to v0.2."""
    return ToolResult(tool="get_financials", symbol=symbol.upper(), data={"error": "fundamentals coming in v0.2"}, source="stub")


def get_corporate_actions(symbol):
    """Stub. NSE corporate-actions RSS in v0.2."""
    return ToolResult(tool="get_corporate_actions", symbol=symbol.upper(), data={"error": "corporate_actions coming in v0.2"}, source="stub")


def get_company_profile(symbol):
    """Extract name, sector, exchange from yfinance."""
    import yfinance as yf
    sym = symbol.upper()
    ns_sym = sym if sym.endswith(".NS") else f"{sym}.NS"
    try:
        t = yf.Ticker(ns_sym)
        info = t.info or {}
    except Exception:
        info = {}
    profile = {
        "symbol": sym,
        "name": info.get("shortName") or info.get("longName") or sym,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "exchange": "NSE",
        "currency": info.get("currency"),
    }
    return ToolResult(tool="get_company_profile", symbol=sym, data=profile, source="yfinance")


def get_top_movers(period="1d", limit=10):
    """Get quotes for a subset of Nifty 50 and return sorted by absolute pct_change."""
    syms = NIFTY_50[:20]
    results = []
    for s in syms:
        q = yfinance.quote(s)
        if q is not None:
            d = q.model_dump(mode="json") if hasattr(q, "model_dump") else q
            results.append({
                "symbol": s,
                "ltp": d.get("ltp"),
                "pct_change": d.get("pct_change"),
                "volume": d.get("volume"),
            })
    results.sort(key=lambda x: abs(x.get("pct_change") or 0), reverse=True)
    return ToolResult(tool="get_top_movers", symbol=None, data={"movers": results[:limit]}, source="yfinance")



import json
from pistol import charts, compute
from pistol.data import yfinance
from pistol.types import ToolResult
from pistol.tools import _bars_from_yfinance, _INDICATOR_DISPATCH, NIFTY_50


def get_historical_volatility(symbol, period=30, annualize=True):
    """Stddev of log returns over `period` days (annualized by default)."""
    sym = symbol.upper()
    bars = _bars_from_yfinance(sym, period="6mo")
    if not bars:
        return ToolResult(tool="get_historical_volatility", symbol=sym, data={"error": "no bars"}, source="compute")
    vals = volatility.historical_volatility(bars, period=period, annualize=annualize)
    chart = None
    if vals:
        clean = [v for v in vals if v is not None]
        if clean:
            dates = [b.timestamp.isoformat() for b, v in zip(bars, vals) if v is not None]
            chart = charts.line_chart(f"{sym} HV({period})", dates, clean, "vol")
    latest = next((v for v in reversed(vals) if v is not None), None)
    return ToolResult(tool="get_historical_volatility", symbol=sym, data={"values": vals, "latest": latest}, chart=chart, source="compute")


def get_parkinson_volatility(symbol, period=30):
    """Parkinson high-low volatility estimator (annualized)."""
    sym = symbol.upper()
    bars = _bars_from_yfinance(sym, period="6mo")
    if not bars:
        return ToolResult(tool="get_parkinson_volatility", symbol=sym, data={"error": "no bars"}, source="compute")
    vals = volatility.parkinson(bars, period=period)
    chart = None
    if vals:
        clean = [v for v in vals if v is not None]
        if clean:
            dates = [b.timestamp.isoformat() for b, v in zip(bars, vals) if v is not None]
            chart = charts.line_chart(f"{sym} Parkinson({period})", dates, clean, "vol")
    latest = next((v for v in reversed(vals) if v is not None), None)
    return ToolResult(tool="get_parkinson_volatility", symbol=sym, data={"values": vals, "latest": latest}, chart=chart, source="compute")


def get_garman_klass_volatility(symbol, period=30):
    """Garman-Klass OHLC volatility estimator (annualized)."""
    sym = symbol.upper()
    bars = _bars_from_yfinance(sym, period="6mo")
    if not bars:
        return ToolResult(tool="get_garman_klass_volatility", symbol=sym, data={"error": "no bars"}, source="compute")
    vals = volatility.garman_klass(bars, period=period)
    chart = None
    if vals:
        clean = [v for v in vals if v is not None]
        if clean:
            dates = [b.timestamp.isoformat() for b, v in zip(bars, vals) if v is not None]
            chart = charts.line_chart(f"{sym} GK({period})", dates, clean, "vol")
    latest = next((v for v in reversed(vals) if v is not None), None)
    return ToolResult(tool="get_garman_klass_volatility", symbol=sym, data={"values": vals, "latest": latest}, chart=chart, source="compute")


def get_yang_zhang_volatility(symbol, period=30):
    """Yang-Zhang overnight + intraday volatility estimator (annualized)."""
    sym = symbol.upper()
    bars = _bars_from_yfinance(sym, period="6mo")
    if not bars:
        return ToolResult(tool="get_yang_zhang_volatility", symbol=sym, data={"error": "no bars"}, source="compute")
    vals = volatility.yang_zhang(bars, period=period)
    chart = None
    if vals:
        clean = [v for v in vals if v is not None]
        if clean:
            dates = [b.timestamp.isoformat() for b, v in zip(bars, vals) if v is not None]
            chart = charts.line_chart(f"{sym} YZ({period})", dates, clean, "vol")
    latest = next((v for v in reversed(vals) if v is not None), None)
    return ToolResult(tool="get_yang_zhang_volatility", symbol=sym, data={"values": vals, "latest": latest}, chart=chart, source="compute")


def get_hurst_exponent(symbol, max_lag=20):
    """Hurst exponent. <0.5 mean-reverting, >0.5 trending, ==0.5 random walk."""
    sym = symbol.upper()
    bars = _bars_from_yfinance(sym, period="1y")
    if not bars:
        return ToolResult(tool="get_hurst_exponent", symbol=sym, data={"error": "no bars"}, source="compute")
    vals = volatility.hurst_exponent(bars, max_lag=max_lag)
    latest = next((v for v in reversed(vals) if v is not None), None)
    interpretation = "unknown"
    if latest is not None:
        if latest < 0.45:
            interpretation = "mean-reverting"
        elif latest > 0.55:
            interpretation = "trending"
        else:
            interpretation = "random-walk"
    return ToolResult(tool="get_hurst_exponent", symbol=sym, data={"values": vals, "latest": latest, "interpretation": interpretation}, source="compute")


def get_z_score(symbol, period=20):
    """Z-score of close vs rolling mean/std."""
    sym = symbol.upper()
    bars = _bars_from_yfinance(sym, period="6mo")
    if not bars:
        return ToolResult(tool="get_z_score", symbol=sym, data={"error": "no bars"}, source="compute")
    vals = statistics.z_score(bars, period=period)
    chart = None
    if vals:
        clean = [v for v in vals if v is not None]
        if clean:
            dates = [b.timestamp.isoformat() for b, v in zip(bars, vals) if v is not None]
            chart = charts.line_chart(f"{sym} Z({period})", dates, clean, "z", thresholds=[-2, 0, 2])
    latest = next((v for v in reversed(vals) if v is not None), None)
    return ToolResult(tool="get_z_score", symbol=sym, data={"values": vals, "latest": latest}, chart=chart, source="compute")


def get_correlation(symbol_a, symbol_b, period=60):
    """Rolling correlation between two stocks' close returns."""
    a = symbol_a.upper()
    b = symbol_b.upper()
    bars_a = _bars_from_yfinance(a, period="1y")
    bars_b = _bars_from_yfinance(b, period="1y")
    if not bars_a or not bars_b:
        return ToolResult(tool="get_correlation", symbol=f"{a}/{b}", data={"error": "no bars"}, source="compute")
    vals = statistics.correlation(bars_a, "close", bars_b, "close", period=period)
    latest = next((v for v in reversed(vals) if v is not None), None)
    chart = None
    if vals:
        clean = [v for v in vals if v is not None]
        if clean:
            ref_bars = bars_a if len(bars_a) <= len(bars_b) else bars_b
            dates = [bar.timestamp.isoformat() for bar in ref_bars[-len(clean):]]
            chart = charts.line_chart(f"{a} vs {b} corr({period})", dates, clean, "corr", thresholds=[0])
    return ToolResult(tool="get_correlation", symbol=f"{a}/{b}", data={"values": vals, "latest": latest}, chart=chart, source="compute")


def get_beta(symbol, index_symbol="^NSEI", period=60):
    """Rolling beta of stock vs index (Nifty 50 by default)."""
    sym = symbol.upper()
    bars = _bars_from_yfinance(sym, period="1y")
    # yfinance uses ^NSEI for Nifty 50 (no .NS suffix); _bars_from_yfinance adds .NS so bypass.
    from .data.yfinance import _to_nse_symbol, price_history as _ph
    idx_ns = index_symbol if index_symbol.startswith("^") else _to_nse_symbol(index_symbol)
    cache_key = f"ohlcv_1d"
    from .data import cache as _cache
    def _fetch_idx():
        import yfinance as yf
        df = yf.Ticker(idx_ns).history(period="1y", interval="1d", auto_adjust=False)
        if df is None or df.empty:
            return []
        out = []
        for idx, row in df.iterrows():
            ts = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
            out.append({"timestamp": ts.date().isoformat() if hasattr(ts, "date") else str(ts),
                        "open": float(row.get("Open", 0) or 0), "high": float(row.get("High", 0) or 0),
                        "low": float(row.get("Low", 0) or 0), "close": float(row.get("Close", 0) or 0),
                        "volume": int(row.get("Volume", 0) or 0), "adj_close": None,
                        "delivery_pct": None, "delivery_volume": None})
        return out
    raw_idx = _cache.get_or_set("ohlcv_1d", _fetch_idx, symbol=idx_ns, period="1y", interval="1d")
    from .types import PriceBar as _PB
    idx_bars = [_PB(**b) for b in (raw_idx or [])]
    if not bars or not idx_bars:
        return ToolResult(tool="get_beta", symbol=sym, data={"error": "no bars"}, source="compute")
    vals = statistics.beta(bars, idx_bars, period=period)
    latest = next((v for v in reversed(vals) if v is not None), None)
    chart = None
    if vals:
        clean = [v for v in vals if v is not None]
        if clean:
            dates = [bar.timestamp.isoformat() for bar in bars[-len(clean):]]
            chart = charts.line_chart(f"{sym} beta vs {index_symbol}", dates, clean, "beta", thresholds=[1.0])
    return ToolResult(tool="get_beta", symbol=sym, data={"values": vals, "latest": latest, "index": index_symbol}, chart=chart, source="compute")


def screen_by_indicator(symbols, indicator, op, value, period=14):
    """Screen a universe using a technical indicator. Returns matched symbols."""
    if indicator not in _INDICATOR_DISPATCH:
        return ToolResult(tool="screen_by_indicator", symbol=None, data={"error": f"unsupported {indicator}"}, source="compute")
    fn = _INDICATOR_DISPATCH[indicator]
    universe = {}
    for s in (symbols or NIFTY_50):
        bars = _bars_from_yfinance(s, period="6mo")
        if bars:
            universe[s] = bars
    if not universe:
        return ToolResult(tool="screen_by_indicator", symbol=None, data={"matched": [], "total_scanned": 0}, source="compute")
    matched = screeners.screen_by_indicator(universe, fn, op, value, period=period)
    return ToolResult(tool="screen_by_indicator", symbol=None, data={"matched": matched, "indicator": indicator, "op": op, "value": value, "total_scanned": len(universe)}, source="compute")


def portfolio_sector_concentration(holdings_json, sectors_json):
    """Sector concentration of a portfolio. holdings_json=[{symbol,value}], sectors_json={sym:sector}."""
    try:
        holdings = json.loads(holdings_json) if isinstance(holdings_json, str) else holdings_json
        sectors = json.loads(sectors_json) if isinstance(sectors_json, str) else sectors_json
    except Exception as e:
        return ToolResult(tool="portfolio_sector_concentration", symbol=None, data={"error": f"bad json: {e}"}, source="compute")
    if not holdings:
        return ToolResult(tool="portfolio_sector_concentration", symbol=None, data={"error": "empty holdings"}, source="compute")
    conc = portfolio.sector_concentration(holdings, sectors)
    chart = charts.pie_chart("Sector concentration", list(conc.keys()), list(conc.values())) if conc else None
    return ToolResult(tool="portfolio_sector_concentration", symbol=None, data=conc, chart=chart, source="compute")


def portfolio_var(returns_json, confidence=0.95):
    """Historical Value-at-Risk at `confidence`. returns_json is a list of returns."""
    try:
        rets = json.loads(returns_json) if isinstance(returns_json, str) else returns_json
    except Exception as e:
        return ToolResult(tool="portfolio_var", symbol=None, data={"error": f"bad json: {e}"}, source="compute")
    v = portfolio.var(rets, confidence=confidence)
    return ToolResult(tool="portfolio_var", symbol=None, data={"value_at_risk": v, "confidence": confidence}, source="compute")


def portfolio_sharpe(returns_json, risk_free=0.06):
    """Annualized Sharpe ratio from daily returns."""
    try:
        rets = json.loads(returns_json) if isinstance(returns_json, str) else returns_json
    except Exception as e:
        return ToolResult(tool="portfolio_sharpe", symbol=None, data={"error": f"bad json: {e}"}, source="compute")
    s = portfolio.sharpe(rets, risk_free=risk_free)
    return ToolResult(tool="portfolio_sharpe", symbol=None, data={"sharpe": s, "risk_free": risk_free}, source="compute")


def portfolio_max_drawdown(equity_json):
    """Max drawdown of an equity curve. equity_json is a list of equity values."""
    try:
        eq = json.loads(equity_json) if isinstance(equity_json, str) else equity_json
    except Exception as e:
        return ToolResult(tool="portfolio_max_drawdown", symbol=None, data={"error": f"bad json: {e}"}, source="compute")
    dd, start, end = portfolio.max_drawdown(eq)
    return ToolResult(tool="portfolio_max_drawdown", symbol=None, data={"max_drawdown": dd, "start_idx": start, "end_idx": end}, source="compute")


def portfolio_correlation_matrix(returns_json):
    """NxN correlation heatmap of portfolio returns. returns_json={sym:[r1,r2,...]}."""
    try:
        d = json.loads(returns_json) if isinstance(returns_json, str) else returns_json
    except Exception as e:
        return ToolResult(tool="portfolio_correlation_matrix", symbol=None, data={"error": f"bad json: {e}"}, source="compute")
    mat = portfolio.correlation_matrix(d)
    syms = list(mat.columns)
    chart = charts.heatmap_chart("Correlation matrix", mat.values.tolist(), syms, syms) if not mat.empty else None
    return ToolResult(tool="portfolio_correlation_matrix", symbol=None, data=mat.to_dict(), chart=chart, source="compute")


def backtest_sma_crossover(symbol, fast=50, slow=200, years=5):
    """SMA crossover backtest over `years` of daily bars."""
    sym = symbol.upper()
    bars = _bars_from_yfinance(sym, period=f"{years}y")
    if not bars:
        return ToolResult(tool="backtest_sma_crossover", symbol=sym, data={"error": "no bars"}, source="compute")
    res = portfolio.backtest_sma_crossover(bars, fast, slow)
    chart = charts.line_chart(
        title=f"{sym} SMA({fast}/{slow}) equity",
        x=list(range(len(res["equity_curve"]))),
        y=res["equity_curve"],
        y_name="equity",
    )
    return ToolResult(tool="backtest_sma_crossover", symbol=sym, data=res, chart=chart, source="compute")


_NSE_SEARCH_UNIVERSE = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN", "ICICIBANK", "TATAMOTORS",
    "BHARTIARTL", "ITC", "LT", "AXISBANK", "KOTAKBANK", "ASIANPAINT", "MARUTI",
    "SUNPHARMA", "WIPRO", "HCLTECH", "ULTRACEMCO", "NESTLEIND", "POWERGRID",
    "NTPC", "ONGC", "TECHM", "INDUSINDBK", "M&M", "BAJFINANCE", "BAJAJFINSV",
    "TITAN", "ADANIENT", "ADANIPORTS", "COALINDIA", "GRASIM", "JSWSTEEL",
    "DRREDDY", "CIPLA", "DIVISLAB", "EICHERMOT", "HEROMOTOCO", "BRITANNIA",
    "BPCL", "IOC", "HINDALCO", "JINDALSTEL", "TATASTEEL", "VEDL", "ZOMATO",
    "PAYTM", "NAUKRI", "POLICYBZR", "IRCTC", "IDEA", "SUZLON", "YESBANK",
    "BANDHANBNK", "FEDERALBNK", "IDFCFIRSTB", "PNB", "BANKBARODA", "CANBK",
    "UNIONBANK",
]


def search_stocks(query, limit=20):
    """Substring search over a hardcoded NSE universe. ponytail: yfinance has no search API."""
    q = (query or "").upper()
    matched = [s for s in _NSE_SEARCH_UNIVERSE if q in s][:limit]
    return ToolResult(tool="search_stocks", symbol=None, data={"matched": matched, "query": query}, source="local")


def get_batch_quotes(symbols, currency="INR"):
    """Fetch live quotes for a list of symbols."""
    out = []
    for s in symbols or []:
        q = yfinance.quote(s)
        if q is not None:
            d = q.model_dump(mode="json") if hasattr(q, "model_dump") else q
            d["currency"] = currency
            out.append(d)
    return ToolResult(tool="get_batch_quotes", symbol=None, data={"quotes": out, "currency": currency}, source="yfinance")


def get_intraday_ticks(symbol, interval="5m"):
    """Intraday OHLCV ticks. ponytail: yfinance limits intraday to ~60 days."""
    sym = symbol.upper()
    bars = _bars_from_yfinance(sym, period="5d", interval=interval)
    if not bars:
        return ToolResult(tool="get_intraday_ticks", symbol=sym, data={"error": "no bars"}, source="yfinance")
    return ToolResult(tool="get_intraday_ticks", symbol=sym, data={"bars": [b.model_dump(mode="json") for b in bars], "interval": interval}, source="yfinance")


def get_advanced_chart(symbol, chart_type="candlestick", period="6mo", indicators=None):
    """Price history + chart, optionally with indicator overlays. ponytail: indicators computed and returned in data; not fused into candlestick fig."""
    sym = symbol.upper()
    bars = _bars_from_yfinance(sym, period=period)
    if not bars:
        return ToolResult(tool="get_advanced_chart", symbol=sym, data={"error": "no bars"}, source="yfinance")
    overlay_pts = {}
    for name in (indicators or []):
        if name in _INDICATOR_DISPATCH:
            overlay_pts[name] = [p.model_dump(mode="json") for p in _INDICATOR_DISPATCH[name](bars, 14)]
    if chart_type == "candlestick":
        chart = charts.candlestick_chart(bars, f"{sym} {period}")
    else:
        chart = charts.line_chart(
            title=f"{sym} close ({period})",
            x=[b.timestamp.isoformat() for b in bars],
            y=[b.close for b in bars],
            y_name="close",
        )
    return ToolResult(
        tool="get_advanced_chart",
        symbol=sym,
        data={"bars": [b.model_dump(mode="json") for b in bars], "indicators": overlay_pts},
        chart=chart,
        source="yfinance",
    )


TOOL_REGISTRY = {
    "get_stock_quote": get_stock_quote,
    "get_price_history": get_price_history,
    "get_indicator": get_indicator,
    "get_candlestick_patterns": get_candlestick_patterns,
    "get_signals": get_signals,
    "screen_stocks": screen_stocks,
    "backtest_sma": backtest_sma,
    "get_market_news": get_market_news,
    "get_stock_news": get_stock_news,
    "get_shareholding": get_shareholding,
    "get_financials": get_financials,
    "get_corporate_actions": get_corporate_actions,
    "get_company_profile": get_company_profile,
    "get_top_movers": get_top_movers,
    "get_historical_volatility": get_historical_volatility,
    "get_parkinson_volatility": get_parkinson_volatility,
    "get_garman_klass_volatility": get_garman_klass_volatility,
    "get_yang_zhang_volatility": get_yang_zhang_volatility,
    "get_hurst_exponent": get_hurst_exponent,
    "get_z_score": get_z_score,
    "get_correlation": get_correlation,
    "get_beta": get_beta,
    "screen_by_indicator": screen_by_indicator,
    "portfolio_sector_concentration": portfolio_sector_concentration,
    "portfolio_var": portfolio_var,
    "portfolio_sharpe": portfolio_sharpe,
    "portfolio_max_drawdown": portfolio_max_drawdown,
    "portfolio_correlation_matrix": portfolio_correlation_matrix,
    "backtest_sma_crossover": backtest_sma_crossover,
    "search_stocks": search_stocks,
    "get_batch_quotes": get_batch_quotes,
    "get_intraday_ticks": get_intraday_ticks,
    "get_advanced_chart": get_advanced_chart,
}


def _hint_to_json_type(h):
    if h in (int, "int"):
        return "integer"
    if h in (float, "float"):
        return "number"
    if h in (bool, "bool"):
        return "boolean"
    if h in (str, "str"):
        return "string"
    return "string"


def claude_tool_schema(registry):
    """Convert TOOL_REGISTRY into Anthropic tool schema list. Uses docstrings + type hints."""
    out = []
    for name, fn in registry.items():
        sig = inspect.signature(fn)
        doc = (fn.__doc__ or "").strip().splitlines()[0] if fn.__doc__ else name
        props = {}
        required = []
        for pname, param in sig.parameters.items():
            if pname == "self":
                continue
            hint = param.annotation if param.annotation is not inspect.Parameter.empty else str
            props[pname] = {"type": _hint_to_json_type(hint), "description": pname}
            if param.default is inspect.Parameter.empty:
                required.append(pname)
        schema = {
            "name": name,
            "description": doc,
            "input_schema": {"type": "object", "properties": props, "required": required},
        }
        out.append(schema)
    return out


__all__ = [
    "TOOL_REGISTRY",
    "get_stock_quote", "get_price_history", "get_indicator",
    "get_candlestick_patterns", "get_signals", "screen_stocks",
    "backtest_sma", "get_market_news", "get_stock_news",
    "get_shareholding", "get_financials", "get_corporate_actions",
    "get_company_profile", "get_top_movers",
    "get_historical_volatility", "get_parkinson_volatility", "get_garman_klass_volatility",
    "get_yang_zhang_volatility", "get_hurst_exponent", "get_z_score", "get_correlation",
    "get_beta", "screen_by_indicator", "portfolio_sector_concentration",
    "portfolio_var", "portfolio_sharpe", "portfolio_max_drawdown",
    "portfolio_correlation_matrix", "backtest_sma_crossover", "search_stocks",
    "get_batch_quotes", "get_intraday_ticks", "get_advanced_chart",
    "claude_tool_schema", "ToolResult",
]
