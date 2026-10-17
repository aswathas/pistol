# pistol

Indian stock market data + compute engine. **110 tools, all free, AI-native.** Ship 15 today, ship the rest as the compute library already supports them.

pistol is a Python toolkit + MCP server that gives any LLM (Claude, GPT, Gemini) full access to NSE/BSE quotes, technicals, fundamentals, news, screeners, and portfolio analytics — through a single, free, MIT-licensed package. No API keys, no paid tiers, no signup.

```
                ┌──────────────┐
                │  pistol-core │  (data + compute + tool registry)
                │   15 tools   │
                └──────┬───────┘
                       │
        ┌──────────────┴───────────────┐
        │                              │
        v                              v
  ┌───────────┐                  ┌────────────┐
  │ pistol-mcp│  stdio           │ pistol-web │
  │ MCP server│ ─────────►       │ FastAPI UI │
  │ (Claude,  │  any LLM         │ chat demo  │
  │  Cursor)  │                  │            │
  └───────────┘                  └────────────┘
```

## Install

```bash
git clone <this repo>
cd pistol
pip install -e packages/pistol-core
pip install -e packages/pistol-mcp      # optional, for MCP
```

## Run the web demo

```bash
export ANTHROPIC_AUTH_TOKEN=sk-ant-...
uvicorn pistol.chat_app:app --host 127.0.0.1 --port 8000
# open http://127.0.0.1:8000
```

The chat picks any of the 15 tools based on your question, fetches data, and renders the chart inline.

## Run as an MCP server (Claude Code, Cursor, etc.)

```bash
claude mcp add pistol -- python -m pistol_mcp.server
```

Then in any Claude Code session:

> "Show me RELIANCE 14-day RSI"
> "What's the latest news on TCS?"
> "Backtest INFY SMA crossover for 5 years"
> "Top movers in the Nifty 50 right now"

## The 15 tools (shipped in v0.1)

| Tool | One-liner |
|------|-----------|
| `get_stock_quote` | Live LTP/volume/OHLC for any NSE symbol |
| `get_price_history` | OHLCV bars + line chart |
| `get_indicator` | RSI/EMA/SMA/MACD/Bollinger/ATR/ADX/Stochastic/CCI/Williams %R/ROC/MFI/OBV/VWAP/Ichimoku/Parabolic SAR/Keltner/Donchian/Aroon/Supertrend |
| `get_candlestick_patterns` | Detect 12 candlestick patterns on recent bars |
| `get_signals` | Run 8 signal detectors: golden/death cross, MACD crossover, RSI overbought/oversold, volume spike, 52w breakout/breakdown |
| `screen_stocks` | Run a preset screener across a universe |
| `backtest_sma` | SMA crossover backtest over N years |
| `get_market_news` | Top Indian market news from Google News RSS |
| `get_stock_news` | Stock-specific news search |
| `get_shareholding` | Stub — coming in v0.2 |
| `get_financials` | Stub — coming in v0.2 |
| `get_corporate_actions` | Stub — coming in v0.2 |
| `get_company_profile` | Name, sector, industry from yfinance |
| `get_top_movers` | Top movers by abs % change across Nifty 50 |
| `get_advanced_chart` | Candlestick or line chart wrapper |

## Roadmap to 110

The compute layer (`pistol.compute`) already ships 20 indicators, 12 candlestick patterns, 8 signals, 5 volatility estimators, 4 stats primitives, 10+ screeners, and a backtest engine. v0.2 wraps each one as a public tool, plus adds paid data integrations (XBRL fundamentals, NSE shareholding, delivery %, corporate actions). v0.3 adds FII/DII flow, MF holdings, and macro (RBI). v0.4 adds LLM-generated research reports and portfolio analytics. All free, all MIT.

## Repo layout

```
pistol/
  packages/
    pistol-core/   # the library + tool registry + web demo
    pistol-mcp/    # MCP server (stdio, talks to pistol-core)
    pistol-web/    # (reserved for future React/Vite UI)
```

## License

MIT — see [LICENSE](packages/pistol-core/LICENSE).
