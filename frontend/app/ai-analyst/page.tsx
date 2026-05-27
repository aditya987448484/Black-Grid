"use client";

import { useState } from "react";
import ChatPanel from "@/components/ai-analyst/ChatPanel";
import AnalystWorkspace, { type AnalystReport } from "@/components/ai-analyst/AnalystWorkspace";
import { DEEPSEEK_MODELS } from "@/lib/types/ai-analyst";

type Tab = "report" | "chat";

export default function AIAnalystPage() {
  const [model, setModel] = useState("deepseek-chat");
  const [ticker, setTicker] = useState("");
  const [tab, setTab] = useState<Tab>("report");
  const [report, setReport] = useState<AnalystReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFetchReport() {
    if (!ticker.trim()) return;
    setLoading(true);
    setError(null);
    setReport(null);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/report/${ticker.toUpperCase()}`
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `HTTP ${res.status}`);
      }
      const json = await res.json();
      setReport(json.data);
      setTab("report");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load report");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-screen bg-[#050505] text-white">
      {/* ── Page header ── */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-[#1f2937]">
        <div>
          <h1 className="text-lg font-bold tracking-tight">AI Analyst</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Powered by{" "}
            {DEEPSEEK_MODELS.find((m) => m.id === model)?.label ?? "DeepSeek"}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Ticker input */}
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === "Enter" && handleFetchReport()}
            placeholder="Ticker…"
            maxLength={6}
            className="bg-[#111827] text-white text-sm border border-[#374151] rounded px-3 py-1.5 w-32 focus:outline-none focus:ring-1 focus:ring-emerald-500 placeholder-gray-600 font-mono"
          />

          {/* Generate button */}
          <button
            onClick={handleFetchReport}
            disabled={!ticker.trim() || loading}
            className="text-sm bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium px-4 py-1.5 rounded transition-colors"
          >
            {loading ? "Loading…" : "Analyse"}
          </button>

          {/* Model selector (used by chat tab) */}
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="text-sm bg-[#111827] text-gray-300 border border-[#374151] rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          >
            {DEEPSEEK_MODELS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label} {m.badge ? `· ${m.badge}` : ""}
              </option>
            ))}
          </select>
        </div>
      </header>

      {/* ── Tabs ── */}
      <div className="flex border-b border-[#1f2937] px-6">
        {(["report", "chat"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`py-2.5 px-4 text-sm font-medium border-b-2 transition-colors ${
              tab === t
                ? "border-emerald-500 text-emerald-400"
                : "border-transparent text-gray-500 hover:text-gray-300"
            }`}
          >
            {t === "report" ? "Research Report" : "Chat"}
          </button>
        ))}
      </div>

      {/* ── Content area ── */}
      <main className="flex-1 overflow-y-auto p-6">
        {error && (
          <div className="mb-4 p-3 bg-red-950 border border-red-800 rounded-lg text-red-300 text-sm">
            {error}
          </div>
        )}

        {tab === "report" && (
          <>
            {!report && !loading && (
              <div className="flex flex-col items-center justify-center h-full text-gray-600 text-sm gap-2">
                <span className="text-4xl">📊</span>
                <p>Enter a ticker and click <strong className="text-gray-400">Analyse</strong> to generate a report.</p>
              </div>
            )}
            {loading && (
              <div className="flex items-center justify-center h-full">
                <div className="text-gray-400 text-sm animate-pulse">Generating report…</div>
              </div>
            )}
            {report && !loading && <AnalystWorkspace report={report} />}
          </>
        )}

        {tab === "chat" && (
          <div className="h-full">
            <ChatPanel ticker={ticker || undefined} />
          </div>
        )}
      </main>
    </div>
  );
}
