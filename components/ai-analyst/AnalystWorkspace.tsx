"use client";

import { useRef, useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Download, FileText, Printer, TrendingUp, TrendingDown, Shield,
  ArrowUpRight, ArrowDownRight, BarChart3, Target, AlertTriangle, Award,
} from "lucide-react";
import {
  ResponsiveContainer, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";
import { cn } from "@/lib/utils";
import type { AiAnalystResponse, AnalysisPricePoint } from "@/types/ai-analyst";

interface WorkspaceProps { data: AiAnalystResponse | null; loading?: boolean }

const LOGO_API = "https://logo.clearbit.com";
const TICKER_DOMAINS: Record<string, string> = {
  AAPL: "apple.com", MSFT: "microsoft.com", GOOGL: "google.com", AMZN: "amazon.com",
  NVDA: "nvidia.com", TSLA: "tesla.com", META: "meta.com", TSM: "tsmc.com",
  JPM: "jpmorganchase.com", V: "visa.com", JNJ: "jnj.com", WMT: "walmart.com",
  NFLX: "netflix.com", DIS: "disney.com", INTC: "intel.com", AMD: "amd.com",
  CRM: "salesforce.com", BA: "boeing.com", GS: "goldmansachs.com", COST: "costco.com",
  ASML: "asml.com", AVGO: "broadcom.com", ORCL: "oracle.com", ADBE: "adobe.com",
};

const ratingColor: Record<string, string> = {
  "Strong Buy": "#059669", Buy: "#10b981", Hold: "#eab308", Sell: "#ef4444", "Strong Sell": "#dc2626",
};

// ── Company logo ────────────────────────────────────────────────────────────

function Logo({ ticker, name }: { ticker: string; name: string }) {
  const domain = TICKER_DOMAINS[ticker] || `${name.split(" ")[0].toLowerCase().replace(/[^a-z]/g, "")}.com`;
  return (
    <div className="relative w-16 h-16 rounded-2xl overflow-hidden bg-white/10 border border-white/[0.08] flex items-center justify-center flex-shrink-0">
      <img src={`${LOGO_API}/${domain}`} alt="" className="w-full h-full object-contain p-2"
        onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
      <span className="absolute inset-0 flex items-center justify-center text-xl font-bold text-white/60 pointer-events-none select-none">
        {ticker.slice(0, 2)}
      </span>
    </div>
  );
}

// ── Charts ──────────────────────────────────────────────────────────────────

function PricePerformanceChart({ data }: { data: AnalysisPricePoint[] }) {
  if (!data || data.length < 2) return null;
  const isUp = data[data.length - 1].close >= data[0].close;
  const c = isUp ? "#059669" : "#dc2626";
  const pctChange = ((data[data.length - 1].close - data[0].close) / data[0].close * 100).toFixed(1);
  return (
    <div className="bg-gray-50/80 rounded-2xl p-6 border border-gray-100">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-gray-400" />
          <h4 className="text-[11px] font-bold text-gray-500 uppercase tracking-[0.12em]">Price Performance</h4>
        </div>
        <span className={cn("text-xs font-bold px-2.5 py-0.5 rounded-full", isUp ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700")}>
          {isUp ? "+" : ""}{pctChange}%
        </span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
          <defs>
            <linearGradient id="perfGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={c} stopOpacity={0.15} />
              <stop offset="100%" stopColor={c} stopOpacity={0.01} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis dataKey="date" tick={{ fontSize: 9, fill: "#9ca3af" }} tickLine={false} axisLine={false}
            tickFormatter={(v) => new Date(v).toLocaleDateString("en-US", { month: "short" })} />
          <YAxis domain={["auto", "auto"]} tick={{ fontSize: 9, fill: "#9ca3af" }} tickLine={false} axisLine={false}
            tickFormatter={(v) => `$${v}`} />
          <Tooltip contentStyle={{ backgroundColor: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, fontSize: 11, boxShadow: "0 4px 12px rgba(0,0,0,0.08)" }}
            labelFormatter={(v) => new Date(v).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })}
            formatter={(v) => [`$${Number(v).toFixed(2)}`, "Close"]} />
          <Area type="monotone" dataKey="close" stroke={c} fill="url(#perfGrad)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function VolumeChart({ data }: { data: AnalysisPricePoint[] }) {
  if (!data || data.length < 5) return null;
  const recent = data.slice(-30);
  const avg = recent.reduce((s, d) => s + d.volume, 0) / recent.length;
  return (
    <div className="bg-gray-50/80 rounded-2xl p-6 border border-gray-100">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-gray-400" />
          <h4 className="text-[11px] font-bold text-gray-500 uppercase tracking-[0.12em]">30-Day Volume</h4>
        </div>
        <span className="text-[10px] text-gray-400">Avg: {(avg / 1e6).toFixed(1)}M</span>
      </div>
      <ResponsiveContainer width="100%" height={110}>
        <BarChart data={recent} margin={{ top: 2, right: 5, bottom: 2, left: 5 }}>
          <XAxis dataKey="date" tick={false} axisLine={false} tickLine={false} />
          <YAxis tick={false} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={{ backgroundColor: "#fff", border: "1px solid #e5e7eb", borderRadius: 8, fontSize: 10 }}
            labelFormatter={(v) => new Date(v).toLocaleDateString()} formatter={(v) => [`${(Number(v) / 1e6).toFixed(1)}M`, "Vol"]} />
          <Bar dataKey="volume" fill="#818cf8" radius={[3, 3, 0, 0]} opacity={0.65} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Section rendering ───────────────────────────────────────────────────────

const sectionIcons: Record<string, React.ElementType> = {
  executiveSummary: Award,
  keyHighlights: Target,
  bullCase: ArrowUpRight,
  bearCase: ArrowDownRight,
  risksCatalysts: AlertTriangle,
  recommendation: Award,
};

function ProseSection({ title, content, icon }: { title: string; content: string; icon?: React.ElementType }) {
  const Icon = icon || FileText;
  return (
    <div className="mt-9">
      <div className="flex items-center gap-2.5 mb-4">
        <div className="w-7 h-7 rounded-lg bg-gray-900 flex items-center justify-center flex-shrink-0">
          <Icon className="h-3.5 w-3.5 text-white" />
        </div>
        <h2 className="text-[12px] font-extrabold text-gray-800 uppercase tracking-[0.14em]">{title}</h2>
      </div>
      <div className="text-[13.5px] text-gray-700 leading-[1.85] whitespace-pre-line pl-[38px]"
        style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}>
        {content}
      </div>
    </div>
  );
}

function AccentCard({ title, content, color }: { title: string; content: string; color: string }) {
  return (
    <div className="rounded-2xl border overflow-hidden" style={{ borderColor: `${color}22` }}>
      <div className="px-6 py-3" style={{ backgroundColor: `${color}08` }}>
        <h3 className="text-[11px] font-extrabold uppercase tracking-[0.14em]" style={{ color }}>{title}</h3>
      </div>
      <div className="px-6 py-5 bg-white">
        <div className="text-[13px] text-gray-700 leading-[1.85] whitespace-pre-line"
          style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}>
          {content}
        </div>
      </div>
    </div>
  );
}

// ── Main workspace ──────────────────────────────────────────────────────────

const LOADING_PHRASES = [
  "Thinking", "Reviewing the numbers", "Building the thesis",
  "Analyzing fundamentals", "Drafting the report", "Cooking",
];

function WorkspaceLoading() {
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    const i = setInterval(() => setIdx((p) => (p + 1) % LOADING_PHRASES.length), 2200);
    return () => clearInterval(i);
  }, []);
  return (
    <div className="flex flex-col items-center justify-center h-full text-center gap-6">
      <div className="w-16 h-16 rounded-2xl bg-surface-hover/50 flex items-center justify-center">
        <div className="h-6 w-6 rounded-full border-2 border-accent border-t-transparent animate-spin" />
      </div>
      <div>
        <p className="text-sm font-medium text-text-secondary mb-1.5">Generating Research Report</p>
        <p key={idx} className="text-xs text-text-muted animate-fade-in italic">{LOADING_PHRASES[idx]}...</p>
      </div>
    </div>
  );
}

export default function AnalystWorkspace({ data, loading }: WorkspaceProps) {
  const docRef = useRef<HTMLDivElement>(null);

  if (loading && (!data || !data.ticker)) {
    return <WorkspaceLoading />;
  }

  if (!data || !data.ticker) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center gap-5 px-10">
        <div className="w-20 h-20 rounded-2xl bg-surface-hover/50 flex items-center justify-center">
          <FileText className="h-10 w-10 text-text-muted/30" />
        </div>
        <p className="text-sm font-medium text-text-secondary mb-0.5">Research Workspace</p>
        <p className="text-xs text-text-muted max-w-[260px] leading-relaxed">
          Ask the AI Analyst to analyze a company. The institutional research report will render here.
        </p>
      </div>
    );
  }

  const rc = ratingColor[data.rating || "Hold"] || "#eab308";
  const isPos = (data.quote?.change ?? 0) >= 0;
  const now = new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });

  function handleExport() {
    if (!docRef.current) return;
    const w = window.open("", "_blank");
    if (!w) return;
    w.document.write(`<!DOCTYPE html><html><head><title>${data!.ticker} — BlackGrid Research</title>
      <style>*{margin:0;padding:0;box-sizing:border-box}
      body{font-family:Georgia,'Times New Roman',serif;max-width:820px;margin:0 auto;color:#111;line-height:1.8;font-size:13.5px}
      .hdr{background:#0a0a0f;color:#fff;padding:56px 56px 44px}
      .hdr h1{font-size:28px;font-weight:700;font-family:system-ui}
      h2{font-size:11px;text-transform:uppercase;letter-spacing:2px;color:#333;margin:32px 0 12px;font-weight:800}
      .body{padding:44px 56px}
      .card{background:#f9fafb;border:1px solid #f3f4f6;border-radius:12px;padding:24px;margin:20px 0}
      .disc{font-size:9px;color:#999;border-top:1px solid #e5e7eb;padding-top:16px;margin-top:48px}
      @media print{.hdr{-webkit-print-color-adjust:exact;print-color-adjust:exact}}</style></head><body>`);
    w.document.write(docRef.current.innerHTML);
    w.document.write("</body></html>");
    w.document.close();
    setTimeout(() => w.print(), 300);
  }

  const find = (key: string) => data.analysisSections.find((s) => s.key === key);
  const special = new Set(["companyOverview", "financialSnapshot", "valuationAnalysis", "technicalMomentum", "bullCase", "bearCase"]);
  const regular = data.analysisSections.filter((s) => !special.has(s.key));

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border/50 flex-shrink-0">
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <FileText className="h-3.5 w-3.5" />
          <span>{data.ticker} Equity Research</span>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={handleExport} className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary hover:bg-surface-hover rounded-lg transition-colors">
            <Printer className="h-3.5 w-3.5" /> Print
          </button>
          <button onClick={handleExport} className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-accent hover:bg-accent/10 rounded-lg transition-colors">
            <Download className="h-3.5 w-3.5" /> Export
          </button>
        </div>
      </div>

      {/* Document */}
      <div className="flex-1 overflow-y-auto bg-[#131316] p-4 md:p-6">
        <motion.div ref={docRef} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
          className="max-w-3xl mx-auto rounded-2xl overflow-hidden shadow-2xl shadow-black/50">

          {/* ═══════════════ BLACK LUXURY HEADER ═══════════════ */}
          <div className="relative bg-[#08080c] px-12 pt-14 pb-12"
            style={{ backgroundImage: "radial-gradient(ellipse at 15% 80%, rgba(99,102,241,0.07) 0%, transparent 55%), radial-gradient(ellipse at 85% 15%, rgba(0,212,255,0.05) 0%, transparent 55%)" }}>
            {/* Grain texture */}
            <div className="absolute inset-0 opacity-[0.025]" style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
            }} />
            {/* Subtle border line at top */}
            <div className="absolute top-0 left-12 right-12 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

            <div className="relative flex items-start gap-6">
              <Logo ticker={data.ticker} name={data.companyName || data.ticker} />
              <div className="flex-1 min-w-0">
                <p className="text-[10px] text-gray-500 uppercase tracking-[0.2em] font-medium mb-2">Equity Research Report</p>
                <h1 className="text-[26px] font-bold text-white tracking-tight leading-tight" style={{ fontFamily: "system-ui, -apple-system, sans-serif" }}>
                  {data.companyName}
                </h1>
                <p className="text-[13px] text-gray-400 mt-2 flex items-center gap-2">
                  <span className="font-semibold text-gray-300">{data.ticker}</span>
                  <span className="w-1 h-1 rounded-full bg-gray-600" />
                  <span>{data.sector || "Equity"}</span>
                  <span className="w-1 h-1 rounded-full bg-gray-600" />
                  <span>{now}</span>
                </p>
              </div>
            </div>

            {/* Key metrics strip */}
            <div className="relative flex items-center gap-6 mt-8 pt-7 border-t border-white/[0.06]">
              {data.rating && (
                <div>
                  <p className="text-[9px] text-gray-600 uppercase tracking-widest font-medium mb-1.5">Rating</p>
                  <span className="inline-block px-5 py-1.5 rounded-lg text-[11px] font-extrabold text-white tracking-wide"
                    style={{ backgroundColor: rc }}>{data.rating.toUpperCase()}</span>
                </div>
              )}
              {data.quote && (
                <div>
                  <p className="text-[9px] text-gray-600 uppercase tracking-widest font-medium mb-1.5">Price</p>
                  <div className="flex items-center gap-2">
                    <span className="text-2xl font-bold text-white">${data.quote.price.toFixed(2)}</span>
                    <span className={cn("flex items-center gap-0.5 text-xs font-semibold", isPos ? "text-emerald-400" : "text-red-400")}>
                      {isPos ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                      {isPos ? "+" : ""}{data.quote.changePercent.toFixed(2)}%
                    </span>
                  </div>
                </div>
              )}
              {data.confidenceScore != null && (
                <div className="flex-1">
                  <p className="text-[9px] text-gray-600 uppercase tracking-widest font-medium mb-1.5">Confidence</p>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 rounded-full bg-white/[0.08] overflow-hidden">
                      <div className="h-full rounded-full transition-all" style={{ width: `${data.confidenceScore * 100}%`, backgroundColor: rc }} />
                    </div>
                    <span className="text-sm font-bold text-white">{Math.round(data.confidenceScore * 100)}%</span>
                  </div>
                </div>
              )}
            </div>

            <p className="relative text-[9px] text-gray-700 mt-6 tracking-wide">BLACKGRID RESEARCH &middot; AI-GENERATED</p>
          </div>

          {/* ═══════════════ WHITE DOCUMENT BODY ═══════════════ */}
          <div className="bg-white px-12 py-10" style={{ color: "#1f2937" }}>

            {/* Company overview lead paragraph */}
            {find("companyOverview") && (
              <div className="mb-8 pb-8 border-b border-gray-200">
                <p className="text-[15px] text-gray-600 leading-[1.9] first-letter:text-4xl first-letter:font-bold first-letter:text-gray-900 first-letter:float-left first-letter:mr-2 first-letter:mt-1"
                  style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}>
                  {find("companyOverview")!.content}
                </p>
              </div>
            )}

            {/* Charts row */}
            {data.chart.length > 0 && (
              <div className="grid grid-cols-1 gap-4 mb-8">
                <PricePerformanceChart data={data.chart} />
                <VolumeChart data={data.chart} />
              </div>
            )}

            {/* Financial Snapshot + Valuation as accent cards */}
            {(find("financialSnapshot") || find("valuationAnalysis")) && (
              <div className="grid grid-cols-1 gap-4 mb-6">
                {find("financialSnapshot") && <AccentCard title="Financial Snapshot" content={find("financialSnapshot")!.content} color="#6366f1" />}
                {find("valuationAnalysis") && <AccentCard title="Valuation Analysis" content={find("valuationAnalysis")!.content} color="#0891b2" />}
              </div>
            )}

            {/* Technical Momentum */}
            {find("technicalMomentum") && (
              <ProseSection title="Technical Momentum" content={find("technicalMomentum")!.content} icon={BarChart3} />
            )}

            {/* Bull / Bear side by side */}
            {(find("bullCase") || find("bearCase")) && (
              <div className="grid grid-cols-2 gap-4 mt-9">
                {find("bullCase") && <AccentCard title="Bull Case" content={find("bullCase")!.content} color="#059669" />}
                {find("bearCase") && <AccentCard title="Bear Case" content={find("bearCase")!.content} color="#dc2626" />}
              </div>
            )}

            {/* Regular sections */}
            {regular.map((s) => (
              <ProseSection key={s.key} title={s.title} content={s.content} icon={sectionIcons[s.key]} />
            ))}

            {/* Disclaimer */}
            {data.disclaimer && (
              <div className="mt-14 pt-6 border-t border-gray-200">
                <p className="text-[9px] text-gray-400 uppercase tracking-[0.2em] font-bold mb-2">Important Disclosures</p>
                <p className="text-[10px] text-gray-400 leading-relaxed">{data.disclaimer}</p>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
