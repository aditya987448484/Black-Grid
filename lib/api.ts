const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function fetcher<T>(path: string): Promise<T> {
  const url = `${BASE_URL}${path}`;
  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) {
      console.error(`API error: ${res.status} ${res.statusText} for ${url}`);
      throw new Error(`API ${res.status}`);
    }
    return res.json();
  } catch (err) {
    console.error(`Fetch failed for ${url}:`, err);
    throw err;
  }
}

import type { MarketOverviewResponse } from "@/types/market";
import type { AssetDetail, AssetTechnicalResponse, AssetForecastResponse } from "@/types/asset";
import type { AnalystReportResponse } from "@/types/report";
import type { BacktestSummaryResponse, BacktestModelResult, StrategyRegistry } from "@/types/backtest";
import type { WatchlistResponse } from "@/types/portfolio";
import type { FlightsResponse, ShipsResponse, GeopoliticalResponse, WorldHubOverview } from "@/types/world-hub";
import type { CompanySearchResponse } from "@/types/universe";
import type { AiAnalystResponse, ChatMessage, AttachmentMeta } from "@/types/ai-analyst";

export function getMarketOverview() {
  return fetcher<MarketOverviewResponse>("/api/market/overview");
}

export function getAssetDetail(ticker: string) {
  return fetcher<AssetDetail>(`/api/asset/${ticker}`);
}

export function getTechnicals(ticker: string) {
  return fetcher<AssetTechnicalResponse>(`/api/asset/${ticker}/technicals`);
}

export function getForecast(ticker: string) {
  return fetcher<AssetForecastResponse>(`/api/asset/${ticker}/forecast`);
}

export function getReport(ticker: string) {
  return fetcher<AnalystReportResponse>(`/api/asset/${ticker}/report`);
}

export function getBacktestSummary() {
  return fetcher<BacktestSummaryResponse>("/api/backtests/summary");
}

export async function getBacktestResults(
  ticker = "SPY",
  startDate?: string,
  endDate?: string,
): Promise<BacktestSummaryResponse> {
  const params = new URLSearchParams({ ticker });
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const res = await fetch(`${BASE_URL}/api/backtests/summary?${params}`);
  if (!res.ok) throw new Error(`Backtest failed: ${res.status}`);
  return res.json();
}

export async function getStrategyList(): Promise<StrategyRegistry> {
  const res = await fetch(`${BASE_URL}/api/backtests/strategies/list`);
  if (!res.ok) throw new Error("Failed to load strategies");
  return res.json();
}

export async function runCustomStrategy(payload: {
  ticker: string;
  strategy_key: string;
  params: Record<string, number>;
  custom_name?: string;
  start_date?: string;
  end_date?: string;
}): Promise<BacktestModelResult> {
  const res = await fetch(`${BASE_URL}/api/backtests/strategies/run-custom`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Custom strategy failed: ${res.status}`);
  return res.json();
}

export async function strategyChat(payload: {
  message: string;
  history: { role: string; content: string }[];
  ticker: string;
  start_date?: string;
  end_date?: string;
  model?: string;
  api_key?: string;
}): Promise<{
  reply: string;
  strategy_key: string | null;
  params: Record<string, number>;
  run_immediately: boolean;
  strategyResult?: BacktestModelResult;
  market_context?: string;
}> {
  const res = await fetch(`${BASE_URL}/api/backtests/strategies/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
  return res.json();
}

export function getWatchlist() {
  return fetcher<WatchlistResponse>("/api/portfolio/watchlist");
}

export function getWorldHubFlights() {
  return fetcher<FlightsResponse>("/api/world-hub/flights");
}

export function getWorldHubShips() {
  return fetcher<ShipsResponse>("/api/world-hub/ships");
}

export function getWorldHubGeopolitical() {
  return fetcher<GeopoliticalResponse>("/api/world-hub/geopolitical");
}

export function getWorldHubOverview() {
  return fetcher<WorldHubOverview>("/api/world-hub/overview");
}

export function searchCompanies(query: string) {
  return fetcher<CompanySearchResponse>(`/api/search/companies?q=${encodeURIComponent(query)}`);
}

export async function aiAnalystChat(
  message: string,
  history: ChatMessage[],
  model: string = "claude-sonnet-4-20250514",
  attachments: AttachmentMeta[] = [],
): Promise<AiAnalystResponse> {
  const url = `${BASE_URL}/api/ai-analyst/chat`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, model, attachments }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export async function uploadAnalystFile(file: File): Promise<AttachmentMeta> {
  const url = `${BASE_URL}/api/ai-analyst/upload`;
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(url, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed (${res.status})`);
  }
  return res.json();
}
