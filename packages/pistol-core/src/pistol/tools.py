"""Unified tool registry. Each tool returns a ToolResult with data + chart + source."""

from __future__ import annotations
import json
import pandas as pd
import os

import inspect
import re

from . import charts, compute
from .compute import indicators as ind, patterns as pat, signals as sig, volatility as vol, statistics as stat, portfolio as pf, screeners as scr
from .data import fii_dii, news, yfinance
from .types import ChartSpec, Fundamentals, PriceBar, Quote, ToolResult

# Aliases for back-compat with merged vol/portfolio functions
volatility = vol
statistics = stat
portfolio = pf
screeners = scr
patterns = pat
signals = sig



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

_NSE_SEARCH_UNIVERSE = ["RELIANCE","TCS","INFY","HDFCBANK","SBIN","ICICIBANK","TATAMOTORS","BHARTIARTL","ITC","LT","AXISBANK","KOTAKBANK","ASIANPAINT","MARUTI","SUNPHARMA","WIPRO","HCLTECH","ULTRACEMCO","NESTLEIND","POWERGRID","NTPC","ONGC","TECHM","INDUSINDBK","M&M","BAJFINANCE","BAJAJFINSV","TITAN","ADANIENT","ADANIPORTS","COALINDIA","GRASIM","JSWSTEEL","DRREDDY","CIPLA","DIVISLAB","EICHERMOT","HEROMOTOCO","BRITANNIA","BPCL","IOC","HINDALCO","JINDALSTEL","TATASTEEL","VEDL","ZOMATO","PAYTM","NAUKRI","POLICYBZR","IRCTC","IDEA","SUZLON","YESBANK","BANDHANBNK","FEDERALBNK","IDFCFIRSTB","PNB","BANKBARODA","CANBK","UNIONBANK"]



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


def get_shareholding(symbol, periods=4):
    """Fetch shareholding pattern (major/institutional holders)."""
    sym = symbol.upper()
    t, _ = _yfinance_ticker(sym)
    try:
        major = t.major_holders
        institutional = t.institutional_holders
    except Exception:
        major, institutional = None, None

    rows = []
    if major is not None and not major.empty:
        for _, r in major.iterrows():
            pct = r.iloc[0] if len(r) > 0 else None
            label = r.index[0] if hasattr(r, "index") else None
            if isinstance(pct, str) and pct.endswith("%"):
                pct = float(pct.rstrip("%"))
            rows.append({"holder": str(label) if label is not None else "Unknown", "pct": float(pct) if pct is not None else None})

    snapshot = {
        "symbol": sym,
        "period": "current",
        "major_holders": rows,
        "institutional_holders": (
            institutional.fillna("").to_dict(orient="records") if institutional is not None and not institutional.empty else []
        ),
        "source": "yfinance",
    }
    note = None
    if not rows and not snapshot["institutional_holders"]:
        note = "yfinance returned no holders; historical quarters require NSE API; coming v0.2"

    chart = charts.pie_chart(
        title=f"{sym} major holders",
        labels=[r["holder"] for r in rows] or ["n/a"],
        values=[r["pct"] for r in rows] or [1.0],
    )
    return ToolResult(tool="get_shareholding", symbol=sym, data=snapshot, chart=chart, source="yfinance", note=note)



def get_financials(symbol, period="annual", years=5):
    """Fetch P&L / balance sheet / cashflow from yfinance as Fundamentals list."""
    sym = symbol.upper()
    t, _ = _yfinance_ticker(sym)
    try:
        if period == "quarterly":
            pl = t.quarterly_financials
            bs = t.quarterly_balance_sheet
            cf = t.quarterly_cashflow
        else:
            pl = t.financials
            bs = t.balance_sheet
            cf = t.cashflow
    except Exception as e:
        return ToolResult(tool="get_financials", symbol=sym, data={"error": str(e)}, source="yfinance")

    periods_list = list(pl.columns) if pl is not None and not pl.empty else []
    out = []
    for col in periods_list:
        ts = pd_ts_str(col)
        bs_col = None
        if bs is not None and not bs.empty:
            for c in bs.columns:
                if pd_ts_str(c) == ts:
                    bs_col = c
                    break
        bs_col = bs_col or (bs.columns[0] if bs is not None and not bs.empty else None)

        rev = _gv(pl, col, "Total Revenue", "Operating Revenue")
        op_inc = _gv(pl, col, "Operating Income", "Operating Income Loss")
        ni = _gv(pl, col, "Net Income")
        eps_val = _gv(pl, col, "Diluted EPS")
        if eps_val is None:
            eps_val = _gv(pl, col, "Basic EPS")

        ta = _gv(bs, bs_col, "Total Assets")
        td = _gv(bs, bs_col, "Total Debt")
        if td is None:
            td = _gv(bs, bs_col, "Long Term Debt")
        te = _gv(bs, bs_col, "Stockholders Equity", "Total Equity Gross Minority Interest")
        bv = _gv(bs, bs_col, "Common Stock Equity", "Stockholders Equity", "Total Equity Gross Minority Interest")

        ocf = _gv(cf, bs_col, "Operating Cash Flow", "Cash Flow From Continuing Operating Activities")
        capex = _gv(cf, bs_col, "Capital Expenditure", "Purchase Of Property Plant Equipment")

        fcf = None
        if ocf is not None and capex is not None:
            fcf = ocf + capex

        d = Fundamentals(
            symbol=sym, period=ts,
            revenue=rev, operating_income=op_inc, net_income=ni, eps=eps_val,
            book_value=bv, total_assets=ta, total_debt=td, total_equity=te,
            operating_cf=ocf, capex=capex, fcf=fcf,
            source=f"yfinance ({period})",
        ).model_dump(mode="json")
        out.append(d)

    table_cols = ["period", "revenue", "operating_income", "net_income", "eps", "total_assets", "total_debt", "total_equity", "operating_cf", "fcf"]
    chart = charts.screener_table(f"{sym} {period} fundamentals", out, table_cols) if out else None
    return ToolResult(tool="get_financials", symbol=sym, data={"fundamentals": out}, chart=chart, source=f"yfinance ({period})")




def get_corporate_actions(symbol, years=5):
    """Fetch dividends + splits from yfinance. Bonus/demerger from NSE if accessible."""
    sym = symbol.upper()
    t, _ = _yfinance_ticker(sym)
    out = {"dividends": [], "splits": [], "bonus_issues": [], "demergers": []}
    source = "yfinance (splits+dividends only)"
    try:
        actions = t.actions
        if actions is not None and not actions.empty:
            for idx, row in actions.iterrows():
                ts = pd_ts_str(idx)
                div = row.get("Dividends") if hasattr(row, "get") else None
                sp = row.get("Stock Splits") if hasattr(row, "get") else None
                if div is not None and float(div) != 0:
                    out["dividends"].append({"date": ts, "amount": float(div)})
                if sp is not None and float(sp) != 0:
                    out["splits"].append({"date": ts, "ratio": float(sp)})
    except Exception:
        pass

    try:
        import requests
        end = datetime.now().strftime("%d-%m-%Y")
        start = (datetime.now() - timedelta(days=365 * years)).strftime("%d-%m-%Y")
        url = f"https://www.nseindia.com/api/corporate-announcements?index=equities&symbol={sym}&from_date={start}&to_date={end}"
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code == 200:
            data = r.json()
            for item in (data if isinstance(data, list) else []):
                desc = (item.get("desc") or "").lower()
                ts = item.get("an_dt") or item.get("dissemDT") or ""
                if "bonus" in desc:
                    out["bonus_issues"].append({"date": ts, "description": item.get("desc", "")})
                elif "demerger" in desc:
                    out["demergers"].append({"date": ts, "description": item.get("desc", "")})
            if out["bonus_issues"] or out["demergers"]:
                source = "yfinance + NSE"
    except Exception:
        pass

    return ToolResult(tool="get_corporate_actions", symbol=sym, data=out, source=source)



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


def get_advanced_chart(symbol, chart_type="candlestick", period="6mo", indicators=None):
    """Get candlestick or line chart for a stock. Optionally overlay indicators."""
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
    overlays = {}
    for ind_name in (indicators or []):
        if ind_name in _INDICATOR_DISPATCH:
            try:
                pts = _INDICATOR_DISPATCH[ind_name](bars, period=14)
                overlays[ind_name] = {
                    "x": [p.timestamp.isoformat() for p in pts if p.value is not None],
                    "y": [p.value for p in pts if p.value is not None],
                }
            except Exception:
                overlays[ind_name] = {"error": "compute failed"}
    return ToolResult(tool="get_advanced_chart", symbol=sym, data={"bars": [b.model_dump(mode="json") for b in bars][-60:], "indicators": overlays}, chart=chart, source="yfinance")

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



# === added by merge from feat/volatility-stats-portfolio ===
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



def get_intraday_ticks(symbol, interval="5m"):
    """Intraday OHLCV ticks. ponytail: yfinance limits intraday to ~60 days."""
    sym = symbol.upper()
    bars = _bars_from_yfinance(sym, period="5d", interval=interval)
    if not bars:
        return ToolResult(tool="get_intraday_ticks", symbol=sym, data={"error": "no bars"}, source="yfinance")
    return ToolResult(tool="get_intraday_ticks", symbol=sym, data={"bars": [b.model_dump(mode="json") for b in bars], "interval": interval}, source="yfinance")



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



def portfolio_max_drawdown(equity_json):
    """Max drawdown of an equity curve. equity_json is a list of equity values."""
    try:
        eq = json.loads(equity_json) if isinstance(equity_json, str) else equity_json
    except Exception as e:
        return ToolResult(tool="portfolio_max_drawdown", symbol=None, data={"error": f"bad json: {e}"}, source="compute")
    dd, start, end = portfolio.max_drawdown(eq)
    return ToolResult(tool="portfolio_max_drawdown", symbol=None, data={"max_drawdown": dd, "start_idx": start, "end_idx": end}, source="compute")



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



def portfolio_sharpe(returns_json, risk_free=0.06):
    """Annualized Sharpe ratio from daily returns."""
    try:
        rets = json.loads(returns_json) if isinstance(returns_json, str) else returns_json
    except Exception as e:
        return ToolResult(tool="portfolio_sharpe", symbol=None, data={"error": f"bad json: {e}"}, source="compute")
    s = portfolio.sharpe(rets, risk_free=risk_free)
    return ToolResult(tool="portfolio_sharpe", symbol=None, data={"sharpe": s, "risk_free": risk_free}, source="compute")



def portfolio_var(returns_json, confidence=0.95):
    """Historical Value-at-Risk at `confidence`. returns_json is a list of returns."""
    try:
        rets = json.loads(returns_json) if isinstance(returns_json, str) else returns_json
    except Exception as e:
        return ToolResult(tool="portfolio_var", symbol=None, data={"error": f"bad json: {e}"}, source="compute")
    v = portfolio.var(rets, confidence=confidence)
    return ToolResult(tool="portfolio_var", symbol=None, data={"value_at_risk": v, "confidence": confidence}, source="compute")



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



def search_stocks(query, limit=20):
    """Substring search over a hardcoded NSE universe. ponytail: yfinance has no search API."""
    q = (query or "").upper()
    matched = [s for s in _NSE_SEARCH_UNIVERSE if q in s][:limit]
    return ToolResult(tool="search_stocks", symbol=None, data={"matched": matched, "query": query}, source="local")



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



# === added by merge from feat/fundamentals-shareholding ===
def _first_row(df, *keys):
    if df is None or df.empty:
        return None
    idx_lower = [str(i).lower() for i in df.index]
    for k in keys:
        kl = k.lower()
        for i, name in enumerate(idx_lower):
            if kl in name:
                return df.iloc[i]
    return None



def _get_annual_fundamentals(symbol):
    res = get_financials(symbol, period="annual", years=5)
    if res.data and "fundamentals" in res.data:
        return res.data["fundamentals"]
    return []



def _gv(df, col, *keys):
    row = _first_row(df, *keys)
    if row is None:
        return None
    try:
        v = row[col]
    except Exception:
        return None
    if v is None:
        return None
    try:
        f = float(v)
        return f if f == f else None
    except Exception:
        return None




def _info(symbol):
    t, _ = _yfinance_ticker(symbol)
    try:
        return t.info or {}
    except Exception:
        return {}



def _safe_div(a, b):
    if a is None or b is None or b == 0:
        return None
    try:
        return float(a) / float(b)
    except Exception:
        return None




def _yfinance_ticker(symbol):
    import yfinance as yf
    s = symbol.upper().strip()
    ns_sym = s if s.endswith(".NS") or s.endswith(".BO") else f"{s}.NS"
    return yf.Ticker(ns_sym), ns_sym



def pd_ts_str(col):
    try:
        if hasattr(col, "strftime"):
            return col.strftime("%Y-%m-%d")
        if hasattr(col, "year"):
            return f"{col.year}-{getattr(col, 'month', 1):02d}"
    except Exception:
        pass
    return str(col)




def get_bulk_block_deals(symbol, days=90):
    """Bulk/block deals from NSE; stub fallback when blocked."""
    sym = symbol.upper()
    try:
        import requests
        end = datetime.now().strftime("%d-%m-%Y")
        start = (datetime.now() - timedelta(days=days)).strftime("%d-%m-%Y")
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        out = {"bulk_deals": [], "block_deals": []}
        for kind, path in (("bulk_deals", "/api/bulk-deal"), ("block_deals", "/api/block-deal")):
            url = f"https://www.nseindia.com{path}?from_date={start}&to_date={end}"
            try:
                r = requests.get(url, headers=headers, timeout=8)
                if r.status_code == 200:
                    items = r.json()
                    for it in (items if isinstance(items, list) else []):
                        if (it.get("symbol") or "").upper() == sym:
                            out[kind].append(it)
            except Exception:
                continue
        return ToolResult(tool="get_bulk_block_deals", symbol=sym, data=out, source="NSE")
    except Exception:
        return ToolResult(
            tool="get_bulk_block_deals",
            symbol=sym,
            data={"bulk_deals": [], "block_deals": []},
            source="stub",
            note="NSE block/bulk deal API blocked or unavailable; coming v0.2",
        )



def get_dividend_history(symbol, years=10):
    """yfinance dividends time series; aggregate by year."""
    sym = symbol.upper()
    t, _ = _yfinance_ticker(sym)
    out = {"by_year": {}, "by_date": []}
    try:
        divs = t.dividends
        if divs is not None and not divs.empty:
            for idx, amt in divs.items():
                ts = pd_ts_str(idx)
                y = idx.year if hasattr(idx, "year") else None
                out["by_date"].append({"date": ts, "amount": float(amt)})
                if y:
                    out["by_year"][str(y)] = out["by_year"].get(str(y), 0.0) + float(amt)
    except Exception:
        pass
    info = _info(sym)
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    if price and out["by_year"]:
        latest_year = max(out["by_year"].keys())
        out["yield_latest_year_pct"] = round(out["by_year"][latest_year] / price * 100, 2)
    return ToolResult(tool="get_dividend_history", symbol=sym, data=out, source="yfinance")



def get_earnings_calendar(symbol):
    """Next earnings date + last quarters with surprise."""
    sym = symbol.upper()
    t, _ = _yfinance_ticker(sym)
    out = {"next_earnings": None, "past_quarters": []}
    try:
        cal = t.calendar
        if cal is not None and not cal.empty:
            try:
                out["next_earnings"] = pd_ts_str(cal.iloc[0, 0])
            except Exception:
                pass
    except Exception:
        pass
    try:
        ed = t.earnings_dates
        if ed is not None and not ed.empty:
            for idx, row in ed.head(8).iterrows():
                ts = pd_ts_str(idx)
                actual = row.get("Reported EPS") if hasattr(row, "get") else None
                estimate = row.get("EPS Estimate") if hasattr(row, "get") else None
                surprise = None
                if actual is not None and estimate is not None:
                    try:
                        surprise = float(actual) - float(estimate)
                    except Exception:
                        surprise = None
                out["past_quarters"].append({
                    "date": ts,
                    "actual_eps": float(actual) if actual is not None else None,
                    "estimate_eps": float(estimate) if estimate is not None else None,
                    "surprise": surprise,
                })
    except Exception:
        pass
    return ToolResult(tool="get_earnings_calendar", symbol=sym, data=out, source="yfinance")



def get_financial_ratios(symbol, years=5):
    """Compute valuation + profitability ratios from annual fundamentals + current price."""
    sym = symbol.upper()
    info = _info(sym)
    price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
    mc = info.get("marketCap")
    shares = info.get("sharesOutstanding")
    fundamentals = _get_annual_fundamentals(sym)
    if not fundamentals:
        return ToolResult(tool="get_financial_ratios", symbol=sym, data={"error": "no fundamentals"}, source="compute")

    latest = fundamentals[0]
    prev = fundamentals[1] if len(fundamentals) > 1 else None
    rev = latest.get("revenue")
    op_inc = latest.get("operating_income")
    ni = latest.get("net_income")
    eps = latest.get("eps")
    ta = latest.get("total_assets")
    td = latest.get("total_debt")
    te = latest.get("total_equity")
    bv = latest.get("book_value")
    fcf = latest.get("fcf")

    ttm_eps = None
    try:
        qres = get_financials(sym, period="quarterly", years=2)
        qf = (qres.data or {}).get("fundamentals", [])
        eps_vals = [q.get("eps") for q in qf[:4] if q.get("eps") is not None]
        if eps_vals:
            ttm_eps = sum(eps_vals)
    except Exception:
        pass

    cash = info.get("totalCash")
    ev = (mc + (td or 0) - (cash or 0)) if mc is not None else None
    bv_per_share = _safe_div(bv, shares) if (bv is not None and shares) else None

    rev_prev = prev.get("revenue") if prev else None
    eps_prev = prev.get("eps") if prev else None
    rev_growth = _safe_div(rev - rev_prev, rev_prev) if (rev is not None and rev_prev) else None
    eps_growth = _safe_div(eps - eps_prev, eps_prev) if (eps is not None and eps_prev) else None
    capital_employed = (ta - (td or 0)) if ta is not None else None

    ratios = {
        "pe": _safe_div(price, ttm_eps if ttm_eps is not None else eps),
        "pb": _safe_div(price, bv_per_share),
        "ev_ebitda": _safe_div(ev, op_inc),
        "roe": _safe_div(ni, te),
        "roce": _safe_div(op_inc, capital_employed),
        "debt_to_equity": _safe_div(td, te),
        "current_ratio": None,
        "gross_margin": None,
        "operating_margin": _safe_div(op_inc, rev),
        "net_margin": _safe_div(ni, rev),
        "revenue_growth_yoy": rev_growth,
        "eps_growth_yoy": eps_growth,
        "dividend_yield": info.get("dividendYield"),
        "payout_ratio": info.get("payoutRatio"),
        "fcf_yield": _safe_div(fcf, mc),
    }
    out = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in ratios.items()}
    return ToolResult(tool="get_financial_ratios", symbol=sym, data=out, source="compute (yfinance fundamentals + info)")




def get_industry_comparison(symbol, peers_json=None):
    """Compare key ratios across sector peers."""
    sym = symbol.upper()
    info = _info(sym)
    sector = info.get("sector") or "Default"
    peers = peers_json or SECTOR_PEERS.get(sector) or SECTOR_PEERS["Default"]
    targets = [sym] + [p for p in peers if p.upper() != sym]
    rows = []
    for p in targets:
        try:
            res = get_financial_ratios(p)
            d = res.data if res.data else {}
            rows.append({
                "symbol": p,
                "pe": d.get("pe"),
                "pb": d.get("pb"),
                "roe": d.get("roe"),
                "roce": d.get("roce"),
                "net_margin": d.get("net_margin"),
                "debt_to_equity": d.get("debt_to_equity"),
                "revenue_growth_yoy": d.get("revenue_growth_yoy"),
            })
        except Exception:
            rows.append({"symbol": p, "error": "fetch failed"})
    chart = charts.screener_table(
        f"{sym} vs {sector} peers",
        rows,
        ["symbol", "pe", "pb", "roe", "roce", "net_margin", "debt_to_equity", "revenue_growth_yoy"],
    )
    return ToolResult(tool="get_industry_comparison", symbol=sym, data={"sector": sector, "comparison": rows}, chart=chart, source="compute")



def get_promoter_pledge(symbol):
    """Promoter pledge data from BSE; stub fallback."""
    sym = symbol.upper()
    try:
        import requests
        url = f"https://api.bseindia.com/BseIndiaAPI/api/AnnouncementGetData/w?strSearch=PLEDGE&strSymbol={sym}"
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code == 200:
            return ToolResult(tool="get_promoter_pledge", symbol=sym, data={"announcements": r.json()}, source="BSE")
    except Exception:
        pass
    return ToolResult(
        tool="get_promoter_pledge",
        symbol=sym,
        data={"pledged_pct": None},
        source="stub",
        note="BSE pledge API unavailable; consult shareholding pattern disclosure in v0.2",
    )




def get_quality_score(symbol):
    """Piotroski F-Score + Altman Z-Score + composite."""
    sym = symbol.upper()
    fundamentals = _get_annual_fundamentals(sym)
    if not fundamentals or len(fundamentals) < 2:
        return ToolResult(tool="get_quality_score", symbol=sym, data={"error": "need 2+ years of fundamentals"}, source="compute")

    cur, prev = fundamentals[0], fundamentals[1]

    def t(v):
        return v is not None and isinstance(v, (int, float))

    ni_cur = cur.get("net_income")
    ni_prev = prev.get("net_income")
    te_cur = cur.get("total_equity")
    te_prev = prev.get("total_equity")
    roe_cur = _safe_div(ni_cur, te_cur)
    roe_prev = _safe_div(ni_prev, te_prev)
    at_cur = _safe_div(cur.get("revenue"), cur.get("total_assets"))
    at_prev = _safe_div(prev.get("revenue"), prev.get("total_assets"))

    piotroski = {
        "net_income_positive": bool(t(ni_cur) and ni_cur > 0),
        "ocf_positive": bool(t(cur.get("operating_cf")) and cur["operating_cf"] > 0),
        "roe_improving": bool(roe_cur is not None and roe_prev is not None and roe_cur > roe_prev),
        "fcf_positive": bool(t(cur.get("fcf")) and cur["fcf"] > 0),
        "debt_decreasing": bool(t(cur.get("total_debt")) and t(prev.get("total_debt")) and cur["total_debt"] <= prev["total_debt"]),
        "current_ratio_improving": None,
        "shares_dilution": None,
        "gross_margin_improving": None,
        "asset_turnover_improving": bool(at_cur is not None and at_prev is not None and at_cur > at_prev),
    }

    score = sum(1 for v in piotroski.values() if v is True)
    max_score = sum(1 for v in piotroski.values() if v is not None)

    info = _info(sym)
    mc = info.get("marketCap")
    wc = None
    if info.get("totalCurrentAssets") is not None and info.get("totalCurrentLiabilities") is not None:
        wc = info["totalCurrentAssets"] - info["totalCurrentLiabilities"]
    A = _safe_div(wc, cur.get("total_assets")) or 0
    C = _safe_div(cur.get("operating_income"), cur.get("total_assets")) or 0
    D = _safe_div(mc, cur.get("total_debt")) or 0
    E = _safe_div(cur.get("revenue"), cur.get("total_assets")) or 0
    altman_z = 1.2 * A + 1.4 * 0 + 3.3 * C + 0.6 * D + 1.0 * E

    composite = round((score / max_score * 10) if max_score else 0, 2)
    out = {
        "piotroski_f_score": f"{score}/{max_score}",
        "piotroski_tests": piotroski,
        "altman_z_score": round(altman_z, 2),
        "composite_quality": composite,
    }
    return ToolResult(tool="get_quality_score", symbol=sym, data=out, source="compute")




def get_valuation_vs_sector(symbol):
    """Compare stock's ratios against sector median."""
    sym = symbol.upper()
    info = _info(sym)
    sector = info.get("sector") or "Default"
    peers = [p for p in (SECTOR_PEERS.get(sector) or SECTOR_PEERS["Default"]) if p.upper() != sym]
    stock_res = get_financial_ratios(sym)
    stock_data = stock_res.data if stock_res.data else {}
    peer_ratios = {p: get_financial_ratios(p).data for p in peers}

    keys = ["pe", "pb", "ev_ebitda", "roe", "net_margin", "debt_to_equity"]
    out = {}
    for k in keys:
        stock_v = stock_data.get(k)
        peer_vals = []
        for v in peer_ratios.values():
            if v and isinstance(v.get(k), (int, float)):
                peer_vals.append(v[k])
        if peer_vals:
            s = sorted(peer_vals)
            n = len(s)
            median = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
        else:
            median = None
        premium = ((stock_v - median) / median * 100) if (stock_v is not None and median) else None
        out[k] = {
            "stock": stock_v,
            "sector_median": median,
            "premium_pct": round(premium, 2) if premium is not None else None,
        }
    return ToolResult(tool="get_valuation_vs_sector", symbol=sym, data={"sector": sector, "ratios": out}, source="compute")




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

    "get_bulk_block_deals": get_bulk_block_deals,
    "get_dividend_history": get_dividend_history,
    "get_earnings_calendar": get_earnings_calendar,
    "get_financial_ratios": get_financial_ratios,
    "get_industry_comparison": get_industry_comparison,
    "get_promoter_pledge": get_promoter_pledge,
    "get_quality_score": get_quality_score,
    "get_valuation_vs_sector": get_valuation_vs_sector,
}
