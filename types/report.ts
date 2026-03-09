export interface ReportSection {
  title: string;
  content: string;
}

export interface ReportPricePoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ReportQuote {
  price: number;
  change: number;
  changePercent: number;
  volume: number;
}

export interface AnalystReportResponse {
  ticker: string;
  name: string;
  generatedAt: string;
  rating: "Strong Buy" | "Buy" | "Hold" | "Sell" | "Strong Sell";
  confidenceScore: number;
  sector?: string;
  analystName: string;
  sections: ReportSection[];
  executiveSummary: string;
  keyHighlights: string;
  technicalView: string;
  fundamentalSnapshot: string;
  macroContext: string;
  forecastView: string;
  valuationScenarios: string;
  competitiveLandscape: string;
  bullCase: string;
  bearCase: string;
  risksCatalysts: string;
  analystConclusion: string;
  disclaimer: string;
  // Chart data and quote for rendering
  quote?: ReportQuote;
  chart?: ReportPricePoint[];
}
