"use client";

import { Sparkles } from "lucide-react";
import PlotlyChart from "./PlotlyChart";

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCall?: { name: string; input: any } | null;
  toolResult?: any;
  chart?: any;
  pending?: boolean;
};

function escape(s: string) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderInline(s: string): string {
  return escape(s)
    .replace(/`([^`]+)`/g, '<code class="px-1 py-0.5 rounded bg-panel-2 text-[12.5px] font-mono text-ink/90">$1</code>')
    .replace(/\*\*([^*\n]+)\*\*/g, '<strong class="text-ink font-medium">$1</strong>')
    .replace(/^\s*[-*]\s+(.+)$/gm, '<li class="ml-4 list-disc text-ink/85">$1</li>')
    .replace(/\n\n+/g, '</p><p class="mt-2.5">')
    .replace(/\n/g, "<br/>")
    .replace(/^(?!<[puol])/gm, "")
    .replace(/^/, "<p>")
    .replace(/$/, "</p>");
}

function tableRender(text: string): string {
  // Convert pipe tables to <table>
  const lines = text.split("\n");
  const i = lines.findIndex((l) => /^\s*\|/.test(l) && /^\s*\|[\s\-:|]+\|/.test(lines[i + 1] || ""));
  if (i < 0) return text;
  const header = lines[i].split("|").slice(1, -1).map((c) => c.trim());
  const body = lines.slice(i + 2).filter((l) => /^\s*\|/.test(l));
  const rows = body.map((l) =>
    l.split("|").slice(1, -1).map((c) => c.trim())
  );
  let html = '<table class="w-full my-3 text-[12.5px] border-collapse prose-tables">';
  html += "<thead><tr>";
  header.forEach((h) => (html += `<th>${escape(h)}</th>`));
  html += "</tr></thead><tbody>";
  rows.forEach((r) => {
    html += "<tr>";
    r.forEach((c) => (html += `<td>${escape(c)}</td>`));
    html += "</tr>";
  });
  html += "</tbody></table>";
  // Replace original lines with rendered table
  const before = lines.slice(0, i).join("\n");
  const after = lines.slice(i + 2 + body.length).join("\n");
  return before + "\n" + html + "\n" + after;
}

export default function MessageList({ messages }: { messages: Message[] }) {
  if (messages.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center px-6 py-16">
        <div className="text-[44px] leading-[1.05] tracking-[-0.02em] text-center max-w-[680px]">
          Ask anything about <span className="font-serif italic">Indian stocks.</span>
        </div>
        <div className="mt-3 text-[15px] text-mute text-center max-w-[540px]">
          Free AI agent with 53 tools. NSE/BSE quotes, charts, indicators, news, screeners, backtests.
        </div>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-7">
      {messages.map((m) => (
        <Bubble key={m.id} m={m} />
      ))}
    </div>
  );
}

function Bubble({ m }: { m: Message }) {
  if (m.role === "user") {
    return (
      <div className="flex justify-end anim-fade">
        <div className="max-w-[78%] bg-accent/15 border border-accent/30 text-ink rounded-2xl px-4 py-2.5 text-[14.5px] leading-relaxed">
          {m.content}
        </div>
      </div>
    );
  }
  const stats = pickStats(m.toolResult);
  return (
    <div className="flex gap-3 anim-fade">
      <div className="w-7 h-7 shrink-0 rounded-md bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center text-white text-[11px] font-bold shadow-glow">
        P
      </div>
      <div className="flex-1 min-w-0">
        {m.toolCall && (
          <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-panel border border-border text-[11px] font-mono text-mute mb-2.5">
            <Sparkles size={11} className="text-accent" />
            <span className="text-ink/80">{m.toolCall.name}</span>
            <span className="text-mute/70">({summarizeArgs(m.toolCall.input)})</span>
          </div>
        )}
        {m.pending && !m.content ? (
          <div className="flex items-center gap-1.5 py-2.5">
            <span className="typing-dot w-1.5 h-1.5 rounded-full bg-mute" />
            <span className="typing-dot w-1.5 h-1.5 rounded-full bg-mute" />
            <span className="typing-dot w-1.5 h-1.5 rounded-full bg-mute" />
          </div>
        ) : (
          <div
            className="text-[14.5px] leading-[1.7] text-ink/90 prose-tables"
            dangerouslySetInnerHTML={{ __html: renderInline(tableRender(m.content)) }}
          />
        )}
        {stats && (
          <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2">
            {stats.map((s) => (
              <div key={s.k} className="bg-panel border border-border rounded-md px-3 py-2">
                <div className="text-[10.5px] uppercase tracking-wider text-mute">{s.k}</div>
                <div className={"text-[14.5px] font-medium mt-0.5 " + s.cls}>{s.v}</div>
              </div>
            ))}
          </div>
        )}
        {m.chart && (
          <div className="mt-3 bg-panel border border-border rounded-lg p-1.5">
            <PlotlyChart spec={m.chart} />
          </div>
        )}
      </div>
    </div>
  );
}

function summarizeArgs(input: any): string {
  try {
    const s = JSON.stringify(input);
    return s.length > 60 ? s.slice(0, 57) + "..." : s;
  } catch {
    return "{}";
  }
}

function pickStats(r: any): Array<{ k: string; v: string; cls: string }> | null {
  if (!r) return null;
  const out: Array<{ k: string; v: string; cls: string }> = [];
  if (typeof r.ltp === "number") {
    const sign = r.change >= 0 ? "+" : "";
    out.push({ k: "LTP", v: r.ltp.toFixed(2), cls: r.change >= 0 ? "text-good" : "text-bad" });
  }
  if (r.indicator === "rsi" && r.latest) {
    const v = r.latest.value;
    const cls = v >= 70 ? "text-bad" : v <= 30 ? "text-good" : "text-ink";
    out.push({ k: `RSI(${r.period})`, v: String(v), cls });
    if (r.latest.date) out.push({ k: "As of", v: r.latest.date, cls: "text-ink/80" });
  }
  if (r.symbol) out.push({ k: "Symbol", v: r.symbol, cls: "text-ink/80" });
  if (typeof r.value === "number") out.push({ k: "Value", v: String(r.value), cls: "text-ink" });
  return out.length ? out : null;
}
