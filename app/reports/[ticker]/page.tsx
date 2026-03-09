"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { getReport } from "@/lib/api";
import type { AnalystReportResponse } from "@/types/report";
import ReportHeader from "@/components/report/ReportHeader";
import ReportSection from "@/components/report/ReportSection";

const sectionOrder = [
  { key: "executiveSummary", title: "Executive Summary" },
  { key: "keyHighlights", title: "Key Investment Highlights" },
  { key: "technicalView", title: "Technical View" },
  { key: "fundamentalSnapshot", title: "Fundamental Snapshot" },
  { key: "valuationScenarios", title: "Valuation Scenarios" },
  { key: "macroContext", title: "Macro Context" },
  { key: "competitiveLandscape", title: "Competitive Landscape & Market Positioning" },
  { key: "forecastView", title: "Forecast & Scenario View" },
  { key: "bullCase", title: "Bull Case" },
  { key: "bearCase", title: "Bear Case" },
  { key: "risksCatalysts", title: "Key Risks & Mitigants" },
  { key: "analystConclusion", title: "Analyst Conclusion & Recommendation" },
] as const;

export default function ReportPage() {
  const { ticker } = useParams<{ ticker: string }>();
  const [report, setReport] = useState<AnalystReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    setError(null);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120_000);

    fetch(
      `${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/api/asset/${ticker.toUpperCase()}/report`,
      { signal: controller.signal, cache: "no-store" }
    )
      .then((res) => {
        if (!res.ok) throw new Error(`API ${res.status}`);
        return res.json();
      })
      .then((data) => setReport(data))
      .catch((err) => {
        if (err.name === "AbortError") {
          setError("Report generation timed out. The AI analyst may need more time. Please try again.");
        } else {
          setError(err.message || "Failed to load report.");
        }
      })
      .finally(() => {
        clearTimeout(timeoutId);
        setLoading(false);
      });

    return () => {
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, [ticker]);

  if (loading) {
    return (
      <div className="space-y-4 max-w-4xl">
        <div className="skeleton h-28 rounded-2xl" />
        <div className="glass-card p-6 text-center">
          <div className="inline-flex items-center gap-3">
            <div className="h-4 w-4 rounded-full border-2 border-accent border-t-transparent animate-spin" />
            <span className="text-sm text-text-secondary">
              Generating institutional research report for {ticker?.toUpperCase()}...
            </span>
          </div>
          <p className="text-xs text-text-muted mt-2">
            AI analysis may take up to 60 seconds
          </p>
        </div>
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="skeleton h-32 rounded-2xl" />
        ))}
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="max-w-4xl space-y-4">
        <div className="glass-card p-8 text-center">
          <p className="text-text-secondary">{error || `Unable to generate report for ${ticker?.toUpperCase()}.`}</p>
          <p className="text-xs text-text-muted mt-2">Ensure the backend is running and the AI reasoning provider is configured.</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 text-xs font-medium text-accent border border-accent/20 rounded-lg hover:bg-accent/10 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4 max-w-4xl">
      <ReportHeader
        ticker={report.ticker}
        name={report.name}
        rating={report.rating}
        confidence={report.confidenceScore}
        generatedAt={report.generatedAt}
        sector={report.sector}
        analystName={report.analystName}
      />

      {sectionOrder.map((s, i) => {
        const content = (report as unknown as Record<string, string>)[s.key];
        if (!content) return null;
        return <ReportSection key={s.key} title={s.title} content={content} index={i} />;
      })}

      {/* Final Rating */}
      <div className="glass-card p-5">
        <h3 className="text-sm font-semibold text-accent mb-2">Rating & Confidence</h3>
        <div className="flex items-center gap-4">
          <span className="text-2xl font-bold">{report.rating}</span>
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-muted">Confidence:</span>
            <div className="w-32 h-2 rounded-full bg-surface-hover overflow-hidden">
              <div
                className="h-full rounded-full bg-accent"
                style={{ width: `${(report.confidenceScore || 0) * 100}%` }}
              />
            </div>
            <span className="text-xs font-semibold">{Math.round((report.confidenceScore || 0) * 100)}%</span>
          </div>
        </div>
      </div>

      {/* Disclaimer */}
      {report.disclaimer && (
        <div className="glass-card p-5 opacity-70">
          <h3 className="text-xs font-semibold text-text-muted mb-2 uppercase tracking-wider">
            Important Disclosures
          </h3>
          <p className="text-[11px] text-text-muted leading-relaxed">{report.disclaimer}</p>
        </div>
      )}
    </motion.div>
  );
}
