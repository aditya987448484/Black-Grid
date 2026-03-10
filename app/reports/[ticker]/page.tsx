"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  Download, FileText, Printer, TrendingUp, TrendingDown,
  BarChart3, Target, AlertTriangle, Award, ArrowUpRight, ArrowDownRight,
  Building2, Calendar, User,
} from "lucide-react";
import {
  ResponsiveContainer, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";
import { cn } from "@/lib/utils";
import type { AnalystReportResponse, ReportPricePoint } from "@/types/report";

const LOGO_API = "https://logo.clearbit.com";
const TICKER_DOMAINS: Record<string, string> = {
  AAPL: "apple.com", MSFT: "microsoft.com", GOOGL: "google.com", GOOG: "google.com",
  AMZN: "amazon.com", NVDA: "nvidia.com", TSLA: "tesla.com", META: "meta.com",
  TSM: "tsmc.com", JPM: "jpmorganchase.com", V: "visa.com", JNJ: "jnj.com",
  WMT: "walmart.com", NFLX: "netflix.com", DIS: "disney.com", INTC: "intel.com",
  AMD: "amd.com", CRM: "salesforce.com", BA: "boeing.com", GS: "goldmansachs.com",
  COST: "costco.com", ASML: "asml.com", AVGO: "broadcom.com", ORCL: "oracle.com",
  ADBE: "adobe.com", PLTR: "palantir.com", CRWD: "crowdstrike.com", DDOG: "datadoghq.com",
  NET: "cloudflare.com", ZS: "zscaler.com", PANW: "paloaltonetworks.com", SNOW: "snowflake.com",
  SHOP: "shopify.com", SQ: "block.xyz", COIN: "coinbase.com", UBER: "uber.com",
  ABNB: "airbnb.com", PYPL: "paypal.com", NOW: "servicenow.com", INTU: "intuit.com",
  MA: "mastercard.com", BAC: "bankofamerica.com", WFC: "wellsfargo.com", MS: "morganstanley.com",
  BLK: "blackrock.com", SCHW: "schwab.com", UNH: "unitedhealthgroup.com", LLY: "lilly.com",
  PFE: "pfizer.com", MRK: "merck.com", ABT: "abbott.com", ABBV: "abbvie.com",
  PG: "pg.com", KO: "coca-colacompany.com", PEP: "pepsico.com", MCD: "mcdonalds.com",
  SBUX: "starbucks.com", NKE: "nike.com", HD: "homedepot.com", LOW: "lowes.com",
  XOM: "exxonmobil.com", CVX: "chevron.com", CAT: "caterpillar.com", DE: "deere.com",
  LMT: "lockheedmartin.com", GE: "ge.com", HON: "honeywell.com", UPS: "ups.com",
  FDX: "fedex.com", T: "att.com", VZ: "verizon.com", TMUS: "t-mobile.com",
  MRNA: "modernatx.com", GILD: "gilead.com", AMGN: "amgen.com", BIIB: "biogen.com",
  HOOD: "robinhood.com", SOFI: "sofi.com", RIVN: "rivian.com", LCID: "lucidmotors.com",
  SMCI: "supermicro.com", ARM: "arm.com", DASH: "doordash.com", RBLX: "roblox.com",
  SNAP: "snap.com", PINS: "pinterest.com", ROKU: "roku.com", ETSY: "etsy.com",
  GME: "gamestop.com", F: "ford.com", GM: "gm.com", DAL: "delta.com",
  LULU: "lululemon.com", TGT: "target.com", CMG: "chipotle.com", BKNG: "booking.com",
};

const ratingColor: Record<string, string> = {
  "Strong Buy": "#059669", Buy: "#10b981", Hold: "#eab308", Sell: "#ef4444", "Strong Sell": "#dc2626",
};

const sectionOrder = [
  { key: "executiveSummary", title: "Executive Summary", icon: Award },
  { key: "keyHighlights", title: "Key Investment Highlights", icon: Target },
  { key: "technicalView", title: "Technical View", icon: BarChart3 },
  { key: "fundamentalSnapshot", title: "Fundamental Snapshot", icon: FileText },
  { key: "valuationScenarios", title: "Valuation Scenarios", icon: Target },
  { key: "macroContext", title: "Macro Context", icon: Building2 },
  { key: "competitiveLandscape", title: "Competitive Landscape", icon: FileText },
  { key: "forecastView", title: "Forecast & Scenario View", icon: BarChart3 },
  { key: "bullCase", title: "Bull Case", icon: ArrowUpRight },
  { key: "bearCase", title: "Bear Case", icon: ArrowDownRight },
  { key: "risksCatalysts", title: "Key Risks & Mitigants", icon: AlertTriangle },
  { key: "analystConclusion", title: "Analyst Conclusion & Recommendation", icon: Award },
] as const;

// ── Logo ────────────────────────────────────────────────────────────────────

function Logo({ ticker, name }: { ticker: string; name: string }) {
  const domain = TICKER_DOMAINS[ticker] || `${name.split(" ")[0].toLowerCase().replace(/[^a-z]/g, "")}.com`;
  return (
    <div className="relative w-14 h-14 rounded-xl overflow-hidden bg-white/10 border border-white/[0.08] flex items-center justify-center flex-shrink-0">
      <img src={`${LOGO_API}/${domain}`} alt="" className="w-full h-full object-contain p-1.5"
        onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
      <span className="absolute inset-0 flex items-center justify-center text-lg font-bold text-white/60 pointer-events-none select-none">
        {ticker.slice(0, 2)}
      </span>
    </div>
  );
}

// ── Charts ──────────────────────────────────────────────────────────────────

function PriceChart({ data }: { data: ReportPricePoint[] }) {
  if (!data || data.length < 2) return null;
  const isUp = data[data.length - 1].close >= data[0].close;
  const c = isUp ? "#059669" : "#dc2626";
  const pctChange = ((data[data.length - 1].close - data[0].close) / data[0].close * 100).toFixed(1);
  return (
    <div className="glass-card p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-text-muted" />
          <h4 className="text-[11px] font-bold text-text-muted uppercase tracking-[0.12em]">Price Performance</h4>
        </div>
        <span className={cn("text-xs font-bold px-2.5 py-0.5 rounded-full",
          isUp ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400")}>
          {isUp ? "+" : ""}{pctChange}%
        </span>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
          <defs>
            <linearGradient id="reportPerfGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={c} stopOpacity={0.2} />
              <stop offset="100%" stopColor={c} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
          <XAxis dataKey="date" tick={{ fontSize: 9, fill: "#6b7280" }} tickLine={false} axisLine={false}
            tickFormatter={(v) => new Date(v).toLocaleDateString("en-US", { month: "short" })} />
          <YAxis domain={["auto", "auto"]} tick={{ fontSize: 9, fill: "#6b7280" }} tickLine={false} axisLine={false}
            tickFormatter={(v) => `$${v}`} />
          <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: 10, fontSize: 11, color: "#fff" }}
            labelFormatter={(v) => new Date(v).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })}
            formatter={(v) => [`$${Number(v).toFixed(2)}`, "Close"]} />
          <Area type="monotone" dataKey="close" stroke={c} fill="url(#reportPerfGrad)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function VolumeChart({ data }: { data: ReportPricePoint[] }) {
  if (!data || data.length < 5) return null;
  const recent = data.slice(-30);
  const avg = recent.reduce((s, d) => s + d.volume, 0) / recent.length;
  return (
    <div className="glass-card p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-text-muted" />
          <h4 className="text-[11px] font-bold text-text-muted uppercase tracking-[0.12em]">30-Day Volume</h4>
        </div>
        <span className="text-[10px] text-text-muted">Avg: {(avg / 1e6).toFixed(1)}M</span>
      </div>
      <ResponsiveContainer width="100%" height={100}>
        <BarChart data={recent} margin={{ top: 2, right: 5, bottom: 2, left: 5 }}>
          <XAxis dataKey="date" tick={false} axisLine={false} tickLine={false} />
          <YAxis tick={false} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: 8, fontSize: 10, color: "#fff" }}
            labelFormatter={(v) => new Date(v).toLocaleDateString()} formatter={(v) => [`${(Number(v) / 1e6).toFixed(1)}M`, "Vol"]} />
          <Bar dataKey="volume" fill="#818cf8" radius={[3, 3, 0, 0]} opacity={0.65} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Export ───────────────────────────────────────────────────────────────────

function handleExport(report: AnalystReportResponse) {
  const w = window.open("", "_blank");
  if (!w) return;
  const now = new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  const sections = sectionOrder
    .map((s) => {
      const content = (report as unknown as Record<string, string>)[s.key];
      if (!content) return "";
      return `<h2>${s.title}</h2><div class="prose">${content.replace(/\n/g, "<br/>")}</div>`;
    })
    .filter(Boolean)
    .join("");

  w.document.write(`<!DOCTYPE html><html><head><title>${report.ticker} — BlackGrid Research</title>
    <style>*{margin:0;padding:0;box-sizing:border-box}
    body{font-family:Georgia,'Times New Roman',serif;max-width:820px;margin:0 auto;color:#111;line-height:1.8;font-size:13.5px}
    .hdr{background:#0a0a0f;color:#fff;padding:56px 56px 44px}
    .hdr h1{font-size:28px;font-weight:700;font-family:system-ui}
    .hdr .meta{font-size:12px;color:#9ca3af;margin-top:8px}
    .hdr .rating{display:inline-block;padding:6px 16px;border-radius:8px;font-size:12px;font-weight:700;color:#fff;margin-top:16px}
    h2{font-size:11px;text-transform:uppercase;letter-spacing:2px;color:#333;margin:32px 0 12px;font-weight:800;font-family:system-ui}
    .body{padding:44px 56px}
    .prose{white-space:pre-line}
    .disc{font-size:9px;color:#999;border-top:1px solid #e5e7eb;padding-top:16px;margin-top:48px}
    @media print{.hdr{-webkit-print-color-adjust:exact;print-color-adjust:exact}}</style></head><body>
    <div class="hdr">
      <div style="font-size:10px;color:#6b7280;text-transform:uppercase;letter-spacing:3px;margin-bottom:12px">Equity Research Report</div>
      <h1>${report.name}</h1>
      <div class="meta">${report.ticker} · ${report.sector || "Equity"} · ${now} · ${report.analystName}</div>
      <div class="rating" style="background:${ratingColor[report.rating] || "#eab308"}">${report.rating.toUpperCase()}</div>
      ${report.quote ? `<div style="color:#d1d5db;margin-top:12px;font-family:system-ui;font-size:14px">$${report.quote.price.toFixed(2)} <span style="color:${report.quote.change >= 0 ? '#34d399' : '#f87171'}">${report.quote.change >= 0 ? '+' : ''}${report.quote.changePercent.toFixed(2)}%</span></div>` : ""}
    </div>
    <div class="body">${sections}
      <div class="disc"><strong>IMPORTANT DISCLOSURES</strong><br/>${report.disclaimer}</div>
    </div></body></html>`);
  w.document.close();
  setTimeout(() => w.print(), 300);
}

// ── Main Page ───────────────────────────────────────────────────────────────

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
    const timeoutId = setTimeout(() => controller.abort(), 150_000);

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
            AI analysis may take up to 90 seconds
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

  const rc = ratingColor[report.rating] || "#eab308";
  const isPos = (report.quote?.change ?? 0) >= 0;
  const now = new Date(report.generatedAt).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  const chartData = report.chart || [];

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4 max-w-4xl">
      {/* ═══════════ HEADER WITH LOGO, PRICE, RATING ═══════════ */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <Logo ticker={report.ticker} name={report.name} />
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-2xl font-bold">{report.name}</h1>
              </div>
              <div className="flex items-center gap-3 text-xs text-text-muted">
                <span className="font-semibold text-text-secondary">{report.ticker}</span>
                {report.sector && (
                  <><span className="opacity-30">·</span><span className="flex items-center gap-1"><Building2 className="h-3 w-3" />{report.sector}</span></>
                )}
                <span className="opacity-30">·</span>
                <span className="flex items-center gap-1"><Calendar className="h-3 w-3" />{now}</span>
                {report.analystName && (
                  <><span className="opacity-30">·</span><span className="flex items-center gap-1"><User className="h-3 w-3" />{report.analystName}</span></>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => handleExport(report)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary hover:bg-surface-hover rounded-lg transition-colors">
              <Printer className="h-3.5 w-3.5" /> Print
            </button>
            <button onClick={() => handleExport(report)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-accent hover:bg-accent/10 rounded-lg transition-colors font-medium">
              <Download className="h-3.5 w-3.5" /> Export
            </button>
          </div>
        </div>

        {/* Price + Rating strip */}
        <div className="flex items-center gap-6 pt-4 border-t border-border/30">
          <div>
            <p className="text-[9px] text-text-muted uppercase tracking-widest font-medium mb-1">Rating</p>
            <span className="inline-block px-4 py-1 rounded-lg text-[11px] font-extrabold text-white tracking-wide"
              style={{ backgroundColor: rc }}>{report.rating.toUpperCase()}</span>
          </div>
          {report.quote && (
            <div>
              <p className="text-[9px] text-text-muted uppercase tracking-widest font-medium mb-1">Price</p>
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold">${report.quote.price.toFixed(2)}</span>
                <span className={cn("flex items-center gap-0.5 text-xs font-semibold", isPos ? "text-emerald-400" : "text-red-400")}>
                  {isPos ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                  {isPos ? "+" : ""}{report.quote.changePercent.toFixed(2)}%
                </span>
              </div>
            </div>
          )}
          <div className="flex-1">
            <p className="text-[9px] text-text-muted uppercase tracking-widest font-medium mb-1">Confidence</p>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-2 rounded-full bg-surface-hover overflow-hidden max-w-[200px]">
                <div className="h-full rounded-full transition-all" style={{ width: `${(report.confidenceScore || 0) * 100}%`, backgroundColor: rc }} />
              </div>
              <span className="text-sm font-bold">{Math.round((report.confidenceScore || 0) * 100)}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* ═══════════ CHARTS ═══════════ */}
      {chartData.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <PriceChart data={chartData} />
          <VolumeChart data={chartData} />
        </div>
      )}

      {/* ═══════════ REPORT SECTIONS ═══════════ */}
      {sectionOrder.map((s, i) => {
        const content = (report as unknown as Record<string, string>)[s.key];
        if (!content) return null;
        const Icon = s.icon;
        return (
          <motion.div key={s.key} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
            className="glass-card p-6">
            <div className="flex items-center gap-2.5 mb-4">
              <div className="w-7 h-7 rounded-lg bg-accent/10 flex items-center justify-center flex-shrink-0">
                <Icon className="h-3.5 w-3.5 text-accent" />
              </div>
              <h2 className="text-[11px] font-extrabold text-text-secondary uppercase tracking-[0.14em]">{s.title}</h2>
            </div>
            <div className="text-[13.5px] text-text-secondary leading-[1.85] whitespace-pre-line pl-[38px]"
              style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}>
              {content}
            </div>
          </motion.div>
        );
      })}

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
