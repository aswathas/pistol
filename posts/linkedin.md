# LinkedIn post

Building in public: an AI agent for the Indian stock market.

Six weeks ago I got frustrated every time I wanted to ask "is RELIANCE overbought right now?" or "show me top gainers in Nifty 50" — the existing tools are either expensive subscriptions, fragile scrapers, or clunky screeners that need a PhD to configure.

So I'm building one that's free, open-source, and talks to any LLM.

**pistol** — a Python toolkit + MCP server with 53 tools covering:
• Live quotes for 8,000+ NSE/BSE stocks
• 20 technical indicators (RSI, MACD, Bollinger, Ichimoku, SuperTrend, ...)
• 12 candlestick pattern detectors
• Fundamentals (P/E, P/B, ROE, Piotroski F-Score, peer comparison)
• Volatility models (Parkinson, Garman-Klass, Yang-Zhang)
• Backtests, screeners, market breadth, FII/DII flows
• News search with sentiment

The wedge: AI-native UX. You don't pick 20 filters and click "Run." You type "show me RELIANCE 14-day RSI with a chart" and Claude picks the right tool, fetches real NSE data, and renders the chart inline.

Screenshots:
1. Landing — `screenshots/01-landing.png`
2. Live chart — `screenshots/03-rsi-chart.png`

The whole thing is MIT, no signup, no quota, no paid tier. The compute layer is pure pandas — every indicator, every backtest, every screener runs on your machine or any VPS. Data sources are all free: yfinance, AMFI, NSE public, Google News RSS, RBI.

If you're a developer with Claude Code, install it as an MCP:
```
pip install pistol-mcp
claude mcp add pistol -- python -m pistol_mcp.server
```

If you just want the chat:
```
pip install pistol-core
uvicorn pistol.chat_app:app
```

It's a v0.1 demo today. Real bugs, missing features, but the wedge works: type a question, get a real chart with real NSE data in 4 seconds. Watch this space.

#indianstocks #buildinpublic #aiagents #mcp #quant #claude
