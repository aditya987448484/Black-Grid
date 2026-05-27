"use client";

import { useState, useRef, useEffect, FormEvent } from "react";
import {
  ChatMessage,
  AIAnalystModel,
  DEEPSEEK_MODELS,
  DEFAULT_AI_MODEL,
} from "@/lib/types/ai-analyst";

interface ChatPanelProps {
  ticker?: string;
}

export default function ChatPanel({ ticker }: ChatPanelProps) {
  const [model, setModel] = useState<string>(DEFAULT_AI_MODEL); // "deepseek-chat"
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = {
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/ai-analyst/chat`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: [...messages, userMsg].map(({ role, content }) => ({
              role,
              content,
            })),
            model,
            ticker: ticker ?? undefined,
          }),
        }
      );

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `HTTP ${res.status}`);
      }

      const data = await res.json();
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: data.reply,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] border border-[#1f2937] rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1f2937]">
        <span className="text-sm font-semibold text-white tracking-wide">
          AI Analyst
          {ticker && (
            <span className="ml-2 text-xs text-emerald-400 font-mono">
              {ticker.toUpperCase()}
            </span>
          )}
        </span>

        {/* Model selector */}
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="text-xs bg-[#111827] text-gray-300 border border-[#374151] rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-emerald-500"
        >
          {DEEPSEEK_MODELS.map((m: AIAnalystModel) => (
            <option key={m.id} value={m.id}>
              {m.label}
              {m.badge ? ` · ${m.badge}` : ""}
            </option>
          ))}
        </select>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 text-sm">
        {messages.length === 0 && (
          <p className="text-gray-500 text-center mt-8">
            Ask me anything about{" "}
            {ticker ? (
              <span className="text-emerald-400 font-mono">
                {ticker.toUpperCase()}
              </span>
            ) : (
              "any ticker"
            )}
            .
          </p>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-3 py-2 whitespace-pre-wrap leading-relaxed ${
                msg.role === "user"
                  ? "bg-emerald-900/40 text-emerald-100"
                  : "bg-[#111827] text-gray-200"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-[#111827] text-gray-400 rounded-lg px-3 py-2 text-xs animate-pulse">
              Thinking…
            </div>
          </div>
        )}

        {error && (
          <div className="text-red-400 text-xs text-center">{error}</div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-[#1f2937] px-4 py-3 flex gap-2"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about earnings, technicals, valuation…"
          disabled={loading}
          className="flex-1 bg-[#111827] text-white text-sm rounded px-3 py-2 border border-[#374151] focus:outline-none focus:ring-1 focus:ring-emerald-500 placeholder-gray-600 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium px-4 py-2 rounded transition-colors"
        >
          Send
        </button>
      </form>
    </div>
  );
}
