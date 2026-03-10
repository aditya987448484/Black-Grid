"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Sparkles, Bookmark, BookmarkCheck, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { strategyChat } from "@/lib/api";
import type { ChatStrategyMessage, StrategyRegistry, BacktestModelResult, SavedStrategy } from "@/types/backtest";

const SUGGESTIONS = [
  { text: "Run RSI mean reversion with oversold at 25 on this ticker", icon: "\u25C8" },
  { text: "Backtest a Bollinger Band squeeze with tighter bands (std=1.5)", icon: "\u25CE" },
  { text: "Run the turtle trading system with 55-day breakout", icon: "\u25C7" },
  { text: "What strategy has the best Sharpe ratio for volatile stocks?", icon: "\u26A1" },
];

const STATUS = ["Asking Claude...", "Parsing strategy...", "Fetching data...", "Running backtest...", "Crunching metrics..."];

const CHAT_STORAGE_KEY = "blackgrid_backtest_chat";
const SAVED_STRATEGIES_KEY = "blackgrid_saved_strategies";

interface Props {
  onRunStrategy: (key: string, params: Record<string, number>, customName: string, result?: BacktestModelResult) => void;
  onSaveStrategy: (strategy: SavedStrategy) => void;
  loading: boolean;
  registry: StrategyRegistry;
  ticker: string;
  startDate?: string;
  endDate?: string;
  customResults: BacktestModelResult[];
}

export default function StrategyChat({
  onRunStrategy, onSaveStrategy, loading, registry, ticker, startDate, endDate, customResults,
}: Props) {
  const [messages, setMessages] = useState<ChatStrategyMessage[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const stored = localStorage.getItem(CHAT_STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch { return []; }
  });
  const [input, setInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [statusIdx, setStatusIdx] = useState(0);
  const [savedStrategies, setSavedStrategies] = useState<SavedStrategy[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const stored = localStorage.getItem(SAVED_STRATEGIES_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch { return []; }
  });
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Persist chat to localStorage
  useEffect(() => {
    try { localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages.slice(-50))); }
    catch {}
  }, [messages]);

  useEffect(() => {
    try { localStorage.setItem(SAVED_STRATEGIES_KEY, JSON.stringify(savedStrategies)); }
    catch {}
  }, [savedStrategies]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, chatLoading]);

  useEffect(() => {
    if (!chatLoading) return;
    setStatusIdx(0);
    const t = setInterval(() => setStatusIdx(i => (i + 1) % STATUS.length), 1400);
    return () => clearInterval(t);
  }, [chatLoading]);

  const submit = useCallback(async (text?: string) => {
    const val = (text || input).trim();
    if (!val || chatLoading || loading) return;
    setInput("");
    if (inputRef.current) inputRef.current.style.height = "auto";

    const userMsg: ChatStrategyMessage = { role: "user", content: val };
    setMessages(prev => [...prev, userMsg]);
    setChatLoading(true);

    try {
      const response = await strategyChat({
        message: val,
        history: messages.slice(-8).map(m => ({ role: m.role, content: m.content })),
        ticker,
        start_date: startDate,
        end_date: endDate,
      });

      const assistantMsg: ChatStrategyMessage = {
        role: "assistant",
        content: response.reply,
        strategyResult: response.strategyResult as BacktestModelResult | undefined,
        marketContext: response.market_context,
      };
      setMessages(prev => [...prev, assistantMsg]);

      // If strategy result came back, push to parent
      if (response.strategy_key && response.strategyResult) {
        const customName = `Custom ${customResults.length + 1}`;
        onRunStrategy(
          response.strategy_key,
          response.params,
          customName,
          response.strategyResult as BacktestModelResult,
        );
      } else if (response.strategy_key && response.run_immediately) {
        const customName = `Custom ${customResults.length + 1}`;
        onRunStrategy(response.strategy_key, response.params, customName);
      }
    } catch (e: any) {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: `Error: ${e.message || "Something went wrong"}. Make sure ANTHROPIC_API_KEY is set in your .env file.`,
      }]);
    } finally {
      setChatLoading(false);
    }
  }, [input, chatLoading, loading, messages, ticker, startDate, endDate, customResults, onRunStrategy]);

  function saveStrategy(result: BacktestModelResult) {
    const saved: SavedStrategy = {
      id: `${Date.now()}`,
      label: result.modelName,
      strategyKey: result.strategyKey ?? "",
      params: result.params ?? {},
      ticker,
      savedAt: new Date().toISOString(),
      result,
    };
    setSavedStrategies(prev => [saved, ...prev.slice(0, 19)]);
    onSaveStrategy(saved);
  }

  function deleteSaved(id: string) {
    setSavedStrategies(prev => prev.filter(s => s.id !== id));
  }

  function clearChat() {
    setMessages([]);
    try { localStorage.removeItem(CHAT_STORAGE_KEY); } catch {}
  }

  // Empty state
  if (messages.length === 0 && !chatLoading) {
    return (
      <div className="flex flex-col h-full bg-[#050508]">
        <div className="flex-1 overflow-y-auto px-4 pt-4 pb-2 space-y-4">
          {/* Header */}
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-accent/20 to-purple-500/20 flex items-center justify-center">
              <Sparkles className="h-4 w-4 text-accent" />
            </div>
            <div>
              <h3 className="text-xs font-bold text-text-primary">Strategy Builder</h3>
              <p className="text-[10px] text-text-muted">Powered by Claude · Natural language</p>
            </div>
          </div>

          <p className="text-[11px] text-text-secondary leading-relaxed">
            Describe any strategy in plain English. Claude will design it, set the parameters,
            and run the backtest automatically.
          </p>

          {/* Suggestions */}
          <div>
            <p className="text-[10px] text-text-muted uppercase tracking-wider mb-2">Try asking</p>
            <div className="space-y-1.5">
              {SUGGESTIONS.map(s => (
                <button key={s.text} onClick={() => submit(s.text)}
                  className="w-full text-left px-3 py-2 rounded-lg border border-white/[0.05]
                             text-[11px] text-text-secondary hover:bg-white/[0.04]
                             hover:border-white/[0.1] transition-all flex items-start gap-2">
                  <span className="text-accent flex-shrink-0 mt-0.5">{s.icon}</span>
                  {s.text}
                </button>
              ))}
            </div>
          </div>

          {/* Saved strategies */}
          {savedStrategies.length > 0 && (
            <div>
              <p className="text-[10px] text-text-muted uppercase tracking-wider mb-2">
                Saved Strategies ({savedStrategies.length})
              </p>
              <div className="space-y-1.5">
                {savedStrategies.slice(0, 5).map(s => (
                  <div key={s.id}
                    className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.05]">
                    <div className="flex-1 min-w-0">
                      <p className="text-[11px] font-semibold text-text-primary truncate">{s.label}</p>
                      <p className="text-[10px] text-text-muted">{s.ticker} · {s.savedAt.slice(0, 10)}</p>
                    </div>
                    <div className="flex items-center gap-1.5 ml-2">
                      <button onClick={() => {
                        if (s.result) onRunStrategy(s.strategyKey, s.params, s.label, s.result);
                        else onRunStrategy(s.strategyKey, s.params, s.label);
                      }}
                        className="text-[10px] px-2 py-0.5 rounded-md bg-accent/10 text-accent hover:bg-accent/20 transition-colors">
                        Load
                      </button>
                      <button onClick={() => deleteSaved(s.id)}
                        className="text-gray-600 hover:text-danger transition-colors">
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Strategy pills */}
          {Object.keys(registry).length > 0 && (
            <div>
              <p className="text-[10px] text-text-muted uppercase tracking-wider mb-1.5">
                {Object.keys(registry).length} strategies available
              </p>
              <div className="flex flex-wrap gap-1">
                {Object.values(registry).slice(0, 15).map(s => (
                  <button key={s.name} onClick={() => submit(`Run ${s.name}`)}
                    className="text-[10px] px-2 py-0.5 rounded-full bg-white/[0.04] border border-white/[0.06]
                               text-text-muted hover:bg-accent/10 hover:text-accent transition-all">
                    {s.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
        {renderComposer()}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[#050508]">
      {/* Chat header with clear button */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/[0.05]">
        <div className="flex items-center gap-1.5">
          <Sparkles className="h-3 w-3 text-accent" />
          <span className="text-[11px] font-semibold text-text-primary">Strategy Chat</span>
          <span className="text-[10px] text-text-muted">· Claude</span>
        </div>
        <button onClick={clearChat}
          className="text-[10px] text-text-muted hover:text-danger transition-colors px-2 py-0.5 rounded hover:bg-danger/10">
          Clear
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {messages.map((msg, i) => (
          <div key={i}>
            {msg.role === "user" ? (
              <div className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-md bg-white/[0.07] px-3.5 py-2.5 text-[12px] text-gray-200 leading-relaxed">
                  {msg.content}
                </div>
              </div>
            ) : (
              <div>
                <div className="flex items-center gap-1.5 mb-1.5">
                  <div className="w-5 h-5 rounded-full bg-gradient-to-br from-accent/30 to-purple-500/30 flex items-center justify-center">
                    <Sparkles className="h-2.5 w-2.5 text-accent" />
                  </div>
                  <span className="text-[10px] text-gray-500">Claude · Strategy Engine</span>
                </div>
                <div className="pl-6 text-[12px] text-gray-300 leading-[1.7] whitespace-pre-wrap">
                  {msg.content}
                </div>
                {msg.marketContext && (
                  <div className="pl-6 mt-1.5">
                    <span className="text-[10px] text-text-muted italic">{msg.marketContext}</span>
                  </div>
                )}
                {/* Strategy result card */}
                {msg.strategyResult && (
                  <div className="pl-6 mt-2">
                    <div className="bg-white/[0.04] border border-white/[0.08] rounded-xl p-3">
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-[11px] font-bold text-accent">{msg.strategyResult.modelName}</p>
                        <button
                          onClick={() => saveStrategy(msg.strategyResult!)}
                          title="Save strategy"
                          className="text-gray-500 hover:text-accent transition-colors">
                          {savedStrategies.some(s => s.label === msg.strategyResult!.modelName && s.ticker === ticker)
                            ? <BookmarkCheck className="h-3.5 w-3.5 text-accent" />
                            : <Bookmark className="h-3.5 w-3.5" />}
                        </button>
                      </div>
                      <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                        {[
                          ["Return", `${(msg.strategyResult.cumulativeReturn * 100).toFixed(1)}%`, msg.strategyResult.cumulativeReturn > 0],
                          ["Sharpe", msg.strategyResult.sharpeRatio.toFixed(2), msg.strategyResult.sharpeRatio > 1],
                          ["Win Rate", `${(msg.strategyResult.winRate * 100).toFixed(1)}%`, msg.strategyResult.winRate > 0.5],
                          ["Max DD", `${(msg.strategyResult.maxDrawdown * 100).toFixed(1)}%`, false],
                          ["Calmar", msg.strategyResult.calmarRatio?.toFixed(2) ?? "\u2014", (msg.strategyResult.calmarRatio ?? 0) > 1],
                          ["Trades", msg.strategyResult.totalTrades?.toString() ?? "\u2014", true],
                        ].map(([l, v, pos]) => (
                          <div key={String(l)} className="flex justify-between">
                            <span className="text-[10px] text-gray-500">{l}</span>
                            <span className={cn("text-[10px] font-bold",
                              pos === true ? "text-success" : pos === false ? "text-danger" : "text-gray-300")}>
                              {v}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {chatLoading && (
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <div className="w-5 h-5 rounded-full bg-gradient-to-br from-accent/30 to-purple-500/30 flex items-center justify-center">
                <Sparkles className="h-2.5 w-2.5 text-accent" />
              </div>
              <span className="text-[10px] text-gray-500">Claude · Strategy Engine</span>
            </div>
            <div className="pl-6 flex items-center gap-2.5">
              <div className="flex gap-1">
                {[0, 200, 400].map(d => (
                  <span key={d} className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse"
                    style={{ animationDelay: `${d}ms` }} />
                ))}
              </div>
              <span key={statusIdx} className="text-[11px] text-gray-500 italic">{STATUS[statusIdx]}</span>
            </div>
          </div>
        )}
      </div>
      {renderComposer()}
    </div>
  );

  function renderComposer() {
    return (
      <div className="px-3 pb-3 pt-1.5">
        <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl">
          <textarea ref={inputRef} value={input}
            onChange={e => {
              setInput(e.target.value);
              e.target.style.height = "auto";
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
            }}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
            placeholder="Describe your strategy in plain English..."
            disabled={chatLoading || loading} rows={1}
            className="w-full bg-transparent text-[12px] text-gray-200 placeholder-gray-600
                       outline-none resize-none px-3.5 pt-3 pb-1 leading-relaxed" />
          <div className="flex items-center justify-between px-3 pb-2.5">
            <span className="text-[10px] text-gray-600">{ticker} · Claude claude-sonnet-4-20250514</span>
            <button onClick={() => submit()}
              disabled={!input.trim() || chatLoading || loading}
              className={cn("w-7 h-7 rounded-xl flex items-center justify-center transition-all",
                input.trim() && !chatLoading && !loading
                  ? "bg-accent text-background hover:bg-accent/80"
                  : "bg-white/[0.04] text-gray-700 cursor-not-allowed")}>
              <Send className="h-3 w-3" />
            </button>
          </div>
        </div>
      </div>
    );
  }
}
