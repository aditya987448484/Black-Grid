export interface MarketMetric {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  volume?: number;
  sparkline?: number[];
}

export interface MacroIndicator {
  name: string;
  value: number;
  unit: string;
  trend: "rising" | "falling" | "stable";
}

export interface SignalItem {
  ticker: string;
  name: string;
  signal: "bullish" | "bearish" | "neutral";
  confidence: number;
  expectedReturn: number;
}

export interface MarketOverviewResponse {
  indices: MarketMetric[];
  signals: SignalItem[];
  macro: MacroIndicator[];
  watchlist: WatchlistItem[];
  recentReports: ReportSummary[];
}

export interface WatchlistItem {
  ticker: string;
  name: string;
  price: number;
  change1d: number;
  change5d: number;
  change1m: number;
  signal: "bullish" | "bearish" | "neutral";
  signalScore: number;
  confidence: number;
  riskScore: number;
  alert?: string;
}

export interface ReportSummary {
  ticker: string;
  name: string;
  rating: string;
  confidence: number;
  generatedAt: string;
  summary: string;
}
