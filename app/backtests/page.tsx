"use client";

import { useState, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { getBacktestSummary, getStrategyList, runCustomStrategy } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { BacktestSummaryResponse, BacktestModelResult, StrategyRegistry } from "@/types/backtest";
import PerformanceChart from "@/components/backtest/PerformanceChart";
import ComparisonTable from "@/components/backtest/ComparisonTable";
import StrategyChat from "@/components/backtest/StrategyChat";
import IndicatorBar from "@/components/backtest/IndicatorBar";

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
  const [startDate, setStartDate] = useState<string>(() => {
    const d = new Date(); d.setFullYear(d.getFullYear() - 5);
    return d.toISOString().split("T")[0];
  });
  const [endDate, setEndDate] = useState(new Date().toISOString().split("T")[0]);
  const [activePreset, setActivePreset] = useState("5Y");

  const [data, setData] = useState<BacktestSummaryResponse | null>(null);
  const [customModels, setCustomModels] = useState<BacktestModelResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [registry, setRegistry] = useState<StrategyRegistry>({});
  const [activeIndicators, setActiveIndicators] = useState<string[]>([
    "rsi_mean_rev", "macd_trend", "bollinger_squeeze", "atr_channel", "rsi_macd_conf", "buy_hold",
  ]);

  useEffect(() => { getStrategyList().then(setRegistry).catch(console.error); }, []);

  const allModels = [
    ...(data?.models.filter(m => activeIndicators.includes(m.strategyKey ?? "")) ?? []),
    ...customModels,
  ];

  const runBacktest = useCallback(async () => {
    if (!tickerInput.trim()) return;
    setLoading(true); setError(null); setSelectedIdx(0);
    try {
      const result = await getBacktestSummary(tickerInput.trim().toUpperCase(), startDate, endDate);
      setData(result);
    } catch (e: any) { setError(e.message || "Backtest failed"); }
    finally { setLoading(false); }
  }, [tickerInput, startDate, endDate]);

  const handleRunCustom = useCallback(async (key: string, params: Record<string, number>, customName: string) => {
    setChatLoading(true);
    try {
      const result = await runCustomStrategy({
        ticker: tickerInput.toUpperCase(), strategy_key: key, params,
        custom_name: customName, start_date: startDate, end_date: endDate,
      });
      if ((result as any).error) { console.error((result as any).error); return; }
      result.isCustom = true;
      result.customLabel = customName;
      setCustomModels(prev => [...prev, result]);
    } catch (e) { console.error("Custom strategy failed:", e); }
    finally { setChatLoading(false); }
  }, [tickerInput, startDate, endDate]);

  const selected = allModels[selectedIdx] ?? null;

  return (
    <div className="flex h-[calc(100vh-7rem)] gap-0">

      {/* ── LEFT: Chat Panel ─────────────────────────────── */}
      <div className="w-[340px] flex-shrink-0 border-r border-white/[0.06] flex flex-col">
        <div className="px-3 pt-3 pb-2 border-b border-white/[0.05] space-y-2">
          <div className="flex gap-2">
            <input value={tickerInput} onChange={e => setTickerInput(e.target.value.toUpperCase())}
              onKeyDown={e => e.key === "Enter" && runBacktest()} placeholder="SPY" maxLength={10}
              className="bg-surface border border-border rounded-lg px-3 py-1.5 text-sm font-mono w-full text-center focus:outline-none focus:border-accent" />
            <button onClick={runBacktest} disabled={loading}
              className="px-3 py-1.5 text-xs font-bold rounded-lg bg-accent/15 hover:bg-accent/25 text-accent border border-accent/30 disabled:opacity-40 whitespace-nowrap flex-shrink-0">
              {loading ? "\u2026" : "\u25B6 Run"}
            </button>
          </div>
          <div className="flex gap-2">
            <div className="flex-1">
              <p className="text-[9px] text-text-muted mb-0.5">From</p>
              <input type="date" value={startDate} max={endDate}
                onChange={e => { setStartDate(e.target.value); setActivePreset(""); }}
                className="bg-surface border border-border rounded-md px-2 py-1 text-[11px] w-full focus:outline-none focus:border-accent text-text-primary [color-scheme:dark]" />
            </div>
            <div className="flex-1">
              <p className="text-[9px] text-text-muted mb-0.5">To</p>
              <input type="date" value={endDate} min={startDate} max={new Date().toISOString().split("T")[0]}
                onChange={e => { setEndDate(e.target.value); setActivePreset(""); }}
                className="bg-surface border border-border rounded-md px-2 py-1 text-[11px] w-full focus:outline-none focus:border-accent text-text-primary [color-scheme:dark]" />
            </div>
          </div>
          <div className="flex gap-1">
            {[{l:"1Y",y:1},{l:"2Y",y:2},{l:"3Y",y:3},{l:"5Y",y:5},{l:"10Y",y:10},{l:"Max",y:0}].map(({l,y}) => (
              <button key={l} onClick={() => {
                const today = new Date(); setEndDate(today.toISOString().split("T")[0]);
                if (y === 0) setStartDate("2000-01-01");
                else { const s = new Date(today); s.setFullYear(today.getFullYear()-y); setStartDate(s.toISOString().split("T")[0]); }
                setActivePreset(l);
              }} className={cn("flex-1 py-1 text-[9px] font-bold rounded-md border transition-all",
                activePreset === l ? "bg-accent/15 border-accent/30 text-accent" : "bg-surface border-border text-text-muted")}>
                {l}
              </button>
            ))}
          </div>
          {data && <p className="text-[10px] text-text-muted text-center">{data.ticker} &middot; {data.dataPoints.toLocaleString()} bars &middot; {data.period}</p>}
        </div>

        <div className="flex-1 min-h-0">
          <StrategyChat onRunStrategy={handleRunCustom} loading={chatLoading}
            registry={registry} ticker={tickerInput} customResults={customModels} />
        </div>
      </div>

      {/* ── RIGHT: Main Content ───────────────────────────── */}
      <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
        <div className="px-4 pt-3 flex-shrink-0">
          {Object.keys(registry).length > 0 && (
            <IndicatorBar registry={registry} activeKeys={activeIndicators}
              onToggle={k => setActiveIndicators(prev => prev.includes(k) ? prev.filter(x => x !== k) : [...prev, k])} />
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-4 pb-4 pt-3 space-y-4">
          {!data && !loading && !error && (
            <div className="glass-card p-16 text-center flex flex-col items-center justify-center">
              <p className="text-text-secondary font-semibold mb-1">Enter a ticker and press Run</p>
              <p className="text-xs text-text-muted">Select indicators above, or describe a custom strategy in the chat</p>
            </div>
          )}
          {loading && (
            <div className="space-y-3">
              <div className="grid grid-cols-7 gap-2">{Array.from({length:7}).map((_,i) => <div key={i} className="skeleton h-14 rounded-xl" />)}</div>
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
            {allModels.length > 0 && !loading && (
              <motion.div key="results" initial={{opacity:0,y:6}} animate={{opacity:1,y:0}} className="space-y-4">
                {/* Strategy selector */}
                <div className="flex flex-wrap gap-2">
                  {allModels.map((m, i) => (
                    <button key={m.modelName + i} onClick={() => setSelectedIdx(i)}
                      className={cn("px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all",
                        selectedIdx === i ? "bg-white/[0.07] border-accent/50 text-accent" : "border-transparent text-text-muted hover:bg-surface-hover")}>
                      {m.isCustom && <span className="mr-1 text-[9px] opacity-70">\u2726</span>}
                      {m.customLabel ?? m.modelName}
                    </button>
                  ))}
                  {customModels.length > 0 && (
                    <button onClick={() => setCustomModels([])}
                      className="px-2.5 py-1.5 rounded-xl text-[10px] text-text-muted border border-border hover:border-danger/30 hover:text-danger transition-all">
                      Clear custom
                    </button>
                  )}
                </div>

                {selected && (
                  <>
                    <div className="glass-card p-4">
                      <div className="flex items-center gap-2 mb-0.5">
                        {selected.isCustom && <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-accent/10 text-accent border border-accent/20 font-bold">CUSTOM</span>}
                        <span className="text-[10px] text-text-muted">{selected.category}</span>
                      </div>
                      <h3 className="text-sm font-bold mb-1">{selected.customLabel ?? selected.modelName}</h3>
                      <p className="text-xs text-text-secondary leading-relaxed">{selected.description}</p>
                      {selected.params && (
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {Object.entries(selected.params).map(([k, v]) => (
                            <span key={k} className="text-[10px] px-2 py-0.5 rounded-full bg-surface border border-border text-text-muted">{k}: {v}</span>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="grid grid-cols-4 gap-2 lg:grid-cols-7">
                      <MetricBadge label="Return" value={`${(selected.cumulativeReturn*100).toFixed(1)}%`} positive={selected.cumulativeReturn > 0} />
                      <MetricBadge label="Win Rate" value={`${(selected.winRate*100).toFixed(1)}%`} positive={selected.winRate > 0.5} />
                      <MetricBadge label="Sharpe" value={selected.sharpeRatio.toFixed(2)} positive={selected.sharpeRatio > 1} />
                      <MetricBadge label="Calmar" value={selected.calmarRatio.toFixed(2)} positive={selected.calmarRatio > 1} />
                      <MetricBadge label="Max DD" value={`${(selected.maxDrawdown*100).toFixed(1)}%`} positive={false} />
                      <MetricBadge label="Volatility" value={`${(selected.volatility*100).toFixed(1)}%`} />
                      <MetricBadge label="Trades" value={selected.totalTrades.toString()} />
                    </div>

                    {data && data.dataPoints < 500 && (
                      <div className="glass-card p-3 border border-warning/20 bg-warning/5">
                        <p className="text-xs text-warning font-semibold">Warning: Short window ({data.dataPoints} bars)</p>
                        <p className="text-[11px] text-text-muted">Try 3Y or 5Y for better signals.</p>
                      </div>
                    )}
                  </>
                )}

                <PerformanceChart models={allModels} selectedIdx={selectedIdx} />
                <ComparisonTable models={allModels} selectedIdx={selectedIdx} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
