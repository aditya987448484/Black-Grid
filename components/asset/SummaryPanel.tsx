"use client";

import Link from "next/link";
import { FileText } from "lucide-react";

export default function SummaryPanel({ ticker, summary }: { ticker: string; summary: string }) {
  return (
    <div className="glass-card p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-accent" />
          <h3 className="text-sm font-semibold">AI Analyst Summary</h3>
        </div>
        <Link
          href={`/reports/${ticker}`}
          className="text-xs text-accent hover:underline"
        >
          View Full Report
        </Link>
      </div>
      <p className="text-sm text-text-secondary leading-relaxed">{summary}</p>
    </div>
  );
}
