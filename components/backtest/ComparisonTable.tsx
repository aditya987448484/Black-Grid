"use client";

import { cn } from "@/lib/utils";
import type { BacktestModelResult } from "@/types/backtest";

export default function ComparisonTable({ models }: { models: BacktestModelResult[] }) {
  return (
    <div className="glass-card p-5 overflow-x-auto">
      <h3 className="text-sm font-semibold mb-4">Model Comparison</h3>
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-border text-xs text-text-muted">
            <th className="pb-2 font-medium">Model</th>
            <th className="pb-2 font-medium">Accuracy</th>
            <th className="pb-2 font-medium">Cum. Return</th>
            <th className="pb-2 font-medium">Win Rate</th>
            <th className="pb-2 font-medium">Sharpe</th>
            <th className="pb-2 font-medium">Max DD</th>
            <th className="pb-2 font-medium">Volatility</th>
          </tr>
        </thead>
        <tbody>
          {models.map((m) => (
            <tr key={m.modelName} className="border-b border-border/50">
              <td className="py-2.5 font-semibold text-text-primary">{m.modelName}</td>
              <td className="py-2.5">{(m.accuracy * 100).toFixed(1)}%</td>
              <td className={cn("py-2.5 font-medium", m.cumulativeReturn >= 0 ? "text-success" : "text-danger")}>
                {m.cumulativeReturn >= 0 ? "+" : ""}{(m.cumulativeReturn * 100).toFixed(1)}%
              </td>
              <td className="py-2.5">{(m.winRate * 100).toFixed(1)}%</td>
              <td className="py-2.5">{m.sharpeRatio.toFixed(2)}</td>
              <td className="py-2.5 text-danger">{(m.maxDrawdown * 100).toFixed(1)}%</td>
              <td className="py-2.5">{(m.volatility * 100).toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
