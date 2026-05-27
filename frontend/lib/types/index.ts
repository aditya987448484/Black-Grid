// Market Data
export interface MarketMetric {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  timestamp: string;
}

export interface MarketOverviewResponse {
  status: string;
  data: MarketMetric[];
  market_time: string;
  total_results: number;
}

// Asset Data
export interface AssetDetail {
  status: string;
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
  market_cap: number;
  pe_ratio: number;
  dividend_yield: number;
  week_52_high: number;
  week_52_low: number;
  avg_volume: number;
  timestamp: string;
}

// Technical Data
export interface Candle {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TechnicalIndicators {
  sma_20: number;
  sma_50: number;
  sma_200: number;
  ema_12: number;
  ema_26: number;
  rsi_14: number;
  macd: number;
  macd_signal: number;
  macd_histogram: number;
  bb_upper: number;
  bb_middle: number;
  bb_lower: number;
}

export interface TechnicalDataResponse {
  status: string;
  symbol: string;
  candles: Candle[];
  indicators: TechnicalIndicators;
  timestamp: string;
}

// Forecast Data — matches backend ForecastResponse / ModelForecastOutput schemas
export interface ModelForecastOutput {
  model_name: string;
  model_type: 'baseline' | 'lstm' | 'gru' | 'tft' | 'ensemble';
  signal: 'BUY' | 'HOLD' | 'SELL';
  /** Expected return as a real percentage, e.g. 2.1 means 2.1% */
  expected_return: number;
  /** Confidence score 0–100 */
  confidence: number;
  status: 'ready' | 'training' | 'stale' | 'error';
  /** Backtest accuracy 0–100, null for placeholder models */
  accuracy: number | null;
  last_updated: string;
  description: string;
}

export interface ForecastConsensus {
  consensus_signal: 'BUY' | 'HOLD' | 'SELL';
  /** Probability 0–100 */
  consensus_probability: number;
  /** Mean confidence 0–100 */
  average_confidence: number;
  /** Mean expected return as a real percentage */
  average_return: number;
  best_model: string;
  most_optimistic: string;
  most_conservative: string;
  model_agreement: string;
}

export interface ForecastResponse {
  status: string;
  ticker: string;
  current_price: number;
  horizon_days: number;
  models: ModelForecastOutput[];
  consensus: ForecastConsensus;
  generated_at: string;
  next_update: string;
}

// Analyst Report
export interface TechnicalViewpoint {
  trend: string;
  key_levels: number[];
  signal_strength: number;
  momentum: string;
  ma_alignment: string;
  summary: string;
}

export interface FundamentalSnapshot {
  eps: number | null;
  revenue_growth: number | null;
  profit_margin: number | null;
  roe: number | null;
  debt_to_equity: number | null;
  valuation_assessment: string;
  quality_score: number;
}

export interface MacroContext {
  sector_performance: string;
  industry_tailwinds: string[];
  macro_headwinds: string[];
  correlation_market: number;
  macro_outlook: string;
}

export interface InvestmentCase {
  thesis: string;
  key_catalysts: string[];
  timeline: string;
  probability: number;
}

export interface RiskCatalyst {
  description: string;
  severity: string;
  mitigation?: string;
}

export interface FinalRating {
  recommendation: 'BUY' | 'HOLD' | 'SELL';
  target_price: number;
  price_upside: number;
  conviction: string;
  rationale: string;
}

export interface AnalystReport {
  ticker: string;
  company_name: string;
  report_date: string;
  current_price: number;
  executive_summary: string;
  investment_highlight: string;
  technical_view: TechnicalViewpoint;
  fundamental_snapshot: FundamentalSnapshot;
  macro_context: MacroContext;
  bull_case: InvestmentCase;
  bear_case: InvestmentCase;
  risks: RiskCatalyst[];
  catalysts: RiskCatalyst[];
  final_rating: FinalRating;
  confidence_score: number;
}

export interface AnalystReportResponse {
  status: string;
  data: AnalystReport;
  generated_at: string;
}

// Backtest — matches backend BacktestResult / BacktestSummaryResponse schemas
export interface BacktestResult {
  backtest_id: string;
  strategy: string;
  /** Human-readable strategy description for display */
  strategy_description: string | null;
  ticker: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_value: number | null;
  total_return: number;
  annual_return: number | null;
  sharpe_ratio: number;
  sortino_ratio: number | null;
  max_drawdown: number;
  volatility: number | null;
  trades_count: number;
  win_rate: number;
  /** Next-day direction accuracy %; null for non-ML strategies */
  direction_accuracy: number | null;
  /** "completed" | "estimated" | "error" */
  status: string;
  created_at: string;
}

export interface BacktestSummaryResponse {
  status: string;
  data: BacktestResult[];
  total_results: number;
  timestamp: string;
}

// Portfolio/Watchlist
export interface PeriodChanges {
  change_1d: number;
  change_5d: number;
  change_1m: number;
}

export interface WatchlistItem {
  ticker: string;
  name: string;
  current_price: number;
  change: number;
  change_percent: number;
  market_cap: number;
  added_date: string;
}

export interface WatchlistIntelligenceItem {
  ticker: string;
  name: string;
  current_price: number;
  change_24h: number;
  added_date: string;
  signal_score?: number;
  confidence_score?: number;
  risk_score?: number;
  period_changes?: PeriodChanges;
  alert_level: string;
  alert_message: string;
  allocation_weight?: number;
}

export interface WatchlistResponse {
  status: string;
  data: WatchlistItem[];
  total_items: number;
  timestamp: string;
}

export interface WatchlistIntelligenceResponse {
  status: string;
  data: WatchlistIntelligenceItem[];
  total_items: number;
  updated_at: string;
}
