"""Unified tool registry. Each tool returns a ToolResult with data + chart + source."""

from __future__ import annotations

import inspect

from . import charts, compute
from .compute import indicators as ind
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
    matched = compute.screeners.screen_multiple(universe, filters)
    return ToolResult(tool="screen_stocks", symbol=None, data={"matched": matched, "total_scanned": len(universe)}, source="compute")


def backtest_sma(symbol, fast=50, slow=200, years=5):
    """Run an SMA crossover backtest over `years` of daily bars."""
    sym = symbol.upper()
    bars = _bars_from_yfinance(sym, period=f"{years}y")
    if not bars:
        return ToolResult(tool="backtest_sma", symbol=sym, data={"error": "no bars"}, source="compute")
    res = compute.portfolio.backtest_sma_crossover(bars, fast, slow)
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


def get_advanced_chart(symbol, chart_type="candlestick", period="6mo"):
    """Wrapper: price history + candlestick chart."""
    sym = symbol.upper()
    bars = _bars_from_yfinance(sym, period=period)
    if not bars:
        return ToolResult(tool="get_advanced_chart", symbol=sym, data={"error": "no bars"}, source="yfinance")
    if chart_type == "candlestick":
        chart = charts.candlestick_chart(bars, f"{sym} {period}")
    else:
        chart = charts.line_chart(
            title=f"{sym} close ({period})",
            x=[b.timestamp.isoformat() for b in bars],
            y=[b.close for b in bars],
            y_name="close",
        )
    return ToolResult(tool="get_advanced_chart", symbol=sym, data={"bars": [b.model_dump(mode="json") for b in bars]}, chart=chart, source="yfinance")


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
    "get_company_profile", "get_top_movers", "get_advanced_chart",
    "claude_tool_schema", "ToolResult",
]
