"""Plotly chart helpers. Each returns a ChartSpec with JSON-serialized fig."""

from __future__ import annotations

import json

import plotly.graph_objects as go

from ..types import ChartSpec, IndicatorPoint, PriceBar


def _base_layout(title, height=380, xaxis_title=""):
    return dict(
        title=title,
        template="plotly_dark",
        height=height,
        margin=dict(l=40, r=20, t=50, b=30),
        xaxis_title=xaxis_title,
        hovermode="x unified",
    )


def line_chart(title, x, y, y_name, thresholds=None, colors=None):
    """Line + optional horizontal thresholds."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(x), y=list(y), mode="lines", name=y_name,
                             line=dict(color=(colors or {}).get("line", "#7c3aed"), width=2)))
    for t in thresholds or []:
        fig.add_hline(y=t, line=dict(color="#6b6b7a", width=1, dash="dash"))
    fig.update_layout(**_base_layout(title))
    fig.update_yaxes(title=y_name)
    return ChartSpec(chart_type="line", title=title, plotly_fig=json.loads(fig.to_json()))


def candlestick_chart(bars, title):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=[b.timestamp.isoformat() for b in bars],
        open=[b.open for b in bars],
        high=[b.high for b in bars],
        low=[b.low for b in bars],
        close=[b.close for b in bars],
        increasing_line_color="#10b981",
        decreasing_line_color="#ef4444",
    ))
    fig.update_layout(**_base_layout(title))
    fig.update_layout(xaxis_rangeslider_visible=False)
    return ChartSpec(chart_type="candlestick", title=title, plotly_fig=json.loads(fig.to_json()))


def bar_chart(title, x, y, y_name):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=list(x), y=list(y), name=y_name, marker_color="#7c3aed"))
    fig.update_layout(**_base_layout(title))
    fig.update_yaxes(title=y_name)
    return ChartSpec(chart_type="bar", title=title, plotly_fig=json.loads(fig.to_json()))


def pie_chart(title, labels, values):
    fig = go.Figure(data=[go.Pie(labels=list(labels), values=list(values))])
    fig.update_layout(title=title, template="plotly_dark", height=380)
    return ChartSpec(chart_type="pie", title=title, plotly_fig=json.loads(fig.to_json()))


def heatmap_chart(title, z, x_labels, y_labels):
    fig = go.Figure(data=go.Heatmap(z=z, x=list(x_labels), y=list(y_labels), colorscale="Viridis"))
    fig.update_layout(title=title, template="plotly_dark", height=380)
    return ChartSpec(chart_type="heatmap", title=title, plotly_fig=json.loads(fig.to_json()))


def screener_table(title, rows, columns):
    fig = go.Figure(data=[go.Table(
        header=dict(values=list(columns), fill_color="#7c3aed", font=dict(color="white")),
        cells=dict(values=[[r.get(c, "") for r in rows] for c in columns], fill_color="#131318"),
    )])
    fig.update_layout(title=title, template="plotly_dark", height=380)
    return ChartSpec(chart_type="table", title=title, plotly_fig=json.loads(fig.to_json()))


def indicator_grid(title, indicators):
    fig = go.Figure()
    for name, pts in indicators.items():
        fig.add_trace(go.Scatter(
            x=[p.timestamp.isoformat() for p in pts],
            y=[p.value for p in pts],
            mode="lines",
            name=name,
        ))
    fig.update_layout(**_base_layout(title, height=500))
    return ChartSpec(chart_type="indicator_grid", title=title, plotly_fig=json.loads(fig.to_json()))
