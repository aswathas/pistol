"use client";

import { ArrowUp, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

const EXAMPLES = [
  "RELIANCE 14-day RSI with a chart",
  "TCS 6-month price chart",
  "INFY overbought right now?",
  "HDFC vs ICICI peer comparison",
  "Top 5 gainers in Nifty 50 today",
];

export default function Composer({
  onSend,
  busy,
}: {
  onSend: (text: string) => void;
  busy: boolean;
}) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const t = ref.current;
    if (!t) return;
    t.style.height = "auto";
    t.style.height = Math.min(t.scrollHeight, 180) + "px";
  }, [text]);

  const submit = () => {
    const v = text.trim();
    if (!v || busy) return;
    onSend(v);
    setText("");
  };

  return (
    <>
      <div className="px-6 pb-2 pt-1 flex flex-wrap gap-1.5 justify-center max-w-[860px] mx-auto">
        {EXAMPLES.map((q) => (
          <button
            key={q}
            onClick={() => onSend(q)}
            className="px-3 py-1.5 rounded-full border border-border bg-transparent text-mute text-[12px] hover:border-accent hover:text-ink transition-colors"
          >
            {q}
          </button>
        ))}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="px-6 pb-5 pt-1"
      >
        <div className="max-w-[860px] mx-auto flex items-end gap-2 bg-panel border border-border rounded-[14px] p-2.5 focus-within:border-accent transition-colors">
          <textarea
            ref={ref}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            rows={1}
            placeholder="Ask about an Indian stock, indicator, or the market…"
            className="flex-1 bg-transparent text-ink placeholder:text-mute/80 text-[14.5px] leading-[1.55] outline-none resize-none max-h-[180px] px-1.5 py-1"
            disabled={busy}
            aria-label="Message"
          />
          <button
            type="submit"
            disabled={!text.trim() || busy}
            className="shrink-0 w-9 h-9 rounded-[10px] bg-gradient-to-br from-accent to-accent-2 text-white flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed hover:shadow-glow transition-shadow"
            aria-label="Send"
          >
            {busy ? <Loader2 size={16} className="animate-spin" /> : <ArrowUp size={16} strokeWidth={2.5} />}
          </button>
        </div>
      </form>
    </>
  );
}
