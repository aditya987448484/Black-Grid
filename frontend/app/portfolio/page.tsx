'use client';

import { useCallback } from 'react';
import { Plus, Trash2, AlertCircle, TrendingUp, TrendingDown, AlertTriangle, CheckCircle } from 'lucide-react';
import { GlassCard, DataCard } from '@/components/common/Card';
import { DashboardLayoutWrapper } from '@/components/common/DashboardLayout';
import { useApi } from '@/lib/hooks/useApi';
import { portfolio } from '@/lib/api/client';
import type { WatchlistIntelligenceResponse, WatchlistIntelligenceItem } from '@/lib/types';

// Mini score bar component
const ScoreBar = ({ value, max }: { value: number; max: number }) => {
  const percentage = (value / max) * 100;
  const getColor = () => {
    if (max === 1) return percentage > 30 ? 'bg-success' : 'bg-destructive';
    return percentage < 30 ? 'bg-success' : percentage < 60 ? 'bg-warning' : 'bg-destructive';
  };
  return (
    <div className="flex items-center gap-2 w-32">
      <div className="flex-1 h-1.5 rounded-full bg-surface-secondary/50 overflow-hidden">
        <div className={`h-full ${getColor()}`} style={{ width: `${Math.min(percentage, 100)}%` }} />
      </div>
      <span className="text-xs font-semibold text-muted-foreground/80 w-10 text-right">
        {value.toFixed(0)}
      </span>
    </div>
  );
};

export default function PortfolioPage() {
  const watchlistRequest = useCallback(
    () => portfolio.getWatchlistIntelligence(undefined, 252),
    []
  );
  const { data: watchlistResponse, status } = useApi<WatchlistIntelligenceResponse>(
    watchlistRequest,
    true
  );

  const isLoading = status === 'pending';
  const hasError = status === 'error';

  const watchlistItems = watchlistResponse?.data || [];

  // Calculate summary stats
  const totalAllocation = watchlistItems.reduce((sum, item) => sum + (item.allocation_weight || 0), 0);
  const avgConfidence = watchlistItems.length > 0
    ? watchlistItems.reduce((sum, item) => sum + (item.confidence_score || 0), 0) / watchlistItems.length
    : 0;
  const avgRiskScore = watchlistItems.length > 0
    ? watchlistItems.reduce((sum, item) => sum + (item.risk_score || 0), 0) / watchlistItems.length
    : 0;

  return (
    <DashboardLayoutWrapper>
      <div className="min-h-screen section-padding py-6">
        {/* Header */}
        <div className="animate-in mb-10">
          <h1 className="text-5xl font-bold tracking-tight text-foreground leading-tight">Portfolio</h1>
          <p className="text-sm text-muted-foreground/60 mt-3 uppercase tracking-widest font-semibold">Real-time intelligence and risk metrics</p>
        </div>

        {/* Error State */}
        {hasError && (
          <div className="flex items-start gap-4 px-4 py-4 rounded-lg bg-destructive/10 border border-destructive/20 mb-8 backdrop-blur-sm">
            <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-destructive">Failed to load watchlist intelligence</p>
              <p className="text-xs text-destructive/70 mt-1.5">Please try refreshing the page</p>
            </div>
          </div>
        )}

        {/* Portfolio Summary */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-5 mb-8">
          <DataCard
            label="Total Allocation"
            value={`${totalAllocation.toFixed(1)}%`}
            change={watchlistItems.length}
            changeLabel={`${watchlistItems.length} assets`}
          />
          <DataCard
            label="Avg. Confidence"
            value={`${avgConfidence.toFixed(1)}%`}
            change={watchlistItems.length > 0 ? (avgConfidence > 70 ? 5 : -2) : 0}
            changeLabel="Model agreement"
          />
          <DataCard
            label="Avg. Risk Score"
            value={avgRiskScore.toFixed(1)}
            change={avgRiskScore > 50 ? -3 : 2}
            changeLabel={avgRiskScore > 60 ? 'High' : avgRiskScore > 40 ? 'Moderate' : 'Low'}
          />
          <DataCard
            label="Watchlist Items"
            value={watchlistItems.length.toString()}
            change={watchlistItems.length}
            changeLabel="tracked"
          />
        </div>

        {/* Watchlist Management */}
        <GlassCard className="mb-8">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-2xl font-bold text-foreground tracking-tight">Watchlist Analysis</h2>
              <p className="text-xs text-muted-foreground/60 mt-2 uppercase tracking-widest font-semibold">Portfolio Performance & Risk Metrics</p>
            </div>
            <button className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-primary text-primary-foreground font-semibold hover:shadow-premium-lg active:opacity-95 transition-smooth duration-200 flex-shrink-0">
              <Plus className="w-4 h-4"/>
              Add Asset
            </button>
          </div>

          {/* Error Alert */}
          {hasError && (
            <div className="mb-6 p-4 rounded-lg bg-destructive/10 border border-destructive/20 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-destructive">Failed to load watchlist intelligence</p>
                <p className="text-xs text-destructive/70 mt-1.5">Please try refreshing the page</p>
              </div>
            </div>
          )}

          {/* Loading State */}
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 rounded-lg bg-surface-secondary/50 shimmer" />
              ))}
            </div>
          ) : watchlistItems && watchlistItems.length > 0 ? (
            <div className="overflow-x-auto -mx-6 px-6">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/30 bg-surface-secondary/20">
                    <th className="px-5 py-4 text-left text-xs font-semibold text-muted-foreground/60 uppercase tracking-widest">Asset</th>
                    <th className="px-5 py-4 text-right text-xs font-semibold text-muted-foreground/60 uppercase tracking-widest">Price</th>
                    <th className="px-5 py-4 text-center text-xs font-semibold text-muted-foreground/60 uppercase tracking-widest">24h Δ</th>
                    <th className="px-5 py-4 text-center text-xs font-semibold text-muted-foreground/60 uppercase tracking-widest">Performance</th>
                    <th className="px-5 py-4 text-center text-xs font-semibold text-muted-foreground/60 uppercase tracking-widest">Signal</th>
                    <th className="px-5 py-4 text-center text-xs font-semibold text-muted-foreground/60 uppercase tracking-widest">Confidence</th>
                    <th className="px-5 py-4 text-center text-xs font-semibold text-muted-foreground/60 uppercase tracking-widest">Risk</th>
                    <th className="px-5 py-4 text-center text-xs font-semibold text-muted-foreground/60 uppercase tracking-widest">Allocation</th>
                    <th className="px-5 py-4 text-center text-xs font-semibold text-muted-foreground/60 uppercase tracking-widest">Status</th>
                    <th className="px-5 py-4 text-center text-xs font-semibold text-muted-foreground/60 uppercase tracking-widest">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/15">
                  {watchlistItems.map((item: WatchlistIntelligenceItem, idx) => (
                    <tr key={idx} className="hover:bg-surface-secondary/20 transition-colors duration-150 border-border/10">
                      {/* Asset */}
                      <td className="px-5 py-5">
                        <div className="flex items-center gap-3">
                          <div className="w-11 h-11 rounded-lg bg-gradient-to-br from-primary/80 to-cyan-500/80 flex items-center justify-center flex-shrink-0 shadow-sm">
                            <span className="text-xs font-bold text-primary-foreground">
                              {item.ticker.substring(0, 2).toUpperCase()}
                            </span>
                          </div>
                          <div className="min-w-0">
                            <p className="font-semibold text-foreground text-sm">{item.ticker}</p>
                            <p className="text-xs text-muted-foreground/60 truncate">{item.name}</p>
                          </div>
                        </div>
                      </td>
                      
                      {/* Price */}
                      <td className="px-5 py-5 text-right">
                        <p className="font-semibold text-foreground text-sm">${item.current_price.toFixed(2)}</p>
                      </td>
                      
                      {/* 24h Change */}
                      <td className="px-5 py-5 text-center">
                        <div
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold ${
                            item.change_24h >= 0
                              ? 'bg-success/15 text-success/90'
                              : 'bg-destructive/15 text-destructive/90'
                          }`}
                        >
                          {item.change_24h > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                          {Math.abs(item.change_24h).toFixed(2)}%
                        </div>
                      </td>
                      
                      {/* Period Changes */}
                      <td className="px-5 py-5 text-center">
                        {item.period_changes ? (
                          <div className="space-y-0.5 text-xs text-muted-foreground/80">
                            <div className={item.period_changes.change_1d >= 0 ? 'text-success/80' : 'text-destructive/80'}>
                              1D: {item.period_changes.change_1d > 0 ? '+' : ''}{item.period_changes.change_1d.toFixed(2)}%
                            </div>
                            <div className={item.period_changes.change_5d >= 0 ? 'text-success/80' : 'text-destructive/80'}>
                              5D: {item.period_changes.change_5d > 0 ? '+' : ''}{item.period_changes.change_5d.toFixed(2)}%
                            </div>
                            <div className={item.period_changes.change_1m >= 0 ? 'text-success/80' : 'text-destructive/80'}>
                              1M: {item.period_changes.change_1m > 0 ? '+' : ''}{item.period_changes.change_1m.toFixed(2)}%
                            </div>
                          </div>
                        ) : (
                          <span className="text-muted-foreground/40 text-xs">—</span>
                        )}
                      </td>
                      
                      {/* Signal Score with visual bar */}
                      <td className="px-5 py-5 text-center">
                        {item.signal_score !== undefined ? (
                          <div className="flex flex-col items-center gap-2">
                            <span className={`text-sm font-bold tracking-tight ${
                              item.signal_score > 0.3 ? 'text-success/90' : 
                              item.signal_score < -0.3 ? 'text-destructive/90' : 
                              'text-warning/90'
                            }`}>
                              {item.signal_score > 0 ? '+' : ''}{item.signal_score.toFixed(2)}
                            </span>
                            <div className="w-20 h-1.5 rounded-full bg-surface-secondary/40 overflow-hidden">
                              <div 
                                className={`h-full transition-all ${
                                  item.signal_score > 0 
                                    ? 'bg-success/60' 
                                    : item.signal_score < 0 
                                      ? 'bg-destructive/60' 
                                      : 'bg-warning/60'
                                }`}
                                style={{ width: `${Math.min(Math.abs(item.signal_score) * 50 + 50, 100)}%` }}
                              />
                            </div>
                          </div>
                        ) : (
                          <span className="text-muted-foreground/40 text-xs">—</span>
                        )}
                      </td>
                      
                      {/* Confidence Score with bar */}
                      <td className="px-5 py-5 text-center">
                        {item.confidence_score !== undefined ? (
                          <ScoreBar value={item.confidence_score} max={100} />
                        ) : (
                          <span className="text-muted-foreground/40 text-xs">—</span>
                        )}
                      </td>
                      
                      {/* Risk Score with bar */}
                      <td className="px-5 py-5 text-center">
                        {item.risk_score !== undefined ? (
                          <ScoreBar value={item.risk_score} max={100} />
                        ) : (
                          <span className="text-muted-foreground/40 text-xs">—</span>
                        )}
                      </td>
                      
                      {/* Allocation Weight */}
                      <td className="px-5 py-5 text-center">
                        {item.allocation_weight !== undefined ? (
                          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-primary/12 border border-primary/25">
                            <span className="text-xs font-semibold text-primary/90">
                              {item.allocation_weight.toFixed(1)}%
                            </span>
                          </div>
                        ) : (
                          <span className="text-muted-foreground/40 text-xs">—</span>
                        )}
                      </td>
                      
                      {/* Alert Status */}
                      <td className="px-5 py-5 text-center">
                        <div className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-semibold border transition-colors ${
                          item.alert_level === 'critical' 
                            ? 'bg-destructive/12 text-destructive/90 border-destructive/20' :
                          item.alert_level === 'warning' 
                            ? 'bg-warning/12 text-warning/90 border-warning/20' :
                          item.alert_level === 'info' 
                            ? 'bg-cyan-500/12 text-cyan-400/90 border-cyan-500/20' :
                          'bg-success/12 text-success/90 border-success/20'
                        }`}>
                          {item.alert_level === 'critical' && <AlertTriangle className="w-3.5 h-3.5" />}
                          {item.alert_level === 'warning' && <AlertCircle className="w-3.5 h-3.5" />}
                          {item.alert_level === 'info' && <AlertCircle className="w-3.5 h-3.5" />}
                          {item.alert_level === 'none' && <CheckCircle className="w-3.5 h-3.5" />}
                          <span className="text-xs">{item.alert_level.charAt(0).toUpperCase() + item.alert_level.slice(1)}</span>
                        </div>
                      </td>
                      
                      {/* Action */}
                      <td className="px-5 py-5 text-center">
                        <button className="p-2 hover:bg-destructive/15 rounded-md transition-colors duration-150 text-muted-foreground/70 hover:text-destructive/80">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-16">
              <p className="text-muted-foreground/70 font-medium">No items in watchlist yet</p>
              <button className="mt-4 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:shadow-premium transition-smooth duration-200">
                Add your first asset
              </button>
            </div>
          )}
        </GlassCard>

        {/* Holdings Details */}
        <GlassCard>
          <div className="flex items-center justify-between mb-8">
            <h3 className="text-xl font-bold text-foreground tracking-tight">Top Holdings</h3>
            <span className="text-xs text-muted-foreground/60 uppercase tracking-widest font-semibold">By Allocation</span>
          </div>
          
          <div className="space-y-3">
            {watchlistItems
              .sort((a, b) => (b.allocation_weight || 0) - (a.allocation_weight || 0))
              .slice(0, 5)
              .map((item, idx) => (
                <div key={idx} className="flex items-center justify-between p-5 rounded-lg bg-surface-secondary/20 hover:bg-surface-secondary/35 transition-colors duration-200 border border-border/30 hover:border-border/40 group">
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    <div className="w-11 h-11 rounded-lg bg-gradient-to-br from-primary/80 to-cyan-500/80 flex items-center justify-center flex-shrink-0 shadow-sm">
                      <span className="text-xs font-bold text-primary-foreground">{item.ticker.substring(0, 2).toUpperCase()}</span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-foreground text-sm">{item.ticker}</p>
                      <div className="flex items-center gap-4 mt-1.5 text-xs text-muted-foreground/70">
                        <span className="font-medium text-primary/80">{(item.allocation_weight || 0).toFixed(1)}% allocation</span>
                        <span className="text-border/40">•</span>
                        <span className={`font-semibold ${
                          (item.signal_score || 0) > 0.3 ? 'text-success/80' :
                          (item.signal_score || 0) < -0.3 ? 'text-destructive/80' :
                          'text-warning/80'
                        }`}>
                          {((item.signal_score || 0) > 0 ? '+' : '')}{(item.signal_score || 0).toFixed(2)} signal
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="font-semibold text-foreground text-sm">${item.current_price.toFixed(2)}</p>
                    <p
                      className={`text-xs font-semibold tracking-tight mt-1 ${
                        item.change_24h >= 0 ? 'text-success/80' : 'text-destructive/80'
                      }`}
                    >
                      {item.change_24h > 0 ? '+' : ''}{item.change_24h.toFixed(2)}%
                    </p>
                  </div>
                </div>
              ))}
          </div>
        </GlassCard>
      </div>
    </DashboardLayoutWrapper>
  );
}
