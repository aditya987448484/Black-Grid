"use client";

import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  Tooltip, CartesianGrid, Legend, ReferenceLine,
} from "recharts";
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

export default function PerformanceChart({
  models, selectedIdx = 0,
}: { models: BacktestModelResult[]; selectedIdx?: number }) {
  if (!models.length || !models[0].equityCurve.length) {
    return (
      <div className="glass-card p-5 flex items-center justify-center h-64 text-text-muted text-sm">
        No equity data available
      </div>
    );
  }

  // Find the model with the most data points to use as the date spine
  const spineModel = [...models].sort(
    (a, b) => b.equityCurve.length - a.equityCurve.length,
  )[0];

  // Build a lookup map per model: date -> value
  const lookup = new Map<string, Map<string, number>>();
  models.forEach((m) => {
    const dateMap = new Map<string, number>();
    m.equityCurve.forEach((pt) => dateMap.set(pt.date, pt.value));
    lookup.set(m.customLabel ?? m.modelName, dateMap);
  });

  // Merge on the spine's dates — every model looks up its value for that date
  const merged = spineModel.equityCurve.map((pt) => {
    const row: Record<string, string | number> = { date: pt.date };
    models.forEach((m) => {
      const key = m.customLabel ?? m.modelName;
      row[key] = lookup.get(key)?.get(pt.date) ?? 100;
    });
    return row;
  });

  const tickInterval = Math.max(1, Math.floor(merged.length / 8));

  return (
    <div className="glass-card p-5">
      <h3 className="text-sm font-semibold mb-4">Equity Curves &mdash; All Strategies</h3>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={merged} margin={{ top: 5, right: 10, bottom: 5, left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: "#5a5a6a" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => String(new Date(v).getFullYear())}
            interval={tickInterval}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#5a5a6a" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${(Number(v) - 100).toFixed(0)}%`}
            width={52}
          />
          <ReferenceLine
            y={100}
            stroke="rgba(255,255,255,0.15)"
            strokeDasharray="4 4"
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#12121a",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "8px",
              fontSize: 11,
            }}
            formatter={(v, name) => [`${(Number(v) - 100).toFixed(2)}% return`, String(name)]}
            labelFormatter={(l) => `Date: ${l}`}
          />
          <Legend wrapperStyle={{ fontSize: 11, color: "#8a8a9a" }} />
          {models.map((m, i) => (
            <Line
              key={m.customLabel ?? m.modelName}
              type="monotone"
              dataKey={m.customLabel ?? m.modelName}
              stroke={getColor(m, i)}
              strokeWidth={selectedIdx === i ? 2.5 : 1}
              strokeOpacity={selectedIdx === i ? 1 : 0.3}
              dot={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
