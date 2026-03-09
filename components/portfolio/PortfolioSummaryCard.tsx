"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { DollarSign, TrendingUp, Shield, Zap } from "lucide-react";
import type { PortfolioSummary } from "@/types/portfolio";

export default function PortfolioSummaryCard({ summary }: { summary: PortfolioSummary }) {
  const items = [
    {
      icon: DollarSign,
      label: "Total Value",
      value: `$${summary.totalValue.toLocaleString()}`,
    },
    {
      icon: TrendingUp,
      label: "Daily P&L",
      value: `${summary.dailyChange >= 0 ? "+" : ""}$${summary.dailyChange.toLocaleString()}`,
      color: summary.dailyChange >= 0 ? "text-success" : "text-danger",
    },
    {
      icon: Zap,
      label: "Top Signal",
      value: summary.topSignal,
    },
    {
      icon: Shield,
      label: "Risk Level",
      value: summary.riskLevel.toUpperCase(),
      color: cn(
        summary.riskLevel === "low" && "text-success",
        summary.riskLevel === "medium" && "text-warning",
        summary.riskLevel === "high" && "text-danger"
      ),
    },
  ];

  return (
    <div className="grid grid-cols-4 gap-4">
      {items.map((item, i) => (
        <motion.div
          key={item.label}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          className="glass-card p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <item.icon className="h-4 w-4 text-accent" />
            <span className="text-xs text-text-muted">{item.label}</span>
          </div>
          <p className={cn("text-lg font-bold", item.color)}>{item.value}</p>
        </motion.div>
      ))}
    </div>
  );
}
