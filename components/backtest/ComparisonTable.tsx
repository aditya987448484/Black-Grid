"use client";

import { cn } from "@/lib/utils";
import type { BacktestModelResult } from "@/types/backtest";

const CATEGORY_COLORS: Record<string, string> = {
  Trend: "#00d4ff", Oscillator: "#8b5cf6", Volatility: "#22c55e",
  Volume: "#f59e0b", Confluence: "#ec4899", Momentum: "#f97316", Benchmark: "#6b7280",
};
const FALLBACK = ["#00d4ff", "#8b5cf6", "#22c55e", "#f59e0b", "#ec4899", "#f97316", "#06b6d4", "#84cc16"];

function getColor(m: BacktestModelResult, i: number): string {
  if (m.category && CATEGORY_COLORS[m.category]) return CATEGORY_COLORS[m.category];
  return FALLBACK[i % FALLBACK.length];
}

export default function ComparisonTable({ models, selectedIdx = 0 }: { models: BacktestModelResult[]; selectedIdx?: number }) {
  return (
    <div className="glass-card p-5 overflow-x-auto">
      <h3 className="text-sm font-semibold mb-4">Strategy Comparison</h3>
      <table className="w-full text-left text-xs">
        <thead>
          <tr className="text-text-muted">
            {["", "Strategy", "Return", "Win %", "Sharpe", "Calmar", "Max DD", "Vol", "Trades"].map(h => (
              <th key={h} className="pb-2 pr-4 font-medium whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {models.map((m, i) => (
            <tr key={m.modelName + i}
              className={cn("border-b border-border/30 transition-colors",
                selectedIdx === i ? "bg-white/[0.04]" : "hover:bg-surface-hover/50")}>
              <td className="py-2.5 pr-4"><div className="w-2 h-2 rounded-full" style={{ background: getColor(m, i) }} /></td>
              <td className="py-2.5 pr-4 font-semibold whitespace-nowrap">
                {m.isCustom && <span className="text-[9px] text-accent mr-1">\u2726</span>}
                {m.customLabel ?? m.modelName}
              </td>
              <td className={cn("py-2.5 pr-4 font-bold", m.cumulativeReturn >= 0 ? "text-success" : "text-danger")}>
                {m.cumulativeReturn >= 0 ? "+" : ""}{(m.cumulativeReturn * 100).toFixed(1)}%
              </td>
              <td className="py-2.5 pr-4">{(m.winRate * 100).toFixed(1)}%</td>
              <td className={cn("py-2.5 pr-4 font-medium",
                m.sharpeRatio > 1 ? "text-success" : m.sharpeRatio > 0 ? "text-warning" : "text-danger")}>
                {m.sharpeRatio.toFixed(2)}
              </td>
              <td className={cn("py-2.5 pr-4", m.calmarRatio > 1 ? "text-success" : "text-text-secondary")}>{m.calmarRatio.toFixed(2)}</td>
              <td className="py-2.5 pr-4 text-danger">{(m.maxDrawdown * 100).toFixed(1)}%</td>
              <td className="py-2.5 pr-4">{(m.volatility * 100).toFixed(1)}%</td>
              <td className="py-2.5 text-text-secondary">{m.totalTrades}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
