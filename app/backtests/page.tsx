"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { getBacktestSummary } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { BacktestSummaryResponse, BacktestModelResult } from "@/types/backtest";
import PerformanceChart from "@/components/backtest/PerformanceChart";
import ComparisonTable from "@/components/backtest/ComparisonTable";

const STRATEGY_META: Record<string, { num: string; color: string; icon: string }> = {
  "RSI Mean Reversion":             { num: "01", color: "#00d4ff", icon: "\u25C8" },
  "MACD Trend Following":           { num: "02", color: "#8b5cf6", icon: "\u25C9" },
  "Bollinger Band Squeeze":         { num: "03", color: "#22c55e", icon: "\u25CE" },
  "ATR Volatility Channel":         { num: "04", color: "#f59e0b", icon: "\u25C7" },
  "RSI + MACD + Volume Confluence": { num: "05", color: "#ec4899", icon: "\u2726" },
  "Buy & Hold":                     { num: "BM", color: "#6b7280", icon: "\u25A3" },
};

function MetricBadge({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
  return (
    <div className="bg-surface rounded-lg p-2.5">
      <p className="text-[10px] text-text-muted uppercase tracking-wider mb-1">{label}</p>
      <p className={cn("text-base font-black",
        positive === true ? "text-success" : positive === false ? "text-danger" : "text-text-primary"
      )}>{value}</p>
    </div>
  );
}

export default function BacktestPage() {
  const [tickerInput, setTickerInput] = useState("SPY");
  const [data, setData] = useState<BacktestSummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIdx, setSelectedIdx] = useState(0);

  // Date range state — default to 5 years
  const [startDate, setStartDate] = useState<string>(() => {
    const d = new Date(); d.setFullYear(d.getFullYear() - 5);
    return d.toISOString().split("T")[0];
  });
  const [endDate, setEndDate] = useState<string>(new Date().toISOString().split("T")[0]);
  const [activePreset, setActivePreset] = useState<string>("5Y");

  const runBacktest = useCallback(async () => {
    if (!tickerInput.trim()) return;
    setLoading(true);
    setError(null);
    setSelectedIdx(0);
    try {
      const result = await getBacktestSummary(
        tickerInput.trim().toUpperCase(),
        startDate || undefined,
        endDate || undefined,
      );
      setData(result);
    } catch (e: any) {
      setError(e.message || "Backtest failed.");
    } finally {
      setLoading(false);
    }
  }, [tickerInput, startDate, endDate]);

  const selected: BacktestModelResult | null = data?.models[selectedIdx] ?? null;

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-4 h-[calc(100vh-7rem)]">
      {/* LEFT PANEL */}
      <div className="w-64 flex-shrink-0 flex flex-col gap-3 overflow-y-auto">
        <div className="glass-card p-3 space-y-3">
          <div>
            <p className="text-[10px] text-text-muted uppercase tracking-wider mb-1.5">Ticker</p>
            <input value={tickerInput} onChange={e => setTickerInput(e.target.value.toUpperCase())}
              onKeyDown={e => e.key === "Enter" && runBacktest()} placeholder="SPY" maxLength={10}
              className="bg-surface border border-border rounded-lg px-3 py-2 text-sm font-mono w-full text-center focus:outline-none focus:border-accent" />
          </div>

          <div>
            <p className="text-[10px] text-text-muted uppercase tracking-wider mb-1.5">Date Range</p>
            <div className="space-y-1.5">
              <div>
                <p className="text-[10px] text-text-muted mb-1">From</p>
                <input type="date" value={startDate} max={endDate || undefined}
                  onChange={e => { setStartDate(e.target.value); setActivePreset(""); }}
                  className="bg-surface border border-border rounded-lg px-2 py-1.5 text-xs w-full focus:outline-none focus:border-accent text-text-primary [color-scheme:dark]" />
              </div>
              <div>
                <p className="text-[10px] text-text-muted mb-1">To</p>
                <input type="date" value={endDate} min={startDate || undefined}
                  max={new Date().toISOString().split("T")[0]}
                  onChange={e => { setEndDate(e.target.value); setActivePreset(""); }}
                  className="bg-surface border border-border rounded-lg px-2 py-1.5 text-xs w-full focus:outline-none focus:border-accent text-text-primary [color-scheme:dark]" />
              </div>
            </div>
          </div>

          <div>
            <p className="text-[10px] text-text-muted uppercase tracking-wider mb-1.5">Quick Select</p>
            <div className="grid grid-cols-3 gap-1">
              {[
                { label: "1Y", years: 1 }, { label: "2Y", years: 2 }, { label: "3Y", years: 3 },
                { label: "5Y", years: 5 }, { label: "10Y", years: 10 }, { label: "Max", years: 0 },
              ].map(({ label, years }) => (
                <button key={label} onClick={() => {
                  const today = new Date();
                  setEndDate(today.toISOString().split("T")[0]);
                  if (years === 0) { setStartDate("2000-01-01"); }
                  else { const s = new Date(today); s.setFullYear(today.getFullYear() - years); setStartDate(s.toISOString().split("T")[0]); }
                  setActivePreset(label);
                }} className={cn("py-1 text-[10px] font-bold rounded-md transition-all border",
                  activePreset === label ? "bg-accent/20 border-accent/40 text-accent" : "bg-surface hover:bg-surface-hover border-border text-text-muted hover:text-text-secondary"
                )}>{label}</button>
              ))}
            </div>
          </div>

          <button onClick={runBacktest} disabled={loading}
            className="w-full py-2 text-xs font-bold rounded-lg bg-accent/15 hover:bg-accent/25 text-accent border border-accent/30 disabled:opacity-40 transition-all">
            {loading ? "Running\u2026" : "\u25B6  Run Backtest"}
          </button>

          {data && (
            <div className="text-center space-y-0.5">
              <p className="text-[10px] text-text-muted">{data.ticker} &middot; {data.dataPoints.toLocaleString()} bars</p>
              <p className="text-[10px] text-text-muted">{data.period}</p>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <p className="text-[10px] text-text-muted uppercase tracking-wider px-1">
            {data ? `Strategies (${data.models.length})` : "Strategies"}
          </p>
          {!data && !loading && Object.entries(STRATEGY_META).map(([name, s]) => (
            <div key={s.num} className="glass-card p-3 opacity-40 rounded-xl">
              <span className="text-[10px] font-mono" style={{ color: s.color }}>{s.icon} {s.num}</span>
              <p className="text-xs font-semibold leading-tight mt-1">{name}</p>
            </div>
          ))}
          {data?.models.map((m, i) => {
            const meta = STRATEGY_META[m.modelName] ?? { num: `0${i+1}`, color: "#00d4ff", icon: "\u25C8" };
            const isSel = selectedIdx === i;
            return (
              <motion.button key={m.modelName} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }} onClick={() => setSelectedIdx(i)}
                className={cn("glass-card p-3 text-left rounded-xl border transition-all w-full",
                  isSel ? "bg-white/5" : "border-transparent hover:bg-surface-hover")}
                style={{ borderColor: isSel ? meta.color : undefined }}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-mono font-bold" style={{ color: meta.color }}>{meta.icon} STRATEGY {meta.num}</span>
                  {isSel && <span className="text-[9px] px-1.5 py-0.5 rounded-full font-bold" style={{ background: `${meta.color}22`, color: meta.color }}>ACTIVE</span>}
                </div>
                <p className="text-xs font-bold leading-tight mb-2">{m.modelName}</p>
                <div className="flex items-center justify-between">
                  <span className={cn("text-sm font-black", m.cumulativeReturn >= 0 ? "text-success" : "text-danger")}>
                    {m.cumulativeReturn >= 0 ? "+" : ""}{(m.cumulativeReturn * 100).toFixed(1)}%
                  </span>
                  <span className="text-[10px] text-text-muted">SR {m.sharpeRatio.toFixed(2)}</span>
                </div>
                <div className="mt-1.5 h-0.5 rounded-full bg-surface-hover overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${Math.min(100, Math.max(0, (m.sharpeRatio / 3) * 100))}%`, background: meta.color }} />
                </div>
              </motion.button>
            );
          })}
        </div>

        <div className="glass-card p-3 mt-auto">
          <p className="text-[10px] text-text-muted uppercase tracking-wider mb-1.5">Data Sources</p>
          {[{ n: "yfinance", b: "PRIMARY", c: "#22c55e" }, { n: "Alpha Vantage", b: "FALLBACK", c: "#00d4ff" },
            { n: "Finnhub", b: "FALLBACK", c: "#8b5cf6" }, { n: "Twelve Data", b: "FALLBACK", c: "#f59e0b" }].map(s => (
            <div key={s.n} className="flex items-center justify-between py-0.5">
              <span className="text-[10px] text-text-secondary">{s.n}</span>
              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded" style={{ background: `${s.c}20`, color: s.c }}>{s.b}</span>
            </div>
          ))}
        </div>
      </div>

      {/* RIGHT MAIN */}
      <div className="flex-1 min-w-0 overflow-y-auto space-y-4">
        {!data && !loading && !error && (
          <div className="glass-card p-16 text-center h-64 flex flex-col items-center justify-center">
            <p className="text-text-secondary font-semibold mb-1">Enter a ticker and press Run</p>
            <p className="text-xs text-text-muted">Runs 5 rule-based strategies on up to 20 years of data</p>
          </div>
        )}
        {loading && (
          <div className="space-y-4">
            <div className="grid grid-cols-4 gap-3">{Array.from({ length: 7 }).map((_, i) => <div key={i} className="skeleton h-16 rounded-xl" />)}</div>
            <div className="skeleton h-72 rounded-2xl" /><div className="skeleton h-48 rounded-2xl" />
          </div>
        )}
        {error && (
          <div className="glass-card p-6 text-center border border-danger/20">
            <p className="text-danger font-semibold mb-1">Backtest Failed</p>
            <p className="text-xs text-text-muted">{error}</p>
          </div>
        )}
        <AnimatePresence mode="wait">
          {data && !loading && selected && (
            <motion.div key={selected.modelName} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
              <div className="glass-card p-4">
                <div className="flex items-start gap-3">
                  <div className="w-1 self-stretch rounded-full flex-shrink-0" style={{ background: STRATEGY_META[selected.modelName]?.color ?? "#00d4ff" }} />
                  <div className="flex-1">
                    <span className="text-[10px] font-mono text-text-muted">STRATEGY {STRATEGY_META[selected.modelName]?.num ?? "\u2014"}</span>
                    <h3 className="text-base font-bold mb-1">{selected.modelName}</h3>
                    <p className="text-xs text-text-secondary leading-relaxed">{selected.description}</p>
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-4 gap-3 lg:grid-cols-7">
                <MetricBadge label="Return" value={`${(selected.cumulativeReturn*100).toFixed(1)}%`} positive={selected.cumulativeReturn > 0} />
                <MetricBadge label="Win Rate" value={`${(selected.winRate*100).toFixed(1)}%`} positive={selected.winRate > 0.5} />
                <MetricBadge label="Sharpe" value={selected.sharpeRatio.toFixed(2)} positive={selected.sharpeRatio > 1} />
                <MetricBadge label="Calmar" value={selected.calmarRatio.toFixed(2)} positive={selected.calmarRatio > 1} />
                <MetricBadge label="Max DD" value={`${(selected.maxDrawdown*100).toFixed(1)}%`} positive={false} />
                <MetricBadge label="Volatility" value={`${(selected.volatility*100).toFixed(1)}%`} />
                <MetricBadge label="Trades" value={selected.totalTrades.toString()} />
              </div>
              <PerformanceChart models={data.models} selectedIdx={selectedIdx} />
              <ComparisonTable models={data.models} selectedIdx={selectedIdx} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
