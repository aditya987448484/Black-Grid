"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import type { BacktestModelResult } from "@/types/backtest";

const CATEGORY_COLORS: Record<string, string> = {
  Trend: "#00d4ff", Oscillator: "#8b5cf6", Volatility: "#22c55e",
  Volume: "#f59e0b", Confluence: "#ec4899", Momentum: "#f97316", Benchmark: "#6b7280",
};
const CUSTOM_COLORS = ["#a855f7", "#14b8a6", "#f43f5e", "#84cc16", "#06b6d4", "#fb923c"];

function getColor(m: BacktestModelResult, allModels: BacktestModelResult[]): string {
  if (m.isCustom) {
    const idx = allModels.filter(x => x.isCustom).indexOf(m);
    return CUSTOM_COLORS[idx % CUSTOM_COLORS.length];
  }
  return CATEGORY_COLORS[m.category ?? ""] ?? "#00d4ff";
}

interface Props {
  models: BacktestModelResult[];
  selectedIdx?: number;
}

export default function PerformanceChart({ models, selectedIdx = 0 }: Props) {
  const validModels = models.filter(m => m.equityCurve && m.equityCurve.length > 0);

  if (!validModels.length) {
    return (
      <div className="glass-card p-5 flex items-center justify-center h-64 text-text-muted text-sm">
        Run a backtest to see equity curves
      </div>
    );
  }

  // Merge all equity curves by date index, converting to % return from baseline
  const maxLen = Math.max(...validModels.map(m => m.equityCurve.length));
  const merged = Array.from({ length: maxLen }, (_, i) => {
    const row: Record<string, string | number> = {
      date: validModels[0].equityCurve[i]?.date ?? "",
    };
    validModels.forEach(m => {
      const pt = m.equityCurve[i];
      // Store as % return from 100 baseline
      row[m.customLabel ?? m.modelName] = pt ? parseFloat((pt.value - 100).toFixed(2)) : 0;
    });
    return row;
  });

  // Thin data for performance — max 500 points
  const thinned = merged.length > 500
    ? merged.filter((_, i) => i % Math.ceil(merged.length / 500) === 0)
    : merged;

  return (
    <div className="glass-card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold">Equity Curve — % Return</h3>
        <div className="flex flex-wrap gap-2">
          {validModels.map((m, i) => {
            const color = getColor(m, validModels);
            const isSelected = i === selectedIdx;
            return (
              <div key={m.customLabel ?? m.modelName} className="flex items-center gap-1.5">
                <div className="w-6 h-0.5 rounded-full"
                  style={{ background: color, opacity: isSelected ? 1 : 0.4 }} />
                <span className="text-[10px]" style={{ color, opacity: isSelected ? 1 : 0.6 }}>
                  {m.customLabel ?? m.modelName}
                  {" "}
                  <span className="font-bold">
                    {m.cumulativeReturn >= 0 ? "+" : ""}
                    {(m.cumulativeReturn * 100).toFixed(1)}%
                  </span>
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={thinned} margin={{ top: 5, right: 10, bottom: 5, left: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: "#5a5a6a" }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
            tickFormatter={v => {
              if (!v) return "";
              const d = new Date(v);
              return `${d.toLocaleString("default", { month: "short" })} '${String(d.getFullYear()).slice(2)}`;
            }}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#5a5a6a" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={v => `${v >= 0 ? "+" : ""}${v.toFixed(0)}%`}
            width={52}
          />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.1)" strokeDasharray="4 4" />
          <Tooltip
            contentStyle={{
              backgroundColor: "#0d0d14",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "10px",
              fontSize: 12,
              padding: "8px 12px",
            }}
            formatter={(value: number, name: string) => [
              `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`,
              name,
            ]}
            labelFormatter={label => {
              if (!label) return "";
              return new Date(label).toLocaleDateString("en-US", {
                year: "numeric", month: "short", day: "numeric",
              });
            }}
          />
          {validModels.map((m, i) => {
            const key = m.customLabel ?? m.modelName;
            const color = getColor(m, validModels);
            const isSelected = i === selectedIdx;
            return (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={color}
                strokeWidth={isSelected ? 2.5 : 1}
                strokeOpacity={isSelected ? 1 : 0.35}
                dot={false}
                activeDot={{ r: 4, fill: color, stroke: "#0d0d14", strokeWidth: 2 }}
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
