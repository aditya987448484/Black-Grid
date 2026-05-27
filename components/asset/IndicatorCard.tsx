"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { TechnicalIndicator } from "@/types/asset";

export default function IndicatorCard({ indicator }: { indicator: TechnicalIndicator }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      className="glass-card p-4"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-text-secondary">{indicator.name}</span>
        <span
          className={cn(
            "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
            indicator.signal === "bullish" && "bg-success/10 text-success",
            indicator.signal === "bearish" && "bg-danger/10 text-danger",
            indicator.signal === "neutral" && "bg-warning/10 text-warning"
          )}
        >
          {indicator.signal}
        </span>
      </div>
      <p className="text-2xl font-bold">{indicator.value.toFixed(2)}</p>
      <p className="text-xs text-text-muted mt-1">{indicator.description}</p>
    </motion.div>
  );
}
