"use client";

import {
  MessageSquare,
  Filter,
  Eye,
  Briefcase,
  Bell,
  Wrench,
  CreditCard,
} from "lucide-react";
import { useState } from "react";

const NAV = [
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "screener", label: "Screener", icon: Filter },
  { id: "watchlist", label: "Watchlist", icon: Eye },
  { id: "portfolio", label: "Portfolio", icon: Briefcase },
  { id: "alerts", label: "Alerts", icon: Bell },
  { id: "tools", label: "Tools", icon: Wrench },
  { id: "pricing", label: "Pricing", icon: CreditCard },
] as const;

export default function Sidebar({ active = "chat", onSelect }: { active?: string; onSelect?: (id: string) => void }) {
  const [hovered, setHovered] = useState<string | null>(null);
  return (
    <aside className="w-[260px] shrink-0 h-screen sticky top-0 border-r border-border bg-bg flex flex-col">
      <div className="px-5 py-5 flex items-center gap-2.5">
        <div className="w-2.5 h-2.5 rounded-full bg-accent brand-glow" />
        <div className="text-[17px] font-semibold tracking-tight">pistol</div>
        <div className="ml-auto text-[10px] uppercase tracking-wider text-mute">v0.1</div>
      </div>

      <nav className="px-2.5 flex-1 flex flex-col gap-0.5">
        {NAV.map((n) => {
          const Icon = n.icon;
          const isActive = n.id === active;
          const isHover = n.id === hovered;
          return (
            <button
              key={n.id}
              onClick={() => onSelect?.(n.id)}
              onMouseEnter={() => setHovered(n.id)}
              onMouseLeave={() => setHovered(null)}
              className={
                "flex items-center gap-2.5 px-3 py-2 rounded-md text-[13.5px] transition-colors " +
                (isActive
                  ? "bg-panel text-ink font-medium"
                  : isHover
                  ? "bg-panel/60 text-ink/90"
                  : "text-mute hover:text-ink/90")
              }
            >
              <Icon size={15} strokeWidth={1.75} />
              <span>{n.label}</span>
              {n.id !== "chat" && (
                <span className="ml-auto text-[9px] uppercase tracking-wider text-mute/70">soon</span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="m-3 p-3 rounded-md bg-panel border border-border">
        <div className="text-[12px] font-semibold mb-0.5">53 tools, all free</div>
        <div className="text-[10.5px] text-mute leading-relaxed">
          1 dev · MIT · v0.1 demo
          <br />
          Powered by Claude
        </div>
      </div>
    </aside>
  );
}
