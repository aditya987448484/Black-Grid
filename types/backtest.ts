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
  equityCurve: { date: string; value: number }[];
}

export interface BacktestSummaryResponse {
  models: BacktestModelResult[];
  benchmarkReturn: number;
  period: string;
  ticker: string;
  dataPoints: number;
}
