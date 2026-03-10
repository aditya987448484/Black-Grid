"use client";

import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
} from "recharts";
import type { PortfolioItem } from "@/types/portfolio";

const COLORS = ["#00d4ff", "#8b5cf6", "#22c55e", "#f59e0b", "#ef4444", "#6366f1", "#ec4899"];

export default function AllocationPanel({ items }: { items: PortfolioItem[] }) {
  const data = items.map((i) => ({ name: i.ticker, value: i.allocation }));

  return (
    <div className="glass-card p-5">
      <h3 className="text-sm font-semibold mb-4">Suggested Allocation</h3>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data}
            innerRadius={55}
            outerRadius={85}
            paddingAngle={3}
            dataKey="value"
          >
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: "#12121a",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "8px",
              fontSize: 12,
            }}
            formatter={(v) => [`${v}%`, "Allocation"]}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="flex flex-wrap gap-3 mt-2 justify-center">
        {data.map((d, i) => (
          <div key={d.name} className="flex items-center gap-1.5 text-xs text-text-secondary">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
            {d.name} ({d.value}%)
          </div>
        ))}
      </div>
    </div>
  );
}
