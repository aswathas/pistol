"""pistol chat — AI-native web app, MVP demo.

One file. FastAPI + raw HTML + 15 tools via pistol.tools.TOOL_REGISTRY + Claude call.
Run: ANTHROPIC_BASE_URL=... ANTHROPIC_AUTH_TOKEN=... uvicorn pistol.chat_app:app

The chat is the wedge. This file proves: type natural language, Claude picks
a tool, the tool returns data + a chart, the chart renders inline.
"""

from __future__ import annotations

import json
import os

import inspect
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from pistol.tools import TOOL_REGISTRY, claude_tool_schema

# ponytail: anthropic SDK pulls a big dep. Use the same protocol via raw requests.
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
ANTHROPIC_AUTH_TOKEN = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")

app = FastAPI(title="pistol", version="0.1.0")

# ---------- CLAUDE INTEGRATION (raw requests, no SDK) ----------

TOOL_SCHEMAS = claude_tool_schema(TOOL_REGISTRY)

SYSTEM_PROMPT = """You are pistol, an AI agent for the Indian stock market. You answer in plain English, you call tools when needed, and you explain what you see.

You have 15 tools: get_stock_quote, get_price_history, get_indicator (rsi/ema/sma/macd/bollinger/atr/adx/stochastic/cci/williams_r/roc/mfi/obv/vwap/ichimoku/parabolic_sar/keltner/donchian/aroon/supertrend), get_candlestick_patterns, get_signals, screen_stocks, backtest_sma, get_market_news, get_stock_news, get_shareholding, get_financials, get_corporate_actions, get_company_profile, get_top_movers, get_advanced_chart.

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
    """Run a chat turn. May call any of 15 tools. Returns {reply, tool_call, tool_result, chart}."""
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


# ---------- HTML (inline, polished, no separate file) ----------

HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>pistol · Indian stocks, ask anything</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  :root { --bg:#0a0a0c; --panel:#131318; --line:#1f1f28; --ink:#e8e8ee; --mute:#6b6b7a; --accent:#7c3aed; --good:#10b981; --bad:#ef4444; }
  * { box-sizing: border-box; }
  html, body { margin:0; padding:0; background:var(--bg); color:var(--ink); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", system-ui, sans-serif; -webkit-font-smoothing:antialiased; }
  body { min-height:100vh; display:flex; }
  .side { width:280px; border-right:1px solid var(--line); padding:24px 16px; display:flex; flex-direction:column; gap:24px; }
  .brand { display:flex; align-items:center; gap:10px; font-weight:700; font-size:18px; }
  .brand .dot { width:10px; height:10px; border-radius:50%; background:var(--accent); box-shadow:0 0 12px var(--accent); }
  .nav { display:flex; flex-direction:column; gap:4px; }
  .nav a { color:var(--mute); text-decoration:none; padding:8px 12px; border-radius:8px; font-size:14px; }
  .nav a:hover { background:var(--panel); color:var(--ink); }
  .nav a.active { background:var(--panel); color:var(--ink); }
  .meta { margin-top:auto; padding:12px; background:var(--panel); border-radius:10px; font-size:12px; color:var(--mute); line-height:1.5; }
  .meta strong { color:var(--ink); display:block; margin-bottom:4px; font-size:13px; }
  .main { flex:1; display:flex; flex-direction:column; max-height:100vh; }
  .topbar { padding:16px 32px; border-bottom:1px solid var(--line); display:flex; align-items:center; gap:12px; }
  .pill { background:var(--panel); border:1px solid var(--line); padding:4px 10px; border-radius:999px; font-size:12px; color:var(--mute); }
  .pill .dot { width:6px; height:6px; border-radius:50%; background:var(--good); display:inline-block; margin-right:6px; vertical-align:middle; }
  .chat { flex:1; overflow-y:auto; padding:32px; max-width:880px; width:100%; margin:0 auto; }
  .msg { margin-bottom:28px; display:flex; gap:12px; }
  .avatar { width:32px; height:32px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:13px; flex-shrink:0; }
  .user .avatar { background:linear-gradient(135deg, #7c3aed, #c026d3); }
  .ai .avatar { background:linear-gradient(135deg, #0ea5e9, #06b6d4); }
  .bubble { line-height:1.65; font-size:15px; max-width:100%; }
  .bubble pre { background:var(--panel); border:1px solid var(--line); padding:12px 14px; border-radius:10px; overflow-x:auto; font-size:13px; }
  .bubble p { margin:0 0 8px 0; }
  .bubble p:last-child { margin-bottom:0; }
  .bubble code { background:var(--panel); padding:1px 6px; border-radius:4px; font-size:13px; }
  .chart-wrap { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:8px; margin-top:12px; }
  .tool-pill { display:inline-flex; align-items:center; gap:6px; background:var(--panel); border:1px solid var(--line); padding:4px 10px; border-radius:8px; font-size:12px; color:var(--mute); margin-top:8px; font-family:ui-monospace, SFMono-Regular, monospace; }
  .tool-pill .spinner { width:8px; height:8px; border-radius:50%; background:var(--accent); animation:p 1s linear infinite; }
  @keyframes p { 0%{transform:scale(1);opacity:1} 50%{transform:scale(1.6);opacity:.5} 100%{transform:scale(1);opacity:1} }
  .input-bar { border-top:1px solid var(--line); padding:20px 32px; background:var(--bg); position:sticky; bottom:0; }
  .input-wrap { max-width:880px; margin:0 auto; display:flex; gap:8px; align-items:flex-end; background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:12px 14px; transition:border-color .15s; }
  .input-wrap:focus-within { border-color:var(--accent); }
  .input-wrap textarea { flex:1; background:transparent; color:var(--ink); border:0; outline:0; resize:none; font:inherit; font-size:15px; max-height:180px; line-height:1.5; }
  .input-wrap textarea::placeholder { color:var(--mute); }
  .send { background:var(--accent); color:#fff; border:0; padding:8px 14px; border-radius:10px; font-weight:600; cursor:pointer; font-size:14px; }
  .send:disabled { opacity:.5; cursor:not-allowed; }
  .examples { display:flex; flex-wrap:wrap; gap:6px; padding:0 32px 12px; max-width:880px; margin:0 auto; }
  .examples button { background:transparent; border:1px solid var(--line); color:var(--mute); padding:6px 12px; border-radius:8px; font-size:12px; cursor:pointer; font-family:inherit; }
  .examples button:hover { background:var(--panel); color:var(--ink); border-color:var(--accent); }
  .typing { display:flex; gap:4px; padding:8px 0; }
  .typing span { width:6px; height:6px; background:var(--mute); border-radius:50%; animation:b 1.2s infinite; }
  .typing span:nth-child(2) { animation-delay:.2s; }
  .typing span:nth-child(3) { animation-delay:.4s; }
  @keyframes b { 0%,60%,100%{opacity:.3; transform:translateY(0)} 30%{opacity:1; transform:translateY(-4px)} }
  .label { font-size:11px; color:var(--mute); text-transform:uppercase; letter-spacing:.06em; margin-bottom:4px; }
  .stat-row { display:flex; gap:16px; flex-wrap:wrap; margin-top:8px; }
  .stat { background:var(--panel); border:1px solid var(--line); padding:8px 12px; border-radius:8px; font-size:13px; }
  .stat .k { color:var(--mute); font-size:11px; text-transform:uppercase; }
  .stat .v { font-weight:600; margin-top:2px; }
  .v.up { color:var(--good); }
  .v.dn { color:var(--bad); }
  ::-webkit-scrollbar { width:8px; height:8px; }
  ::-webkit-scrollbar-track { background:transparent; }
  ::-webkit-scrollbar-thumb { background:var(--line); border-radius:4px; }
  .empty { text-align:center; padding:80px 20px; color:var(--mute); }
  .empty h2 { font-size:28px; font-weight:700; color:var(--ink); margin:0 0 12px; letter-spacing:-0.02em; }
  .empty p { margin:0 0 24px; font-size:15px; }
  .kbd { display:inline-block; padding:1px 6px; background:var(--panel); border:1px solid var(--line); border-radius:4px; font-size:11px; font-family:ui-monospace, monospace; }
</style>
</head>
<body>
<aside class="side">
  <div class="brand"><span class="dot"></span>pistol</div>
  <nav class="nav">
    <a class="active">Chat</a>
    <a>Screener</a>
    <a>Watchlist</a>
    <a>Portfolio</a>
    <a>Alerts</a>
    <a>Tools</a>
    <a>Pricing</a>
  </nav>
  <div class="meta">
    <strong>110 tools, all free</strong>
    1 dev · MIT · v0.1 demo<br>
    Powered by Claude + 15 tools wired
  </div>
</aside>
<main class="main">
  <div class="topbar">
    <span class="pill"><span class="dot"></span>Market open · NSE</span>
    <span class="pill">BSE 500 ▲ 0.42%</span>
    <span class="pill">India VIX 14.2</span>
    <span style="margin-left:auto;color:var(--mute);font-size:12px;">pistol v0.1 · localhost</span>
  </div>
  <div class="chat" id="chat">
    <div class="empty">
      <h2>Ask anything about Indian stocks.</h2>
      <p>Free AI agent with 15 tools: quotes, charts, indicators, news, screeners, backtests.</p>
      <div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center;max-width:640px;margin:0 auto;">
        <button class="ex" data-q="Show me RELIANCE 14-day RSI with a chart">RELIANCE 14-day RSI with a chart</button>
        <button class="ex" data-q="What does TCS's price look like over the last 6 months?">TCS 6-month price chart</button>
        <button class="ex" data-q="Is INFY overbought right now?">INFY overbought?</button>
        <button class="ex" data-q="Compare HDFCBANK and ICICIBANK RSI">HDFC vs ICICI RSI</button>
        <button class="ex" data-q="Show me SBIN with a candlestick chart">SBIN candlestick</button>
      </div>
    </div>
  </div>
  <div class="examples" id="examples" style="display:none;">
    <button class="ex" data-q="Show me RELIANCE 14-day RSI with a chart">RELIANCE RSI</button>
    <button class="ex" data-q="What does TCS's price look like over the last 6 months?">TCS 6mo</button>
    <button class="ex" data-q="Is INFY overbought right now?">INFY overbought?</button>
  </div>
  <form class="input-bar" id="form">
    <div class="input-wrap" style="width:100%;">
      <textarea id="input" rows="1" placeholder="Ask about an Indian stock, indicator, or the market…" autofocus></textarea>
      <button class="send" type="submit">Send</button>
    </div>
  </form>
</main>
<script>
const chat = document.getElementById("chat");
const form = document.getElementById("form");
const input = document.getElementById("input");
const examples = document.getElementById("examples");
const history = [];

// ponytail: input auto-resize
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 180) + "px";
});

// ponytail: enter to send, shift+enter for newline
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
});

document.querySelectorAll(".ex").forEach(b => b.addEventListener("click", () => {
  input.value = b.dataset.q;
  input.dispatchEvent(new Event("input"));
  form.requestSubmit();
}));

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = ""; input.style.height = "auto";
  hideEmpty();
  examples.style.display = "flex";
  history.push({ role: "user", content: text });
  appendMsg("user", text);
  const pending = appendMsg("ai", '<div class="typing"><span></span><span></span><span></span></div>');
  try {
    const r = await fetch("/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history }),
    });
    const data = await r.json();
    if (data.error) {
      pending.innerHTML = `<div class="bubble"><p style="color:var(--bad)">Error: ${esc(data.error)}</p></div>`;
      return;
    }
    let html = "";
    if (data.tool_call) {
      html += `<div class="tool-pill">⚡ ${esc(data.tool_call.name)}(${esc(JSON.stringify(data.tool_call.input))})</div>`;
    }
    if (data.reply) {
      html += `<div class="bubble">${fmt(data.reply)}</div>`;
    }
    if (data.tool_result) {
      html += renderResult(data.tool_result);
    }
    if (data.chart) {
      html += `<div class="chart-wrap" id="chart-${Date.now()}"></div>`;
    }
    pending.innerHTML = `<div class="avatar">P</div><div style="flex:1">${html}</div>`;
    history.push({ role: "assistant", content: data.reply || "" });
    // ponytail: render chart after attach
    if (data.chart) {
      const last = pending.querySelector(".chart-wrap");
      if (last) Plotly.newPlot(last, data.chart.data, data.chart.layout, { displayModeBar: false, responsive: true });
    }
    chat.scrollTop = chat.scrollHeight;
  } catch (e) {
    pending.innerHTML = `<div class="bubble"><p style="color:var(--bad)">Network error: ${esc(String(e))}</p></div>`;
  }
});

function appendMsg(role, html) {
  const div = document.createElement("div");
  div.className = "msg " + role;
  div.innerHTML = `<div class="avatar">${role === "user" ? "U" : "P"}</div><div style="flex:1">${html}</div>`;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div.querySelector("div[style*='flex:1']") || div;
}

function hideEmpty() { const e = chat.querySelector(".empty"); if (e) e.remove(); }

function esc(s) { return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }

// ponytail: minimal markdown (bold, lists, code, links)
function fmt(s) {
  s = esc(s);
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/^\s*[-•]\s+(.+)$/gm, "<li>$1</li>");
  s = s.replace(/(<li>.*<\/li>\n?)+/g, m => "<ul>" + m + "</ul>");
  s = s.replace(/\n\n/g, "</p><p>");
  s = s.replace(/\n/g, "<br>");
  if (!s.startsWith("<p>")) s = "<p>" + s;
  if (!s.endsWith("</p>") && !s.endsWith("</ul>")) s += "</p>";
  return s;
}

function renderResult(r) {
  if (r.error) return `<div class="bubble" style="color:var(--bad)">${esc(r.error)}</div>`;
  if (r.indicator === "rsi" && r.values && r.values.length) {
    const last = r.values[r.values.length - 1];
    const v = last ? last.value : null;
    const cls = v != null && v >= 70 ? "bad" : v != null && v <= 30 ? "good" : "";
    const zone = v != null && v >= 70 ? "Overbought" : v != null && v <= 30 ? "Oversold" : "Neutral";
    return `<div class="bubble"><div class="stat-row">
      <div class="stat"><div class="k">Latest RSI</div><div class="v ${cls}">${v} - ${last.timestamp || last.date || ""}</div></div>
      <div class="stat"><div class="k">Symbol</div><div class="v">${esc(r.symbol || "")}</div></div>
      <div class="stat"><div class="k">Zone</div><div class="v">${zone}</div></div>
    </div></div>`;
  }
  return `<div class="bubble"><pre>${esc(JSON.stringify(r, null, 2).slice(0, 600))}</pre></div>`;
}
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def home():
    return HTML


@app.get("/api/health")
def health():
    return {"ok": True, "model": ANTHROPIC_MODEL, "has_key": bool(ANTHROPIC_AUTH_TOKEN)}


# ponytail: run with `python -m pistol.chat_app` or `uvicorn pistol.chat_app:app`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
