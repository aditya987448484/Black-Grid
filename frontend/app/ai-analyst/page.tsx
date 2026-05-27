"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";

// ── Types (all inline — no external imports) ──────────────────────────────────

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

interface RiskItem {
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

interface AnalystReport {
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
  risks: RiskItem[];
  catalysts: RiskItem[];
  final_rating: FinalRating;
  confidence_score: number;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  reportTicker?: string;
  reportData?: AnalystReport | null;
  reportLoading?: boolean;
  isTyping?: boolean;
}

interface Attachment {
  id: string;
  filename: string;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  report: AnalystReport | null;
  lastMessage?: string;
}

// Extend CSSProperties for non-standard scrollbar props
type CSS = React.CSSProperties & {
  scrollbarWidth?: string;
  scrollbarColor?: string;
};

// ── Constants ─────────────────────────────────────────────────────────────────

const MODELS = [
  { id: "deepseek-chat",     label: "DeepSeek V3" },
  { id: "deepseek-reasoner", label: "DeepSeek R1" },
];

const SUGGESTIONS = [
  "Analyze TSMC",
  "Analyze NVIDIA",
  "Analyze Apple",
  "What are the risks for Microsoft?",
  "Compare AMD vs Intel",
];

const BG         = "#09090c";
const CARD       = "#111318";
const SIDEBAR_BG = "#0d0f14";
const BORDER     = "rgba(255,255,255,0.07)";
const BORDER_SUB = "rgba(255,255,255,0.06)";
const PURPLE     = "#7c3aed";
const PURPLE_DIM = "rgba(124,58,237,0.18)";
const PURPLE_MID = "rgba(124,58,237,0.35)";
const API        = process.env.NEXT_PUBLIC_API_URL ?? "";

// ── Helpers ───────────────────────────────────────────────────────────────────

const genId = () => Math.random().toString(36).slice(2, 9);

const ratingBg    = (r: string) => r === "BUY" ? "rgba(34,197,94,0.14)"  : r === "SELL" ? "rgba(239,68,68,0.14)"  : "rgba(245,158,11,0.14)";
const ratingColor = (r: string) => r === "BUY" ? "#4ade80"               : r === "SELL" ? "#f87171"               : "#fbbf24";
const sevBg       = (s: string) => s === "High" ? "rgba(239,68,68,0.15)" : s === "Medium" ? "rgba(245,158,11,0.15)" : "rgba(34,197,94,0.15)";
const sevColor    = (s: string) => s === "High" ? "#f87171"              : s === "Medium" ? "#fbbf24"              : "#4ade80";
const fmtP        = (v: number | null) => v == null ? "N/A" : `$${v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const fmtPct      = (v: number | null) => v == null ? "N/A" : `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;

// ── Markdown renderer ─────────────────────────────────────────────────────────

function renderInline(text: string, bk = "k"): React.ReactNode {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let ki = 0;

  while (remaining.length > 0) {
    const boldM = remaining.match(/\*\*(.+?)\*\*/);
    const codeM = remaining.match(/`([^`]+)`/);
    const bi = boldM ? remaining.indexOf(boldM[0]) : Infinity;
    const ci = codeM ? remaining.indexOf(codeM[0]) : Infinity;

    if (bi === Infinity && ci === Infinity) { parts.push(remaining); break; }

    if (bi <= ci && boldM) {
      if (bi > 0) parts.push(remaining.slice(0, bi));
      parts.push(<strong key={`${bk}-b${ki++}`} style={{ fontWeight: 600 }}>{boldM[1]}</strong>);
      remaining = remaining.slice(bi + boldM[0].length);
    } else if (codeM) {
      if (ci > 0) parts.push(remaining.slice(0, ci));
      parts.push(
        <code key={`${bk}-c${ki++}`} style={{ background: "rgba(255,255,255,0.08)", borderRadius: 4, padding: "1px 5px", fontFamily: "monospace", fontSize: "0.85em" }}>
          {codeM[1]}
        </code>
      );
      remaining = remaining.slice(ci + codeM[0].length);
    } else { parts.push(remaining); break; }
  }
  return <>{parts}</>;
}

function renderMarkdown(text: string): React.ReactNode {
  const lines = text.split("\n");
  const els: React.ReactNode[] = [];
  let i = 0, key = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.trimStart().startsWith("```")) {
      const code: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trimStart().startsWith("```")) { code.push(lines[i]); i++; }
      els.push(
        <pre key={key++} style={{ background: "rgba(255,255,255,0.05)", border: `1px solid ${BORDER}`, borderRadius: 8, padding: "10px 14px", overflowX: "auto", fontSize: 13, fontFamily: "monospace", margin: "8px 0", lineHeight: 1.6, color: "#e2e8f0" }}>
          <code>{code.join("\n")}</code>
        </pre>
      );
      i++; continue;
    }

    if (line.startsWith("### ")) { els.push(<h4 key={key++} style={{ fontSize: 13, fontWeight: 600, color: "#cbd5e1", margin: "10px 0 4px" }}>{renderInline(line.slice(4), `h4${key}`)}</h4>); i++; continue; }
    if (line.startsWith("## "))  { els.push(<h3 key={key++} style={{ fontSize: 14, fontWeight: 600, color: "#e2e8f0", margin: "12px 0 4px" }}>{renderInline(line.slice(3), `h3${key}`)}</h3>); i++; continue; }
    if (line.startsWith("# "))   { els.push(<h2 key={key++} style={{ fontSize: 16, fontWeight: 700, color: "#f1f5f9", margin: "14px 0 6px" }}>{renderInline(line.slice(2), `h2${key}`)}</h2>); i++; continue; }

    if (/^[\-\*]\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^[\-\*]\s/.test(lines[i])) { items.push(lines[i].slice(2)); i++; }
      els.push(
        <ul key={key++} style={{ margin: "4px 0 4px 16px", padding: 0, listStyleType: "disc" }}>
          {items.map((item, j) => <li key={j} style={{ fontSize: 14, color: "#cbd5e1", marginBottom: 3, lineHeight: 1.5 }}>{renderInline(item, `li${key}${j}`)}</li>)}
        </ul>
      );
      continue;
    }

    if (line.trim() === "") { els.push(<div key={key++} style={{ height: 6 }} />); i++; continue; }
    els.push(<p key={key++} style={{ fontSize: 14, color: "#cbd5e1", margin: "2px 0", lineHeight: 1.6 }}>{renderInline(line, `p${key}`)}</p>);
    i++;
  }
  return <>{els}</>;
}

// ── TypingIndicator ───────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div style={{ display: "flex", gap: 4, alignItems: "center", padding: "6px 0" }}>
      {[0, 1, 2].map((i) => (
        <span key={i} className={`ai-dot ai-dot-${i}`} style={{ width: 6, height: 6, borderRadius: "50%", background: "rgba(255,255,255,0.35)", display: "inline-block" }} />
      ))}
    </div>
  );
}

// ── EmptyState ────────────────────────────────────────────────────────────────

function EmptyState({ onChipClick }: { onChipClick: (t: string) => void }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 16, padding: 24 }}>
      <div style={{ width: 56, height: 56, borderRadius: 14, background: PURPLE_DIM, border: `1px solid ${PURPLE_MID}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 28 }}>
        📈
      </div>
      <div style={{ textAlign: "center" }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>AI Analyst</h2>
        <p style={{ fontSize: 13, color: "rgba(255,255,255,0.35)", marginTop: 4, marginBottom: 0 }}>Powered by DeepSeek · Ask about any stock</p>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", marginTop: 4 }}>
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onChipClick(s)}
            style={{ background: CARD, border: `1px solid ${BORDER}`, borderRadius: 20, padding: "7px 16px", color: "#94a3b8", fontSize: 13, cursor: "pointer" }}
            onMouseEnter={(e) => { const b = e.currentTarget; b.style.background = PURPLE_DIM; b.style.borderColor = PURPLE_MID; b.style.color = "#e2e8f0"; }}
            onMouseLeave={(e) => { const b = e.currentTarget; b.style.background = CARD; b.style.borderColor = BORDER; b.style.color = "#94a3b8"; }}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── MessageBubble ─────────────────────────────────────────────────────────────

function MessageBubble({ msg, onViewReport }: { msg: Message; onViewReport: (r: AnalystReport) => void }) {
  const isUser = msg.role === "user";
  return (
    <div style={{ display: "flex", flexDirection: isUser ? "row-reverse" : "row", alignItems: "flex-start", gap: 10, marginBottom: 16 }}>
      {!isUser && (
        <div style={{ width: 30, height: 30, borderRadius: 8, background: PURPLE_DIM, border: `1px solid ${PURPLE_MID}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, flexShrink: 0, marginTop: 2 }}>
          📈
        </div>
      )}
      <div style={{ maxWidth: "76%", minWidth: 40 }}>
        <div style={{ background: isUser ? "rgba(124,58,237,0.14)" : "rgba(255,255,255,0.04)", border: `1px solid ${isUser ? PURPLE_MID : BORDER_SUB}`, borderRadius: isUser ? "12px 4px 12px 12px" : "4px 12px 12px 12px", padding: "10px 14px" }}>
          {msg.isTyping ? <TypingIndicator /> : renderMarkdown(msg.content)}
        </div>

        {!isUser && msg.reportLoading && (
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 8 }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="ai-spin">
              <circle cx="12" cy="12" r="10" stroke="rgba(255,255,255,0.12)" strokeWidth="3" />
              <path d="M12 2a10 10 0 0110 10" stroke={PURPLE} strokeWidth="3" strokeLinecap="round" />
            </svg>
            <span style={{ fontSize: 12, color: "rgba(255,255,255,0.35)" }}>Fetching structured report…</span>
          </div>
        )}
        {!isUser && msg.reportData && !msg.reportLoading && (
          <button
            onClick={() => onViewReport(msg.reportData!)}
            style={{ marginTop: 8, background: PURPLE_DIM, border: `1px solid ${PURPLE_MID}`, borderRadius: 6, padding: "5px 12px", color: "#a78bfa", fontSize: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 5 }}
            onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(124,58,237,0.28)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = PURPLE_DIM; }}
          >
            📋 View Report
          </button>
        )}
      </div>
    </div>
  );
}

// ── Document panel sub-components ────────────────────────────────────────────

function PSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.28)", borderBottom: `1px solid ${BORDER}`, paddingBottom: 6, marginBottom: 10 }}>
        {title}
      </div>
      {children}
    </div>
  );
}

function MTile({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ background: "rgba(255,255,255,0.03)", border: `1px solid ${BORDER_SUB}`, borderRadius: 6, padding: "8px 10px" }}>
      <div style={{ fontSize: 9, color: "rgba(255,255,255,0.28)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 3 }}>{label}</div>
      <div style={{ fontSize: 13, fontWeight: 600, color: "#e2e8f0" }}>{value}</div>
    </div>
  );
}

// ── DocPanel ──────────────────────────────────────────────────────────────────

interface DocPanelProps {
  report: AnalystReport | null;
  lastAssistantText: string | null;
  onExportReport: (r: AnalystReport) => Promise<void>;
  exporting: boolean;
  exportErr: string | null;
}

function DocPanel({ report, lastAssistantText, onExportReport, exporting, exportErr }: DocPanelProps) {
  const scrollCSS: CSS = { flex: 1, overflowY: "auto", padding: 20, scrollbarWidth: "thin", scrollbarColor: "rgba(255,255,255,0.07) transparent" };

  // ── Empty placeholder ─────────────────────────────────────────────────────
  if (!report && !lastAssistantText) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 12, padding: 32, opacity: 0.5 }}>
        <div style={{ width: 48, height: 48, borderRadius: 12, background: "rgba(255,255,255,0.04)", border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22 }}>
          📄
        </div>
        <div style={{ textAlign: "center" }}>
          <p style={{ fontSize: 14, fontWeight: 600, color: "#94a3b8", margin: 0 }}>Document Panel</p>
          <p style={{ fontSize: 12, color: "rgba(255,255,255,0.25)", marginTop: 6, lineHeight: 1.5 }}>Ask to analyze a stock to<br />generate a structured report</p>
        </div>
      </div>
    );
  }

  // ── Markdown fallback (only text, no structured report yet) ───────────────
  if (!report && lastAssistantText) {
    return (
      <div style={scrollCSS} className="ai-panel-body">
        <div style={{ marginBottom: 16, paddingBottom: 12, borderBottom: `1px solid ${BORDER}` }}>
          <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: PURPLE, margin: 0 }}>AI Response</p>
        </div>
        {renderMarkdown(lastAssistantText)}
      </div>
    );
  }

  // ── Full structured report ─────────────────────────────────────────────────
  const r  = report!;
  const rt = r.final_rating;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Panel header */}
      <div style={{ padding: "14px 18px", borderBottom: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 700, color: "#f1f5f9" }}>{r.ticker.toUpperCase()}</div>
          <div style={{ fontSize: 12, color: "rgba(255,255,255,0.38)", marginTop: 1 }}>{r.company_name}</div>
        </div>
        <button
          onClick={() => onExportReport(r)}
          disabled={exporting}
          style={{ background: PURPLE_DIM, border: `1px solid ${PURPLE_MID}`, borderRadius: 6, padding: "5px 12px", color: "#a78bfa", fontSize: 12, cursor: exporting ? "not-allowed" : "pointer", opacity: exporting ? 0.6 : 1 }}
        >
          {exporting ? "Exporting…" : "⬇ PDF"}
        </button>
      </div>
      {exportErr && <div style={{ padding: "7px 18px", background: "rgba(239,68,68,0.1)", fontSize: 12, color: "#f87171", borderBottom: `1px solid ${BORDER}` }}>{exportErr}</div>}

      {/* Scrollable content */}
      <div style={scrollCSS} className="ai-panel-body">

        <PSection title="Recommendation">
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
            <p style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.5, margin: 0, flex: 1 }}>{r.executive_summary}</p>
            <div style={{ background: ratingBg(rt?.recommendation ?? "HOLD"), border: `1px solid ${ratingColor(rt?.recommendation ?? "HOLD")}44`, borderRadius: 8, padding: "10px 14px", textAlign: "center", flexShrink: 0 }}>
              <div style={{ fontSize: 22, fontWeight: 800, color: ratingColor(rt?.recommendation ?? "HOLD") }}>{rt?.recommendation ?? "HOLD"}</div>
              <div style={{ fontSize: 11, color: "rgba(255,255,255,0.45)", marginTop: 2 }}>{fmtP(rt?.target_price ?? null)}</div>
              <div style={{ fontSize: 11, color: ratingColor(rt?.recommendation ?? "HOLD"), fontWeight: 600 }}>{fmtPct(rt?.price_upside ?? null)}</div>
            </div>
          </div>
        </PSection>

        <PSection title="Fundamentals">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, marginBottom: 6 }}>
            <MTile label="EPS"            value={fmtP(r.fundamental_snapshot?.eps ?? null)} />
            <MTile label="Revenue Growth" value={fmtPct(r.fundamental_snapshot?.revenue_growth ?? null)} />
            <MTile label="Profit Margin"  value={fmtPct(r.fundamental_snapshot?.profit_margin ?? null)} />
            <MTile label="ROE"            value={fmtPct(r.fundamental_snapshot?.roe ?? null)} />
            <MTile label="Debt/Equity"    value={r.fundamental_snapshot?.debt_to_equity?.toFixed(2) ?? "N/A"} />
            <MTile label="Quality Score"  value={`${(r.fundamental_snapshot?.quality_score ?? 0).toFixed(0)} / 100`} />
          </div>
          <div style={{ background: "rgba(255,255,255,0.03)", border: `1px solid ${BORDER_SUB}`, borderRadius: 6, padding: "8px 10px" }}>
            <div style={{ fontSize: 9, color: "rgba(255,255,255,0.28)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 3 }}>Valuation</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#e2e8f0" }}>{r.fundamental_snapshot?.valuation_assessment ?? "—"}</div>
          </div>
        </PSection>

        <PSection title="Technical Analysis">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, marginBottom: 8 }}>
            <MTile label="Trend"        value={r.technical_view?.trend ?? "—"} />
            <MTile label="Signal"       value={`${(r.technical_view?.signal_strength ?? 0).toFixed(0)} / 100`} />
            <MTile label="Momentum"     value={r.technical_view?.momentum ?? "—"} />
            <MTile label="MA Alignment" value={r.technical_view?.ma_alignment ?? "—"} />
          </div>
          <p style={{ fontSize: 12, color: "rgba(255,255,255,0.42)", lineHeight: 1.5, margin: 0 }}>{r.technical_view?.summary ?? ""}</p>
        </PSection>

        <PSection title="Investment Cases">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <div style={{ background: "rgba(34,197,94,0.05)", border: "1px solid rgba(34,197,94,0.2)", borderRadius: 8, padding: "10px 12px" }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#4ade80", marginBottom: 5 }}>▲ Bull ({(r.bull_case?.probability ?? 0).toFixed(0)}%)</div>
              <p style={{ fontSize: 11, color: "#94a3b8", lineHeight: 1.4, margin: "0 0 8px" }}>{r.bull_case?.thesis ?? ""}</p>
              <div style={{ height: 3, background: "rgba(255,255,255,0.06)", borderRadius: 2 }}>
                <div style={{ height: 3, background: "#22c55e", borderRadius: 2, width: `${r.bull_case?.probability ?? 0}%` }} />
              </div>
            </div>
            <div style={{ background: "rgba(239,68,68,0.05)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 8, padding: "10px 12px" }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#f87171", marginBottom: 5 }}>▼ Bear ({(r.bear_case?.probability ?? 0).toFixed(0)}%)</div>
              <p style={{ fontSize: 11, color: "#94a3b8", lineHeight: 1.4, margin: "0 0 8px" }}>{r.bear_case?.thesis ?? ""}</p>
              <div style={{ height: 3, background: "rgba(255,255,255,0.06)", borderRadius: 2 }}>
                <div style={{ height: 3, background: "#ef4444", borderRadius: 2, width: `${r.bear_case?.probability ?? 0}%` }} />
              </div>
            </div>
          </div>
        </PSection>

        <PSection title="Macro Context">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <div>
              <div style={{ fontSize: 10, color: "#4ade80", fontWeight: 700, marginBottom: 6 }}>Tailwinds</div>
              <ul style={{ margin: 0, padding: "0 0 0 14px" }}>
                {(r.macro_context?.industry_tailwinds ?? []).map((t, i) => <li key={i} style={{ fontSize: 11, color: "#94a3b8", marginBottom: 3, lineHeight: 1.4 }}>{t}</li>)}
              </ul>
            </div>
            <div>
              <div style={{ fontSize: 10, color: "#f87171", fontWeight: 700, marginBottom: 6 }}>Headwinds</div>
              <ul style={{ margin: 0, padding: "0 0 0 14px" }}>
                {(r.macro_context?.macro_headwinds ?? []).map((h, i) => <li key={i} style={{ fontSize: 11, color: "#94a3b8", marginBottom: 3, lineHeight: 1.4 }}>{h}</li>)}
              </ul>
            </div>
          </div>
        </PSection>

        <PSection title="Key Risks">
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {(r.risks ?? []).map((risk, i) => (
              <div key={i} style={{ background: "rgba(255,255,255,0.02)", border: `1px solid ${BORDER_SUB}`, borderRadius: 6, padding: "8px 10px", display: "flex", gap: 8, alignItems: "flex-start" }}>
                <span style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", background: sevBg(risk.severity), color: sevColor(risk.severity), borderRadius: 3, padding: "2px 5px", flexShrink: 0, marginTop: 1 }}>{risk.severity}</span>
                <div>
                  <p style={{ fontSize: 12, color: "#e2e8f0", margin: 0, lineHeight: 1.4 }}>{risk.description}</p>
                  {risk.mitigation && <p style={{ fontSize: 11, color: "rgba(255,255,255,0.32)", margin: "3px 0 0" }}>↳ {risk.mitigation}</p>}
                </div>
              </div>
            ))}
          </div>
        </PSection>

        <PSection title="Catalysts">
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {(r.catalysts ?? []).map((cat, i) => (
              <div key={i} style={{ background: "rgba(255,255,255,0.02)", border: `1px solid ${BORDER_SUB}`, borderRadius: 6, padding: "8px 10px", display: "flex", gap: 8, alignItems: "flex-start" }}>
                <span style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", background: sevBg(cat.severity), color: sevColor(cat.severity), borderRadius: 3, padding: "2px 5px", flexShrink: 0, marginTop: 1 }}>{cat.severity}</span>
                <div>
                  <p style={{ fontSize: 12, color: "#e2e8f0", margin: 0, lineHeight: 1.4 }}>{cat.description}</p>
                  {cat.mitigation && <p style={{ fontSize: 11, color: "rgba(255,255,255,0.32)", margin: "3px 0 0" }}>↳ {cat.mitigation}</p>}
                </div>
              </div>
            ))}
          </div>
        </PSection>

        <PSection title="Final Recommendation">
          <p style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.5, margin: "0 0 12px" }}>{rt?.rationale ?? ""}</p>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 10, color: "rgba(255,255,255,0.32)", flexShrink: 0 }}>Confidence</span>
            <div style={{ flex: 1, height: 6, background: "rgba(255,255,255,0.06)", borderRadius: 3 }}>
              <div style={{ height: 6, borderRadius: 3, background: PURPLE, width: `${r.confidence_score ?? 0}%`, transition: "width 0.6s ease" }} />
            </div>
            <span style={{ fontSize: 12, fontWeight: 700, color: "#e2e8f0", flexShrink: 0 }}>{(r.confidence_score ?? 0).toFixed(0)}%</span>
          </div>
        </PSection>

      </div>
    </div>
  );
}

// ── Sidebar ───────────────────────────────────────────────────────────────────

interface SidebarProps {
  conversations: Conversation[];
  activeId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
}

function Sidebar({ conversations, activeId, onSelect, onNew }: SidebarProps) {
  const scrollCSS: CSS = { flex: 1, overflowY: "auto", padding: "8px 0", scrollbarWidth: "none" };

  return (
    <div style={{ width: 240, flexShrink: 0, background: SIDEBAR_BG, borderRight: `1px solid ${BORDER}`, display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>

      {/* Brand + New button */}
      <div style={{ padding: "16px 14px 12px", borderBottom: `1px solid ${BORDER}`, flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <div style={{ width: 28, height: 28, borderRadius: 7, background: PURPLE_DIM, border: `1px solid ${PURPLE_MID}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14 }}>📈</div>
          <span style={{ fontSize: 13, fontWeight: 700, color: "#f1f5f9", letterSpacing: "0.01em" }}>AI Analyst</span>
        </div>
        <button
          onClick={onNew}
          style={{ width: "100%", background: PURPLE_DIM, border: `1px solid ${PURPLE_MID}`, borderRadius: 8, padding: "8px 12px", color: "#a78bfa", fontSize: 13, fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}
          onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(124,58,237,0.28)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = PURPLE_DIM; }}
        >
          <span style={{ fontSize: 16, lineHeight: 1 }}>+</span>
          New Conversation
        </button>
      </div>

      {/* Conversation list */}
      <div style={scrollCSS} className="ai-sidebar-scroll">
        {conversations.length === 0 && (
          <p style={{ fontSize: 12, color: "rgba(255,255,255,0.2)", padding: "12px 14px", margin: 0 }}>No conversations yet</p>
        )}
        {conversations.map((conv) => {
          const isActive = conv.id === activeId;
          return (
            <button
              key={conv.id}
              onClick={() => onSelect(conv.id)}
              style={{ width: "calc(100% - 16px)", background: isActive ? PURPLE_DIM : "transparent", border: isActive ? `1px solid ${PURPLE_MID}` : "1px solid transparent", borderRadius: 8, margin: "2px 8px", padding: "8px 10px", cursor: "pointer", textAlign: "left", display: "block", boxSizing: "border-box" }}
              onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = "rgba(255,255,255,0.04)"; }}
              onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = "transparent"; }}
            >
              <p style={{ fontSize: 12, fontWeight: 600, color: isActive ? "#a78bfa" : "#94a3b8", margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {conv.title}
              </p>
              {conv.lastMessage && (
                <p style={{ fontSize: 11, color: "rgba(255,255,255,0.25)", margin: "2px 0 0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {conv.lastMessage}
                </p>
              )}
            </button>
          );
        })}
      </div>

      {/* Footer */}
      <div style={{ padding: "10px 14px", borderTop: `1px solid ${BORDER}`, flexShrink: 0 }}>
        <p style={{ fontSize: 10, color: "rgba(255,255,255,0.18)", margin: 0, letterSpacing: "0.04em" }}>BlackGrid · AI Research</p>
      </div>
    </div>
  );
}

// ── InputBar ──────────────────────────────────────────────────────────────────

interface InputBarProps {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  model: string;
  onModelChange: (m: string) => void;
  attachments: Attachment[];
  onAttach: (files: FileList) => void;
  onRemoveAttachment: (id: string) => void;
  disabled: boolean;
}

function InputBar({ value, onChange, onSend, model, onModelChange, attachments, onAttach, onRemoveAttachment, disabled }: InputBarProps) {
  const taRef   = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 180)}px`;
  }, [value]);

  const canSend = value.trim().length > 0 && !disabled;

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (canSend) onSend(); }
  }

  return (
    <div style={{ borderTop: `1px solid ${BORDER}`, background: BG, flexShrink: 0, padding: "12px 16px" }}>
      {attachments.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
          {attachments.map((a) => (
            <div key={a.id} style={{ display: "flex", alignItems: "center", gap: 5, background: CARD, border: `1px solid ${BORDER}`, borderRadius: 5, padding: "3px 8px", fontSize: 12, color: "#94a3b8" }}>
              📎 {a.filename}
              <button onClick={() => onRemoveAttachment(a.id)} style={{ background: "none", border: "none", color: "rgba(255,255,255,0.3)", cursor: "pointer", fontSize: 15, lineHeight: 1, padding: 0, marginLeft: 2 }} aria-label={`Remove ${a.filename}`}>×</button>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "flex", alignItems: "flex-end", gap: 8, background: CARD, border: `1px solid ${BORDER}`, borderRadius: 12, padding: "8px 10px" }}>

        {/* Paperclip */}
        <button onClick={() => fileRef.current?.click()} aria-label="Attach file"
          style={{ background: "none", border: "none", color: "rgba(255,255,255,0.3)", cursor: "pointer", padding: 4, display: "flex", alignItems: "center", flexShrink: 0 }}
          onMouseEnter={(e) => { e.currentTarget.style.color = "rgba(255,255,255,0.6)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = "rgba(255,255,255,0.3)"; }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
          </svg>
        </button>
        <input ref={fileRef} type="file" multiple accept=".pdf,.txt,.csv,.docx,.png,.jpg,.jpeg,.webp" style={{ display: "none" }}
          onChange={(e) => { if (e.target.files) { onAttach(e.target.files); e.target.value = ""; } }} />

        {/* Textarea */}
        <textarea
          ref={taRef} value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask about any stock or market…"
          rows={1}
          style={{ flex: 1, background: "transparent", border: "none", outline: "none", color: "#e2e8f0", fontSize: 14, fontFamily: "inherit", resize: "none", lineHeight: 1.5, maxHeight: 180, overflowY: "auto", padding: "2px 0" } as CSS}
        />

        {/* Model selector */}
        <select value={model} onChange={(e) => onModelChange(e.target.value)}
          style={{ background: "rgba(255,255,255,0.05)", border: `1px solid ${BORDER}`, borderRadius: 6, color: "rgba(255,255,255,0.45)", fontSize: 11, padding: "4px 6px", cursor: "pointer", flexShrink: 0, outline: "none" }}>
          {MODELS.map((m) => <option key={m.id} value={m.id} style={{ background: "#1a1a1a" }}>{m.label}</option>)}
        </select>

        {/* Send button */}
        <button onClick={onSend} disabled={!canSend} aria-label="Send"
          style={{ background: canSend ? PURPLE : "rgba(255,255,255,0.07)", border: "none", borderRadius: 8, width: 34, height: 34, display: "flex", alignItems: "center", justifyContent: "center", cursor: canSend ? "pointer" : "not-allowed", flexShrink: 0, transition: "background 0.15s" }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={canSend ? "#fff" : "rgba(255,255,255,0.25)"} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
    </div>
  );
}

// ── Ticker extraction ─────────────────────────────────────────────────────────

function extractTicker(text: string): string | null {
  // "analyze TSMC", "analysis of META", "what about AAPL", "NVDA looks", "$TSLA"
  const patterns = [
    /\banalyze\s+([a-z]{1,10})\b/i,
    /\banalysis\s+(?:of\s+)?([a-z]{1,10})\b/i,
    /\banalysis\s+for\s+([a-z]{1,10})\b/i,
    /\bwhat\s+about\s+([a-z]{1,10})\b/i,
    /\btell\s+me\s+about\s+([a-z]{1,10})\b/i,
    /\bbreak\s+down\s+([a-z]{1,10})\b/i,
    /\breport\s+(?:on\s+|for\s+)?([a-z]{1,10})\b/i,
    /\$([A-Z]{1,5})\b/,
    /\b([A-Z]{2,5})\s+(?:stock|shares|ticker|analysis|price|forecast)\b/,
  ];
  for (const p of patterns) {
    const m = text.match(p);
    if (m) {
      const t = m[1].toUpperCase();
      // Exclude common English words
      const stopWords = ["THE", "AND", "FOR", "ALL", "ARE", "NOT", "WITH", "THIS", "THAT", "FROM", "HAVE", "WILL", "WHAT", "WHICH"];
      if (!stopWords.includes(t)) return t;
    }
  }
  return null;
}

// ── Main page ─────────────────────────────────────────────────────────────────

const newConversation = (): Conversation => ({
  id:           genId(),
  title:        "New Chat",
  messages:     [],
  report:       null,
  lastMessage:  undefined,
});

export default function AIAnalystPage() {
  const [conversations,    setConversations]    = useState<Conversation[]>([newConversation()]);
  const [activeId,         setActiveId]         = useState<string>(conversations[0].id);
  const [input,            setInput]            = useState("");
  const [model,            setModel]            = useState("deepseek-chat");
  const [attachments,      setAttachments]      = useState<Attachment[]>([]);
  const [isLoading,        setIsLoading]        = useState(false);
  const [exporting,        setExporting]        = useState(false);
  const [exportErr,        setExportErr]        = useState<string | null>(null);
  const threadRef = useRef<HTMLDivElement>(null);

  // Active conversation helpers
  const activeConv = conversations.find((c) => c.id === activeId) ?? conversations[0];

  const updateConv = useCallback((id: string, updater: (c: Conversation) => Conversation) => {
    setConversations((prev) => prev.map((c) => c.id === id ? updater(c) : c));
  }, []);

  // Auto-scroll
  useEffect(() => {
    if (threadRef.current) threadRef.current.scrollTop = threadRef.current.scrollHeight;
  }, [activeConv?.messages]);

  // ── New conversation ───────────────────────────────────────────────────────
  function handleNew() {
    const conv = newConversation();
    setConversations((prev) => [conv, ...prev]);
    setActiveId(conv.id);
    setInput("");
    setAttachments([]);
  }

  // ── File attach ────────────────────────────────────────────────────────────
  async function handleAttach(files: FileList) {
    const next: Attachment[] = [];
    for (const file of Array.from(files)) {
      try {
        const fd = new FormData();
        fd.append("file", file);
        await fetch(`${API}/ai-analyst/upload`, { method: "POST", body: fd });
      } catch (_err) { /* best-effort */ }
      next.push({ id: genId(), filename: file.name });
    }
    setAttachments((prev) => [...prev, ...next]);
  }

  // ── Export PDF ─────────────────────────────────────────────────────────────
  async function handleExportReport(r: AnalystReport) {
    setExporting(true); setExportErr(null);
    try {
      const res = await fetch(`${API}/analyst/export-pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(r),
      });
      if (!res.ok) {
        const e = await res.json().catch(() => ({})) as { detail?: string };
        throw new Error(e.detail ?? `HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `${r.ticker.toUpperCase()}_BlackGrid_Research.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportErr(err instanceof Error ? err.message : "Export failed");
    } finally { setExporting(false); }
  }

  // ── Send message ───────────────────────────────────────────────────────────
  async function handleSend() {
    if (!input.trim() || isLoading) return;

    const convId    = activeId;
    const userText  = input.trim();
    const sentAttach = [...attachments];
    setInput(""); setAttachments([]); setIsLoading(true);

    // Derive title from first message
    const isFirst = activeConv.messages.length === 0;
    const title = isFirst ? userText.slice(0, 36) + (userText.length > 36 ? "…" : "") : activeConv.title;

    // 1. Add user message
    const userMsgId = genId();
    updateConv(convId, (c) => ({
      ...c,
      title,
      lastMessage: userText.slice(0, 50),
      messages: [...c.messages, { id: userMsgId, role: "user", content: userText }],
    }));

    // 2. Placeholder assistant message
    const asstId = genId();
    updateConv(convId, (c) => ({
      ...c,
      messages: [...c.messages, { id: asstId, role: "assistant", content: "", isTyping: true, reportLoading: false }],
    }));

    // 3. Extract ticker
    const ticker = extractTicker(userText);

    const history = activeConv.messages.map((m) => ({ role: m.role, content: m.content }));

    if (ticker) {
      updateConv(convId, (c) => ({
        ...c,
        messages: c.messages.map((m) => m.id === asstId ? { ...m, reportLoading: true, reportTicker: ticker } : m),
      }));
    }

    // 4. Parallel fetches
    const chatFetch = fetch(`${API}/ai-analyst/chat`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ message: userText, history, model, attachments: sentAttach.map((a) => a.filename) }),
    });
    const reportFetch = ticker ? fetch(`${API}/report/${ticker}`) : null;

    // 5. Chat response
    try {
      const chatRes = await chatFetch;
      if (!chatRes.ok) {
        const e = await chatRes.json().catch(() => ({})) as { detail?: string };
        throw new Error(e.detail ?? `HTTP ${chatRes.status}`);
      }
      const json = await chatRes.json() as { reply?: string; message?: string };
      const reply = json.reply ?? json.message ?? "No response received.";
      updateConv(convId, (c) => ({
        ...c,
        messages: c.messages.map((m) => m.id === asstId ? { ...m, content: reply, isTyping: false } : m),
      }));
    } catch (err) {
      const msg = err instanceof Error ? err.message : "An error occurred.";
      updateConv(convId, (c) => ({
        ...c,
        messages: c.messages.map((m) => m.id === asstId ? { ...m, content: `⚠️ ${msg}`, isTyping: false, reportLoading: false } : m),
      }));
      setIsLoading(false);
      return;
    }

    // 6. Report response
    if (reportFetch) {
      try {
        const rRes = await reportFetch;
        if (!rRes.ok) throw new Error(`Report HTTP ${rRes.status}`);
        const rJson = await rRes.json() as { data: AnalystReport };
        const reportData = rJson.data;
        updateConv(convId, (c) => ({
          ...c,
          report: reportData,
          messages: c.messages.map((m) => m.id === asstId ? { ...m, reportLoading: false, reportData } : m),
        }));
      } catch (_err) {
        updateConv(convId, (c) => ({
          ...c,
          messages: c.messages.map((m) => m.id === asstId ? { ...m, reportLoading: false } : m),
        }));
      }
    }

    setIsLoading(false);
  }

  // ── Doc panel content ──────────────────────────────────────────────────────
  const lastAssistant = [...activeConv.messages].reverse().find((m) => m.role === "assistant" && !m.isTyping && m.content);
  const docReport = activeConv.report;
  const docText   = lastAssistant?.content ?? null;

  const threadCSS: CSS = {
    flex: 1, overflowY: "auto",
    padding: activeConv.messages.length === 0 ? 0 : "20px 20px 8px",
    scrollbarWidth: "thin",
    scrollbarColor: "rgba(255,255,255,0.07) transparent",
  };

  return (
    <>
      <style>{`
        @keyframes ai-bounce {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.35; }
          30%            { transform: translateY(-5px); opacity: 0.8; }
        }
        .ai-dot   { animation: ai-bounce 1.2s ease-in-out infinite; }
        .ai-dot-0 { animation-delay: 0s;   }
        .ai-dot-1 { animation-delay: 0.2s; }
        .ai-dot-2 { animation-delay: 0.4s; }

        @keyframes ai-spin { to { transform: rotate(360deg); } }
        .ai-spin { animation: ai-spin 1s linear infinite; }

        .ai-sidebar-scroll::-webkit-scrollbar { display: none; }

        .ai-thread::-webkit-scrollbar,
        .ai-panel-body::-webkit-scrollbar,
        textarea::-webkit-scrollbar       { width: 4px; height: 4px; }
        .ai-thread::-webkit-scrollbar-track,
        .ai-panel-body::-webkit-scrollbar-track,
        textarea::-webkit-scrollbar-track { background: transparent; }
        .ai-thread::-webkit-scrollbar-thumb,
        .ai-panel-body::-webkit-scrollbar-thumb,
        textarea::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.07); border-radius: 2px; }
      `}</style>

      <div style={{ display: "flex", height: "100vh", background: BG, color: "#e2e8f0", fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", overflow: "hidden" }}>

        {/* ── Sidebar ─────────────────────────────────────────────────────── */}
        <Sidebar
          conversations={conversations}
          activeId={activeId}
          onSelect={(id) => { setActiveId(id); }}
          onNew={handleNew}
        />

        {/* ── Chat column ─────────────────────────────────────────────────── */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", minWidth: 0 }}>
          <div ref={threadRef} className="ai-thread" style={threadCSS}>
            {activeConv.messages.length === 0
              ? <EmptyState onChipClick={(t) => setInput(t)} />
              : activeConv.messages.map((msg) => (
                  <MessageBubble
                    key={msg.id}
                    msg={msg}
                    onViewReport={(r) => updateConv(activeId, (c) => ({ ...c, report: r }))}
                  />
                ))
            }
          </div>
          <InputBar
            value={input} onChange={setInput} onSend={handleSend}
            model={model} onModelChange={setModel}
            attachments={attachments} onAttach={handleAttach}
            onRemoveAttachment={(id) => setAttachments((prev) => prev.filter((a) => a.id !== id))}
            disabled={isLoading}
          />
        </div>

        {/* ── Document panel (50% width) ───────────────────────────────────── */}
        <div style={{ width: "50%", flexShrink: 0, background: CARD, borderLeft: `1px solid ${BORDER}`, display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
          <DocPanel
            report={docReport}
            lastAssistantText={docText}
            onExportReport={handleExportReport}
            exporting={exporting}
            exportErr={exportErr}
          />
        </div>

      </div>
    </>
  );
}
