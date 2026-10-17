# pistol

Indian stock market data + compute engine. **53 tools, all free, AI-native.** Real NSE/BSE data, real-time quotes, technicals, fundamentals, screeners, portfolio, backtests, news, breadth, FII/DII.

pistol is a Python toolkit + MCP server that gives any LLM (Claude, GPT, Gemini) full access to NSE/BSE quotes, technicals, fundamentals, news, screeners, and portfolio analytics — through a single, free, MIT-licensed package. No signup. No quota. No paid tier.

```
                ┌──────────────┐
                │  pistol-core │  (data + compute + 53 tools)
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

The chat picks any of the 53 tools based on your question, fetches data, and renders charts inline.

## Run as an MCP server (Claude Code, Cursor, etc.)

```bash
claude mcp add pistol -- python -m pistol_mcp.server
```

Then in any Claude Code session:

> "Show me RELIANCE 14-day RSI"
> "What's the Piotroski F-Score of TCS?"
> "Backtest INFY SMA crossover for 5 years"
> "Top movers in the Nifty 50 right now"
> "Compare RELIANCE with sector peers"

## The 53 tools (shipped in v0.1)

### Quotes & discovery (5)
`get_stock_quote`, `search_stocks`, `get_batch_quotes`, `get_company_profile`, `list_indices`

### Price history (5)
`get_price_history`, `get_intraday_ticks`, `get_advanced_chart`, `get_market_pulse`, `get_market_pulse_with_flows`

### Technical indicators (1 umbrella tool + 20 indicators)
`get_indicator` with: rsi, ema, sma, macd, bollinger, atr, adx, stochastic, cci, williams_r, roc, mfi, obv, vwap, ichimoku, parabolic_sar, keltner, donchian, aroon, supertrend

### Candlestick patterns (1 umbrella tool + 12 patterns)
`get_candlestick_patterns`: doji, hammer, shooting_star, engulfing_bullish/bearish, morning_star, evening_star, three_white_soldiers, three_black_crows, harami_bullish/bearish, marubozu

### Volatility (5)
`get_historical_volatility`, `get_parkinson_volatility`, `get_garman_klass_volatility`, `get_yang_zhang_volatility`, `get_hurst_exponent`

### Statistics (3)
`get_z_score`, `get_correlation`, `get_beta`

### Fundamentals (5)
`get_financials`, `get_financial_ratios`, `get_industry_comparison`, `get_valuation_vs_sector`, `get_quality_score` (Piotroski + Altman Z)

### Shareholding & corporate (4)
`get_shareholding`, `get_dividend_history`, `get_earnings_calendar`, `get_bulk_block_deals`, `get_promoter_pledge`, `get_corporate_actions`

### Market breadth (5)
`get_top_movers`, `get_market_breadth`, `get_new_highs_lows`, `get_market_heatmap`, `get_sector_rotation`

### Indices & macro (3)
`get_index_performance`, `get_india_vix`, `get_fii_dii_flows`

### Signals (1 umbrella tool)
`get_signals`: golden_cross, death_cross, macd_crossover, rsi_oversold, rsi_overbought, volume_spike, breakout_52w_high, breakdown_52w_low

### Screeners (1)
`screen_stocks`, `screen_by_indicator`

### Backtest (1)
`backtest_sma`, `backtest_sma_crossover`

### Portfolio (5)
`portfolio_sector_concentration`, `portfolio_var`, `portfolio_sharpe`, `portfolio_max_drawdown`, `portfolio_correlation_matrix`

### News (3)
`get_market_news`, `get_stock_news`, `get_india_market_news`, `get_stock_news_with_sentiment`

## Run the tests

```bash
cd packages/pistol-core
pytest -q   # 93 tests
```

## Repo layout

```
pistol/
  packages/
    pistol-core/   # the library + tool registry + web demo
    pistol-mcp/    # MCP server (stdio, talks to pistol-core)
    pistol-web/    # (reserved for future)
  README.md
```

## Data sources (all free)

- **yfinance** — quotes, OHLCV, financials, shareholding, dividends, splits, calendar
- **AMFI** — mutual fund NAVs
- **NSE public** — corporate announcements, indices (with cookie-jar dance)
- **BSE public** — scrip search, corporate actions
- **Google News RSS** — market and stock news
- **RBI / data.gov.in** — macro (reserved for v0.2)
- **NSDL** — FII/DII monthly (with fallback snapshot)

No paid vendors. No scraping that violates terms. All data flows degrade gracefully when a source is unavailable.

## License

MIT.
