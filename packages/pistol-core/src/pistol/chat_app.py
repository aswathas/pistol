"""pistol chat — AI-native web app, MVP demo.

One file. FastAPI + raw HTML + 53 tools via pistol.tools.TOOL_REGISTRY + Claude call.
Run: ANTHROPIC_BASE_URL=... ANTHROPIC_AUTH_TOKEN=... uvicorn pistol.chat_app:app

The chat is the wedge. This file proves: type natural language, Claude picks
a tool, the tool returns data + a chart, the chart renders inline.
"""

from __future__ import annotations

import json
import os
import pathlib

import inspect
import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

from pistol.tools import TOOL_REGISTRY, claude_tool_schema

# ponytail: anthropic SDK pulls a big dep. Use the same protocol via raw requests.
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
ANTHROPIC_AUTH_TOKEN = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")

app = FastAPI(title="pistol", version="0.1.0")

# ponytail: CORS only for /api/* so the Astro static page can call us from any origin.
from starlette.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=False,
)

# ---------- CLAUDE INTEGRATION (raw requests, no SDK) ----------

TOOL_SCHEMAS = claude_tool_schema(TOOL_REGISTRY)

SYSTEM_PROMPT = """You are pistol, an AI agent for the Indian stock market. You answer in plain English, you call tools when needed, and you explain what you see.

You have 53 tools: get_stock_quote, get_price_history, get_indicator (rsi/ema/sma/macd/bollinger/atr/adx/stochastic/cci/williams_r/roc/mfi/obv/vwap/ichimoku/parabolic_sar/keltner/donchian/aroon/supertrend), get_candlestick_patterns, get_signals, screen_stocks, backtest_sma, get_market_news, get_stock_news, get_shareholding, get_financials, get_corporate_actions, get_company_profile, get_top_movers, get_advanced_chart.

When the user asks about a stock, call the most specific tool. Be specific about numbers and what they mean. Be brief."""


def _call_claude(messages: list[dict]) -> dict:
    """One Anthropic messages call. raw requests, no SDK."""
    if not ANTHROPIC_AUTH_TOKEN:
        return {"error": "ANTHROPIC_AUTH_TOKEN not set"}
    r = requests.post(
        f"{ANTHROPIC_BASE_URL.rstrip('/')}/v1/messages",
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_AUTH_TOKEN,
            "X-Api-Key": ANTHROPIC_AUTH_TOKEN,  # ponytail: some proxies (MiniMax) want this header name
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": 2048,
            "system": SYSTEM_PROMPT,
            "tools": TOOL_SCHEMAS,
            "messages": messages,
        },
        timeout=60,
    )
    if r.status_code != 200:
        return {"error": f"claude {r.status_code}: {r.text[:200]}"}
    return r.json()


# ---------- CHAT ROUTE ----------

class ChatRequest(BaseModel):
    messages: list[dict]  # [{role, content}]


@app.post("/api/chat")
def chat(req: ChatRequest):
    """Run a chat turn. May call any of 53 tools. Returns {reply, tool_call, tool_result, chart}."""
    messages = list(req.messages)
    resp = _call_claude(messages)
    if "error" in resp:
        return JSONResponse({"error": resp["error"]}, status_code=500)

    reply_text = ""
    tool_call = None
    tool_result = None
    chart = None

    for block in resp.get("content", []):
        if block.get("type") == "text":
            reply_text += block.get("text", "")
        elif block.get("type") == "tool_use":
            tool_call = {"name": block.get("name"), "input": block.get("input", {})}
            fn = TOOL_REGISTRY.get(tool_call["name"])
            if fn is None:
                tool_result = {"error": "unknown tool: " + tool_call["name"]}
                chart = None
            else:
                try:
                    # ponytail: LLMs send "14" instead of 14. Coerce int params based on annotation OR default.
                    sig = inspect.signature(fn)
                    inp = dict(tool_call["input"])
                    for pname, param in sig.parameters.items():
                        if pname not in inp:
                            continue
                        want_int = param.annotation is int or isinstance(param.default, int)
                        if want_int:
                            try:
                                inp[pname] = int(inp[pname])
                            except (TypeError, ValueError):
                                pass
                    tres = fn(**inp)
                    tool_result = tres.data if not hasattr(tres.data, "model_dump") else tres.data
                    chart = tres.chart.plotly_fig if tres.chart else None
                except Exception as e:
                    tool_result = {"error": str(e)}
                    chart = None
            # Send tool result back, get final reply
            messages.append({"role": "assistant", "content": resp["content"]})
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": block.get("id"),
                    "content": json.dumps(tool_result, default=str)[:6000],
                }],
            })
            follow = _call_claude(messages)
            if "error" in follow:
                reply_text += f"\n\n[Follow-up error: {follow['error']}]"
                break
            for fb in follow.get("content", []):
                if fb.get("type") == "text":
                    reply_text += "\n\n" + fb.get("text", "")
            break  # one tool call per turn in MVP

    return {
        "reply": reply_text.strip(),
        "tool_call": tool_call,
        "tool_result": tool_result,
        "chart": chart,
    }




# ---------- STATIC FRONTEND ----------


_DIST_DIR = pathlib.Path(__file__).resolve().parents[3] / "pistol-web" / "dist"
_DIST = _DIST_DIR / "index.html"
# ponytail: serve Astro's hashed assets (_astro/*) and dist root favicon. Mount at /_astro avoids shadowing /api/*.
from starlette.staticfiles import StaticFiles
if (_DIST_DIR / "_astro").exists():
    app.mount("/_astro", StaticFiles(directory=str(_DIST_DIR / "_astro"), check_dir=False), name="astro-assets")


@app.get("/", response_class=HTMLResponse)
def home():
    if _DIST.exists():
        return FileResponse(_DIST, media_type="text/html")
    return HTMLResponse("<h1>pistol</h1><p>Astro dist not built. Run `npm run build` in packages/pistol-web.</p>")


@app.get("/api/health")
def health():
    return {"ok": True, "model": ANTHROPIC_MODEL, "has_key": bool(ANTHROPIC_AUTH_TOKEN)}


# ponytail: run with `python -m pistol.chat_app` or `uvicorn pistol.chat_app:app`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
