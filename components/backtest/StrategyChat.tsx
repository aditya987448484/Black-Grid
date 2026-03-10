"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatStrategyMessage, StrategyRegistry, BacktestModelResult } from "@/types/backtest";

const SUGGESTIONS = [
  { text: "Run RSI Mean Reversion with oversold=25, overbought=75", icon: "\u25C8" },
  { text: "Backtest Bollinger Squeeze with std_dev=1.5", icon: "\u25CE" },
  { text: "Try SuperTrend with multiplier=2.0", icon: "\u2605" },
  { text: "Run Ichimoku Cloud strategy", icon: "\u2601" },
  { text: "Test Donchian Channel with entry_period=30", icon: "\u25C7" },
];

interface Props {
  onRunStrategy: (key: string, params: Record<string, number>, customName: string) => void;
  loading: boolean;
  registry: StrategyRegistry;
  ticker: string;
  customResults: BacktestModelResult[];
}

const STATUS = ["Parsing strategy...", "Loading indicators...", "Running backtest...", "Crunching metrics..."];

function parseStrategyInput(input: string, registry: StrategyRegistry): { key: string | null; params: Record<string, number>; reply: string } {
  const lower = input.toLowerCase();
  const keywordMap: Record<string, string> = {
    "rsi mean": "rsi_mean_rev", "rsi reversion": "rsi_mean_rev",
    "macd trend": "macd_trend", "macd": "macd_trend",
    "ema cross": "ema_crossover", "ema crossover": "ema_crossover",
    "sma cross": "sma_crossover", "golden cross": "sma_crossover",
    "triple ema": "triple_ema",
    "bollinger squeeze": "bollinger_squeeze", "bb squeeze": "bollinger_squeeze",
    "bollinger mean": "bollinger_rev", "bollinger reversion": "bollinger_rev",
    "keltner": "keltner",
    "atr channel": "atr_channel", "atr volatility": "atr_channel",
    "donchian": "donchian", "turtle": "donchian",
    "supertrend": "supertrend", "super trend": "supertrend",
    "ichimoku": "ichimoku", "cloud": "ichimoku",
    "parabolic sar": "parabolic_sar", "sar": "parabolic_sar",
    "adx": "adx_trend",
    "stochastic": "stochastic", "stoch": "stochastic",
    "cci": "cci", "williams": "williams_r",
    "mfi": "mfi", "money flow": "mfi",
    "obv": "obv_trend", "vwap": "vwap_reversion",
    "volume breakout": "volume_breakout",
    "confluence": "rsi_macd_conf", "rsi macd": "rsi_macd_conf",
    "triple screen": "triple_screen", "elder": "triple_screen",
    "roc": "roc_momentum", "rate of change": "roc_momentum",
    "tsi": "tsi", "true strength": "tsi",
    "dpo": "dpo", "detrended": "dpo",
    "buy hold": "buy_hold", "buy and hold": "buy_hold",
  };

  let matchedKey: string | null = null;
  for (const [keyword, key] of Object.entries(keywordMap)) {
    if (lower.includes(keyword)) { matchedKey = key; break; }
  }

  const params: Record<string, number> = {};
  const re = /(\w+)\s*[=:]\s*([\d.]+)/g;
  let match;
  while ((match = re.exec(input)) !== null) {
    const val = parseFloat(match[2]);
    if (!isNaN(val)) params[match[1].toLowerCase().replace(/\s+/g, "_")] = val;
  }

  if (!matchedKey) {
    return {
      key: null, params,
      reply: "I didn't recognize that strategy. Try:\n" +
        Object.values(registry).slice(0, 8).map(s => `  ${s.name}`).join("\n") +
        "\n\nExample: \"Run RSI Mean Reversion with oversold=25\""
    };
  }

  const entry = registry[matchedKey];
  const paramStr = Object.entries(params).length > 0
    ? ` with ${Object.entries(params).map(([k, v]) => `${k}=${v}`).join(", ")}`
    : " with defaults";

  return { key: matchedKey, params: { ...entry?.defaultParams, ...params },
    reply: `Running ${entry?.name}${paramStr}...\n\n${entry?.description}` };
}

export default function StrategyChat({ onRunStrategy, loading, registry, ticker, customResults }: Props) {
  const [messages, setMessages] = useState<ChatStrategyMessage[]>([]);
  const [input, setInput] = useState("");
  const [statusIdx, setStatusIdx] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (!loading) return;
    setStatusIdx(0);
    const t = setInterval(() => setStatusIdx(i => (i + 1) % STATUS.length), 1800);
    return () => clearInterval(t);
  }, [loading]);

  function submit(text?: string) {
    const val = (text || input).trim();
    if (!val || loading) return;
    setInput("");
    if (inputRef.current) inputRef.current.style.height = "auto";

    const { key, params, reply } = parseStrategyInput(val, registry);
    setMessages(prev => [
      ...prev,
      { role: "user", content: val },
      { role: "assistant", content: reply },
    ]);

    if (key) {
      const customName = `Strategy ${customResults.length + 1}`;
      onRunStrategy(key, params, customName);
    }
  }

  // Empty state
  if (messages.length === 0 && !loading) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex-1 overflow-y-auto px-4 pt-4 pb-2">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-7 h-7 rounded-lg bg-accent/15 flex items-center justify-center">
              <Sparkles className="h-3.5 w-3.5 text-accent" />
            </div>
            <div>
              <h3 className="text-xs font-bold">Strategy Builder</h3>
              <p className="text-[10px] text-text-muted">Natural language backtest engine</p>
            </div>
          </div>
          <p className="text-[11px] text-text-secondary leading-relaxed mb-3">
            Describe any strategy in plain English with custom parameters.
          </p>
          <p className="text-[10px] text-text-muted uppercase tracking-wider mb-2">Try asking</p>
          <div className="space-y-1.5">
            {SUGGESTIONS.map(s => (
              <button key={s.text} onClick={() => submit(s.text)}
                className="w-full text-left px-3 py-2 rounded-lg border border-white/[0.05]
                           text-[11px] text-text-secondary hover:bg-white/[0.04]
                           hover:border-white/[0.1] transition-all flex items-start gap-2">
                <span className="text-accent flex-shrink-0">{s.icon}</span>{s.text}
              </button>
            ))}
          </div>
          {Object.keys(registry).length > 0 && (
            <div className="mt-3">
              <p className="text-[10px] text-text-muted uppercase tracking-wider mb-1.5">
                {Object.keys(registry).length} strategies available
              </p>
              <div className="flex flex-wrap gap-1">
                {Object.values(registry).slice(0, 12).map(s => (
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
    <div className="flex flex-col h-full">
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.map((msg, i) => (
          <div key={i}>
            {msg.role === "user" ? (
              <div className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-md bg-white/[0.07] px-3 py-2 text-[12px] text-gray-200">
                  {msg.content}
                </div>
              </div>
            ) : (
              <div>
                <div className="flex items-center gap-1.5 mb-1">
                  <Sparkles className="h-2.5 w-2.5 text-accent" />
                  <span className="text-[10px] text-gray-500">Strategy Engine</span>
                </div>
                <div className="pl-4 text-[12px] text-gray-400 leading-[1.65] whitespace-pre-wrap">
                  {msg.content}
                </div>
                {msg.strategyResult && (
                  <div className="pl-4 mt-2 bg-white/[0.03] border border-white/[0.06] rounded-xl p-3">
                    <p className="text-[11px] font-bold text-accent mb-1.5">{msg.strategyResult.modelName}</p>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px]">
                      {[["Return", `${(msg.strategyResult.cumulativeReturn * 100).toFixed(1)}%`],
                        ["Sharpe", msg.strategyResult.sharpeRatio.toFixed(2)],
                        ["Win Rate", `${(msg.strategyResult.winRate * 100).toFixed(1)}%`],
                        ["Max DD", `${(msg.strategyResult.maxDrawdown * 100).toFixed(1)}%`],
                      ].map(([l, v]) => (
                        <div key={l} className="flex justify-between">
                          <span className="text-gray-500">{l}</span>
                          <span className="font-bold text-gray-300">{v}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="pl-4 flex items-center gap-2">
            <div className="flex gap-1">
              {[0, 200, 400].map(d => (
                <span key={d} className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" style={{ animationDelay: `${d}ms` }} />
              ))}
            </div>
            <span className="text-[11px] text-gray-500 italic">{STATUS[statusIdx]}</span>
          </div>
        )}
      </div>
      {renderComposer()}
    </div>
  );

  function renderComposer() {
    return (
      <div className="px-3 pb-3 pt-1">
        <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl">
          <textarea ref={inputRef} value={input}
            onChange={e => { setInput(e.target.value); e.target.style.height = "auto"; e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px"; }}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
            placeholder="Describe a strategy..."
            disabled={loading} rows={1}
            className="w-full bg-transparent text-[12px] text-gray-200 placeholder-gray-600 outline-none resize-none px-3.5 pt-3 pb-1 leading-relaxed" />
          <div className="flex items-center justify-between px-3 pb-2">
            <span className="text-[10px] text-gray-600">{ticker}</span>
            <button onClick={() => submit()} disabled={!input.trim() || loading}
              className={cn("w-7 h-7 rounded-xl flex items-center justify-center transition-all",
                input.trim() && !loading ? "bg-accent text-background hover:bg-accent/80" : "bg-white/[0.04] text-gray-700 cursor-not-allowed")}>
              <Send className="h-3 w-3" />
            </button>
          </div>
        </div>
      </div>
    );
  }
}
