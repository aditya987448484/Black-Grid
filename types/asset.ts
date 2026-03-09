export interface AssetDetail {
  ticker: string;
  name: string;
  sector: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  marketCap: number;
  signal: "bullish" | "bearish" | "neutral";
  signalScore: number;
  priceHistory: PricePoint[];
}

export interface PricePoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TechnicalIndicator {
  name: string;
  value: number;
  signal: "bullish" | "bearish" | "neutral";
  description: string;
}

export interface AssetTechnicalResponse {
  ticker: string;
  indicators: TechnicalIndicator[];
  ema: { period: number; value: number }[];
  rsi: number;
  macd: { macd: number; signal: number; histogram: number };
  atr: number;
  volatility: number;
}

export interface ForecastModelOutput {
  modelName: string;
  status: "live" | "simulated" | "coming_soon";
  directionProbability: number;
  predictedDirection: "up" | "down";
  expectedReturn: number;
  confidence: number;
  explanation: string;
}

export interface AssetForecastResponse {
  ticker: string;
  models: ForecastModelOutput[];
  bullishFactors: string[];
  bearishFactors: string[];
  riskLevel: "low" | "medium" | "high";
  aiSummary: string;
}
