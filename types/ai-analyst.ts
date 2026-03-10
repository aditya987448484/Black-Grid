export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface QuotePayload {
  price: number;
  change: number;
  changePercent: number;
  volume: number;
}

export interface AnalysisPricePoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface AnalysisSection {
  key: string;
  title: string;
  content: string;
}

export interface AttachmentMeta {
  filename: string;
  contentType: string;
  size: number;
  summary?: string;
}

export interface AiAnalystResponse {
  reply: string;
  ticker?: string;
  companyName?: string;
  sector?: string;
  rating?: string;
  confidenceScore?: number;
  quote?: QuotePayload;
  chart: AnalysisPricePoint[];
  analysisSections: AnalysisSection[];
  disclaimer: string;
  modelUsed?: string;
}

export interface ModelOption {
  id: string;
  label: string;
  badge?: string;
}

export const ANTHROPIC_MODELS: ModelOption[] = [
  { id: "claude-opus-4-6", label: "Opus 4.6", badge: "Most Powerful" },
  { id: "claude-sonnet-4-6", label: "Sonnet 4.6", badge: "Recommended" },
  { id: "claude-sonnet-4-20250514", label: "Sonnet 4", badge: "" },
  { id: "claude-haiku-4-5-20251001", label: "Haiku 4.5", badge: "Fastest" },
];
