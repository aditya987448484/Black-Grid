export interface BacktestModelResult {
  modelName: string;
  accuracy: number;
  cumulativeReturn: number;
  winRate: number;
  sharpeRatio: number;
  maxDrawdown: number;
  volatility: number;
  calmarRatio: number;
  totalTrades: number;
  description: string;
  strategyKey?: string;
  category?: string;
  insufficientData: boolean;
  equityCurve: { date: string; value: number }[];
  // Custom strategy fields
  isCustom?: boolean;
  customLabel?: string;
  params?: Record<string, number>;
}

export interface BacktestSummaryResponse {
  models: BacktestModelResult[];
  benchmarkReturn: number;
  period: string;
  ticker: string;
  dataPoints: number;
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
}
