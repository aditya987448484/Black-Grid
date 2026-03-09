"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface Props {
  label: string;
  value: string | number;
  suffix?: string;
  positive?: boolean;
}

export default function BacktestMetricCard({ label, value, suffix, positive }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      className="glass-card p-4"
    >
      <p className="text-xs text-text-muted mb-1">{label}</p>
      <p
        className={cn(
          "text-xl font-bold",
          positive === true && "text-success",
          positive === false && "text-danger"
        )}
      >
        {value}
        {suffix && <span className="text-sm font-medium ml-0.5">{suffix}</span>}
      </p>
    </motion.div>
  );
}
