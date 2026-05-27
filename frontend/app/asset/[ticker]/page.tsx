'use client';

import { useCallback } from 'react';
import { useParams } from 'next/navigation';
import { TrendingUp, DollarSign, Percent, Loader, AlertCircle } from 'lucide-react';
import { GlassCard, DataCard } from '@/components/common/Card';
import { ChartContainer, ChartPlaceholder } from '@/components/charts/ChartContainer';
import { ModelCard } from '@/components/forecast/ModelCard';
import { DashboardLayoutWrapper } from '@/components/common/DashboardLayout';
import { useApi } from '@/lib/hooks/useApi';
import { asset } from '@/lib/api/client';
import type { AssetDetail, TechnicalDataResponse, ForecastResponse, ModelForecastOutput } from '@/lib/types';

export default function AssetDetailPage() {
  const params = useParams();
  const ticker = (params?.ticker as string)?.toUpperCase() || '';

  const detailRequest = useCallback(() => asset.getDetail(ticker), [ticker]);
  const technicalRequest = useCallback(() => asset.getTechnicals(ticker), [ticker]);
  const forecastRequest = useCallback(() => asset.getForecast(ticker), [ticker]);

  const detailApi = useApi<AssetDetail>(detailRequest, !!ticker);
  const techApi = useApi<TechnicalDataResponse>(technicalRequest, !!ticker);
  const forecastApi = useApi<ForecastResponse>(forecastRequest, !!ticker);

  const data = detailApi.data;
  const isLoadingDetail = detailApi.status === 'pending';
  const isLoadingTech = techApi.status === 'pending';
  const isLoadingForecast = forecastApi.status === 'pending';
  const hasError = detailApi.status === 'error' || techApi.status === 'error';
  const hasForecastError = forecastApi.status === 'error';

  if (!ticker) {
    return (
      <DashboardLayoutWrapper>
        <div className="px-8 py-8">
          <p className="text-muted-foreground">Invalid ticker</p>
        </div>
      </DashboardLayoutWrapper>
    );
  }

  return (
    <DashboardLayoutWrapper>
      <div className="min-h-screen section-padding py-6">
        {/* Header */}
        <div className="animate-in mb-8">
          <div className="flex items-start justify-between gap-6">
            <div className="flex-1">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-lg bg-gradient-to-br from-primary/40 to-cyan-500/20 flex items-center justify-center flex-shrink-0 shadow-[0_0_20px_rgba(0,200,255,0.15)]">
                  <TrendingUp className="w-7 h-7 text-primary" />
                </div>
                <div>
                  <h1 className="text-5xl font-bold tracking-tight text-foreground leading-tight">{ticker}</h1>
                  <p className="text-muted-foreground/70 text-base mt-2 font-medium">
                    {isLoadingDetail ? <Loader className="w-4 h-4 inline animate-spin" /> : data?.name || 'Loading...'}
                  </p>
                </div>
              </div>
            </div>
            <button className="px-6 py-2.5 rounded-lg bg-gradient-to-r from-primary to-cyan-500 text-primary-foreground font-semibold hover:shadow-premium-lg active:opacity-95 transition-smooth duration-200 flex-shrink-0 whitespace-nowrap">
              Add to Watchlist
            </button>
          </div>
        </div>

        {/* Error State */}
        {hasError && (
          <div className="flex items-start gap-4 px-4 py-4 rounded-lg bg-destructive/10 border border-destructive/20 mb-8 backdrop-blur-sm">
            <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-destructive">Failed to load asset data</p>
              <p className="text-xs text-destructive/70 mt-1.5">Please check your connection and try again</p>
            </div>
          </div>
        )}

        {/* Price Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-in-up" style={{ animationDelay: '100ms' }}>
          {isLoadingDetail ? (
            <>
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-32 rounded-lg bg-surface-secondary/50 animate-pulse" />
              ))}
            </>
          ) : data ? (
            <>
              <DataCard
                label="Current Price"
                value={data.price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
                change={data.change_percent}
                changeLabel="Today"
                icon={<DollarSign className="w-6 h-6" />}
              />
              <DataCard
                label="Market Cap"
                value={`$${(data.market_cap / 1e12).toFixed(2)}T`}
                change={0.0156}
                changeLabel="vs 7d"
                icon={<TrendingUp className="w-6 h-6" />}
              />
              <DataCard
                label="P/E Ratio"
                value={data.pe_ratio.toFixed(1)}
                suffix="x"
                change={-0.0082}
                changeLabel="vs 90d avg"
                icon={<Percent className="w-6 h-6" />}
              />
            </>
          ) : null}
        </div>

        {/* Key Metrics */}
        <GlassCard className="animate-in-up mb-8" style={{ animationDelay: '150ms' }}>
          {isLoadingDetail ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-20 rounded-lg bg-surface-secondary/50 shimmer" />
              ))}
            </div>
          ) : data ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              {[
                { label: 'Dividend Yield', value: `${(data.dividend_yield * 100).toFixed(2)}%` },
                { label: '52w High', value: data.week_52_high.toLocaleString('en-US', { style: 'currency', currency: 'USD' }) },
                { label: '52w Low', value: data.week_52_low.toLocaleString('en-US', { style: 'currency', currency: 'USD' }) },
                { label: 'Avg Volume', value: `${(data.avg_volume / 1e6).toFixed(1)}M` },
              ].map((metric) => (
                <div key={metric.label} className="space-y-2">
                  <p className="text-label text-muted-foreground/70">{metric.label}</p>
                  <p className="text-2xl font-bold text-foreground tracking-tight">{metric.value}</p>
                </div>
              ))}
            </div>
          ) : null}
        </GlassCard>

        {/* Price Chart */}
        <ChartContainer
          title="Price Chart"
          subtitle="Last 30 days"
          className="min-h-96 animate-in-up mb-8"
          style={{ animationDelay: '200ms' }}
          tools={
            <div className="flex gap-2 bg-surface-secondary/30 rounded-lg p-1">
              <button className="px-3 py-2 text-xs font-semibold rounded-md text-muted-foreground/70 hover:bg-surface-secondary/70 transition-smooth duration-200 uppercase tracking-wider">
                1M
              </button>
              <button className="px-3 py-2 text-xs font-semibold rounded-md bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-smooth duration-200 uppercase tracking-wider">
                6M
              </button>
              <button className="px-3 py-2 text-xs font-semibold rounded-md text-muted-foreground/70 hover:bg-surface-secondary/70 transition-smooth duration-200 uppercase tracking-wider">
                1Y
              </button>
              <button className="px-3 py-2 text-xs font-semibold rounded-md text-muted-foreground/70 hover:bg-surface-secondary/70 transition-smooth duration-200 uppercase tracking-wider">
                ALL
              </button>
            </div>
          }
        >
          <ChartPlaceholder height="h-80" />
        </ChartContainer>

        {/* Technical Analysis */}
        <GlassCard className="animate-in-up mb-8" style={{ animationDelay: '250ms' }}>
          <div className="space-y-6">
            <h3 className="text-lg font-semibold text-foreground tracking-tight">Technical Indicators</h3>
            {isLoadingTech ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-16 rounded-lg bg-surface-secondary/50 shimmer" />
                ))}
              </div>
            ) : techApi.data?.indicators ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: 'RSI (14)', value: techApi.data.indicators.rsi_14.toFixed(2) },
                  { label: 'SMA 20', value: `$${techApi.data.indicators.sma_20.toFixed(2)}` },
                  { label: 'SMA 50', value: `$${techApi.data.indicators.sma_50.toFixed(2)}` },
                  { label: 'MACD', value: techApi.data.indicators.macd.toFixed(4) },
                ].map((indicator) => (
                  <div key={indicator.label} className="p-4 rounded-lg bg-surface-secondary/40 border border-border/20 hover:border-border/30 hover:bg-surface-secondary/60 transition-smooth duration-200">
                    <p className="text-xs text-muted-foreground/70 font-semibold uppercase tracking-wider">{indicator.label}</p>
                    <p className="text-lg font-bold text-foreground mt-2.5 tracking-tight">{indicator.value}</p>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        </GlassCard>

        {/* About Section */}
        <GlassCard className="animate-in-up" style={{ animationDelay: '300ms' }}>
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-foreground tracking-tight">About {ticker}</h3>
            <p className="text-foreground/90 leading-relaxed text-base">
              {data?.name} is a leading company in its sector. The company provides innovative products and services to
              customers worldwide and is committed to delivering excellence in all its operations and customer interactions.
            </p>
          </div>
        </GlassCard>

        {/* AI Forecast Section */}
        <GlassCard className="animate-in-up mt-8" style={{ animationDelay: '350ms' }}>
          <div className="space-y-6">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-semibold text-foreground tracking-tight">AI Forecast Comparison</h3>
                <p className="text-sm text-muted-foreground/70 mt-1">5-day forward price & direction predictions</p>
              </div>
              {forecastApi.data?.generated_at && (
                <div className="text-xs text-muted-foreground/60 text-right">
                  <p>Updated</p>
                  <p className="font-medium text-foreground/70 mt-0.5">
                    {new Date(forecastApi.data.generated_at).toLocaleTimeString()}
                  </p>
                </div>
              )}
            </div>

            {/* Error State */}
            {hasForecastError && (
              <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-amber-400">Could not load forecast models</p>
                  <p className="text-xs text-amber-400/70 mt-1">Showing placeholder predictions</p>
                </div>
              </div>
            )}

            {/* Models Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {isLoadingForecast ? (
                // Loading state: 4 skeleton cards
                ['Baseline', 'LSTM/GRU', 'Temporal Fusion', 'Ensemble'].map((name) => (
                  <ModelCard
                    key={name}
                    model={{
                      model_name: name,
                      model_type: 'baseline',
                      signal: 'HOLD',
                      expected_return: 0,
                      confidence: 0,
                      accuracy: null,
                      status: 'training',
                      last_updated: new Date().toISOString(),
                      description: '',
                    } satisfies ModelForecastOutput}
                    isPlaceholder
                  />
                ))
              ) : forecastApi.data?.models?.length ? (
                // Loaded state: render each model returned by the backend
                forecastApi.data.models.map((m) => (
                  <ModelCard key={m.model_name} model={m} />
                ))
              ) : (
                // Error / no-data state
                ['Baseline', 'LSTM/GRU', 'Temporal Fusion', 'Ensemble'].map((name) => (
                  <ModelCard
                    key={name}
                    model={{
                      model_name: name,
                      model_type: 'baseline',
                      signal: 'HOLD',
                      expected_return: 0,
                      confidence: 0,
                      accuracy: null,
                      status: 'error',
                      last_updated: new Date().toISOString(),
                      description: '',
                    } satisfies ModelForecastOutput}
                    isPlaceholder
                  />
                ))
              )}
            </div>

            {/* Consensus Section */}
            {forecastApi.data?.consensus && !isLoadingForecast && (
              <div className="pt-4 border-t border-border/20">
                <h4 className="text-sm font-semibold text-foreground mb-4 uppercase tracking-wider">Consensus</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Consensus Signal */}
                  <div className="p-4 rounded-lg bg-surface-secondary/40 border border-border/20">
                    <p className="text-xs text-muted-foreground/70 font-semibold uppercase tracking-wider mb-2">
                      Signal
                    </p>
                    <p className={`text-2xl font-bold tracking-tight ${
                      forecastApi.data.consensus.consensus_signal === 'BUY'
                        ? 'text-success'
                        : forecastApi.data.consensus.consensus_signal === 'SELL'
                          ? 'text-destructive'
                          : 'text-amber-400'
                    }`}>
                      {forecastApi.data.consensus.consensus_signal}
                    </p>
                  </div>

                  {/* Average Confidence */}
                  <div className="p-4 rounded-lg bg-surface-secondary/40 border border-border/20">
                    <p className="text-xs text-muted-foreground/70 font-semibold uppercase tracking-wider mb-2">
                      Avg Confidence
                    </p>
                    <p className="text-2xl font-bold text-foreground tracking-tight mb-3">
                      {forecastApi.data.consensus.average_confidence.toFixed(0)}%
                    </p>
                    <div className="w-full h-1.5 rounded-full bg-surface-secondary/50 overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all duration-500"
                        style={{ width: `${Math.min(forecastApi.data.consensus.average_confidence, 100)}%` }}
                      />
                    </div>
                  </div>

                  {/* Average Return */}
                  <div className="p-4 rounded-lg bg-surface-secondary/40 border border-border/20">
                    <p className="text-xs text-muted-foreground/70 font-semibold uppercase tracking-wider mb-2">
                      Avg Return ({forecastApi.data.horizon_days}d)
                    </p>
                    <p className={`text-2xl font-bold tracking-tight ${
                      forecastApi.data.consensus.average_return >= 0 ? 'text-success' : 'text-destructive'
                    }`}>
                      {forecastApi.data.consensus.average_return >= 0 ? '+' : ''}
                      {forecastApi.data.consensus.average_return.toFixed(2)}%
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </GlassCard>
      </div>
    </DashboardLayoutWrapper>
  );
}
