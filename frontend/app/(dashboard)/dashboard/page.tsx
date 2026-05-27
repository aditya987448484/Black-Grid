'use client';

import { useCallback, useEffect } from 'react';
import { TrendingUp, Volume2, Activity, Zap, AlertCircle, Loader } from 'lucide-react';
import { GlassCard, DataCard } from '@/components/common/Card';
import { ChartContainer, ChartPlaceholder } from '@/components/charts/ChartContainer';
import { useApi } from '@/lib/hooks/useApi';
import { market } from '@/lib/api/client';
import type { MarketOverviewResponse } from '@/lib/types';

export default function DashboardPage() {
  const marketRequest = useCallback(() => market.getOverview(), []);
  const { data: marketResponse, status, error } = useApi<MarketOverviewResponse>(marketRequest, true);

  const isLoading = status === 'pending';
  const hasError = status === 'error';

  // Format market data for display
  const marketData = marketResponse?.data || [];

  // Log error details for debugging
  useEffect(() => {
    if (hasError && error) {
      console.error('Dashboard API Error:', {
        endpoint: '/api/market/overview',
        error: error,
      });
    }
  }, [hasError, error]);

  return (
    <div className="min-h-screen section-padding py-6">
      {/* Header */}
      <div className="animate-in mb-8">
        <h1 className="text-5xl font-bold tracking-tight text-foreground leading-tight">Dashboard</h1>
        <p className="text-base text-muted-foreground/70 mt-3 font-medium leading-relaxed">Real-time market analysis and portfolio monitoring</p>
      </div>

      {/* Error State */}
      {hasError && (
        <div className="flex items-start gap-4 px-4 py-4 rounded-lg bg-destructive/10 border border-destructive/20 mb-8 backdrop-blur-sm">
          <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-destructive">Failed to fetch market data from /api/market/overview</p>
            <p className="text-xs text-destructive/70 mt-1.5 leading-relaxed">
              {error ?? 'Unknown error. Check browser console for details.'}
            </p>
          </div>
        </div>
      )}

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 animate-in-up mb-8" style={{ animationDelay: '100ms' }}>
        {isLoading ? (
          <>
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 rounded-lg bg-surface-secondary/50 shimmer" />
            ))}
          </>
        ) : (
          <>
            <DataCard
              label="S&P 500"
              value={marketData[0]?.price.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '—'}
              change={marketData[0]?.change_percent || 0}
              changeLabel="today"
              icon={<Activity className="w-6 h-6" />}
            />
            <DataCard
              label="NASDAQ"
              value={marketData[1]?.price.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '—'}
              change={marketData[1]?.change_percent || 0}
              changeLabel="today"
              icon={<TrendingUp className="w-6 h-6" />}
            />
            <DataCard
              label="Russell 2000"
              value={marketData[2]?.price.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '—'}
              change={marketData[2]?.change_percent || 0}
              changeLabel="today"
              icon={<Volume2 className="w-6 h-6" />}
            />
            <DataCard
              label="Dow Jones"
              value={marketData[3]?.price.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '—'}
              change={marketData[3]?.change_percent || 0}
              changeLabel="today"
              icon={<Zap className="w-6 h-6" />}
            />
          </>
        )}
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-in-up mb-8" style={{ animationDelay: '200ms' }}>
        {/* Main Chart - Takes 2 columns */}
        <ChartContainer
          title="Market Index Movement"
          subtitle="S&P 500, NASDAQ, Russell 2000 - Real-time"
          className="lg:col-span-2 min-h-96"
          tools={
            <div className="flex gap-2 bg-surface-secondary/30 rounded-lg p-1">
              <button className="px-3 py-2 text-xs font-semibold rounded-md bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-smooth duration-200 uppercase tracking-wider">
                1D
              </button>
              <button className="px-3 py-2 text-xs font-semibold rounded-md text-muted-foreground/70 hover:bg-surface-secondary/70 transition-smooth duration-200 uppercase tracking-wider">
                1W
              </button>
              <button className="px-3 py-2 text-xs font-semibold rounded-md text-muted-foreground/70 hover:bg-surface-secondary/70 transition-smooth duration-200 uppercase tracking-wider">
                1M
              </button>
            </div>
          }
        >
          <ChartPlaceholder height="h-80" />
        </ChartContainer>

        {/* Side Chart */}
        <ChartContainer
          title="Asset Allocation"
          subtitle="Portfolio composition"
          className="min-h-96"
        >
          <ChartPlaceholder height="h-80" />
        </ChartContainer>
      </div>

      {/* Bottom Section - Market Data */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-in-up" style={{ animationDelay: '300ms' }}>
        {/* Market Indices List */}
        <GlassCard className="min-h-96">
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-foreground tracking-tight">Market Indices</h3>
              {isLoading && <Loader className="w-4 h-4 animate-spin text-primary" />}
            </div>
            <div className="space-y-2.5">
              {isLoading ? (
                [1, 2, 3].map((i) => <div key={i} className="h-14 rounded-lg bg-surface-secondary/50 shimmer" />)
              ) : marketData.length > 0 ? (
                marketData.map((metric) => (
                  <div
                    key={metric.symbol}
                    className={`flex items-center justify-between px-4 py-3.5 rounded-lg transition-smooth cursor-pointer duration-200 ${
                      metric.change_percent >= 0
                        ? 'bg-success/8 border border-success/20 hover:bg-success/12 hover:border-success/30'
                        : 'bg-destructive/8 border border-destructive/20 hover:bg-destructive/12 hover:border-destructive/30'
                    }`}
                  >
                    <div>
                      <p className="font-semibold text-foreground text-sm tracking-tight">{metric.symbol}</p>
                      <p className="text-xs text-muted-foreground/60 mt-1">{new Date(metric.timestamp).toLocaleTimeString()}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-foreground text-sm">{metric.price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}</p>
                      <p className={`text-xs font-bold tracking-wide ${metric.change_percent >= 0 ? 'text-success' : 'text-destructive'}`}>
                        {metric.change_percent > 0 ? '+' : ''}{metric.change_percent.toFixed(2)}%
                      </p>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground/60 py-12 text-center font-medium">No data available</p>
              )}
            </div>
          </div>
        </GlassCard>

        {/* Status Card */}
        <GlassCard className="min-h-96">
          <div className="space-y-6">
            <h3 className="text-lg font-semibold text-foreground tracking-tight">System Status</h3>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${marketData.length > 0 ? 'bg-success shadow-[0_0_6px_rgba(34,197,94,0.6)]' : 'bg-amber-500 shadow-[0_0_6px_rgba(245,158,11,0.6)]'}`} />
                <span className="text-sm text-foreground font-medium">
                  {marketData.length > 0 ? 'Market data loaded' : 'Awaiting market data'}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${hasError ? 'bg-destructive shadow-[0_0_6px_rgba(239,68,68,0.6)]' : 'bg-success shadow-[0_0_6px_rgba(34,197,94,0.6)]'}`} />
                <span className="text-sm text-foreground font-medium">
                  {hasError ? 'API unavailable' : 'Backend connected'}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-primary/60 flex-shrink-0" />
                <span className="text-sm text-muted-foreground/70 font-medium">Analyst reports via Groq AI</span>
              </div>
              <div className="mt-6 p-4 rounded-lg bg-primary/8 border border-primary/20 backdrop-blur-sm">
                <p className="text-xs text-muted-foreground/70 mb-2.5 font-semibold uppercase tracking-wide">Last Updated</p>
                <p className="text-lg font-semibold text-foreground tracking-tight">
                  {marketData && marketData.length > 0 ? new Date(marketData[0].timestamp).toLocaleTimeString() : '—'}
                </p>
              </div>
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
