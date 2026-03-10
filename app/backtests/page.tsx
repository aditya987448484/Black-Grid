"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Bookmark, BookmarkCheck, ChevronDown, SlidersHorizontal, Check, Search } from "lucide-react";
import { getBacktestResults, getStrategyList, runCustomStrategy, searchCompanies } from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  BacktestSummaryResponse, BacktestModelResult,
  StrategyRegistry, SavedStrategy
} from "@/types/backtest";
import type { CompanySearchResult } from "@/types/universe";
import PerformanceChart from "@/components/backtest/PerformanceChart";
import ComparisonTable from "@/components/backtest/ComparisonTable";
import StrategyChat from "@/components/backtest/StrategyChat";

const CATEGORY_COLORS: Record<string, string> = {
  "Trend": "#00d4ff", "Oscillator": "#8b5cf6", "Volatility": "#22c55e",
  "Volume": "#f59e0b", "Confluence": "#ec4899", "Momentum": "#f97316", "Benchmark": "#6b7280",
};
const CUSTOM_COLORS = ["#a855f7", "#14b8a6", "#f43f5e", "#84cc16", "#06b6d4", "#fb923c"];

function MetricBadge({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
  return (
    <div className="bg-surface rounded-xl p-3">
      <p className="text-[10px] text-text-muted uppercase tracking-wider mb-1">{label}</p>
      <p className={cn("text-sm font-black",
        positive === true ? "text-success" : positive === false ? "text-danger" : "text-text-primary"
      )}>{value}</p>
    </div>
  );
}

function IndicatorDropdown({ registry, activeKeys, onToggle, onSelectAll, onClearAll }:
  { registry: StrategyRegistry; activeKeys: string[]; onToggle: (k: string) => void; onSelectAll: (cat?: string) => void; onClearAll: (cat?: string) => void }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const categories = Object.entries(registry).reduce((acc, [key, entry]) => {
    if (!acc[entry.category]) acc[entry.category] = [];
    acc[entry.category].push({ key, ...entry });
    return acc;
  }, {} as Record<string, any[]>);

  const filtered = Object.entries(categories).reduce((acc, [cat, strats]) => {
    const f = strats.filter((s: any) => s.name.toLowerCase().includes(search.toLowerCase()));
    if (f.length > 0) acc[cat] = f;
    return acc;
  }, {} as typeof categories);

  useEffect(() => {
    function h(e: MouseEvent) {
      const el = document.getElementById("indicator-dropdown");
      if (el && !el.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  return (
    <div className="relative" id="indicator-dropdown">
      <button onClick={() => setOpen(p => !p)}
        className={cn("flex items-center gap-2 px-3 py-1.5 rounded-xl border text-[11px] font-semibold transition-all",
          open ? "bg-accent/10 border-accent/30 text-accent" : "bg-surface border-border text-text-secondary hover:border-white/20")}>
        <SlidersHorizontal className="h-3.5 w-3.5" />
        Indicators
        {activeKeys.length > 0 && (
          <span className="px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-accent/20 text-accent">{activeKeys.length}</span>
        )}
        <ChevronDown className={cn("h-3 w-3 transition-transform", open && "rotate-180")} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-2 w-[480px] bg-[#09090f] border border-white/[0.1] rounded-2xl shadow-2xl shadow-black/80 z-50 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
            <span className="text-xs font-bold">Select Indicators</span>
            <div className="flex items-center gap-2">
              <button onClick={() => onSelectAll()} className="text-[10px] text-accent hover:text-accent/80 px-2 py-1 rounded-lg hover:bg-accent/10">All</button>
              <button onClick={() => onClearAll()} className="text-[10px] text-text-muted hover:text-danger px-2 py-1 rounded-lg hover:bg-danger/10">Clear</button>
              <button onClick={() => setOpen(false)} className="text-text-muted hover:text-text-primary"><X className="h-3.5 w-3.5" /></button>
            </div>
          </div>
          <div className="px-4 py-2 border-b border-white/[0.05]">
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search indicators..."
              className="w-full bg-surface rounded-xl px-3 py-2 text-[12px] outline-none border border-border focus:border-accent text-text-primary placeholder-text-muted" />
          </div>
          <div className="overflow-y-auto max-h-80 py-2">
            {Object.entries(filtered).map(([cat, strats]) => {
              const color = CATEGORY_COLORS[cat] ?? "#00d4ff";
              return (
                <div key={cat} className="mb-1">
                  <div className="flex items-center justify-between px-4 py-1.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color }}>{cat}</span>
                    <button onClick={() => {
                      const allActive = strats.every((s: any) => activeKeys.includes(s.key));
                      allActive ? onClearAll(cat) : onSelectAll(cat);
                    }} className="text-[9px] text-text-muted hover:text-accent transition-colors">
                      {strats.every((s: any) => activeKeys.includes(s.key)) ? "Clear" : "All"}
                    </button>
                  </div>
                  {strats.map((s: any) => {
                    const isActive = activeKeys.includes(s.key);
                    return (
                      <button key={s.key} onClick={() => onToggle(s.key)}
                        className="w-full flex items-center gap-3 px-5 py-2 hover:bg-white/[0.02] transition-colors text-left">
                        <div className={cn("w-4 h-4 rounded-md flex-shrink-0 flex items-center justify-center border transition-all",
                          isActive ? "border-transparent" : "border-white/20")}
                          style={isActive ? { backgroundColor: color } : undefined}>
                          {isActive && <Check className="h-2.5 w-2.5 text-black" strokeWidth={3} />}
                        </div>
                        <div className="flex-1">
                          <span className="text-[11px] font-medium text-text-secondary">{s.name}</span>
                          <p className="text-[10px] text-text-muted line-clamp-1">{s.description}</p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              );
            })}
          </div>
          <div className="border-t border-white/[0.06] px-4 py-2.5 flex items-center justify-between">
            <div className="flex flex-wrap gap-1 flex-1">
              {activeKeys.slice(0, 4).map(k => {
                const e = registry[k]; if (!e) return null;
                const color = CATEGORY_COLORS[e.category] ?? "#00d4ff";
                return (
                  <span key={k} className="text-[10px] px-2 py-0.5 rounded-full border"
                    style={{ color, borderColor: `${color}40`, backgroundColor: `${color}12` }}>
                    {e.name}
                  </span>
                );
              })}
              {activeKeys.length > 4 && <span className="text-[10px] text-text-muted">+{activeKeys.length - 4}</span>}
            </div>
            <button onClick={() => setOpen(false)}
              className="px-4 py-1.5 rounded-xl text-[11px] font-bold bg-accent text-background hover:bg-accent/80 transition-colors flex-shrink-0 ml-2">
              Apply ({activeKeys.length})
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function TickerSearchInput({ value, onChange, onSubmit }: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
}) {
  const [results, setResults] = useState<CompanySearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [idx, setIdx] = useState(-1);
  const debounce = useRef<ReturnType<typeof setTimeout>>(undefined);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (value.length < 1) { setResults([]); setOpen(false); return; }
    clearTimeout(debounce.current);
    debounce.current = setTimeout(() => {
      searchCompanies(value)
        .then(r => { setResults(r.results); setOpen(r.results.length > 0); setIdx(-1); })
        .catch(() => setResults([]));
    }, 200);
    return () => clearTimeout(debounce.current);
  }, [value]);

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  function select(symbol: string) {
    onChange(symbol);
    setOpen(false);
    setTimeout(onSubmit, 0);
  }

  return (
    <div ref={wrapRef} className="relative flex-1">
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-text-muted pointer-events-none" />
        <input
          value={value}
          onChange={e => onChange(e.target.value.toUpperCase())}
          onFocus={() => results.length > 0 && setOpen(true)}
          onKeyDown={e => {
            if (e.key === "ArrowDown") { e.preventDefault(); setIdx(i => Math.min(i + 1, results.length - 1)); }
            else if (e.key === "ArrowUp") { e.preventDefault(); setIdx(i => Math.max(i - 1, -1)); }
            else if (e.key === "Escape") setOpen(false);
            else if (e.key === "Enter") {
              if (idx >= 0 && results[idx]) { select(results[idx].symbol); }
              else onSubmit();
            }
          }}
          placeholder="SPY" maxLength={10}
          className="bg-surface border border-border rounded-lg pl-7 pr-3 py-1.5 text-sm font-mono w-full text-center focus:outline-none focus:border-accent"
        />
      </div>
      {open && results.length > 0 && (
        <div className="absolute top-full mt-1 left-0 w-72 bg-[#09090f] border border-white/10 rounded-xl shadow-2xl shadow-black/80 z-50 max-h-64 overflow-y-auto">
          {results.slice(0, 8).map((r, i) => (
            <button key={r.symbol} onClick={() => select(r.symbol)}
              className={cn(
                "w-full text-left px-4 py-2.5 flex items-center justify-between transition-colors",
                i === idx ? "bg-accent/10" : "hover:bg-white/[0.04]"
              )}>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-accent">{r.symbol}</span>
                  {r.exchange && (
                    <span className="text-[9px] text-text-muted bg-white/[0.06] rounded px-1.5 py-0.5">{r.exchange}</span>
                  )}
                </div>
                <p className="text-xs text-text-secondary truncate">{r.name}</p>
              </div>
              {r.sector && <span className="text-[10px] text-text-muted flex-shrink-0 ml-3">{r.sector}</span>}
            </button>
          ))}
        </div>
      )}
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
  const [savedStrategies, setSavedStrategies] = useState<SavedStrategy[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [registry, setRegistry] = useState<StrategyRegistry>({});
  const [activeIndicators, setActiveIndicators] = useState<string[]>([
    "rsi_mean_rev", "macd_trend", "bollinger_squeeze", "atr_channel", "rsi_macd_conf", "buy_hold"
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
      const result = await getBacktestResults(tickerInput.trim().toUpperCase(), startDate, endDate);
      if (result.error) {
        setError(result.error);
        setData(null);
      } else {
        setData(result);
      }
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }, [tickerInput, startDate, endDate]);

  const handleRunCustom = useCallback(async (key: string, params: Record<string, number>, customName: string, precomputedResult?: BacktestModelResult) => {
    if (precomputedResult) {
      precomputedResult.isCustom = true;
      precomputedResult.customLabel = customName;
      precomputedResult.modelName = customName;
      setCustomModels(prev => {
        const idx = prev.findIndex(m => m.customLabel === customName);
        if (idx >= 0) { const n = [...prev]; n[idx] = precomputedResult; return n; }
        return [...prev, precomputedResult];
      });
      // Auto-run main backtest if no baseline data yet (so chart has context)
      if (!data && !loading) {
        runBacktest();
      }
      return;
    }
    try {
      const result = await runCustomStrategy({ ticker: tickerInput.toUpperCase(), strategy_key: key, params, custom_name: customName, start_date: startDate, end_date: endDate });
      result.isCustom = true; result.customLabel = customName; result.modelName = customName;
      setCustomModels(prev => {
        const idx = prev.findIndex(m => m.customLabel === customName);
        if (idx >= 0) { const n = [...prev]; n[idx] = result; return n; }
        return [...prev, result];
      });
      // Auto-run main backtest if no baseline data yet
      if (!data && !loading) {
        runBacktest();
      }
    } catch (e: any) { console.error("Custom strategy failed:", e); }
  }, [tickerInput, startDate, endDate, data, loading, runBacktest]);

  function toggleIndicator(key: string) {
    setActiveIndicators(prev => prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]);
  }
  function selectAll(cat?: string) {
    const keys = Object.entries(registry).filter(([, e]) => !cat || e.category === cat).map(([k]) => k);
    setActiveIndicators(prev => Array.from(new Set([...prev, ...keys])));
  }
  function clearAll(cat?: string) {
    if (!cat) { setActiveIndicators([]); return; }
    const catKeys = new Set(Object.entries(registry).filter(([, e]) => e.category === cat).map(([k]) => k));
    setActiveIndicators(prev => prev.filter(k => !catKeys.has(k)));
  }

  const selected = allModels[selectedIdx] ?? null;
  const getColor = (m: BacktestModelResult) => {
    if (m.isCustom) {
      const customIdx = customModels.indexOf(m);
      return CUSTOM_COLORS[customIdx % CUSTOM_COLORS.length];
    }
    return CATEGORY_COLORS[m.category ?? ""] ?? "#00d4ff";
  };

  return (
    <div className="flex h-[calc(100vh-7rem)] gap-0">

      {/* LEFT: Chat + Controls */}
      <div className="w-[340px] flex-shrink-0 border-r border-white/[0.06] flex flex-col">

        {/* Ticker + Date controls */}
        <div className="px-3 pt-3 pb-2 border-b border-white/[0.06] space-y-2">
          <div className="flex gap-2">
            <TickerSearchInput
              value={tickerInput}
              onChange={setTickerInput}
              onSubmit={runBacktest}
            />
            <button onClick={runBacktest} disabled={loading}
              className="px-3 py-1.5 text-xs font-bold rounded-lg bg-accent/15 hover:bg-accent/25 text-accent border border-accent/30 disabled:opacity-40 transition-all whitespace-nowrap">
              {loading ? "\u2026" : "\u25B6 Run"}
            </button>
          </div>
          <div className="flex gap-1.5">
            <div className="flex-1">
              <p className="text-[9px] text-text-muted mb-0.5">From</p>
              <input type="date" value={startDate} max={endDate}
                onChange={e => { setStartDate(e.target.value); setActivePreset(""); }}
                className="bg-surface border border-border rounded-md px-2 py-1 text-[11px] w-full focus:outline-none focus:border-accent [color-scheme:dark]" />
            </div>
            <div className="flex-1">
              <p className="text-[9px] text-text-muted mb-0.5">To</p>
              <input type="date" value={endDate} min={startDate} max={new Date().toISOString().split("T")[0]}
                onChange={e => { setEndDate(e.target.value); setActivePreset(""); }}
                className="bg-surface border border-border rounded-md px-2 py-1 text-[11px] w-full focus:outline-none focus:border-accent [color-scheme:dark]" />
            </div>
          </div>
          <div className="flex gap-1">
            {[{l:"1Y",y:1},{l:"2Y",y:2},{l:"3Y",y:3},{l:"5Y",y:5},{l:"10Y",y:10},{l:"Max",y:0}].map(({l,y}) => (
              <button key={l} onClick={() => {
                const today = new Date(); setEndDate(today.toISOString().split("T")[0]);
                if (y === 0) setStartDate("2000-01-01");
                else { const s = new Date(today); s.setFullYear(today.getFullYear()-y); setStartDate(s.toISOString().split("T")[0]); }
                setActivePreset(l);
              }}
                className={cn("flex-1 py-0.5 text-[9px] font-bold rounded-md border transition-all",
                  activePreset === l ? "bg-accent/15 border-accent/30 text-accent" : "bg-surface border-border text-text-muted hover:text-text-secondary")}>
                {l}
              </button>
            ))}
          </div>

          {/* Custom strategies above indicators */}
          {customModels.length > 0 && (
            <div className="pt-1">
              <p className="text-[10px] text-text-muted uppercase tracking-wider mb-1.5">Custom Strategies</p>
              <div className="space-y-1">
                {customModels.map((m, i) => {
                  const color = CUSTOM_COLORS[i % CUSTOM_COLORS.length];
                  const isSaved = savedStrategies.some(s => s.label === m.modelName);
                  return (
                    <div key={m.customLabel ?? i}
                      className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                      <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: color }} />
                      <span className="text-[11px] font-semibold flex-1 text-text-primary">{m.customLabel ?? m.modelName}</span>
                      <span className={cn("text-[10px] font-bold", m.cumulativeReturn >= 0 ? "text-success" : "text-danger")}>
                        {m.cumulativeReturn >= 0 ? "+" : ""}{(m.cumulativeReturn*100).toFixed(1)}%
                      </span>
                      <button onClick={() => {
                        const saved: SavedStrategy = {
                          id: `${Date.now()}`, label: m.customLabel ?? m.modelName,
                          strategyKey: m.strategyKey ?? "", params: m.params ?? {},
                          ticker: tickerInput, savedAt: new Date().toISOString(), result: m,
                        };
                        setSavedStrategies(prev => [saved, ...prev]);
                        try { localStorage.setItem("blackgrid_saved_strategies", JSON.stringify([saved, ...savedStrategies])); } catch {}
                      }} disabled={isSaved}
                        className="text-gray-600 hover:text-accent disabled:text-accent transition-colors">
                        {isSaved ? <BookmarkCheck className="h-3 w-3" /> : <Bookmark className="h-3 w-3" />}
                      </button>
                      <button onClick={() => setCustomModels(prev => prev.filter((_, j) => j !== i))}
                        className="text-gray-600 hover:text-danger transition-colors">
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {data && (
            <p className="text-[10px] text-text-muted text-center">
              {data.ticker} · {data.dataPoints.toLocaleString()} bars · {data.period}
            </p>
          )}
        </div>

        {/* Strategy Chat */}
        <div className="flex-1 min-h-0">
          <StrategyChat
            onRunStrategy={handleRunCustom}
            onSaveStrategy={s => setSavedStrategies(prev => [s, ...prev])}
            loading={loading}
            registry={registry}
            ticker={tickerInput}
            startDate={startDate}
            endDate={endDate}
            customResults={customModels}
          />
        </div>
      </div>

      {/* RIGHT: Results */}
      <div className="flex-1 min-w-0 flex flex-col overflow-hidden">

        {/* Top bar: indicator dropdown + active pills */}
        <div className="px-4 pt-3 pb-2 border-b border-white/[0.04] flex items-center gap-3">
          {Object.keys(registry).length > 0 && (
            <IndicatorDropdown registry={registry} activeKeys={activeIndicators}
              onToggle={toggleIndicator} onSelectAll={selectAll} onClearAll={clearAll} />
          )}
          <div className="flex-1 min-w-0 flex items-center gap-1.5 overflow-x-auto" style={{ scrollbarWidth: "none" }}>
            {activeIndicators.length === 0 && (
              <span className="text-[11px] text-text-muted italic">No indicators selected</span>
            )}
            {activeIndicators.map(key => {
              const entry = registry[key]; if (!entry) return null;
              const color = CATEGORY_COLORS[entry.category] ?? "#00d4ff";
              return (
                <span key={key} onClick={() => toggleIndicator(key)}
                  className="flex items-center gap-1 text-[10px] px-2 py-1 rounded-lg border font-medium flex-shrink-0 cursor-pointer hover:opacity-70 transition-all"
                  style={{ color, borderColor: `${color}40`, backgroundColor: `${color}12` }}>
                  {entry.name} <X className="h-2.5 w-2.5 opacity-60" />
                </span>
              );
            })}
          </div>
          {activeIndicators.length > 0 && (
            <span className="text-[10px] text-text-muted flex-shrink-0">{activeIndicators.length} active</span>
          )}
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-4 pt-3 pb-4 space-y-4">

          {!data && !loading && !error && (
            <div className="glass-card p-16 text-center h-64 flex flex-col items-center justify-center">
              <p className="text-3xl mb-3">📊</p>
              <p className="text-text-secondary font-semibold mb-1">Enter a ticker and press Run</p>
              <p className="text-xs text-text-muted">Select indicators or describe a custom strategy in the chat</p>
            </div>
          )}

          {loading && (
            <div className="space-y-3">
              <div className="grid grid-cols-7 gap-2">{Array.from({length:7}).map((_,i)=><div key={i} className="skeleton h-14 rounded-xl"/>)}</div>
              <div className="skeleton h-72 rounded-2xl"/>
              <div className="skeleton h-48 rounded-2xl"/>
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

                {/* Strategy selector tabs */}
                <div className="flex flex-wrap gap-2">
                  {allModels.map((m, i) => {
                    const color = getColor(m);
                    return (
                      <button key={(m.customLabel ?? m.modelName) + i}
                        onClick={() => setSelectedIdx(i)}
                        className={cn("px-3 py-1.5 rounded-xl text-[11px] font-semibold border transition-all",
                          selectedIdx === i ? "" : "border-transparent hover:bg-surface-hover")}
                        style={selectedIdx === i ? { borderColor: color, color, backgroundColor: `${color}10` } : {}}>
                        {m.isCustom && <span className="mr-1 text-[9px]">✦</span>}
                        {m.customLabel ?? m.modelName}
                      </button>
                    );
                  })}
                  {customModels.length > 0 && (
                    <button onClick={() => setCustomModels([])}
                      className="px-2.5 py-1.5 rounded-xl text-[10px] text-text-muted border border-border hover:border-danger/30 hover:text-danger transition-all">
                      Clear custom
                    </button>
                  )}
                </div>

                {/* Selected strategy detail */}
                {selected && (
                  <div className="glass-card p-4">
                    <div className="flex items-start gap-3">
                      <div className="w-1 self-stretch rounded-full flex-shrink-0"
                        style={{ background: getColor(selected) }} />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-0.5">
                          {selected.isCustom && <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-accent/10 text-accent border border-accent/20 font-bold">CUSTOM · Claude</span>}
                          <span className="text-[10px] text-text-muted">{selected.category}</span>
                        </div>
                        <h3 className="text-sm font-bold mb-1">{selected.customLabel ?? selected.modelName}</h3>
                        <p className="text-xs text-text-secondary leading-relaxed">{selected.description}</p>
                        {selected.params && Object.keys(selected.params).length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {Object.entries(selected.params).map(([k, v]) => (
                              <span key={k} className="text-[10px] px-2 py-0.5 rounded-full bg-surface border border-border text-text-muted">
                                {k}: {v}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Metrics row */}
                {selected && (
                  <div className="grid grid-cols-4 gap-2 lg:grid-cols-7">
                    <MetricBadge label="Return" value={`${(selected.cumulativeReturn*100).toFixed(1)}%`} positive={selected.cumulativeReturn > 0} />
                    <MetricBadge label="Win Rate" value={`${(selected.winRate*100).toFixed(1)}%`} positive={selected.winRate > 0.5} />
                    <MetricBadge label="Sharpe" value={selected.sharpeRatio.toFixed(2)} positive={selected.sharpeRatio > 1} />
                    <MetricBadge label="Calmar" value={selected.calmarRatio?.toFixed(2) ?? "\u2014"} positive={(selected.calmarRatio ?? 0) > 1} />
                    <MetricBadge label="Max DD" value={`${(selected.maxDrawdown*100).toFixed(1)}%`} positive={false} />
                    <MetricBadge label="Volatility" value={`${(selected.volatility*100).toFixed(1)}%`} />
                    <MetricBadge label="Trades" value={selected.totalTrades?.toString() ?? "\u2014"} />
                  </div>
                )}

                {data && data.dataPoints < 500 && (
                  <div className="glass-card p-3 border border-yellow-500/20 bg-yellow-500/5">
                    <p className="text-xs text-yellow-400 font-semibold">Warning: Short window ({data.dataPoints} bars) — try 3Y+ for reliable signals</p>
                  </div>
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
