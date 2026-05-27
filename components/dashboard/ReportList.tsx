"use client";

import Link from "next/link";
import type { ReportSummary } from "@/types/market";

export default function ReportList({ reports }: { reports: ReportSummary[] }) {
  if (!reports.length) {
    return <p className="text-sm text-text-muted">No recent reports.</p>;
  }

  return (
    <div className="space-y-3">
      {reports.map((r) => (
        <Link
          key={r.ticker}
          href={`/reports/${r.ticker}`}
          className="block rounded-lg px-3 py-2.5 transition-colors hover:bg-surface-hover"
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-semibold text-text-primary">{r.ticker}</span>
            <span className="text-xs text-accent font-medium">{r.rating}</span>
          </div>
          <p className="text-xs text-text-secondary line-clamp-2">{r.summary}</p>
        </Link>
      ))}
    </div>
  );
}
