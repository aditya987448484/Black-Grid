"use client";

import { cn } from "@/lib/utils";
import type { BacktestModelResult } from "@/types/backtest";

const COLORS: Record<string, string> = {
  "RSI Mean Reversion":             "#00d4ff",
  "MACD Trend Following":           "#8b5cf6",
  "Bollinger Band Squeeze":         "#22c55e",
  "ATR Volatility Channel":         "#f59e0b",
  "RSI + MACD + Volume Confluence": "#ec4899",
  "Buy & Hold":                     "#6b7280",
};

export default function ComparisonTable({
  models, selectedIdx = 0,
}: { models: BacktestModelResult[]; selectedIdx?: number }) {
  return (
    <div className="glass-card p-5 overflow-x-auto">
      <h3 className="text-sm font-semibold mb-4">Full Strategy Comparison</h3>
      <table className="w-full text-left text-xs">
        <thead>
          <tr className="text-text-muted">
            {["", "Strategy", "Return", "Win %", "Sharpe", "Calmar", "Max DD", "Vol", "Trades"].map(h => (
              <th key={h} className="pb-2 pr-4 font-medium whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {models.map((m, i) => {
            const color = COLORS[m.modelName] ?? "#00d4ff";
            return (
              <tr key={m.modelName}
                className={cn("border-b border-border/30 transition-colors",
                  selectedIdx === i ? "bg-white/[0.04]" : "hover:bg-surface-hover/50")}>
                <td className="py-2.5 pr-4"><div className="w-2 h-2 rounded-full" style={{ background: color }} /></td>
                <td className="py-2.5 pr-4 font-semibold whitespace-nowrap">{m.modelName}</td>
                <td className={cn("py-2.5 pr-4 font-bold", m.cumulativeReturn >= 0 ? "text-success" : "text-danger")}>
                  {m.cumulativeReturn >= 0 ? "+" : ""}{(m.cumulativeReturn * 100).toFixed(1)}%
                </td>
                <td className="py-2.5 pr-4">{(m.winRate * 100).toFixed(1)}%</td>
                <td className={cn("py-2.5 pr-4 font-medium",
                  m.sharpeRatio > 1 ? "text-success" : m.sharpeRatio > 0 ? "text-warning" : "text-danger")}>
                  {m.sharpeRatio.toFixed(2)}
                </td>
                <td className={cn("py-2.5 pr-4", m.calmarRatio > 1 ? "text-success" : "text-text-secondary")}>
                  {m.calmarRatio.toFixed(2)}
                </td>
                <td className="py-2.5 pr-4 text-danger">{(m.maxDrawdown * 100).toFixed(1)}%</td>
                <td className="py-2.5 pr-4">{(m.volatility * 100).toFixed(1)}%</td>
                <td className="py-2.5 text-text-secondary">{m.totalTrades}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
