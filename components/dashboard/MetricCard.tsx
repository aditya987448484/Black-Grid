"use client";

import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";
import type { MarketMetric } from "@/types/market";

export default function MetricCard({ metric }: { metric: MarketMetric }) {
  const isPositive = metric.change >= 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-4 flex flex-col gap-2"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-text-secondary">{metric.symbol}</span>
        {isPositive ? (
          <TrendingUp className="h-3.5 w-3.5 text-success" />
        ) : (
          <TrendingDown className="h-3.5 w-3.5 text-danger" />
        )}
      </div>
      <p className="text-xl font-semibold">${metric.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "text-xs font-medium",
            isPositive ? "text-success" : "text-danger"
          )}
        >
          {isPositive ? "+" : ""}
          {metric.changePercent.toFixed(2)}%
        </span>
        <span className="text-xs text-text-muted">{metric.name}</span>
      </div>
      {metric.sparkline && metric.sparkline.length > 1 && (
        <div className="mt-1 flex items-end gap-[2px] h-8">
          {metric.sparkline.map((v, i) => {
            const min = Math.min(...metric.sparkline!);
            const max = Math.max(...metric.sparkline!);
            const range = max - min || 1;
            const height = ((v - min) / range) * 100;
            return (
              <div
                key={i}
                className={cn("w-1 rounded-sm", isPositive ? "bg-success/60" : "bg-danger/60")}
                style={{ height: `${Math.max(height, 4)}%` }}
              />
            );
          })}
        </div>
      )}
    </motion.div>
  );
}
