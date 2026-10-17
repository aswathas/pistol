"""Candlestick pattern detectors. Each returns list[date] where pattern was detected."""

from __future__ import annotations

from datetime import date

from ..types import PriceBar


def _body(b: PriceBar) -> float:
    return abs(b.close - b.open)


def _is_green(b: PriceBar) -> bool:
    return b.close > b.open


def _is_red(b: PriceBar) -> bool:
    return b.close < b.open


def _upper_shadow(b: PriceBar) -> float:
    return b.high - max(b.open, b.close)


def _lower_shadow(b: PriceBar) -> float:
    return min(b.open, b.close) - b.low


def _range(b: PriceBar) -> float:
    return b.high - b.low if b.high > b.low else 1e-9


def doji(bars: list[PriceBar]) -> list[date]:
    """Open ≈ close within 0.1% of high-low range."""
    out = []
    for b in bars:
        if _body(b) <= 0.001 * _range(b):
            out.append(b.timestamp)
    return out


def hammer(bars: list[PriceBar]) -> list[date]:
    """Lower shadow >= 2x body, small upper shadow."""
    out = []
    for b in bars:
        body = _body(b)
        if body <= 0:
            continue
        if _lower_shadow(b) >= 2 * body and _upper_shadow(b) <= 0.3 * body:
            out.append(b.timestamp)
    return out


def shooting_star(bars: list[PriceBar]) -> list[date]:
    """Upper shadow >= 2x body, small lower shadow."""
    out = []
    for b in bars:
        body = _body(b)
        if body <= 0:
            continue
        if _upper_shadow(b) >= 2 * body and _lower_shadow(b) <= 0.3 * body:
            out.append(b.timestamp)
    return out


def engulfing_bullish(bars: list[PriceBar]) -> list[date]:
    """Current green body fully engulfs prior red body."""
    out = []
    for i in range(1, len(bars)):
        prev, cur = bars[i - 1], bars[i]
        if not _is_red(prev) or not _is_green(cur):
            continue
        if cur.open <= prev.close and cur.close >= prev.open:
            out.append(cur.timestamp)
    return out


def engulfing_bearish(bars: list[PriceBar]) -> list[date]:
    """Current red body fully engulfs prior green body."""
    out = []
    for i in range(1, len(bars)):
        prev, cur = bars[i - 1], bars[i]
        if not _is_green(prev) or not _is_red(cur):
            continue
        if cur.open >= prev.close and cur.close <= prev.open:
            out.append(cur.timestamp)
    return out


def morning_star(bars: list[PriceBar]) -> list[date]:
    """3-bar: red, small body, green (close > midpoint of bar 1)."""
    out = []
    for i in range(2, len(bars)):
        b1, b2, b3 = bars[i - 2], bars[i - 1], bars[i]
        if not _is_red(b1) or not _is_green(b3):
            continue
        mid1 = (b1.open + b1.close) / 2
        if _body(b2) <= 0.3 * _body(b1) and b3.close > mid1:
            out.append(b3.timestamp)
    return out


def evening_star(bars: list[PriceBar]) -> list[date]:
    """3-bar: green, small body, red (close < midpoint of bar 1)."""
    out = []
    for i in range(2, len(bars)):
        b1, b2, b3 = bars[i - 2], bars[i - 1], bars[i]
        if not _is_green(b1) or not _is_red(b3):
            continue
        mid1 = (b1.open + b1.close) / 2
        if _body(b2) <= 0.3 * _body(b1) and b3.close < mid1:
            out.append(b3.timestamp)
    return out


def three_white_soldiers(bars: list[PriceBar]) -> list[date]:
    """3 consecutive green bodies, each opening within prior body, each closing higher."""
    out = []
    for i in range(2, len(bars)):
        b1, b2, b3 = bars[i - 2], bars[i - 1], bars[i]
        if not (_is_green(b1) and _is_green(b2) and _is_green(b3)):
            continue
        if b2.open > b1.open and b2.open < b1.close and b3.open > b2.open and b3.open < b2.close:
            if b2.close > b1.close and b3.close > b2.close:
                out.append(b3.timestamp)
    return out


def three_black_crows(bars: list[PriceBar]) -> list[date]:
    """3 consecutive red bodies, each opening within prior body, each closing lower."""
    out = []
    for i in range(2, len(bars)):
        b1, b2, b3 = bars[i - 2], bars[i - 1], bars[i]
        if not (_is_red(b1) and _is_red(b2) and _is_red(b3)):
            continue
        if b2.open < b1.open and b2.open > b1.close and b3.open < b2.open and b3.open > b2.close:
            if b2.close < b1.close and b3.close < b2.close:
                out.append(b3.timestamp)
    return out


def harami_bullish(bars: list[PriceBar]) -> list[date]:
    """Current green body inside prior red body."""
    out = []
    for i in range(1, len(bars)):
        prev, cur = bars[i - 1], bars[i]
        if not _is_red(prev) or not _is_green(cur):
            continue
        if cur.open > prev.close and cur.open < prev.open and cur.close < prev.open and cur.close > prev.close:
            out.append(cur.timestamp)
    return out


def harami_bearish(bars: list[PriceBar]) -> list[date]:
    """Current red body inside prior green body."""
    out = []
    for i in range(1, len(bars)):
        prev, cur = bars[i - 1], bars[i]
        if not _is_green(prev) or not _is_red(cur):
            continue
        if cur.open < prev.close and cur.open > prev.open and cur.close > prev.close and cur.close < prev.open:
            out.append(cur.timestamp)
    return out


def marubozu(bars: list[PriceBar]) -> list[date]:
    """Body >= 95% of high-low range (no significant shadows)."""
    out = []
    for b in bars:
        if _body(b) >= 0.95 * _range(b):
            out.append(b.timestamp)
    return out


def detect_all(bars: list[PriceBar]) -> dict[str, list[date]]:
    """Run all 12 detectors and return combined dict."""
    return {
        "doji": doji(bars),
        "hammer": hammer(bars),
        "shooting_star": shooting_star(bars),
        "engulfing_bullish": engulfing_bullish(bars),
        "engulfing_bearish": engulfing_bearish(bars),
        "morning_star": morning_star(bars),
        "evening_star": evening_star(bars),
        "three_white_soldiers": three_white_soldiers(bars),
        "three_black_crows": three_black_crows(bars),
        "harami_bullish": harami_bullish(bars),
        "harami_bearish": harami_bearish(bars),
        "marubozu": marubozu(bars),
    }
