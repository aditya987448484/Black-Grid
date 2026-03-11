"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  Send, Sparkles, Bookmark, BookmarkCheck, Trash2,
  Paperclip, ChevronDown, X, Key, Eye, EyeOff, Copy, Check,
  FileIcon, ExternalLink, AlertTriangle, CheckCircle2, Loader2,
  Play, Shield, Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { strategyChat, parseStrategy, validateStrategy, runStrategySpec } from "@/lib/api";
import type {
  ChatStrategyMessage, StrategyRegistry, BacktestModelResult,
  SavedStrategy, AttachmentMeta, StrategySpec, StrategyParseResponse,
} from "@/types/backtest";
import { ANTHROPIC_MODELS } from "@/types/ai-analyst";

const SUGGESTIONS = [
  "Buy when RSI crosses below 30, sell when RSI crosses above 70, 5% stop loss",
  "Long when MACD crosses above signal and price > 200 SMA, exit on MACD cross below",
  "Bollinger Bands mean reversion: buy at lower band, sell at upper band",
  "SuperTrend strategy with 2.0 multiplier and 5% trailing stop",
  "Donchian Channel breakout: long on 20-day high breakout, exit on 10-day low",
  "RSI + ADX filter: buy when RSI < 30 AND ADX > 25, sell when RSI > 70",
];

const STATUS_PARSE = [
  "Sending to Claude...", "Parsing strategy...", "Analyzing indicators...",
  "Building strategy spec...",
];
const STATUS_RUN = [
  "Validating strategy...", "Compiling conditions...", "Running backtest...",
  "Computing metrics...",
];

const CHAT_STORAGE_KEY = "blackgrid_backtest_chat";
const SAVED_STRATEGIES_KEY = "blackgrid_saved_strategies";
const API_KEY_STORAGE_KEY = "blackgrid_anthropic_key";
const MAX_FILE_SIZE = 10 * 1024 * 1024;

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

interface EnhancedMessage extends ChatStrategyMessage {
  strategySpec?: StrategySpec;
  parseResponse?: StrategyParseResponse;
  validationErrors?: string[];
  validationWarnings?: string[];
  phase?: "parsing" | "parsed" | "validating" | "validated" | "running" | "complete" | "error";
}

export default function StrategyChat({
  onRunStrategy, onSaveStrategy, loading, registry, ticker, startDate, endDate, customResults,
}: Props) {
  const [messages, setMessages] = useState<EnhancedMessage[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const stored = localStorage.getItem(CHAT_STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch { return []; }
  });
  const [input, setInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [statusIdx, setStatusIdx] = useState(0);
  const [currentPhase, setCurrentPhase] = useState<"parse" | "run">("parse");
  const [model, setModel] = useState("claude-sonnet-4-6");
  const [showModelMenu, setShowModelMenu] = useState(false);
  const [showApiKeyPanel, setShowApiKeyPanel] = useState(false);
  const [apiKey, setApiKey] = useState(() => {
    if (typeof window === "undefined") return "";
    return localStorage.getItem(API_KEY_STORAGE_KEY) || "";
  });
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [attachments, setAttachments] = useState<AttachmentMeta[]>([]);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [savedStrategies, setSavedStrategies] = useState<SavedStrategy[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const stored = localStorage.getItem(SAVED_STRATEGIES_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch { return []; }
  });

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const modelMenuRef = useRef<HTMLDivElement>(null);

  const currentModel = ANTHROPIC_MODELS.find(m => m.id === model) || ANTHROPIC_MODELS[1];

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
    const statuses = currentPhase === "run" ? STATUS_RUN : STATUS_PARSE;
    const t = setInterval(() => setStatusIdx(i => (i + 1) % statuses.length), 1400);
    return () => clearInterval(t);
  }, [chatLoading, currentPhase]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (modelMenuRef.current && !modelMenuRef.current.contains(e.target as Node)) setShowModelMenu(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function saveApiKey() {
    const key = apiKeyInput.trim();
    if (key) {
      setApiKey(key);
      localStorage.setItem(API_KEY_STORAGE_KEY, key);
      setApiKeyInput("");
      setShowApiKeyPanel(false);
    }
  }

  function clearApiKey() {
    setApiKey("");
    setApiKeyInput("");
    localStorage.removeItem(API_KEY_STORAGE_KEY);
  }

  function maskKey(key: string) {
    if (key.length < 12) return "****";
    return key.slice(0, 7) + "..." + key.slice(-4);
  }

  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    for (const file of Array.from(files)) {
      if (file.size > MAX_FILE_SIZE) {
        alert(`File "${file.name}" exceeds 10MB limit.`);
        continue;
      }

      const meta: AttachmentMeta = {
        filename: file.name,
        contentType: file.type,
        size: file.size,
      };

      if (file.type.startsWith("image/") || file.type === "application/pdf") {
        const base64 = await fileToBase64(file);
        meta.base64 = base64;
      } else {
        const text = await file.text();
        meta.textContent = text;
      }

      setAttachments(prev => [...prev, meta]);
    }
    e.target.value = "";
  }

  function fileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => { resolve((reader.result as string).split(",")[1]); };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  function removeAttachment(idx: number) {
    setAttachments(prev => prev.filter((_, i) => i !== idx));
  }

  function copyMessage(content: string, idx: number) {
    navigator.clipboard.writeText(content);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 1500);
  }

  // ── Run a parsed strategy spec ──────────────────────────────────────
  const runParsedSpec = useCallback(async (spec: StrategySpec, msgIdx: number) => {
    setChatLoading(true);
    setCurrentPhase("run");

    // Update message phase
    setMessages(prev => prev.map((m, i) => i === msgIdx ? { ...m, phase: "validating" } : m));

    try {
      // Validate
      const validation = await validateStrategy(spec);
      setMessages(prev => prev.map((m, i) => i === msgIdx ? {
        ...m,
        validationErrors: validation.errors,
        validationWarnings: validation.warnings,
        phase: validation.valid ? "validated" : "error",
      } : m));

      if (!validation.valid) {
        setChatLoading(false);
        return;
      }

      // Run
      setMessages(prev => prev.map((m, i) => i === msgIdx ? { ...m, phase: "running" } : m));
      const runResult = await runStrategySpec({
        strategy_spec: spec,
        ticker,
        start_date: startDate,
        end_date: endDate,
      });

      if (runResult.error) {
        setMessages(prev => prev.map((m, i) => i === msgIdx ? {
          ...m,
          phase: "error",
          validationErrors: [...(m.validationErrors ?? []), runResult.error!],
        } : m));
      } else if (runResult.result) {
        const result = runResult.result as BacktestModelResult;
        result.isCustom = true;
        result.customLabel = spec.name;
        setMessages(prev => prev.map((m, i) => i === msgIdx ? {
          ...m,
          strategyResult: result,
          phase: "complete",
        } : m));

        // Push to parent
        onRunStrategy(
          result.strategyKey ?? `custom_${spec.name.toLowerCase().replace(/ /g, "_")}`,
          {},
          spec.name,
          result,
        );
      }
    } catch (e: unknown) {
      const err = e instanceof Error ? e.message : "Run failed";
      setMessages(prev => prev.map((m, i) => i === msgIdx ? {
        ...m, phase: "error", validationErrors: [...(m.validationErrors ?? []), err],
      } : m));
    } finally {
      setChatLoading(false);
    }
  }, [ticker, startDate, endDate, onRunStrategy]);

  // ── Main submit: parse strategy via Claude, then auto-run ───────────
  const submit = useCallback(async (text?: string) => {
    const val = (text || input).trim();
    if (!val || chatLoading || loading) return;
    setInput("");
    if (inputRef.current) inputRef.current.style.height = "auto";

    const userMsg: EnhancedMessage = {
      role: "user",
      content: val,
      timestamp: new Date().toISOString(),
      attachments: attachments.length > 0 ? [...attachments] : undefined,
    };
    setMessages(prev => [...prev, userMsg]);
    setChatLoading(true);
    setCurrentPhase("parse");

    // Build file context
    let fileContext: string | undefined;
    for (const att of attachments) {
      if (att.textContent) {
        fileContext = (fileContext || "") + `\n[${att.filename}]\n${att.textContent}\n`;
      }
    }
    setAttachments([]);

    try {
      // Step 1: Parse via Claude into StrategySpec
      const parseResult = await parseStrategy({
        message: val,
        history: messages.slice(-8).map(m => ({ role: m.role, content: m.content })),
        ticker,
        start_date: startDate,
        end_date: endDate,
        model,
        api_key: apiKey || undefined,
        file_context: fileContext,
      });

      const assistantMsg: EnhancedMessage = {
        role: "assistant",
        content: parseResult.reply,
        strategySpec: parseResult.strategy_spec as StrategySpec | undefined,
        parseResponse: parseResult,
        timestamp: new Date().toISOString(),
        phase: parseResult.strategy_spec ? "parsed" : undefined,
      };

      const newMsgs = [...messages, userMsg, assistantMsg];
      setMessages(prev => [...prev, assistantMsg]);

      // Step 2: If a spec was returned and can_run_immediately, auto-run
      if (parseResult.strategy_spec && parseResult.can_run_immediately) {
        setChatLoading(false);
        // Small delay for UI feedback
        setTimeout(() => {
          const msgIdx = newMsgs.length - 1;
          runParsedSpec(parseResult.strategy_spec as StrategySpec, msgIdx);
        }, 100);
        return;
      }

      // Also try the legacy chat endpoint as fallback for simple registry strategies
      if (!parseResult.strategy_spec) {
        try {
          const legacyResult = await strategyChat({
            message: val,
            history: messages.slice(-8).map(m => ({ role: m.role, content: m.content })),
            ticker,
            start_date: startDate,
            end_date: endDate,
            model,
            api_key: apiKey || undefined,
          });

          if (legacyResult.strategy_key && legacyResult.strategyResult) {
            // Update the assistant message with the legacy result
            setMessages(prev => {
              const updated = [...prev];
              const lastAssistant = updated.length - 1;
              if (updated[lastAssistant]?.role === "assistant") {
                updated[lastAssistant] = {
                  ...updated[lastAssistant],
                  content: legacyResult.reply || updated[lastAssistant].content,
                  strategyResult: legacyResult.strategyResult as BacktestModelResult,
                  marketContext: legacyResult.market_context,
                  phase: "complete",
                };
              }
              return updated;
            });

            const customName = `Custom ${customResults.length + 1}`;
            onRunStrategy(
              legacyResult.strategy_key,
              legacyResult.params,
              customName,
              legacyResult.strategyResult as BacktestModelResult,
            );
          }
        } catch {
          // Legacy fallback failed silently — parse response already shown
        }
      }
    } catch (e: unknown) {
      const errMsg = e instanceof Error ? e.message : "Something went wrong";
      setMessages(prev => [...prev, {
        role: "assistant",
        content: `Error: ${errMsg}. Make sure an API key is configured.`,
        timestamp: new Date().toISOString(),
        phase: "error",
      }]);
    } finally {
      setChatLoading(false);
    }
  }, [input, chatLoading, loading, messages, ticker, startDate, endDate, customResults, onRunStrategy, model, attachments, apiKey, runParsedSpec]);

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

  function formatTime(iso?: string) {
    if (!iso) return "";
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  // ── Render: Strategy Spec Card ─────────────────────────────────────
  function renderSpecCard(msg: EnhancedMessage, msgIdx: number) {
    const spec = msg.strategySpec;
    const parse = msg.parseResponse;
    if (!spec) return null;

    return (
      <div className="pl-6 mt-2">
        <div className="bg-white/[0.04] border border-white/[0.08] rounded-xl p-3 space-y-2">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="h-3.5 w-3.5 text-accent" />
              <span className="text-[11px] font-bold text-accent">{spec.name}</span>
            </div>
            <div className="flex items-center gap-1.5">
              {parse?.confidence !== undefined && (
                <span className={cn(
                  "text-[9px] px-1.5 py-0.5 rounded-full font-bold",
                  parse.confidence >= 0.8 ? "bg-emerald-500/15 text-emerald-400" :
                  parse.confidence >= 0.5 ? "bg-yellow-500/15 text-yellow-400" :
                  "bg-red-500/15 text-red-400"
                )}>
                  {(parse.confidence * 100).toFixed(0)}% conf
                </span>
              )}
              <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-white/[0.06] text-gray-400">
                {spec.direction.replace("_", " ")}
              </span>
            </div>
          </div>

          {/* Entry / Exit summary */}
          <div className="grid grid-cols-2 gap-2">
            <div className="text-[10px]">
              <span className="text-emerald-400 font-semibold">Entry: </span>
              <span className="text-gray-400">
                {spec.entry.long_conditions.length} long group{spec.entry.long_conditions.length !== 1 ? "s" : ""}
                {spec.entry.short_conditions.length > 0 && `, ${spec.entry.short_conditions.length} short`}
              </span>
            </div>
            <div className="text-[10px]">
              <span className="text-red-400 font-semibold">Exit: </span>
              <span className="text-gray-400">
                {spec.exit.long_exit_conditions.length} long group{spec.exit.long_exit_conditions.length !== 1 ? "s" : ""}
                {spec.exit.short_exit_conditions.length > 0 && `, ${spec.exit.short_exit_conditions.length} short`}
              </span>
            </div>
          </div>

          {/* Risk rules */}
          {(spec.risk.stop_loss_pct || spec.risk.take_profit_pct || spec.risk.trailing_stop_pct) && (
            <div className="flex flex-wrap gap-1.5">
              {spec.risk.stop_loss_pct && (
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">
                  SL: {spec.risk.stop_loss_pct}%
                </span>
              )}
              {spec.risk.take_profit_pct && (
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  TP: {spec.risk.take_profit_pct}%
                </span>
              )}
              {spec.risk.trailing_stop_pct && (
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
                  Trail: {spec.risk.trailing_stop_pct}%
                </span>
              )}
            </div>
          )}

          {/* Assumptions */}
          {parse?.assumptions && parse.assumptions.length > 0 && (
            <div className="text-[10px] text-gray-500">
              <span className="font-semibold text-gray-400">Assumptions: </span>
              {parse.assumptions.join("; ")}
            </div>
          )}

          {/* Unsupported */}
          {parse?.unsupported_clauses && parse.unsupported_clauses.length > 0 && (
            <div className="flex items-start gap-1.5 text-[10px] text-yellow-400">
              <AlertTriangle className="h-3 w-3 flex-shrink-0 mt-0.5" />
              <span>Unsupported: {parse.unsupported_clauses.join("; ")}</span>
            </div>
          )}

          {/* Validation errors */}
          {msg.validationErrors && msg.validationErrors.length > 0 && (
            <div className="text-[10px] text-red-400 space-y-0.5">
              {msg.validationErrors.map((e, i) => (
                <div key={i} className="flex items-start gap-1.5">
                  <AlertTriangle className="h-3 w-3 flex-shrink-0 mt-0.5" />
                  <span>{e}</span>
                </div>
              ))}
            </div>
          )}
          {msg.validationWarnings && msg.validationWarnings.length > 0 && (
            <div className="text-[10px] text-yellow-400 space-y-0.5">
              {msg.validationWarnings.map((w, i) => (
                <div key={i} className="flex items-start gap-1.5">
                  <AlertTriangle className="h-3 w-3 flex-shrink-0 mt-0.5" />
                  <span>{w}</span>
                </div>
              ))}
            </div>
          )}

          {/* Phase indicator */}
          {msg.phase && msg.phase !== "complete" && msg.phase !== "error" && (
            <div className="flex items-center gap-2 text-[10px] text-accent">
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>
                {msg.phase === "parsing" && "Parsing..."}
                {msg.phase === "parsed" && "Parsed — ready to run"}
                {msg.phase === "validating" && "Validating..."}
                {msg.phase === "validated" && "Validated — running backtest..."}
                {msg.phase === "running" && "Running backtest..."}
              </span>
            </div>
          )}

          {/* Run button (if not auto-running and no result yet) */}
          {msg.phase === "parsed" && !msg.strategyResult && !chatLoading && (
            <button
              onClick={() => runParsedSpec(spec, msgIdx)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent/15 text-accent text-[11px] font-semibold hover:bg-accent/25 transition-colors"
            >
              <Play className="h-3 w-3" /> Run Backtest
            </button>
          )}

          {/* Completed checkmark */}
          {msg.phase === "complete" && (
            <div className="flex items-center gap-1.5 text-[10px] text-emerald-400">
              <CheckCircle2 className="h-3 w-3" />
              <span>Strategy compiled and executed successfully</span>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ── Render: Result Card ────────────────────────────────────────────
  function renderResultCard(msg: EnhancedMessage) {
    const result = msg.strategyResult;
    if (!result) return null;

    return (
      <div className="pl-6 mt-2">
        <div className="bg-white/[0.04] border border-white/[0.08] rounded-xl p-3">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[11px] font-bold text-accent">{result.modelName}</p>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => {
                  const customName = result.customLabel ?? result.modelName;
                  onRunStrategy(result.strategyKey ?? "", result.params ?? {}, customName, result);
                }}
                className="text-[9px] px-2 py-0.5 rounded-md bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
              >
                Add to Chart
              </button>
              <button
                onClick={() => saveStrategy(result)}
                title="Save strategy"
                className="text-gray-500 hover:text-accent transition-colors">
                {savedStrategies.some(s => s.label === result.modelName && s.ticker === ticker)
                  ? <BookmarkCheck className="h-3.5 w-3.5 text-accent" />
                  : <Bookmark className="h-3.5 w-3.5" />}
              </button>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            {([
              ["Return", `${(result.cumulativeReturn * 100).toFixed(1)}%`, result.cumulativeReturn > 0],
              ["Sharpe", result.sharpeRatio.toFixed(2), result.sharpeRatio > 1],
              ["Win Rate", `${(result.winRate * 100).toFixed(1)}%`, result.winRate > 0.5],
              ["Max DD", `${(result.maxDrawdown * 100).toFixed(1)}%`, false],
              ["Calmar", result.calmarRatio?.toFixed(2) ?? "\u2014", (result.calmarRatio ?? 0) > 1],
              ["Trades", result.totalTrades?.toString() ?? "\u2014", true],
            ] as [string, string, boolean][]).map(([l, v, pos]) => (
              <div key={l} className="flex justify-between">
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
    );
  }

  // ── Empty state ────────────────────────────────────────────────────
  if (messages.length === 0 && !chatLoading) {
    return (
      <div className="flex flex-col h-full bg-[#050508]">
        <div className="flex-1 overflow-y-auto px-4 pt-4 pb-2 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-accent/20 to-purple-500/20 flex items-center justify-center">
                <Sparkles className="h-4 w-4 text-accent" />
              </div>
              <div>
                <h3 className="text-xs font-bold text-text-primary">Strategy Engine</h3>
                <p className="text-[10px] text-text-muted">NL &rarr; Claude &rarr; StrategySpec &rarr; Backtest</p>
              </div>
            </div>
            <button
              onClick={() => setShowApiKeyPanel(!showApiKeyPanel)}
              className="relative p-1.5 rounded-lg hover:bg-white/[0.04] transition-colors"
              title="API Key Settings"
            >
              <Key className="h-3.5 w-3.5 text-text-muted" />
              <span className={cn(
                "absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full",
                apiKey ? "bg-emerald-400" : "bg-amber-400"
              )} />
            </button>
          </div>

          {showApiKeyPanel && renderApiKeyPanel()}

          <div className="flex items-center gap-2 text-[10px] text-text-muted">
            <Shield className="h-3 w-3 text-emerald-400" />
            <span>Safe structured compiler — no eval(), no arbitrary code</span>
          </div>

          <p className="text-[11px] text-text-secondary leading-relaxed">
            Describe any strategy in plain English. Claude parses it into a structured StrategySpec,
            which is validated against 100 indicators, compiled into signals, and backtested deterministically.
          </p>

          <div>
            <p className="text-[10px] text-text-muted uppercase tracking-wider mb-2">Try asking</p>
            <div className="space-y-1.5">
              {SUGGESTIONS.map(s => (
                <button key={s} onClick={() => submit(s)}
                  className="w-full text-left px-3 py-2 rounded-lg border border-white/[0.05]
                             text-[11px] text-text-secondary hover:bg-white/[0.04]
                             hover:border-white/[0.1] transition-all flex items-start gap-2">
                  <span className="text-accent flex-shrink-0 mt-0.5">&#9672;</span>
                  {s}
                </button>
              ))}
            </div>
          </div>

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
      {/* Chat header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/[0.05]">
        <div className="flex items-center gap-1.5">
          <Sparkles className="h-3 w-3 text-accent" />
          <span className="text-[11px] font-semibold text-text-primary">Strategy Engine</span>
          <span className="text-[10px] text-text-muted">· {currentModel.label}</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowApiKeyPanel(!showApiKeyPanel)}
            className="relative p-1 rounded-lg hover:bg-white/[0.04] transition-colors"
            title="API Key Settings"
          >
            <Key className="h-3 w-3 text-text-muted" />
            <span className={cn(
              "absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full",
              apiKey ? "bg-emerald-400" : "bg-amber-400"
            )} />
          </button>
          <button onClick={clearChat}
            className="text-[10px] text-text-muted hover:text-danger transition-colors px-2 py-0.5 rounded hover:bg-danger/10">
            Clear
          </button>
        </div>
      </div>

      {showApiKeyPanel && (
        <div className="border-b border-white/[0.05]">
          {renderApiKeyPanel()}
        </div>
      )}

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className="group">
            {msg.role === "user" ? (
              <div>
                <div className="flex justify-end">
                  <div className="max-w-[85%] rounded-2xl rounded-br-md bg-white/[0.07] px-3.5 py-2.5 text-[12px] text-gray-200 leading-relaxed">
                    {msg.content}
                    {msg.attachments && msg.attachments.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {msg.attachments.map((a, j) => (
                          <span key={j} className="text-[9px] px-1.5 py-0.5 rounded bg-white/[0.06] text-gray-400">
                            {a.filename}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex justify-end mt-0.5 pr-1 gap-1.5 items-center">
                  <span className="text-[9px] text-gray-600">{formatTime(msg.timestamp)}</span>
                  <button
                    onClick={() => copyMessage(msg.content, i)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-600 hover:text-gray-400"
                  >
                    {copiedIdx === i ? <Check className="h-2.5 w-2.5 text-emerald-400" /> : <Copy className="h-2.5 w-2.5" />}
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <div className="flex items-center gap-1.5 mb-1.5">
                  <div className="w-5 h-5 rounded-full bg-gradient-to-br from-accent/30 to-purple-500/30 flex items-center justify-center">
                    <Sparkles className="h-2.5 w-2.5 text-accent" />
                  </div>
                  <span className="text-[10px] text-gray-500">Claude · Strategy Engine</span>
                  <span className="text-[9px] text-gray-600 ml-auto">{formatTime(msg.timestamp)}</span>
                  <button
                    onClick={() => copyMessage(msg.content, i)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-600 hover:text-gray-400"
                  >
                    {copiedIdx === i ? <Check className="h-2.5 w-2.5 text-emerald-400" /> : <Copy className="h-2.5 w-2.5" />}
                  </button>
                </div>
                <div className="pl-6 text-[12px] text-gray-300 leading-[1.7] whitespace-pre-wrap">
                  {msg.content}
                </div>
                {msg.marketContext && (
                  <div className="pl-6 mt-1.5">
                    <span className="text-[10px] text-text-muted italic">{msg.marketContext}</span>
                  </div>
                )}
                {/* Strategy Spec card */}
                {msg.strategySpec && renderSpecCard(msg, i)}
                {/* Result card */}
                {msg.strategyResult && renderResultCard(msg)}
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
              <Loader2 className="h-3.5 w-3.5 text-accent animate-spin" />
              <span key={statusIdx} className="text-[11px] text-gray-500 italic">
                {(currentPhase === "run" ? STATUS_RUN : STATUS_PARSE)[statusIdx]}
              </span>
            </div>
          </div>
        )}
      </div>
      {renderComposer()}
    </div>
  );

  function renderApiKeyPanel() {
    return (
      <div className="px-4 py-3 space-y-2 bg-white/[0.02]">
        <div className="flex items-center justify-between">
          <p className="text-[11px] font-semibold text-text-primary">Anthropic API Key</p>
          <a
            href="https://console.anthropic.com/settings/keys"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-[10px] text-accent hover:text-accent/80 transition-colors"
          >
            Get key <ExternalLink className="h-2.5 w-2.5" />
          </a>
        </div>
        {apiKey ? (
          <div className="flex items-center gap-2">
            <div className="flex-1 flex items-center gap-2 bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-1.5">
              <span className={cn(
                "w-2 h-2 rounded-full flex-shrink-0",
                apiKey ? "bg-emerald-400" : "bg-amber-400"
              )} />
              <span className="text-[11px] text-gray-400 font-mono flex-1">
                {showKey ? apiKey : maskKey(apiKey)}
              </span>
              <button onClick={() => setShowKey(!showKey)} className="text-gray-500 hover:text-gray-300">
                {showKey ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
              </button>
            </div>
            <button onClick={clearApiKey}
              className="text-[10px] text-danger hover:text-danger/80 px-2 py-1 rounded-lg hover:bg-danger/10 transition-colors">
              Remove
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <input
              value={apiKeyInput}
              onChange={e => setApiKeyInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && saveApiKey()}
              placeholder="sk-ant-..."
              type="password"
              className="flex-1 bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-1.5 text-[11px] text-gray-200 placeholder-gray-600 outline-none focus:border-accent"
            />
            <button onClick={saveApiKey} disabled={!apiKeyInput.trim()}
              className="text-[10px] px-3 py-1.5 rounded-lg bg-accent/15 text-accent hover:bg-accent/25 disabled:opacity-40 transition-colors font-semibold">
              Save
            </button>
          </div>
        )}
        <p className="text-[10px] text-text-muted">
          Key stored locally in your browser. Server .env key used as fallback.
        </p>
      </div>
    );
  }

  function renderComposer() {
    return (
      <div className="px-3 pb-3 pt-1.5 relative">
        {showModelMenu && (
          <div ref={modelMenuRef}
            className="absolute bottom-[68px] right-4 w-48 bg-[#0c0c12] border border-white/[0.12] rounded-xl shadow-2xl shadow-black/60 py-1.5 z-[100]">
            {ANTHROPIC_MODELS.map(m => (
              <button
                key={m.id}
                onClick={() => { setModel(m.id); setShowModelMenu(false); }}
                className={cn(
                  "w-full text-left px-4 py-2 text-[11px] transition-colors flex items-center justify-between",
                  m.id === model ? "text-accent bg-accent/10" : "text-gray-400 hover:text-gray-200 hover:bg-white/[0.05]"
                )}
              >
                <span>{m.label}</span>
                {m.badge && (
                  <span className={cn(
                    "text-[8px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wider",
                    m.badge === "Most Powerful" ? "bg-purple-500/20 text-purple-400" :
                    m.badge === "Recommended" ? "bg-accent/20 text-accent" :
                    m.badge === "Fastest" ? "bg-emerald-500/20 text-emerald-400" :
                    "bg-white/10 text-gray-400"
                  )}>
                    {m.badge}
                  </span>
                )}
              </button>
            ))}
          </div>
        )}

        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-2">
            {attachments.map((a, i) => (
              <div key={i} className="flex items-center gap-1.5 bg-white/[0.06] border border-white/[0.08] rounded-lg px-2.5 py-1.5 text-[11px] text-gray-400">
                <FileIcon className="h-3 w-3 text-gray-500" />
                <span className="truncate max-w-[100px]">{a.filename}</span>
                <span className="text-gray-600">{(a.size / 1024).toFixed(0)}KB</span>
                <button onClick={() => removeAttachment(i)} className="text-gray-500 hover:text-gray-300 ml-0.5">
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        )}

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
            <div className="flex items-center gap-1">
              <input ref={fileRef} type="file" className="hidden"
                accept="image/*,application/pdf,text/csv,text/plain"
                multiple
                onChange={handleFileSelect} />
              <button type="button" onClick={() => fileRef.current?.click()}
                className="w-7 h-7 rounded-lg flex items-center justify-center text-gray-600 hover:text-gray-400 hover:bg-white/[0.04] transition-colors"
                title="Attach file or image">
                <Paperclip className="h-3.5 w-3.5" />
              </button>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => setShowModelMenu(!showModelMenu)}
                className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-400 transition-colors select-none px-1.5 py-0.5 rounded hover:bg-white/[0.04]">
                {currentModel.label}
                <ChevronDown className="h-2.5 w-2.5" />
              </button>
              <button onClick={() => submit()}
                disabled={(!input.trim() && attachments.length === 0) || chatLoading || loading}
                className={cn("w-7 h-7 rounded-xl flex items-center justify-center transition-all",
                  (input.trim() || attachments.length > 0) && !chatLoading && !loading
                    ? "bg-accent text-background hover:bg-accent/80"
                    : "bg-white/[0.04] text-gray-700 cursor-not-allowed")}>
                <Send className="h-3 w-3" />
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }
}
