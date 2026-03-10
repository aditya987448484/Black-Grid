"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { StrategyRegistry } from "@/types/backtest";

const CATEGORY_COLORS: Record<string, string> = {
  Trend: "#00d4ff", Oscillator: "#8b5cf6", Volatility: "#22c55e",
  Volume: "#f59e0b", Confluence: "#ec4899", Momentum: "#f97316", Benchmark: "#6b7280",
};

interface Props {
  registry: StrategyRegistry;
  activeKeys: string[];
  onToggle: (key: string) => void;
}

export default function IndicatorBar({ registry, activeKeys, onToggle }: Props) {
  const [activeCat, setActiveCat] = useState("All");
  const categories = ["All", ...Array.from(new Set(Object.values(registry).map(s => s.category)))];
  const filtered = Object.entries(registry).filter(([, e]) => activeCat === "All" || e.category === activeCat);

  return (
    <div className="glass-card px-4 py-3 flex flex-col gap-2">
      <div className="flex items-center gap-1 flex-wrap">
        <span className="text-[10px] text-text-muted uppercase tracking-wider mr-1">Indicators</span>
        {categories.map(cat => (
          <button key={cat} onClick={() => setActiveCat(cat)}
            className={cn("px-2.5 py-1 rounded-full text-[10px] font-semibold transition-all border",
              activeCat === cat ? "bg-accent/15 border-accent/30 text-accent" : "bg-transparent border-white/[0.06] text-text-muted hover:text-text-secondary")}
            style={activeCat === cat && cat !== "All" ? { backgroundColor: `${CATEGORY_COLORS[cat]}18`, borderColor: `${CATEGORY_COLORS[cat]}40`, color: CATEGORY_COLORS[cat] } : undefined}>
            {cat}
          </button>
        ))}
        {activeKeys.length > 0 && <span className="ml-auto text-[10px] text-text-muted">{activeKeys.length} active</span>}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {filtered.map(([key, entry]) => {
          const isActive = activeKeys.includes(key);
          const color = CATEGORY_COLORS[entry.category] ?? "#00d4ff";
          return (
            <button key={key} onClick={() => onToggle(key)} title={entry.description}
              className={cn("px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all border",
                isActive ? "" : "bg-surface border-white/[0.06] text-text-muted hover:text-text-secondary hover:border-white/[0.12]")}
              style={isActive ? { backgroundColor: `${color}18`, borderColor: `${color}50`, color } : undefined}>
              {isActive && <span className="mr-1 text-[9px]">\u2713</span>}{entry.name}
            </button>
          );
        })}
      </div>
    </div>
  );
}
