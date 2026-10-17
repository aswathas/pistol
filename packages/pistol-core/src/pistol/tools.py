"""Unified tool registry. Each tool returns a ToolResult with data + chart + source."""

from __future__ import annotations

import inspect
import re

from . import charts, compute
from .compute import indicators as ind
from .data import fii_dii, news, yfinance
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


SECTOR_MAP = {
    "RELIANCE": "Energy", "TCS": "IT", "HDFCBANK": "Banks", "INFY": "IT",
    "ICICIBANK": "Banks", "HINDUNILVR": "FMCG", "SBIN": "Banks",
    "BHARTIARTL": "Telecom", "ITC": "FMCG", "KOTAKBANK": "Banks", "LT": "Infra",
    "AXISBANK": "Banks", "ASIANPAINT": "Paints", "MARUTI": "Auto",
    "SUNPHARMA": "Pharma", "BAJFINANCE": "Finance", "BAJAJFINSV": "Finance",
    "WIPRO": "IT", "HCLTECH": "IT", "TECHM": "IT", "ULTRACEMCO": "Cement",
    "TITAN": "Consumer", "NESTLEIND": "FMCG", "POWERGRID": "Power", "NTPC": "Power",
    "M&M": "Auto", "TATASTEEL": "Metals", "JSWSTEEL": "Metals",
    "ADANIENT": "Conglomerate", "ADANIPORTS": "Infra", "COALINDIA": "Mining",
    "ONGC": "Energy", "BPCL": "Energy", "GRASIM": "Cement", "INDUSINDBK": "Banks",
    "CIPLA": "Pharma", "DRREDDY": "Pharma", "EICHERMOT": "Auto",
    "HEROMOTOCO": "Auto", "BAJAJ-AUTO": "Auto", "DIVISLAB": "Pharma",
    "BRITANNIA": "FMCG", "APOLLOHOSP": "Healthcare", "HINDALCO": "Metals",
    "TATACONSUM": "FMCG", "SBILIFE": "Insurance", "HDFCLIFE": "Insurance",
    "UPL": "Chemicals", "LTIM": "IT", "SHRIRAMFIN": "Finance",
}


_NSE_INDICES = [
    ("Nifty 50", "^NSEI"),
    ("Bank Nifty", "^NSEBANK"),
    ("Nifty IT", "^CNXIT"),
    ("Nifty Auto", "^CNXAUTO"),
    ("Nifty Pharma", "^CNXPHARMA"),
    ("Nifty FMCG", "^CNXFMCG"),
    ("Nifty Metal", "^CNXMETAL"),
    ("Nifty Realty", "^CNXREALTY"),
    ("Nifty Energy", "^CNXENERGY"),
    ("Nifty PSU Bank", "^CNXPSUBANK"),
    ("India VIX", "^INDIAVIX"),
]


def _bars_from_yfinance(symbol, period="6mo", interval="1d"):
    return yfinance.price_history(symbol, period=period, interval=interval)


def _quote_dict(sym):
    q = yfinance.quote(sym)
    if q is None:
        return None
    return q.model_dump(mode="json") if hasattr(q, "model_dump") else q


def get_stock_quote(symbol):
    sym = symbol.upper()
    q = yfinance.quote(sym)
    if q is None:
        return ToolResult(tool="get_stock_quote", symbol=sym, data={"error": "no quote"}, source="yfinance", note="No data returned")
    return ToolResult(tool="get_stock_quote", symbol=sym, data=q.model_dump(mode="json") if hasattr(q, "model_dump") else q, source="yfinance")


def get_price_history(symbol, period="6mo", interval="1d"):
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
    sym = symbol.upper()
    bars = _bars_from_yfinance(sym, period="6mo")
    if not bars:
        return ToolResult(tool="get_candlestick_patterns", symbol=sym, data={"error": "no bars"}, source="compute")
    sub = bars[-days:] if len(bars) > days else bars
    detected = compute.patterns.detect_all(sub)
    return ToolResult(tool="get_candlestick_patterns", symbol=sym, data=detected, source="compute")


def get_signals(symbol):
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
    matched = compute.screeners.screen_multiple(universe, filters)
    return ToolResult(tool="screen_stocks", symbol=None, data={"matched": matched, "total_scanned": len(universe)}, source="compute")


def backtest_sma(symbol, fast=50, slow=200, years=5):
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
    items = news.market_news(limit=limit)
    return ToolResult(tool="get_market_news", symbol=None, data={"items": items}, source="google_news")


def get_stock_news(symbol, limit=10):
    sym = symbol.upper()
    items = news.search(sym, limit=limit, when="7d")
    return ToolResult(tool="get_stock_news", symbol=sym, data={"items": items}, source="google_news")


def get_shareholding(symbol):
    return ToolResult(tool="get_shareholding", symbol=symbol.upper(), data={"error": "shareholding coming in v0.2"}, source="stub")


def get_financials(symbol):
    return ToolResult(tool="get_financials", symbol=symbol.upper(), data={"error": "fundamentals coming in v0.2"}, source="stub")


def get_corporate_actions(symbol):
    return ToolResult(tool="get_corporate_actions", symbol=symbol.upper(), data={"error": "corporate_actions coming in v0.2"}, source="stub")


def get_company_profile(symbol):
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


def get_top_movers(period="1d", limit=10, direction="mixed"):
    rows = []
    for s in NIFTY_50[:20]:
        d = _quote_dict(s)
        if d is None:
            continue
        rows.append({
            "symbol": s,
            "ltp": d.get("ltp"),
            "change": d.get("change"),
            "pct_change": d.get("pct_change"),
            "volume": d.get("volume"),
        })
    if direction == "gainers":
        rows.sort(key=lambda x: x.get("pct_change") or 0, reverse=True)
    elif direction == "losers":
        rows.sort(key=lambda x: x.get("pct_change") or 0)
    else:
        rows.sort(key=lambda x: abs(x.get("pct_change") or 0), reverse=True)
    return ToolResult(
        tool="get_top_movers", symbol=None,
        data={"direction": direction, "movers": rows[:limit]},
        source="yfinance",
    )


def get_advanced_chart(symbol, chart_type="candlestick", period="6mo"):
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


def get_market_pulse(limit=10):
    cap = max(1, min(int(limit), len(NIFTY_50)))
    rows = []
    for s in NIFTY_50[:cap]:
        d = _quote_dict(s)
        if d is None:
            continue
        rows.append({
            "symbol": s,
            "ltp": d.get("ltp"),
            "change": d.get("change"),
            "pct_change": d.get("pct_change"),
            "volume": d.get("volume"),
        })
    chart = charts.screener_table(
        f"Nifty 50 pulse (top {limit})",
        rows,
        columns=["symbol", "ltp", "change", "pct_change", "volume"],
    )
    return ToolResult(
        tool="get_market_pulse", symbol=None,
        data={"pulse": rows, "count": len(rows)},
        chart=chart, source="yfinance",
    )


def get_index_performance(index="^NSEI", period="1y"):
    index = (index or "^NSEI").strip()
    bars = _bars_from_yfinance(index, period=period)
    if not bars:
        return ToolResult(tool="get_index_performance", symbol=index, data={"error": "no bars"}, source="yfinance")
    first, last = bars[0].close, bars[-1].close
    pct = ((last - first) / first * 100) if first else 0.0
    chart = charts.line_chart(
        title=f"{index} close ({period})",
        x=[b.timestamp.isoformat() for b in bars],
        y=[b.close for b in bars],
        y_name="close",
    )
    return ToolResult(
        tool="get_index_performance", symbol=index,
        data={"index": index, "period": period, "first_close": first, "last_close": last,
              "pct_change": pct, "bars": len(bars)},
        chart=chart, source="yfinance",
    )


def get_market_heatmap(period="1d"):
    pct_by_sym = {}
    for s in NIFTY_50:
        d = _quote_dict(s)
        if d is None:
            continue
        pct_by_sym[s] = float(d.get("pct_change") or 0)
    buckets = [(-10, -2), (-2, -0.5), (-0.5, 0.5), (0.5, 2), (2, 10)]
    labels = ["<-2%", "-2..-0.5%", "-0.5..0.5%", "0.5..2%", ">2%"]
    sectors = sorted({SECTOR_MAP.get(s, "Other") for s in pct_by_sym})
    z = [[0] * len(labels) for _ in sectors]
    for sym, pct in pct_by_sym.items():
        sec = SECTOR_MAP.get(sym, "Other")
        for i, (lo, hi) in enumerate(buckets):
            if lo <= pct < hi:
                z[sectors.index(sec)][i] += 1
                break
    chart = charts.heatmap_chart("Nifty 50 heatmap (sector x % change bucket)", z, labels, sectors)
    return ToolResult(
        tool="get_market_heatmap", symbol=None,
        data={"z": z, "x_labels": labels, "y_labels": sectors, "by_stock": pct_by_sym},
        chart=chart, source="yfinance",
    )


def get_sector_rotation(period="1m"):
    returns_by_sym = {}
    for s in NIFTY_50:
        bars = _bars_from_yfinance(s, period="1mo")
        if not bars or len(bars) < 2 or not bars[0].close:
            continue
        first, last = bars[0].close, bars[-1].close
        returns_by_sym[s] = (last - first) / first * 100
    by_sector = {}
    for sym, r in returns_by_sym.items():
        by_sector.setdefault(SECTOR_MAP.get(sym, "Other"), []).append(r)
    ranked = sorted(
        [(sec, sum(rs) / len(rs), len(rs)) for sec, rs in by_sector.items() if rs],
        key=lambda kv: kv[1], reverse=True,
    )
    labels = [r[0] for r in ranked]
    values = [r[1] for r in ranked]
    chart = charts.bar_chart(f"Sector rotation ({period})", labels, values, "avg % return")
    return ToolResult(
        tool="get_sector_rotation", symbol=None,
        data={"period": period, "sectors": [
            {"sector": s, "avg_return_pct": v, "n_stocks": n} for s, v, n in ranked
        ]},
        chart=chart, source="yfinance",
    )


def list_indices():
    rows = []
    for name, sym in _NSE_INDICES:
        d = _quote_dict(sym)
        if d is None:
            rows.append({"name": name, "symbol": sym, "ltp": None, "pct_change": None})
            continue
        rows.append({"name": name, "symbol": sym, "ltp": d.get("ltp"), "pct_change": d.get("pct_change")})
    return ToolResult(tool="list_indices", symbol=None, data={"indices": rows}, source="yfinance")


def get_india_vix():
    sym = "^INDIAVIX"
    d = _quote_dict(sym)
    if d is None:
        return ToolResult(
            tool="get_india_vix", symbol=sym, data={"error": "no data"},
            source="yfinance", note="yfinance ^INDIAVIX returned no quote",
        )
    return ToolResult(
        tool="get_india_vix", symbol=sym,
        data={"symbol": sym, "ltp": d.get("ltp"), "pct_change": d.get("pct_change")},
        source="yfinance",
    )


def get_market_breadth(period="1d"):
    gains = losses = unchanged = 0
    for s in NIFTY_50:
        d = _quote_dict(s)
        if d is None:
            continue
        pct = d.get("pct_change")
        if pct is None:
            continue
        if pct > 0:
            gains += 1
        elif pct < 0:
            losses += 1
        else:
            unchanged += 1
    chart = charts.pie_chart(
        "Nifty 50 breadth",
        ["Gainers", "Losers", "Unchanged"],
        [gains, losses, unchanged],
    )
    return ToolResult(
        tool="get_market_breadth", symbol=None,
        data={"period": period, "gainers": gains, "losers": losses,
              "unchanged": unchanged, "total": gains + losses + unchanged},
        chart=chart, source="yfinance",
    )


def get_new_highs_lows(period="52w"):
    near_high, near_low = [], []
    for s in NIFTY_50:
        bars = _bars_from_yfinance(s, period="1y")
        if not bars or len(bars) < 10:
            continue
        curr = bars[-1].close
        high_52w = max(b.high for b in bars)
        low_52w = min(b.low for b in bars)
        if high_52w > 0 and curr >= high_52w * 0.98:
            near_high.append(s)
        if low_52w > 0 and curr <= low_52w * 1.02:
            near_low.append(s)
    return ToolResult(
        tool="get_new_highs_lows", symbol=None,
        data={"period": period, "near_high_count": len(near_high),
              "near_low_count": len(near_low), "near_high": near_high,
              "near_low": near_low},
        source="yfinance",
    )


def _parse_days(period):
    s = (period or "30d").strip().lower()
    if s.endswith("d") and s[:-1].isdigit():
        return max(1, min(int(s[:-1]), 30))
    return 30


def get_fii_dii_flows(period="30d"):
    out = fii_dii.daily_flows(days=_parse_days(period))
    return ToolResult(
        tool="get_fii_dii_flows", symbol=None,
        data=out,
        source=out.get("source", "fallback"),
        note=out.get("note"),
    )


def get_market_pulse_with_flows(limit=10, period="30d"):
    pulse_res = get_market_pulse(limit=limit)
    flows_res = get_fii_dii_flows(period=period)
    pulse_data = pulse_res.data if isinstance(pulse_res.data, dict) else {"pulse": pulse_res.data}
    flows_data = flows_res.data if isinstance(flows_res.data, dict) else {"rows": flows_res.data}
    return ToolResult(
        tool="get_market_pulse_with_flows", symbol=None,
        data={"pulse": pulse_data.get("pulse"), "flows": flows_data},
        chart=pulse_res.chart,
        source="yfinance+fii_dii",
    )


def get_india_market_news(limit=30):
    items = news.market_news(limit=limit)
    return ToolResult(tool="get_india_market_news", symbol=None, data={"items": items}, source="google_news")


_POS_WORDS = {"surge", "rally", "beat", "jump", "high", "growth"}
_NEG_WORDS = {"fall", "drop", "miss", "low", "decline", "tumble"}


def _score_text(text):
    words = set(re.findall(r"[a-zA-Z]+", (text or "").lower()))
    return len(words & _POS_WORDS) - len(words & _NEG_WORDS)


def _sentiment_label(pos, neg):
    if pos > neg + 1:
        return "positive"
    if neg > pos + 1:
        return "negative"
    return "neutral"


def get_stock_news_with_sentiment(symbol, limit=10, when="7d"):
    sym = symbol.upper()
    items = news.search(sym, limit=limit, when=when)
    pos = neg = neu = 0
    for it in items:
        s = _score_text((it.get("title") or "") + " " + (it.get("summary") or ""))
        it["sentiment"] = s
        if s > 0:
            pos += 1
        elif s < 0:
            neg += 1
        else:
            neu += 1
    return ToolResult(
        tool="get_stock_news_with_sentiment", symbol=sym,
        data={"items": items, "aggregate": {
            "positive": pos, "negative": neg, "neutral": neu,
            "label": _sentiment_label(pos, neg),
        }},
        source="google_news",
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
    "get_advanced_chart": get_advanced_chart,
    "get_market_pulse": get_market_pulse,
    "get_index_performance": get_index_performance,
    "get_market_heatmap": get_market_heatmap,
    "get_sector_rotation": get_sector_rotation,
    "list_indices": list_indices,
    "get_india_vix": get_india_vix,
    "get_market_breadth": get_market_breadth,
    "get_new_highs_lows": get_new_highs_lows,
    "get_fii_dii_flows": get_fii_dii_flows,
    "get_market_pulse_with_flows": get_market_pulse_with_flows,
    "get_india_market_news": get_india_market_news,
    "get_stock_news_with_sentiment": get_stock_news_with_sentiment,
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
    "get_market_pulse", "get_index_performance", "get_market_heatmap",
    "get_sector_rotation", "list_indices", "get_india_vix",
    "get_market_breadth", "get_new_highs_lows", "get_fii_dii_flows",
    "get_market_pulse_with_flows", "get_india_market_news",
    "get_stock_news_with_sentiment",
    "claude_tool_schema", "ToolResult",
]
