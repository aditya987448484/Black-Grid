"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown } from "lucide-react";
import type { AssetDetail } from "@/types/asset";

export default function AssetHeader({ asset }: { asset: AssetDetail }) {
  const isPositive = asset.change >= 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center justify-between"
    >
      <div>
        <div className="flex items-center gap-3 mb-1">
          <h1 className="text-2xl font-bold">{asset.ticker}</h1>
          <span className={cn(
            "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
            asset.signal === "bullish" && "bg-success/10 text-success",
            asset.signal === "bearish" && "bg-danger/10 text-danger",
            asset.signal === "neutral" && "bg-warning/10 text-warning"
          )}>
            {asset.signal.toUpperCase()}
          </span>
        </div>
        <p className="text-sm text-text-secondary">{asset.name} &middot; {asset.sector}</p>
      </div>
      <div className="text-right">
        <p className="text-3xl font-bold">${asset.price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</p>
        <div className="flex items-center justify-end gap-2 mt-1">
          {isPositive ? (
            <TrendingUp className="h-4 w-4 text-success" />
          ) : (
            <TrendingDown className="h-4 w-4 text-danger" />
          )}
          <span className={cn("text-sm font-medium", isPositive ? "text-success" : "text-danger")}>
            {isPositive ? "+" : ""}{asset.change.toFixed(2)} ({isPositive ? "+" : ""}{asset.changePercent.toFixed(2)}%)
          </span>
        </div>
      </div>
    </motion.div>
  );
}
