"use client";

import { cn } from "@/lib/utils";
import type { BacktestModelResult } from "@/types/backtest";

const CATEGORY_COLORS: Record<string, string> = {
  "Trend": "#00d4ff", "Oscillator": "#8b5cf6", "Volatility": "#22c55e",
  "Volume": "#f59e0b", "Confluence": "#ec4899", "Momentum": "#f97316", "Benchmark": "#6b7280",
};
const CUSTOM_COLORS = ["#a855f7", "#14b8a6", "#f43f5e", "#84cc16", "#06b6d4", "#fb923c"];

function getModelColor(model: BacktestModelResult, _idx: number, allModels: BacktestModelResult[]): string {
  if (model.isCustom) {
    const customIdx = allModels.filter(m => m.isCustom).indexOf(model);
    return CUSTOM_COLORS[customIdx % CUSTOM_COLORS.length];
  }
  return CATEGORY_COLORS[model.category ?? ""] ?? "#00d4ff";
}

export default function ComparisonTable({ models, selectedIdx }: { models: BacktestModelResult[]; selectedIdx?: number }) {
  return (
    <div className="glass-card p-5 overflow-x-auto">
      <h3 className="text-sm font-semibold mb-4">Strategy Comparison</h3>
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-border text-xs text-text-muted">
            <th className="pb-2 font-medium">Strategy</th>
            <th className="pb-2 font-medium">Category</th>
            <th className="pb-2 font-medium">Cum. Return</th>
            <th className="pb-2 font-medium">Win Rate</th>
            <th className="pb-2 font-medium">Sharpe</th>
            <th className="pb-2 font-medium">Calmar</th>
            <th className="pb-2 font-medium">Max DD</th>
            <th className="pb-2 font-medium">Trades</th>
          </tr>
        </thead>
        <tbody>
          {models.map((m, i) => {
            const color = getModelColor(m, i, models);
            const isSelected = selectedIdx !== undefined && selectedIdx === i;
            return (
              <tr key={(m.customLabel ?? m.modelName) + i}
                className={cn("border-b border-border/50 transition-colors",
                  isSelected ? "bg-white/[0.03]" : "hover:bg-white/[0.02]")}>
                <td className="py-2.5 font-semibold text-text-primary">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: color }} />
                    {m.isCustom && <span className="text-[9px] text-accent">✦</span>}
                    {m.customLabel ?? m.modelName}
                  </div>
                </td>
                <td className="py-2.5 text-xs text-text-muted">{m.category ?? "—"}</td>
                <td className={cn("py-2.5 font-medium", m.cumulativeReturn >= 0 ? "text-success" : "text-danger")}>
                  {m.cumulativeReturn >= 0 ? "+" : ""}{(m.cumulativeReturn * 100).toFixed(1)}%
                </td>
                <td className="py-2.5">{(m.winRate * 100).toFixed(1)}%</td>
                <td className={cn("py-2.5 font-medium", m.sharpeRatio > 1 ? "text-success" : "")}>
                  {m.sharpeRatio.toFixed(2)}
                </td>
                <td className="py-2.5">{m.calmarRatio?.toFixed(2) ?? "—"}</td>
                <td className="py-2.5 text-danger">{(m.maxDrawdown * 100).toFixed(1)}%</td>
                <td className="py-2.5">{m.totalTrades ?? "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
