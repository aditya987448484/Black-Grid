export interface BacktestModelResult {
  modelName: string;
  accuracy: number;
  cumulativeReturn: number;
  winRate: number;
  sharpeRatio: number;
  maxDrawdown: number;
  volatility: number;
  description: string;
  calmarRatio?: number;
  totalTrades?: number;
  strategyKey?: string;
  category?: string;
  insufficientData?: boolean;
  params?: Record<string, number>;
  equityCurve: { date: string; value: number }[];
  isCustom?: boolean;
  customLabel?: string;
}

export interface BacktestSummaryResponse {
  models: BacktestModelResult[];
  benchmarkReturn: number;
  period: string;
  ticker: string;
  dataPoints: number;
  error?: string;
}

export interface StrategyMeta {
  name: string;
  category: string;
  description: string;
  defaultParams: Record<string, number>;
}

export type StrategyRegistry = Record<string, StrategyMeta>;

export interface ChatStrategyMessage {
  role: "user" | "assistant";
  content: string;
  strategyResult?: BacktestModelResult;
  marketContext?: string;
}

export interface SavedStrategy {
  id: string;
  label: string;
  strategyKey: string;
  params: Record<string, number>;
  ticker: string;
  savedAt: string;
  result?: BacktestModelResult;
}
