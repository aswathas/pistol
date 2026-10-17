"""Core types. Pydantic models shared by compute, data, and tools layers."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Exchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"


class Signal(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    NEUTRAL = "neutral"
    OVERBOUGHT = "overbought"
    OVERSOLD = "oversold"


class OHLC(BaseModel):
    open: float
    high: float
    low: float
    close: float
    volume: int = 0


class Quote(BaseModel):
    symbol: str
    exchange: Exchange
    name: str | None = None
    ltp: float
    change: float
    pct_change: float
    volume: int
    bid: float | None = None
    ask: float | None = None
    bid_qty: int | None = None
    ask_qty: int | None = None
    ohlc: OHLC
    timestamp: datetime
    source: str


class PriceBar(OHLC):
    timestamp: date
    adj_close: float | None = None
    delivery_pct: float | None = None
    delivery_volume: int | None = None


class Fundamentals(BaseModel):
    symbol: str
    period: str  # e.g. "Q3 FY26" or "FY25"
    revenue: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    eps: float | None = None
    book_value: float | None = None
    total_assets: float | None = None
    total_debt: float | None = None
    total_equity: float | None = None
    operating_cf: float | None = None
    capex: float | None = None
    fcf: float | None = None
    roe: float | None = None
    roce: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    net_margin: float | None = None
    dividend_yield: float | None = None
    pe: float | None = None
    pb: float | None = None
    ev_ebitda: float | None = None
    revenue_growth_yoy: float | None = None
    eps_growth_yoy: float | None = None
    source: str


class Shareholding(BaseModel):
    symbol: str
    period: str
    promoter: float  # percent
    fii: float
    dii: float
    public: float
    mutual_funds: float | None = None
    insurance: float | None = None
    others: float | None = None
    source: str


class IndicatorPoint(BaseModel):
    timestamp: date
    value: float | None = None
    signal: Signal | None = None


class IndicatorResult(BaseModel):
    name: str
    symbol: str
    period_label: str  # e.g. "14-day RSI"
    values: list[IndicatorPoint]
    latest_value: float | None = None
    latest_signal: Signal | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    source: str


class ScreenResult(BaseModel):
    matched: list[str]
    total_scanned: int
    criteria: dict[str, Any]
    metrics: dict[str, dict[str, float | None]] = Field(default_factory=dict)
    source: str


class ChartSpec(BaseModel):
    """Render hint for the LLM/web UI.

    plotly_fig is a JSON-serializable plotly figure dict. The web UI renders
    it inline next to the LLM's prose. The MCP returns it as JSON for clients
    that want to render it themselves.
    """

    chart_type: Literal[
        "line", "candlestick", "bar", "pie", "heatmap", "scatter", "table", "indicator_grid"
    ]
    title: str
    plotly_fig: dict[str, Any]
    caption: str | None = None


class ToolResult(BaseModel):
    """Wrapper returned by every pistol tool. The data field is tool-specific
    (Quote, IndicatorResult, etc.); chart is optional."""

    tool: str
    symbol: str | None = None
    data: Any
    chart: ChartSpec | None = None
    source: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
    note: str | None = None
