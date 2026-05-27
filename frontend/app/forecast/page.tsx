'use client';

import { useState, useCallback } from 'react';
import { RefreshCw, TrendingUp, GitCompare, AlertCircle } from 'lucide-react';
import { GlassCard } from '@/components/common/Card';
import { DashboardLayoutWrapper } from '@/components/common/DashboardLayout';
import { ForecastCard } from '@/components/forecast/ForecastCard';
import { useApi } from '@/lib/hooks/useApi';
import { forecast } from '@/lib/api/client';
import type { ForecastResponse } from '@/lib/types';

const MODEL_DESCRIPTIONS = {
  baseline: 'Simple moving average momentum model. Reference benchmark for other models. Trained on 5-year historical data.',
  lstm: 'Recurrent neural network with 2-layer LSTM. Captures temporal dependencies. Processes 252-day sequences.',
  tft: 'Attention-based transformer model. Multi-head attention across time and features. State-of-the-art architecture.',
  ensemble: 'Weighted combination of all models (40% TFT, 35% LSTM, 15% GRU, 10% Baseline). Reduces individual model risk.',
};

export default function ForecastPage() {
  const [ticker, setTicker] = useState('AAPL');
  const [searchInput, setSearchInput] = useState('AAPL');

  const forecastRequest = useCallback(() => forecast.getComparison(ticker), [ticker]);
  const { data: forecastData, status, execute } = useApi<ForecastResponse>(forecastRequest, true);

  const isLoading = status === 'pending';
  const hasError = status === 'error';

  const handleSearch = () => {
    if (searchInput.trim()) {
      setTicker(searchInput.toUpperCase());
    }
  };

  const handleRefresh = async () => {
    await execute();
  };

  // Models are already in the array from API
  const models = forecastData?.models || [];

  const consensus = forecastData?.consensus;
  const averageConfidence = consensus?.confidence ?? 0;
  const averageReturn = consensus?.average_return ?? 0;

  return (
    <DashboardLayoutWrapper>
      <div className="space-y-6 px-8 py-6">
        {/* Page Header */}
        <div className="animate-in">
          <h1 className="text-4xl font-bold text-foreground">AI Forecast Comparison</h1>
          <p className="text-muted-foreground mt-2">Real-time ML model predictions compared side-by-side</p>
        </div>

        {/* Controls Section */}
        <div className="flex gap-4 items-end">
          <GlassCard className="animate-in-up flex-1" style={{ animationDelay: '50ms' }}>
            <div className="flex items-end gap-3">
              <div className="flex-1">
                <label className="text-xs text-muted-foreground font-semibold uppercase block mb-2">Ticker</label>
                <input
                  type="text"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value.toUpperCase())}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="AAPL"
                  className="w-full px-4 py-3 rounded-lg bg-input border border-border/50 text-foreground placeholder-muted-foreground transition-smooth focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20"
                />
              </div>
              <button
                onClick={handleSearch}
                className="px-6 py-3 rounded-lg bg-primary text-primary-foreground font-semibold hover:shadow-premium-lg active:opacity-95 transition-smooth duration-200"
              >
                Search
              </button>
              <button
                onClick={handleRefresh}
                disabled={isLoading}
                className="px-4 py-3 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary font-semibold transition-all disabled:opacity-50 flex items-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </GlassCard>
        </div>

        {/* Error State */}
        {hasError && (
          <div className="flex items-start gap-4 px-4 py-4 rounded-lg bg-destructive/10 border border-destructive/20 mb-8 backdrop-blur-sm">
            <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-destructive">Failed to load forecast</p>
              <p className="text-xs text-destructive/70 mt-1.5">Check the ticker symbol and try again</p>
            </div>
          </div>
        )}

        {/* Consensus Summary Card */}
        <GlassCard className="animate-in-up" style={{ animationDelay: '100ms' }}>
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-24 rounded-lg bg-surface-secondary/50 shimmer" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Consensus Signal */}
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground font-semibold uppercase">Model Consensus</p>
                <div className="flex items-end gap-2">
                  <p className="text-3xl font-bold bg-gradient-to-r from-success to-cyan-500 bg-clip-text text-transparent">
                    {consensus?.signal || '—'}
                  </p>
                  <p className="text-sm text-muted-foreground mb-1">{Math.round(consensus?.confidence ?? 0)}%</p>
                </div>
                <p className="text-xs text-muted-foreground">
                  {(consensus?.agreement_rate ?? 0) > 66 ? 'High' : 'Moderate'} agreement across models
                </p>
              </div>

              {/* Average Confidence */}
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground font-semibold uppercase">Avg Confidence</p>
                <div className="flex items-end gap-2">
                  <p className="text-3xl font-bold text-primary">{averageConfidence.toFixed(1)}%</p>
                </div>
                <div className="h-1 w-full bg-surface-secondary rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-primary to-cyan-500"
                    style={{ width: `${averageConfidence}%` }}
                  />
                </div>
              </div>

              {/* Average Expected Return */}
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground font-semibold uppercase">Expected Return</p>
                <div className="flex items-end gap-2">
                  <p className={`text-3xl font-bold ${averageReturn > 0 ? 'text-success' : 'text-destructive'}`}>
                    {averageReturn > 0 ? '+' : ''}{averageReturn.toFixed(2)}%
                  </p>
                </div>
                <TrendingUp className="w-4 h-4 text-success" />
              </div>

              {/* Best Model */}
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground font-semibold uppercase">Best Model (Accuracy)</p>
                <p className="text-lg font-bold text-foreground">
                  {models.length > 0 ? models[0].modelName : '—'}
                </p>
                <p className="text-xs text-muted-foreground">{(models[0]?.accuracy ?? 0).toFixed(1)}% backtest accuracy</p>
              </div>
            </div>
          )}
        </GlassCard>

        {/* Model Forecast Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {isLoading ? (
            <>
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-48 rounded-lg bg-surface-secondary/50 shimmer" />
              ))}
            </>
          ) : (
            models.map((model, idx) => (
              <div key={model.modelName} className="animate-in-up" style={{ animationDelay: `${150 + idx * 50}ms` }}>
                <ForecastCard {...model} />
              </div>
            ))
          )}
        </div>

        {/* Model Comparison Details */}
        <GlassCard className="animate-in-up" style={{ animationDelay: '550ms' }}>
          <div className="space-y-6">
            <div className="flex items-center gap-2">
              <GitCompare className="w-5 h-5 text-primary" />
              <h3 className="text-lg font-semibold text-foreground">Model Comparison Analysis</h3>
            </div>

            {/* Extended Metrics Table */}
            <div className="overflow-x-auto">
              {isLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="h-12 rounded bg-surface-secondary/50 shimmer" />
                  ))}
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border/30">
                      <th className="text-left py-3 px-4 text-xs text-muted-foreground font-semibold uppercase">Model</th>
                      <th className="text-center py-3 px-4 text-xs text-muted-foreground font-semibold uppercase">Signal</th>
                      <th className="text-center py-3 px-4 text-xs text-muted-foreground font-semibold uppercase">Return</th>
                      <th className="text-center py-3 px-4 text-xs text-muted-foreground font-semibold uppercase">Confidence</th>
                      <th className="text-center py-3 px-4 text-xs text-muted-foreground font-semibold uppercase">Accuracy</th>
                      <th className="text-center py-3 px-4 text-xs text-muted-foreground font-semibold uppercase">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {models.map((model) => {
                      const signalColor =
                        model.signal === 'BUY'
                          ? 'text-success'
                          : model.signal === 'SELL'
                            ? 'text-destructive'
                            : 'text-warning';
                      return (
                        <tr key={model.modelName} className="border-b border-border/20 hover:bg-surface-secondary/20 transition-colors">
                          <td className="py-3 px-4">
                            <div>
                              <p className="font-semibold text-foreground">{model.modelName}</p>
                              <p className="text-xs text-muted-foreground line-clamp-2">{model.description}</p>
                            </div>
                          </td>
                          <td className="py-3 px-4 text-center">
                            <span className={`inline-flex items-center justify-center px-2 py-1 rounded text-xs font-bold ${signalColor}`}>
                              {model.signal}
                            </span>
                          </td>
                          <td className={`py-3 px-4 text-center font-semibold ${model.expectedReturn > 0 ? 'text-success' : 'text-destructive'}`}>
                            {model.expectedReturn > 0 ? '+' : ''}{model.expectedReturn.toFixed(2)}%
                          </td>
                          <td className="py-3 px-4 text-center">
                            <div className="flex items-center justify-center gap-2">
                              <div className="w-20 h-1.5 bg-surface-secondary rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-gradient-to-r from-primary to-cyan-500"
                                  style={{ width: `${model.confidence}%` }}
                                />
                              </div>
                              <span className="font-semibold text-foreground w-10 text-right">{model.confidence.toFixed(0)}%</span>
                            </div>
                          </td>
                          <td className="py-3 px-4 text-center">
                            <span className="font-semibold text-foreground">{model.accuracy.toFixed(1)}%</span>
                          </td>
                          <td className="py-3 px-4 text-center">
                            <span
                              className={`px-2 py-1 rounded text-xs font-bold ${
                                model.status === 'ready'
                                  ? 'bg-success/10 text-success'
                                  : model.status === 'training'
                                    ? 'bg-primary/10 text-primary'
                                    : 'bg-warning/10 text-warning'
                              }`}
                            >
                              {model.status.charAt(0).toUpperCase() + model.status.slice(1)}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </GlassCard>

        {/* Model Descriptions */}
        <GlassCard className="animate-in-up" style={{ animationDelay: '600ms' }}>
          <div className="space-y-4">
            <h4 className="text-lg font-semibold text-foreground">Model Architecture Guide</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                { name: 'Baseline', key: 'baseline' },
                { name: 'LSTM/GRU', key: 'lstm' as const },
                { name: 'Temporal Fusion', key: 'tft' as const },
                { name: 'Ensemble', key: 'ensemble' as const },
              ].map((model) => (
                <div key={model.name} className="p-4 rounded-lg bg-surface-secondary/20 border border-border/30">
                  <h5 className="font-semibold text-foreground mb-2">{model.name}</h5>
                  <p className="text-sm text-muted-foreground">{MODEL_DESCRIPTIONS[model.key as keyof typeof MODEL_DESCRIPTIONS]}</p>
                </div>
              ))}
            </div>
          </div>
        </GlassCard>

        {/* Footer Note */}
        <div className="text-center text-xs text-muted-foreground px-4 py-3 rounded-lg bg-surface-secondary/20 border border-border/30">
          <p>Models are retrained daily with latest market data. Forecasts are updated every 4 hours during market hours.</p>
        </div>
      </div>
    </DashboardLayoutWrapper>
  );
}
