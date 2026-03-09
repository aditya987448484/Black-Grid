"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getMarketOverview } from "@/lib/api";
import type { MarketOverviewResponse } from "@/types/market";
import MetricCard from "@/components/dashboard/MetricCard";
import SectionCard from "@/components/dashboard/SectionCard";
import SignalList from "@/components/dashboard/SignalList";
import WatchlistTable from "@/components/dashboard/WatchlistTable";
import ReportList from "@/components/dashboard/ReportList";

export default function DashboardPage() {
  const [data, setData] = useState<MarketOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMarketOverview()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <h2 className="text-xl font-bold">Dashboard</h2>
        <div className="grid grid-cols-5 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="skeleton h-32 rounded-2xl" />
          ))}
        </div>
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="skeleton h-64 rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <h2 className="text-xl font-bold">Dashboard</h2>
        <div className="glass-card p-8 text-center">
          <p className="text-text-secondary">Unable to load market data.</p>
          <p className="text-xs text-text-muted mt-2">
            Ensure the backend is running at {process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}
          </p>
          {error && <p className="text-xs text-danger mt-1">{error}</p>}
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      <h2 className="text-xl font-bold">Market Dashboard</h2>

      <div className="grid grid-cols-5 gap-4">
        {data.indices.map((m) => (
          <MetricCard key={m.symbol} metric={m} />
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        <SectionCard title="Top Signals">
          <SignalList signals={data.signals} />
        </SectionCard>

        <SectionCard title="Macro Regime" className="col-span-1">
          <div className="space-y-3">
            {data.macro.map((m) => (
              <div key={m.name} className="flex items-center justify-between">
                <span className="text-xs text-text-secondary">{m.name}</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold">
                    {m.value}
                    {m.unit === "%" ? "%" : ` ${m.unit}`}
                  </span>
                  <span
                    className={`text-xs ${
                      m.trend === "rising"
                        ? "text-success"
                        : m.trend === "falling"
                        ? "text-danger"
                        : "text-warning"
                    }`}
                  >
                    {m.trend}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Recent AI Reports">
          <ReportList reports={data.recentReports} />
        </SectionCard>
      </div>

      <SectionCard title="Watchlist">
        <WatchlistTable items={data.watchlist} />
      </SectionCard>
    </motion.div>
  );
}
