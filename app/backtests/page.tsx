"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getBacktestSummary } from "@/lib/api";
import type { BacktestSummaryResponse } from "@/types/backtest";
import BacktestMetricCard from "@/components/backtest/BacktestMetricCard";
import PerformanceChart from "@/components/backtest/PerformanceChart";
import ComparisonTable from "@/components/backtest/ComparisonTable";
import StrategyNotes from "@/components/backtest/StrategyNotes";

export default function BacktestPage() {
  const [data, setData] = useState<BacktestSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getBacktestSummary()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <h2 className="text-xl font-bold">Backtest Lab</h2>
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton h-24 rounded-2xl" />
          ))}
        </div>
        <div className="skeleton h-80 rounded-2xl" />
      </div>
    );
  }

  if (!data || !data.models.length) {
    return (
      <div className="space-y-6">
        <h2 className="text-xl font-bold">Backtest Lab</h2>
        <div className="glass-card p-8 text-center">
          <p className="text-text-secondary">No backtest results available.</p>
          <p className="text-xs text-text-muted mt-2">Ensure the backend is running.</p>
        </div>
      </div>
    );
  }

  const best = data.models[0];

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">Backtest Lab</h2>
        <span className="text-xs text-text-muted">
          {data.ticker} &middot; {data.period}
        </span>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <BacktestMetricCard
          label="Direction Accuracy"
          value={`${(best.accuracy * 100).toFixed(1)}%`}
          positive={best.accuracy > 0.5}
        />
        <BacktestMetricCard
          label="Cumulative Return"
          value={`${(best.cumulativeReturn * 100).toFixed(1)}%`}
          positive={best.cumulativeReturn > 0}
        />
        <BacktestMetricCard
          label="Sharpe Ratio"
          value={best.sharpeRatio.toFixed(2)}
          positive={best.sharpeRatio > 0}
        />
        <BacktestMetricCard
          label="Max Drawdown"
          value={`${(best.maxDrawdown * 100).toFixed(1)}%`}
          positive={false}
        />
      </div>

      <PerformanceChart models={data.models} />
      <ComparisonTable models={data.models} />
      <StrategyNotes models={data.models} />
    </motion.div>
  );
}
