"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Paperclip, ImagePlus, Sparkles, X, ChevronDown, FileIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { uploadAnalystFile } from "@/lib/api";
import type { ChatMessage, AttachmentMeta, ModelOption } from "@/types/ai-analyst";
import { ANTHROPIC_MODELS } from "@/types/ai-analyst";

const SUGGESTED = [
  "Generate financial analysis of TSMC",
  "Analyze NVDA",
  "Bull and bear case for Apple",
  "Summarize risks for Tesla",
];

const STATUS_PHRASES = [
  "Thinking",
  "Reviewing the numbers",
  "Building the thesis",
  "Analyzing fundamentals",
  "Drafting the report",
  "Cooking",
];

interface Props {
  messages: ChatMessage[];
  onSend: (message: string, attachments: AttachmentMeta[]) => void;
  loading: boolean;
  model: string;
  onModelChange: (model: string) => void;
  onClearHistory?: () => void;
}

export default function ChatPanel({ messages, onSend, loading, model, onModelChange, onClearHistory }: Props) {
  const [input, setInput] = useState("");
  const [statusIdx, setStatusIdx] = useState(0);
  const [attachments, setAttachments] = useState<AttachmentMeta[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [showModelMenu, setShowModelMenu] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const imageRef = useRef<HTMLInputElement>(null);
  const modelMenuRef = useRef<HTMLDivElement>(null);

  const currentModel = ANTHROPIC_MODELS.find((m) => m.id === model) || ANTHROPIC_MODELS[0];

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (!loading) return;
    setStatusIdx(0);
    const interval = setInterval(() => setStatusIdx((i) => (i + 1) % STATUS_PHRASES.length), 2400);
    return () => clearInterval(interval);
  }, [loading]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (modelMenuRef.current && !modelMenuRef.current.contains(e.target as Node)) setShowModelMenu(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function submit() {
    const val = input.trim();
    if ((!val && attachments.length === 0) || loading) return;
    onSend(val || "(Attached files)", attachments);
    setInput("");
    setAttachments([]);
    setUploadError(null);
    if (inputRef.current) inputRef.current.style.height = "auto";
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
  }

  function handleInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 140) + "px";
  }

  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setUploading(true);
    setUploadError(null);

    for (const file of Array.from(files)) {
      try {
        const meta = await uploadAnalystFile(file);
        setAttachments((prev) => [...prev, meta]);
      } catch (err: any) {
        setUploadError(err.message || "Upload failed");
      }
    }
    setUploading(false);
    e.target.value = "";
  }, []);

  function removeAttachment(idx: number) {
    setAttachments((prev) => prev.filter((_, i) => i !== idx));
  }

  // ── Empty state ───────────────────────────────────────────────────────
  if (messages.length === 0 && !loading) {
    return (
      <div className="flex flex-col h-full bg-[#050508]">
        <div className="flex-1 flex flex-col items-center justify-center px-6 gap-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-accent/20 to-accent-violet/20 flex items-center justify-center">
            <Sparkles className="h-7 w-7 text-accent" />
          </div>
          <div className="text-center">
            <h2 className="text-lg font-semibold text-text-primary mb-1.5">BlackGrid AI Analyst</h2>
            <p className="text-xs text-text-muted max-w-[280px] leading-relaxed">
              Institutional-grade equity research powered by Claude. Analyze any publicly traded company.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 w-full max-w-sm">
            {SUGGESTED.map((p) => (
              <button key={p} onClick={() => onSend(p, [])}
                className="text-[11px] text-text-secondary border border-white/[0.06] rounded-xl px-3 py-2.5 hover:bg-white/[0.04] hover:border-white/[0.1] hover:text-text-primary transition-all text-left leading-snug">
                {p}
              </button>
            ))}
          </div>
        </div>
        {renderComposer()}
      </div>
    );
  }

  // ── Conversation ──────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full bg-[#050508]">
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-5 py-6 space-y-6">
          {messages.map((msg, i) => (
            <div key={i} className="space-y-1">
              {msg.role === "user" ? (
                <div className="flex justify-end">
                  <div className="max-w-[80%] rounded-2xl rounded-br-md bg-white/[0.07] px-4 py-3 text-[13px] text-gray-200 leading-relaxed whitespace-pre-wrap">
                    {msg.content}
                  </div>
                </div>
              ) : (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-6 h-6 rounded-full bg-gradient-to-br from-accent/30 to-accent-violet/30 flex items-center justify-center">
                      <Sparkles className="h-3 w-3 text-accent" />
                    </div>
                    <span className="text-[11px] font-medium text-gray-500">BlackGrid Analyst</span>
                  </div>
                  <div className="pl-8 text-[13px] text-gray-400 leading-[1.7] whitespace-pre-wrap">
                    {msg.content}
                  </div>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-full bg-gradient-to-br from-accent/30 to-accent-violet/30 flex items-center justify-center">
                  <Sparkles className="h-3 w-3 text-accent" />
                </div>
                <span className="text-[11px] font-medium text-gray-500">BlackGrid Analyst</span>
              </div>
              <div className="pl-8 flex items-center gap-2.5">
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" style={{ animationDelay: "0ms" }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" style={{ animationDelay: "200ms" }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" style={{ animationDelay: "400ms" }} />
                </div>
                <span key={statusIdx} className="text-xs text-gray-500 italic animate-fade-in">
                  {STATUS_PHRASES[statusIdx]}...
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
      {renderComposer()}
    </div>
  );

  function renderComposer() {
    return (
      <div className="px-4 pb-4 pt-2 relative">
        {/* Clear history */}
        {messages.length > 0 && onClearHistory && (
          <div className="flex justify-end mb-1">
            <button onClick={onClearHistory}
              className="text-[10px] text-gray-600 hover:text-danger transition-colors px-1">
              Clear history
            </button>
          </div>
        )}
        {/* Model dropdown — rendered OUTSIDE the composer box so it's never clipped */}
        {showModelMenu && (
          <div ref={modelMenuRef} className="absolute bottom-[68px] right-6 w-52 bg-[#0c0c12] border border-white/[0.12] rounded-xl shadow-2xl shadow-black/60 py-1.5 z-[100]">
            {ANTHROPIC_MODELS.map((m) => (
              <button
                key={m.id}
                onClick={() => { onModelChange(m.id); setShowModelMenu(false); }}
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

        {/* Attachment previews */}
        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-2">
            {attachments.map((a, i) => (
              <div key={i} className="flex items-center gap-1.5 bg-white/[0.06] border border-white/[0.08] rounded-lg px-2.5 py-1.5 text-[11px] text-gray-400">
                <FileIcon className="h-3 w-3 text-gray-500" />
                <span className="truncate max-w-[120px]">{a.filename}</span>
                <span className="text-gray-600">{(a.size / 1024).toFixed(0)}KB</span>
                <button onClick={() => removeAttachment(i)} className="text-gray-500 hover:text-gray-300 ml-0.5">
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        )}
        {uploadError && <p className="text-[11px] text-red-400 mb-1.5 px-1">{uploadError}</p>}
        {uploading && <p className="text-[11px] text-gray-500 mb-1.5 px-1 animate-pulse">Uploading...</p>}

        <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl">
          <textarea ref={inputRef} value={input} onChange={handleInput} onKeyDown={handleKeyDown}
            placeholder="Ask about any company or ticker..." disabled={loading} rows={1}
            className="w-full bg-transparent text-[13px] text-gray-200 placeholder-gray-600 outline-none resize-none px-4 pt-3.5 pb-1 leading-relaxed" />
          <div className="flex items-center justify-between px-3 pb-2.5">
            <div className="flex items-center gap-1">
              <input ref={fileRef} type="file" className="hidden" accept=".pdf,.docx,.txt,.csv" onChange={handleFileSelect} />
              <button type="button" onClick={() => fileRef.current?.click()} disabled={uploading}
                className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-600 hover:text-gray-400 hover:bg-white/[0.04] transition-colors" title="Attach file">
                <Paperclip className="h-4 w-4" />
              </button>
              <input ref={imageRef} type="file" className="hidden" accept="image/png,image/jpeg,image/webp" onChange={handleFileSelect} />
              <button type="button" onClick={() => imageRef.current?.click()} disabled={uploading}
                className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-600 hover:text-gray-400 hover:bg-white/[0.04] transition-colors" title="Attach image">
                <ImagePlus className="h-4 w-4" />
              </button>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => setShowModelMenu(!showModelMenu)}
                className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-400 transition-colors select-none px-1.5 py-0.5 rounded hover:bg-white/[0.04]">
                {currentModel.label}
                <ChevronDown className="h-2.5 w-2.5" />
              </button>
              <button onClick={submit}
                disabled={(!input.trim() && attachments.length === 0) || loading}
                className={cn("w-8 h-8 rounded-xl flex items-center justify-center transition-all",
                  (input.trim() || attachments.length > 0) && !loading
                    ? "bg-accent text-background hover:bg-accent/80"
                    : "bg-white/[0.04] text-gray-700 cursor-not-allowed")}>
                <Send className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }
}
