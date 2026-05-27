"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getWatchlist } from "@/lib/api";
import type { WatchlistResponse } from "@/types/portfolio";
import PortfolioSummaryCard from "@/components/portfolio/PortfolioSummaryCard";
import PortfolioTable from "@/components/portfolio/PortfolioTable";
import AllocationPanel from "@/components/portfolio/AllocationPanel";

export default function PortfolioPage() {
  const [data, setData] = useState<WatchlistResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getWatchlist()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <h2 className="text-xl font-bold">Portfolio Monitor</h2>
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton h-24 rounded-2xl" />
          ))}
        </div>
        <div className="skeleton h-64 rounded-2xl" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="space-y-6">
        <h2 className="text-xl font-bold">Portfolio Monitor</h2>
        <div className="glass-card p-8 text-center">
          <p className="text-text-secondary">Unable to load portfolio data.</p>
          <p className="text-xs text-text-muted mt-2">Ensure the backend is running.</p>
        </div>
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
      <h2 className="text-xl font-bold">Portfolio Monitor</h2>
      <PortfolioSummaryCard summary={data.summary} />
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2">
          <PortfolioTable items={data.items} />
        </div>
        <AllocationPanel items={data.items} />
      </div>
    </motion.div>
  );
}
