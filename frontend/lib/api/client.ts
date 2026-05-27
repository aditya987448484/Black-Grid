import type {
  MarketOverviewResponse,
  AssetDetail,
  TechnicalDataResponse,
  ForecastResponse,
  AnalystReport,
  BacktestResult,
  BacktestSummaryResponse,
  WatchlistResponse,
  WatchlistIntelligenceResponse,
} from '@/lib/types';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// Market API
export const market = {
  getOverview: (): Promise<MarketOverviewResponse> =>
    get<MarketOverviewResponse>('/market/overview'),
};

// Asset API
export const asset = {
  getDetail: (ticker: string): Promise<AssetDetail> =>
    get<AssetDetail>(`/asset/${ticker}`),
  getTechnicals: (ticker: string, days?: number): Promise<TechnicalDataResponse> =>
    get<TechnicalDataResponse>(`/asset/${ticker}/technicals${days != null ? `?days=${days}` : ''}`),
  getForecast: (ticker: string, days?: number): Promise<ForecastResponse> =>
    get<ForecastResponse>(`/asset/${ticker}/forecast${days != null ? `?days=${days}` : ''}`),
};

// Report API
// Backend returns { status: string, data: AnalystReport, generated_at: string }
// We unwrap and return just the AnalystReport.
export const report = {
  async getAnalystReport(ticker: string): Promise<AnalystReport> {
    const res = await get<{ status: string; data: AnalystReport }>(`/report/${ticker}`);
    return res.data;
  },
};

// Forecast API
export const forecast = {
  getComparison: (ticker: string, days?: number): Promise<ForecastResponse> =>
    get<ForecastResponse>(`/forecast/${ticker}${days != null ? `?days=${days}` : ''}`),
};

// Backtest API
export const backtest = {
  getSummary: (limit?: number): Promise<BacktestSummaryResponse> =>
    get<BacktestSummaryResponse>(`/backtests/summary${limit != null ? `?limit=${limit}` : ''}`),
  getTicker: (ticker: string): Promise<BacktestResult> =>
    get<BacktestResult>(`/backtests/${ticker}`),
};

// Portfolio API
export const portfolio = {
  getWatchlist: (): Promise<WatchlistResponse> =>
    get<WatchlistResponse>('/portfolio/watchlist'),
  getWatchlistIntelligence: (
    tickers?: string,
    historicalDays?: number,
  ): Promise<WatchlistIntelligenceResponse> => {
    const params = new URLSearchParams();
    if (tickers) params.set('tickers', tickers);
    if (historicalDays != null) params.set('historical_days', String(historicalDays));
    const q = params.toString();
    return get<WatchlistIntelligenceResponse>(
      `/portfolio/watchlist/intelligence${q ? `?${q}` : ''}`,
    );
  },
};

export default { market, asset, report, forecast, backtest, portfolio };
