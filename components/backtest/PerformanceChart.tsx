"use client";

import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  Tooltip, CartesianGrid, Legend, ReferenceLine,
} from "recharts";
import type { BacktestModelResult } from "@/types/backtest";

const COLORS: Record<string, string> = {
  "RSI Mean Reversion":             "#00d4ff",
  "MACD Trend Following":           "#8b5cf6",
  "Bollinger Band Squeeze":         "#22c55e",
  "ATR Volatility Channel":         "#f59e0b",
  "RSI + MACD + Volume Confluence": "#ec4899",
  "Buy & Hold":                     "#6b7280",
};

export default function PerformanceChart({
  models, selectedIdx = 0
}: { models: BacktestModelResult[]; selectedIdx?: number }) {
  if (!models.length || !models[0].equityCurve.length) {
    return (
      <div className="glass-card p-5 flex items-center justify-center h-64 text-text-muted text-sm">
        No equity data available
      </div>
    );
  }

  const merged = models[0].equityCurve.map((pt, i) => {
    const row: Record<string, string | number> = { date: pt.date };
    models.forEach(m => { row[m.modelName] = m.equityCurve[i]?.value ?? 100; });
    return row;
  });

  return (
    <div className="glass-card p-5">
      <h3 className="text-sm font-semibold mb-4">Equity Curves &mdash; All Strategies</h3>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={merged} margin={{ top: 5, right: 10, bottom: 5, left: 15 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#5a5a6a" }} tickLine={false} axisLine={false}
            tickFormatter={v => `${new Date(v).getFullYear()}`} />
          <YAxis tick={{ fontSize: 10, fill: "#5a5a6a" }} tickLine={false} axisLine={false}
            tickFormatter={v => `${(Number(v) - 100).toFixed(0)}%`} />
          <ReferenceLine y={100} stroke="rgba(255,255,255,0.1)" strokeDasharray="4 4" />
          <Tooltip
            contentStyle={{ backgroundColor: "#12121a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", fontSize: 11 }}
            formatter={(v, name) => [`${(Number(v) - 100).toFixed(2)}% return`, String(name)]}
            labelFormatter={l => `Date: ${l}`} />
          <Legend wrapperStyle={{ fontSize: 11, color: "#8a8a9a" }} />
          {models.map((m, i) => (
            <Line key={m.modelName} type="monotone" dataKey={m.modelName}
              stroke={COLORS[m.modelName] ?? "#00d4ff"}
              strokeWidth={selectedIdx === i ? 2.5 : 1}
              strokeOpacity={selectedIdx === i ? 1 : 0.3}
              dot={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
