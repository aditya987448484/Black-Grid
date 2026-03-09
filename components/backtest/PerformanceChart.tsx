"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import type { BacktestModelResult } from "@/types/backtest";

const colors = ["#00d4ff", "#8b5cf6", "#22c55e", "#f59e0b"];

export default function PerformanceChart({ models }: { models: BacktestModelResult[] }) {
  if (!models.length || !models[0].equityCurve.length) {
    return (
      <div className="glass-card p-5 flex items-center justify-center h-64 text-text-muted text-sm">
        No performance data available
      </div>
    );
  }

  const merged = models[0].equityCurve.map((pt, i) => {
    const row: Record<string, string | number> = { date: pt.date };
    models.forEach((m, j) => {
      row[m.modelName] = m.equityCurve[i]?.value ?? 0;
    });
    return row;
  });

  return (
    <div className="glass-card p-5">
      <h3 className="text-sm font-semibold mb-4">Equity Curve Comparison</h3>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={merged} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: "#5a5a6a" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => {
              const d = new Date(v);
              return `${d.getMonth() + 1}/${d.getDate()}`;
            }}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#5a5a6a" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${v.toFixed(0)}%`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#12121a",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "8px",
              fontSize: 12,
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 12, color: "#8a8a9a" }}
          />
          {models.map((m, i) => (
            <Line
              key={m.modelName}
              type="monotone"
              dataKey={m.modelName}
              stroke={colors[i % colors.length]}
              strokeWidth={2}
              dot={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
