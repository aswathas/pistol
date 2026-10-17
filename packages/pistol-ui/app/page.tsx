"use client";

import { useEffect, useRef, useState } from "react";
import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import MessageList, { type Message } from "@/components/MessageList";
import Composer from "@/components/Composer";

type ApiResp = {
  reply: string;
  tool_call: { name: string; input: any } | null;
  tool_result: any;
  chart: any;
  source?: string;
};

const STORAGE_KEY = "pistol.chat.history.v1";

export default function Page() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const idCounter = useRef(0);
  const nextId = () => `m-${++idCounter.current}`;

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const saved = JSON.parse(raw) as Message[];
        if (Array.isArray(saved)) setMessages(saved);
      }
    } catch {}
  }, []);

  useEffect(() => {
    if (messages.length) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
      } catch {}
    }
  }, [messages]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, busy]);

  async function send(text: string) {
    const userMsg: Message = { id: nextId(), role: "user", content: text };
    const pendingId = nextId();
    const pendingMsg: Message = {
      id: pendingId,
      role: "assistant",
      content: "",
      pending: true,
    };
    setMessages((m) => [...m, userMsg, pendingMsg]);
    setBusy(true);

    const history = [...messages, userMsg].map((m) => ({ role: m.role, content: m.content }));
    try {
      const r = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history }),
      });
      const data: ApiResp = await r.json();
      setMessages((m) =>
        m.map((x) =>
          x.id === pendingId
            ? {
                id: pendingId,
                role: "assistant",
                content: data.reply ?? "(no response)",
                toolCall: data.tool_call ?? null,
                toolResult: data.tool_result ?? null,
                chart: data.chart ?? null,
                pending: false,
              }
            : x
        )
      );
    } catch (e: any) {
      setMessages((m) =>
        m.map((x) =>
          x.id === pendingId
            ? {
                id: pendingId,
                role: "assistant",
                content: "Network error: " + (e?.message ?? String(e)),
                pending: false,
              }
            : x
        )
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex">
      <Sidebar />
      <main className="flex-1 flex flex-col min-w-0 max-h-screen">
        <TopBar />
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto"
        >
          <div className="max-w-[860px] mx-auto px-6 pt-10 pb-6">
            {messages.length === 0 ? (
              <Empty />
            ) : (
              <MessageList messages={messages} />
            )}
          </div>
        </div>
        <div className="sticky bottom-0 bg-bg/85 backdrop-blur-md border-t border-border">
          <Composer onSend={send} busy={busy} />
        </div>
      </main>
    </div>
  );
}

function Empty() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center">
      <div className="text-[44px] sm:text-[56px] leading-[1.05] tracking-[-0.02em] max-w-[760px]">
        Ask anything about <span className="font-serif italic">Indian stocks.</span>
      </div>
      <div className="mt-4 text-[15px] sm:text-[16px] text-mute max-w-[540px]">
        Free AI agent with <span className="text-ink">53 tools</span>. NSE/BSE quotes, charts, indicators, news, screeners, backtests.
      </div>
      <div className="mt-10 w-full max-w-[640px] grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-left">
        {[
          { t: "Live NSE/BSE data", d: "8,000+ listed companies, real-time quotes, 5y history" },
          { t: "20 technical indicators", d: "RSI, MACD, Bollinger, Ichimoku, Supertrend, ..." },
          { t: "12 candlestick patterns", d: "Hammer, engulfing, doji, three soldiers, ..." },
          { t: "Backtests + screeners", d: "SMA crossover, presets, factor screens" },
        ].map((f) => (
          <div key={f.t} className="bg-panel border border-border rounded-md p-3">
            <div className="text-[13px] font-medium text-ink">{f.t}</div>
            <div className="text-[11.5px] text-mute mt-0.5">{f.d}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
