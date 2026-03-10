export interface BacktestModelResult {
  modelName: string;
  strategyKey?: string;
  category?: string;
  description?: string;
  params?: Record<string, number>;
  isCustom?: boolean;
  customLabel?: string;
  cumulativeReturn: number;
  sharpeRatio: number;
  winRate: number;
  maxDrawdown: number;
  volatility: number;
  calmarRatio?: number;
  totalTrades?: number;
  accuracy?: number;
  insufficientData?: boolean;
  equityCurve: { date: string; value: number }[];
}

export interface StrategyMeta {
  name: string;
  category: string;
  description: string;
  defaultParams: Record<string, number>;
}

export type StrategyRegistry = Record<string, StrategyMeta>;

export interface SavedStrategy {
  id: string;
  label: string;
  strategyKey: string;
  params: Record<string, number>;
  ticker: string;
  savedAt: string;
  result: BacktestModelResult;
}

export interface BacktestSummaryResponse {
  ticker: string;
  period: string;
  dataPoints: number;
  models: BacktestModelResult[];
  benchmarkReturn: number;
  error?: string;
}

export interface ChatStrategyMessage {
  role: "user" | "assistant";
  content: string;
  strategyResult?: BacktestModelResult;
  marketContext?: string;
  timestamp?: string;
  attachments?: AttachmentMeta[];
}

export interface AttachmentMeta {
  filename: string;
  contentType: string;
  size: number;
  base64?: string;
  textContent?: string;
}
