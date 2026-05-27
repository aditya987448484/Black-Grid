'use client';

import { useCallback } from 'react';
import { Play, AlertCircle, BarChart2 } from 'lucide-react';
import { GlassCard } from '@/components/common/Card';
import { ChartContainer } from '@/components/charts/ChartContainer';
import { DashboardLayoutWrapper } from '@/components/common/DashboardLayout';
import { BacktestResultCard, BacktestResultCardSkeleton } from '@/components/backtest/BacktestResultCard';
import { useApi } from '@/lib/hooks/useApi';
import { backtest } from '@/lib/api/client';
import type { BacktestSummaryResponse, BacktestResult } from '@/lib/types';

// ---------------------------------------------------------------------------
// Performance bar chart — renders total return per ticker as inline SVG
// ---------------------------------------------------------------------------
function PerformanceBarChart({ results }: { results: BacktestResult[] }) {
  if (!results.length) return null;

  const BAR_H = 32;
  const GAP = 12;
  const LABEL_W = 56;
  const CHART_W = 480;
  const SVG_H = results.length * (BAR_H + GAP) + 24;
  const maxAbs = Math.max(...results.map((r) => Math.abs(r.total_return)), 1);

  return (
    <div className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${LABEL_W + CHART_W + 80} ${SVG_H}`}
        className="w-full max-w-2xl"
        aria-label="Total return per ticker"
      >
        {results.map((r, i) => {
          const y = i * (BAR_H + GAP) + 12;
          const isPos = r.total_return >= 0;
          const barW = Math.max((Math.abs(r.total_return) / maxAbs) * CHART_W, 4);
          const fill = isPos ? 'rgba(34,197,94,0.65)' : 'rgba(239,68,68,0.65)';
          const stroke = isPos ? 'rgb(34,197,94)' : 'rgb(239,68,68)';
          const textColor = isPos ? 'rgb(34,197,94)' : 'rgb(239,68,68)';

          return (
            <g key={r.backtest_id}>
              {/* Estimated dot */}
              {r.status === 'estimated' && (
                <circle cx={LABEL_W - 10} cy={y + BAR_H / 2} r={3} fill="rgb(251,191,36)" />
              )}
              {/* Ticker */}
              <text
                x={LABEL_W - 14}
                y={y + BAR_H / 2 + 5}
                textAnchor="end"
                fontSize={12}
                fontWeight={700}
                className="fill-foreground"
              >
                {r.ticker}
              </text>
              {/* Bar */}
              <rect x={LABEL_W} y={y} width={barW} height={BAR_H} rx={5} fill={fill} stroke={stroke} strokeWidth={1} />
              {/* Value */}
              <text x={LABEL_W + barW + 8} y={y + BAR_H / 2 + 5} fontSize={12} fontWeight={700} fill={textColor}>
                {isPos ? '+' : ''}{r.total_return.toFixed(1)}%
              </text>
            </g>
          );
        })}
      </svg>

      <div className="flex items-center gap-4 mt-3 ml-14">
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground/60">
          <span className="inline-block w-3 h-3 rounded-sm bg-success/65" />
          Positive return
        </span>
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground/60">
          <span className="inline-block w-3 h-3 rounded-sm bg-destructive/65" />
          Negative return
        </span>
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground/60">
          <span className="inline-block w-2 h-2 rounded-full bg-amber-400" />
          Estimated
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function BacktestLabPage() {
  const summaryRequest = useCallback(() => backtest.getSummary(10), []);
  const { data: response, status } = useApi<BacktestSummaryResponse>(summaryRequest, true);

  const isLoading = status === 'pending';
  const hasError = status === 'error';
  const results: BacktestResult[] = response?.data ?? [];

  return (
    <DashboardLayoutWrapper>
      <div className="min-h-screen section-padding py-6">
        {/* Header */}
        <div className="animate-in mb-10">
          <h1 className="text-5xl font-bold tracking-tight text-foreground leading-tight">
            Backtest Lab
          </h1>
          <p className="text-sm text-muted-foreground/70 mt-2 font-medium">
            Analyze and compare trading strategies with quantitative metrics
          </p>
        </div>

        {/* Error state */}
        {hasError && (
          <div className="flex items-start gap-4 px-4 py-4 rounded-lg bg-destructive/10 border border-destructive/20 mb-8 backdrop-blur-sm">
            <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-destructive">Failed to load backtest results</p>
              <p className="text-xs text-destructive/70 mt-1.5">
                Try refreshing the page or running a new backtest
              </p>
            </div>
          </div>
        )}

        {/* Run New Backtest (Minimal) */}
        <div className="mb-10 animate-in-up" style={{ animationDelay: '50ms' }}>
          <GlassCard>
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-foreground tracking-tight mb-1">New Backtest</h3>
                <p className="text-xs text-muted-foreground/60">Configure strategy parameters</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-muted-foreground/70 uppercase tracking-wider">Strategy</label>
                  <select className="w-full px-3 py-2 rounded-lg bg-input border border-border/40 text-foreground text-sm transition-smooth focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20">
                    <option>MA Crossover</option>
                    <option>RSI Reversion</option>
                    <option>MACD Divergence</option>
                    <option>BB Breakout</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-muted-foreground/70 uppercase tracking-wider">Ticker</label>
                  <input
                    type="text"
                    placeholder="AAPL"
                    className="w-full px-3 py-2 rounded-lg bg-input border border-border/40 text-foreground text-sm placeholder-muted-foreground/40 transition-smooth focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-muted-foreground/70 uppercase tracking-wider">Start</label>
                  <input
                    type="date"
                    className="w-full px-3 py-2 rounded-lg bg-input border border-border/40 text-foreground text-sm transition-smooth focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-muted-foreground/70 uppercase tracking-wider">End</label>
                  <input
                    type="date"
                    className="w-full px-3 py-2 rounded-lg bg-input border border-border/40 text-foreground text-sm transition-smooth focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20"
                  />
                </div>
                <div className="flex items-end pt-1">
                  <button className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-primary to-cyan-500 text-primary-foreground font-semibold text-sm hover:shadow-premium-lg active:opacity-95 transition-smooth duration-200">
                    <Play className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Run</span>
                  </button>
                </div>
              </div>
            </div>
          </GlassCard>
        </div>

        {/* Performance Summary Chart */}
        <ChartContainer
          title="Strategy Performance Summary"
          subtitle="Total return across recent backtests"
          className="mb-10 animate-in-up"
          style={{ animationDelay: '100ms' }}
          tools={
            <div className="flex items-center gap-1 text-xs text-muted-foreground/50">
              <BarChart2 className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Total Return</span>
            </div>
          }
        >
          {isLoading ? (
            <div className="h-48 flex items-center justify-center">
              <div className="space-y-3 w-full max-w-lg">
                {[80, 60, 45].map((w, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className="h-3 w-12 rounded bg-surface-secondary/40 animate-pulse" />
                    <div className="h-8 rounded-md bg-surface-secondary/30 animate-pulse" style={{ width: `${w}%` }} />
                  </div>
                ))}
              </div>
            </div>
          ) : results.length > 0 ? (
            <PerformanceBarChart results={results} />
          ) : (
            <div className="h-48 flex items-center justify-center text-center">
              <p className="text-sm text-muted-foreground/50">Run a backtest to see performance metrics</p>
            </div>
          )}
        </ChartContainer>

        {/* Backtest Results Grid */}
        <div className="animate-in-up" style={{ animationDelay: '150ms' }}>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-foreground tracking-tight">Backtest Results</h2>
              <p className="text-[11px] text-muted-foreground/50 mt-0.5">Detailed performance analysis</p>
            </div>
            {response && response.total_results > 0 && (
              <p className="text-xs text-muted-foreground/40 font-mono">
                {response.total_results} result{response.total_results !== 1 ? 's' : ''}
              </p>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {isLoading ? (
              [1, 2, 3].map((i) => <BacktestResultCardSkeleton key={i} />)
            ) : results.length > 0 ? (
              results.map((result) => (
                <BacktestResultCard key={result.backtest_id} result={result} />
              ))
            ) : (
              <div className="col-span-3 text-center py-20">
                <p className="text-muted-foreground/60 text-sm">No backtest results yet</p>
                <p className="text-muted-foreground/40 text-xs mt-1">Configure and run your first backtest above</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayoutWrapper>
  );
}
