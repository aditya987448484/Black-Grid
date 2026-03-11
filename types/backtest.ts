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

// ── Strategy Engine Types ──────────────────────────────────────────

export interface IndicatorReference {
  indicator_key: string;
  params?: Record<string, number>;
  alias?: string;
}

export interface Condition {
  left: IndicatorReference | string;
  operator: string;
  right: IndicatorReference | string | number;
  right_upper?: number;
}

export interface ConditionGroup {
  logic: "and" | "or";
  conditions: Condition[];
}

export interface EntryRuleSet {
  long_conditions: ConditionGroup[];
  short_conditions: ConditionGroup[];
}

export interface ExitRuleSet {
  long_exit_conditions: ConditionGroup[];
  short_exit_conditions: ConditionGroup[];
}

export interface RiskRuleSet {
  stop_loss_pct?: number;
  take_profit_pct?: number;
  trailing_stop_pct?: number;
  trailing_stop_atr_mult?: number;
  max_positions?: number;
  sizing_mode?: string;
  risk_per_trade_pct?: number;
}

export interface StrategySpec {
  name: string;
  ticker?: string;
  direction: "long_only" | "short_only" | "long_short";
  timeframe: string;
  entry: EntryRuleSet;
  exit: ExitRuleSet;
  risk: RiskRuleSet;
  filters: ConditionGroup[];
  notes: string;
}

export interface StrategyParseResponse {
  reply: string;
  strategy_spec?: StrategySpec;
  interpretation_summary: string;
  assumptions: string[];
  unsupported_clauses: string[];
  confidence: number;
  can_run_immediately: boolean;
}

export interface StrategyRunResponse {
  result?: BacktestModelResult;
  compiled_conditions_summary: string[];
  error?: string;
}

export interface IndicatorCatalogEntry {
  key: string;
  display_name: string;
  category: string;
  parameters: Record<string, number>;
  description: string;
  supported_operators: string[];
  required_fields: string[];
  output_type: string;
}

export type IndicatorCatalog = Record<string, IndicatorCatalogEntry>;
