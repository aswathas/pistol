# pistol-mcp

MCP server for [pistol](https://github.com/aswathas13/pistol): 15 Indian stock-market tools, all free, all local.

## Install

```bash
pip install -e ../pistol-core
pip install -e .
```

## Register with Claude Code

```bash
claude mcp add pistol -- python -m pistol_mcp.server
```

Or use the console-script shortcut:

```bash
claude mcp add pistol -- pistol-mcp
```

## Try it

Ask Claude:

- "Show me RELIANCE 14-day RSI"
- "What's the latest news on TCS?"
- "Run a screener: oversold Nifty 50 stocks"
- "Backtest INFY SMA crossover for 5 years"

## What you get

Every tool returns a `ToolResult` JSON:

```json
{
  "tool": "get_indicator",
  "symbol": "RELIANCE",
  "data": { "indicator": "rsi", "values": [...] },
  "chart": { "chart_type": "line", "title": "...", "plotly_fig": {...} },
  "source": "compute",
  "note": null
}
```

The chart is a plotly figure dict - render it inline or hand it to the client.

## License

MIT
