"use client";

import { useState } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { cn } from "@/lib/utils";
import type { PricePoint } from "@/types/asset";

const timeframes = ["1W", "1M", "3M", "6M", "1Y", "ALL"] as const;

export default function ChartPanel({ data }: { data: PricePoint[] }) {
  const [tf, setTf] = useState<(typeof timeframes)[number]>("3M");

  const filtered = filterByTimeframe(data, tf);
  const isUp = filtered.length >= 2 && filtered[filtered.length - 1].close >= filtered[0].close;

  return (
    <div className="glass-card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold">Price Chart</h3>
        <div className="flex gap-1">
          {timeframes.map((t) => (
            <button
              key={t}
              onClick={() => setTf(t)}
              className={cn(
                "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                tf === t
                  ? "bg-accent/20 text-accent"
                  : "text-text-muted hover:text-text-secondary"
              )}
            >
              {t}
            </button>
          ))}
        </div>
      </div>
      {filtered.length === 0 ? (
        <div className="flex items-center justify-center h-64 text-text-muted text-sm">
          No chart data available
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={320}>
          <AreaChart data={filtered} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
            <defs>
              <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={isUp ? "#22c55e" : "#ef4444"} stopOpacity={0.3} />
                <stop offset="100%" stopColor={isUp ? "#22c55e" : "#ef4444"} stopOpacity={0} />
              </linearGradient>
            </defs>
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
              domain={["auto", "auto"]}
              tick={{ fontSize: 10, fill: "#5a5a6a" }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `$${v}`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#12121a",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
                fontSize: 12,
              }}
              labelFormatter={(v) => new Date(v).toLocaleDateString()}
              formatter={(v) => [`$${Number(v).toFixed(2)}`, "Close"]}
            />
            <Area
              type="monotone"
              dataKey="close"
              stroke={isUp ? "#22c55e" : "#ef4444"}
              fill="url(#chartGrad)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function filterByTimeframe(data: PricePoint[], tf: string): PricePoint[] {
  if (!data.length) return [];
  const now = new Date(data[data.length - 1].date);
  const days: Record<string, number> = {
    "1W": 7,
    "1M": 30,
    "3M": 90,
    "6M": 180,
    "1Y": 365,
    ALL: 9999,
  };
  const cutoff = new Date(now);
  cutoff.setDate(cutoff.getDate() - (days[tf] || 90));
  return data.filter((p) => new Date(p.date) >= cutoff);
}
