// AI Analyst types — all LLM logic uses DeepSeek

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
  /** ISO timestamp added client-side for display */
  timestamp?: string;
}

export interface AIAnalystModel {
  id: string;
  label: string;
  badge?: string;
}

export const DEEPSEEK_MODELS: AIAnalystModel[] = [
  { id: "deepseek-chat", label: "DeepSeek V3", badge: "Recommended" },
  { id: "deepseek-reasoner", label: "DeepSeek R1", badge: "Deep reasoning" },
];

export const DEFAULT_AI_MODEL = DEEPSEEK_MODELS[0].id;

export interface ChatRequest {
  messages: ChatMessage[];
  model?: string;
  ticker?: string;
  context?: Record<string, unknown>;
}

export interface ChatResponse {
  reply: string;
  model: string;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}
