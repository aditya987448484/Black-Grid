"use client";

import { useState, useCallback, useEffect } from "react";
import { aiAnalystChat } from "@/lib/api";
import type { ChatMessage, AiAnalystResponse, AttachmentMeta } from "@/types/ai-analyst";
import ChatPanel from "@/components/ai-analyst/ChatPanel";
import AnalystWorkspace from "@/components/ai-analyst/AnalystWorkspace";

export default function AiAnalystPage() {
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const stored = localStorage.getItem("blackgrid_analyst_chat");
      return stored ? JSON.parse(stored) : [];
    } catch { return []; }
  });
  const [loading, setLoading] = useState(false);
  const [workspace, setWorkspace] = useState<AiAnalystResponse | null>(null);
  const [workspaceLoading, setWorkspaceLoading] = useState(false);
  const [model, setModel] = useState("claude-sonnet-4-6");

  useEffect(() => {
    try {
      localStorage.setItem("blackgrid_analyst_chat", JSON.stringify(messages.slice(-60)));
    } catch {}
  }, [messages]);

  const handleSend = useCallback(async (message: string, attachments: AttachmentMeta[]) => {
    const userMsg: ChatMessage = { role: "user", content: message };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setWorkspaceLoading(true);

    try {
      const history = [...messages, userMsg].slice(-10);
      const response = await aiAnalystChat(message, history, model, attachments);

      const assistantMsg: ChatMessage = { role: "assistant", content: response.reply };
      setMessages((prev) => [...prev, assistantMsg]);

      // Always update workspace when a ticker is resolved — the report is the primary output
      if (response.ticker) {
        setWorkspace(response);
      }
    } catch {
      const errorMsg: ChatMessage = {
        role: "assistant",
        content: "I encountered an error processing your request. Please check that the backend is running and try again.",
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
      setWorkspaceLoading(false);
    }
  }, [messages, model]);

  return (
    <div className="flex h-[calc(100vh-7rem)] gap-0">
      <div className="w-[440px] flex-shrink-0 border-r border-white/[0.06] flex flex-col">
        <ChatPanel
          messages={messages}
          onSend={handleSend}
          loading={loading}
          model={model}
          onModelChange={setModel}
          onClearHistory={() => {
            setMessages([]);
            try { localStorage.removeItem("blackgrid_analyst_chat"); } catch {}
          }}
        />
      </div>
      <div className="flex-1 min-w-0 flex flex-col">
        <AnalystWorkspace data={workspace} loading={workspaceLoading} />
      </div>
    </div>
  );
}
