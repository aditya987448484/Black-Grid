"use client";

import { useState } from "react";

// ── Types (mirroring backend AnalystReport schema) ───────────────────────────

interface TechnicalViewpoint {
  trend: string;
  key_levels: number[];
  signal_strength: number;
  momentum: string;
  ma_alignment: string;
  summary: string;
}

interface FundamentalSnapshot {
  eps: number | null;
  revenue_growth: number | null;
  profit_margin: number | null;
  roe: number | null;
  debt_to_equity: number | null;
  valuation_assessment: string;
  quality_score: number;
}

interface MacroContext {
  sector_performance: string;
  industry_tailwinds: string[];
  macro_headwinds: string[];
  correlation_market: number;
  macro_outlook: string;
}

interface InvestmentCase {
  thesis: string;
  key_catalysts: string[];
  timeline: string;
  probability: number;
}

interface RiskCatalyst {
  description: string;
  severity: string;
  mitigation?: string;
}

interface FinalRating {
  recommendation: "BUY" | "HOLD" | "SELL";
  target_price: number;
  price_upside: number;
  conviction: string;
  rationale: string;
}

export interface AnalystReport {
  ticker: string;
  company_name: string;
  report_date: string;
  current_price: number;
  executive_summary: string;
  investment_highlight: string;
  technical_view: TechnicalViewpoint;
  fundamental_snapshot: FundamentalSnapshot;
  macro_context: MacroContext;
  bull_case: InvestmentCase;
  bear_case: InvestmentCase;
  risks: RiskCatalyst[];
  catalysts: RiskCatalyst[];
  final_rating: FinalRating;
  confidence_score: number;
}

interface AnalystWorkspaceProps {
  report: AnalystReport;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function ratingColour(rec: string) {
  if (rec === "BUY") return "text-emerald-400";
  if (rec === "SELL") return "text-red-400";
  return "text-amber-400";
}

function ratingBorder(rec: string) {
  if (rec === "BUY") return "border-emerald-500";
  if (rec === "SELL") return "border-red-500";
  return "border-amber-500";
}

function severityColour(s: string) {
  if (s === "High") return "text-red-400";
  if (s === "Medium") return "text-amber-400";
  return "text-emerald-400";
}

function fmtPrice(v: number | null) {
  return v != null ? `$${v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "N/A";
}

function fmtPct(v: number | null) {
  if (v == null) return "N/A";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(1)}%`;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-[10px] font-semibold uppercase tracking-widest text-gray-500 border-b border-[#1f2937] pb-2 mb-3">
      {children}
    </h3>
  );
}

function MetricCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-lg p-3">
      <div className="text-[9px] uppercase tracking-wider text-gray-500">{label}</div>
      <div className="text-sm font-semibold text-white mt-1">{value}</div>
      {sub && <div className="text-[10px] text-gray-500 mt-0.5">{sub}</div>}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function AnalystWorkspace({ report }: AnalystWorkspaceProps) {
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const r = report;
  const rating = r.final_rating;

  // ── Export handler — POSTs report to backend, triggers browser download ──
  async function handleExport() {
    setExporting(true);
    setExportError(null);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/analyst/export-pdf`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(report),
        }
      );

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail ?? `HTTP ${res.status}`);
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${r.ticker.toUpperCase()}_BlackGrid_Research.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      // I3 — show inline error instead of blocking alert()
      setExportError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="flex flex-col gap-5 text-white">

      {/* ── Header card ── */}
      <div className={`bg-[#0f172a] border ${ratingBorder(rating.recommendation)} border-l-4 rounded-xl p-5 flex items-start justify-between`}>
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">
            {r.ticker.toUpperCase()} · Research Report
          </div>
          <h2 className="text-xl font-bold text-white">{r.company_name}</h2>
          <p className="text-gray-400 text-sm mt-1">{r.executive_summary}</p>
          <p className="text-white font-medium text-sm mt-2">⚡ {r.investment_highlight}</p>
        </div>

        <div className="flex flex-col items-end gap-3 ml-6 shrink-0">
          {/* Rating badge */}
          <div className="text-center bg-[#1e293b] border border-[#334155] rounded-lg px-4 py-3">
            <div className="text-[9px] uppercase tracking-widest text-gray-500">Recommendation</div>
            <div className={`text-2xl font-bold ${ratingColour(rating.recommendation)}`}>
              {rating.recommendation}
            </div>
            <div className="text-xs text-gray-400 mt-0.5">
              Target: {fmtPrice(rating.target_price)} ({fmtPct(rating.price_upside)})
            </div>
            <div className="text-[10px] text-gray-500">
              Conviction: <span className="text-gray-300">{rating.conviction}</span>
            </div>
          </div>

          {/* Export button */}
          <button
            onClick={handleExport}
            disabled={exporting}
            className="flex items-center gap-2 bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors"
          >
            {exporting ? (
              <>
                <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
                Generating…
              </>
            ) : (
              <>
                <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
                </svg>
                Export PDF
              </>
            )}
          </button>

          {/* I3 — inline error replaces blocking alert() */}
          {exportError && (
            <p className="text-[10px] text-red-400 max-w-[160px] text-right leading-tight">
              {exportError}
            </p>
          )}
        </div>
      </div>

      {/* ── Fundamental Snapshot ── */}
      <div>
        <SectionTitle>Fundamental Snapshot</SectionTitle>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <MetricCard label="EPS" value={fmtPrice(r.fundamental_snapshot.eps)} sub="Diluted" />
          <MetricCard label="Revenue Growth" value={fmtPct(r.fundamental_snapshot.revenue_growth)} sub="Year-over-year" />
          <MetricCard label="Profit Margin" value={fmtPct(r.fundamental_snapshot.profit_margin)} />
          <MetricCard label="ROE" value={fmtPct(r.fundamental_snapshot.roe)} sub="Return on equity" />
          <MetricCard label="Debt / Equity" value={r.fundamental_snapshot.debt_to_equity?.toFixed(2) ?? "N/A"} />
          <MetricCard label="Quality Score" value={`${r.fundamental_snapshot.quality_score.toFixed(0)} / 100`} />
          <div className="col-span-2 bg-[#111827] border border-[#1f2937] rounded-lg p-3">
            <div className="text-[9px] uppercase tracking-wider text-gray-500">Valuation</div>
            <div className="text-sm font-semibold text-white mt-1">{r.fundamental_snapshot.valuation_assessment}</div>
          </div>
        </div>
      </div>

      {/* ── Technical View ── */}
      <div>
        <SectionTitle>Technical Analysis</SectionTitle>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <MetricCard label="Trend" value={r.technical_view.trend} />
          <MetricCard label="Signal Strength" value={`${r.technical_view.signal_strength.toFixed(0)} / 100`} />
          <MetricCard label="Momentum" value={r.technical_view.momentum} />
          <MetricCard label="MA Alignment" value={r.technical_view.ma_alignment} />
        </div>
        <p className="text-gray-400 text-sm mt-3">{r.technical_view.summary}</p>
        <p className="text-[11px] text-gray-500 mt-1">
          Key levels: {r.technical_view.key_levels.map(fmtPrice).join(" · ")}
        </p>
      </div>

      {/* ── Macro Context ── */}
      <div>
        <SectionTitle>Macro Context</SectionTitle>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-[10px] font-semibold text-emerald-400 mb-1">Tailwinds</div>
            <ul className="text-xs text-gray-400 space-y-1 list-disc list-inside">
              {r.macro_context.industry_tailwinds.map((t, i) => <li key={i}>{t}</li>)}
            </ul>
          </div>
          <div>
            <div className="text-[10px] font-semibold text-red-400 mb-1">Headwinds</div>
            <ul className="text-xs text-gray-400 space-y-1 list-disc list-inside">
              {r.macro_context.macro_headwinds.map((h, i) => <li key={i}>{h}</li>)}
            </ul>
          </div>
        </div>
        <div className="mt-2 text-[11px] text-gray-500">
          Sector: <span className="text-gray-300">{r.macro_context.sector_performance}</span>
          &nbsp;·&nbsp;Outlook: <span className="text-gray-300">{r.macro_context.macro_outlook}</span>
          &nbsp;·&nbsp;Market corr: <span className="text-gray-300">{r.macro_context.correlation_market.toFixed(2)}</span>
        </div>
      </div>

      {/* ── Bull / Bear Cases ── */}
      <div>
        <SectionTitle>Investment Cases</SectionTitle>
        <div className="grid grid-cols-2 gap-4">
          {/* Bull */}
          <div className="bg-[#0f172a] border border-emerald-900 rounded-lg p-4">
            <div className="text-xs font-semibold text-emerald-400 mb-1">
              ▲ Bull Case ({r.bull_case.probability.toFixed(0)}%)
            </div>
            <p className="text-xs text-gray-400 mb-2">{r.bull_case.thesis}</p>
            <ul className="text-xs text-gray-300 space-y-1 list-disc list-inside">
              {r.bull_case.key_catalysts.map((c, i) => <li key={i}>{c}</li>)}
            </ul>
            <div className="mt-2 h-1.5 bg-[#1e293b] rounded-full">
              <div className="h-1.5 bg-emerald-500 rounded-full" style={{ width: `${r.bull_case.probability}%` }} />
            </div>
            <div className="text-[10px] text-gray-600 mt-1">{r.bull_case.timeline}</div>
          </div>
          {/* Bear */}
          <div className="bg-[#0f172a] border border-red-900 rounded-lg p-4">
            <div className="text-xs font-semibold text-red-400 mb-1">
              ▼ Bear Case ({r.bear_case.probability.toFixed(0)}%)
            </div>
            <p className="text-xs text-gray-400 mb-2">{r.bear_case.thesis}</p>
            <ul className="text-xs text-gray-300 space-y-1 list-disc list-inside">
              {r.bear_case.key_catalysts.map((c, i) => <li key={i}>{c}</li>)}
            </ul>
            <div className="mt-2 h-1.5 bg-[#1e293b] rounded-full">
              <div className="h-1.5 bg-red-500 rounded-full" style={{ width: `${r.bear_case.probability}%` }} />
            </div>
            <div className="text-[10px] text-gray-600 mt-1">{r.bear_case.timeline}</div>
          </div>
        </div>
      </div>

      {/* ── Risk Factors ── */}
      <div>
        <SectionTitle>Risk Factors</SectionTitle>
        <div className="space-y-2">
          {r.risks.map((risk, i) => (
            <div key={i} className="bg-[#111827] border border-[#1f2937] rounded-lg px-4 py-3 flex items-start gap-3">
              <span className={`text-[10px] font-bold uppercase mt-0.5 shrink-0 ${severityColour(risk.severity)}`}>
                {risk.severity}
              </span>
              <div>
                <p className="text-xs text-white">{risk.description}</p>
                {risk.mitigation && (
                  <p className="text-[11px] text-gray-500 mt-0.5">↳ {risk.mitigation}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Catalysts ── */}
      <div>
        <SectionTitle>Near-Term Catalysts</SectionTitle>
        <div className="space-y-2">
          {r.catalysts.map((cat, i) => (
            <div key={i} className="bg-[#111827] border border-[#1f2937] rounded-lg px-4 py-3 flex items-start gap-3">
              <span className={`text-[10px] font-bold uppercase mt-0.5 shrink-0 ${severityColour(cat.severity)}`}>
                {cat.severity}
              </span>
              <div>
                <p className="text-xs text-white">{cat.description}</p>
                {cat.mitigation && (
                  <p className="text-[11px] text-gray-500 mt-0.5">↳ {cat.mitigation}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Final Rating ── */}
      <div className="bg-[#0f172a] border border-[#1e293b] rounded-xl p-5">
        <SectionTitle>Final Rating</SectionTitle>
        <p className="text-sm text-gray-300">{rating.rationale}</p>
        <div className="mt-3 flex items-center gap-3">
          <div className="text-[10px] text-gray-500">Confidence</div>
          <div className="flex-1 h-2 bg-[#1e293b] rounded-full">
            <div
              className="h-2 rounded-full bg-gradient-to-r from-emerald-600 to-emerald-400"
              style={{ width: `${r.confidence_score}%` }}
            />
          </div>
          <div className="text-xs text-gray-300 font-semibold">{r.confidence_score.toFixed(0)}%</div>
        </div>
      </div>

    </div>
  );
}
