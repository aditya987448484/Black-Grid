export interface PortfolioItem {
  ticker: string;
  name: string;
  price: number;
  change1d: number;
  change5d: number;
  change1m: number;
  signalScore: number;
  confidence: number;
  riskScore: number;
  alert?: string;
  allocation: number;
}

export interface PortfolioSummary {
  totalValue: number;
  dailyChange: number;
  dailyChangePercent: number;
  topSignal: string;
  riskLevel: "low" | "medium" | "high";
}

export interface WatchlistResponse {
  items: PortfolioItem[];
  summary: PortfolioSummary;
}
