'use client';

import { CheckCircle, AlertCircle } from 'lucide-react';
import type { BacktestResult } from '@/lib/types';

interface BacktestResultCardProps {
  result: BacktestResult;
}

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

function metricColor(value: number, positiveIsGood: boolean): string {
  if (positiveIsGood) return value >= 0 ? 'text-success' : 'text-destructive';
  return value <= 0 ? 'text-success' : 'text-destructive';
}

function PrimaryMetric({
  label,
  value,
  color = 'text-foreground',
  unit = '',
}: {
  label: string;
  value: string;
  color?: string;
  unit?: string;
}) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] font-semibold text-muted-foreground/50 uppercase tracking-widest mb-1">
        {label}
      </span>
      <div className="flex items-baseline gap-1">
        <span className={`text-2xl font-bold tracking-tight ${color}`}>{value}</span>
        {unit && <span className="text-xs text-muted-foreground/40">{unit}</span>}
      </div>
    </div>
  );
}

function SecondaryMetricRow({
  label,
  value,
  color = 'text-foreground',
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs font-medium text-muted-foreground/60">{label}</span>
      <span className={`text-sm font-semibold tracking-tight ${color}`}>{value}</span>
    </div>
  );
}

// ------------------------------------------------------------------
// Component
// ------------------------------------------------------------------

export function BacktestResultCard({ result }: BacktestResultCardProps) {
  const isPositive = result.total_return >= 0;

  const statusBadge = {
    completed: {
      label: 'Live',
      classes: 'bg-success/10 border-success/25 text-success',
      icon: CheckCircle,
    },
    estimated: {
      label: 'Estimated',
      classes: 'bg-amber-500/10 border-amber-500/25 text-amber-400',
      icon: AlertCircle,
    },
  }[result.status] ?? {
    label: result.status,
    classes: 'bg-surface-secondary/20 border-border/20 text-muted-foreground/60',
    icon: AlertCircle,
  };

  const StatusIcon = statusBadge.icon;

  return (
    <div className="group rounded-lg border border-border/25 bg-gradient-to-br from-surface-secondary/15 to-surface-secondary/5 p-6 transition-all duration-300 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5">
      {/* ── Header: Ticker + Status Badge ── */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 gap-y-1 flex-wrap mb-2">
            <h3 className="text-lg font-bold tracking-tight text-foreground">{result.ticker}</h3>
            <span
              className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider ${statusBadge.classes}`}
            >
              <StatusIcon className="w-2.5 h-2.5" />
              {statusBadge.label}
            </span>
          </div>
          <p className="text-xs text-muted-foreground/60 font-medium mb-1">{result.strategy}</p>
          <p className="text-[11px] text-muted-foreground/40 font-mono">
            {result.start_date} – {result.end_date}
          </p>
        </div>

        {/* ── Total Return (Primary KPI) ── */}
        <div className="flex-shrink-0 text-right">
          <PrimaryMetric
            label="Total Return"
            value={`${isPositive ? '+' : ''}${result.total_return.toFixed(1)}`}
            unit="%"
            color={isPositive ? 'text-success' : 'text-destructive'}
          />
        </div>
      </div>

      {/* ── Risk-Adjusted Returns Section ── */}
      <div className="mb-6 rounded-lg bg-surface-secondary/25 border border-border/15 px-4 py-4">
        <div className="text-[10px] font-semibold text-muted-foreground/50 uppercase tracking-widest mb-3">
          Risk & Return Metrics
        </div>
        <div className="grid grid-cols-2 gap-4 mb-4 pb-4 border-b border-border/10">
          <PrimaryMetric
            label="Sharpe Ratio"
            value={result.sharpe_ratio.toFixed(2)}
            color={result.sharpe_ratio >= 1 ? 'text-success' : result.sharpe_ratio >= 0.5 ? 'text-amber-400' : 'text-destructive'}
          />
          <PrimaryMetric
            label="Max Drawdown"
            value={`${result.max_drawdown.toFixed(1)}`}
            unit="%"
            color="text-destructive"
          />
        </div>

        <div className="space-y-2.5">
          <SecondaryMetricRow
            label="Sortino Ratio"
            value={result.sortino_ratio != null ? result.sortino_ratio.toFixed(2) : '—'}
            color={
              result.sortino_ratio != null && result.sortino_ratio >= 1
                ? 'text-success'
                : 'text-muted-foreground/60'
            }
          />
          <SecondaryMetricRow
            label="Volatility (annualized)"
            value={result.volatility != null ? `${result.volatility.toFixed(1)}%` : '—'}
            color={
              result.volatility != null
                ? result.volatility <= 20 ? 'text-success' : result.volatility <= 30 ? 'text-amber-400' : 'text-destructive'
                : 'text-muted-foreground/60'
            }
          />
          <SecondaryMetricRow
            label="Annual Return"
            value={
              result.annual_return != null
                ? `${result.annual_return >= 0 ? '+' : ''}${result.annual_return.toFixed(1)}%`
                : '—'
            }
            color={
              result.annual_return != null
                ? metricColor(result.annual_return, true)
                : 'text-muted-foreground/60'
            }
          />
        </div>
      </div>

      {/* ── Trade Execution Section ── */}
      <div className="mb-6 rounded-lg bg-surface-secondary/15 border border-border/10 px-4 py-4">
        <div className="text-[10px] font-semibold text-muted-foreground/50 uppercase tracking-widest mb-3">
          Trade Execution
        </div>
        <div className="grid grid-cols-2 gap-3">
          <SecondaryMetricRow
            label="Total Trades"
            value={String(result.trades_count)}
            color="text-foreground"
          />
          <SecondaryMetricRow
            label="Win Rate"
            value={`${result.win_rate.toFixed(1)}%`}
            color={result.win_rate >= 55 ? 'text-success' : result.win_rate >= 50 ? 'text-amber-400' : 'text-destructive'}
          />
          <SecondaryMetricRow
            label="Direction Accuracy"
            value={result.direction_accuracy != null ? `${result.direction_accuracy.toFixed(1)}%` : '—'}
            color={
              result.direction_accuracy != null
                ? result.direction_accuracy >= 55 ? 'text-success' : result.direction_accuracy >= 52 ? 'text-amber-400' : 'text-destructive'
                : 'text-muted-foreground/60'
            }
          />
        </div>
      </div>

      {/* ── Strategy Notes ── */}
      {result.strategy_description && (
        <div className="pt-4 border-t border-border/10">
          <p className="text-xs leading-relaxed text-muted-foreground/70">
            {result.strategy_description}
          </p>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------
// Loading skeleton — matches the card layout proportions
// ------------------------------------------------------------------
export function BacktestResultCardSkeleton() {
  return (
    <div className="rounded-lg border border-border/20 bg-gradient-to-br from-surface-secondary/15 to-surface-secondary/5 p-6 space-y-4">
      <div className="flex items-start justify-between">
        <div className="flex-1 space-y-2">
          <div className="h-5 w-20 rounded bg-surface-secondary/50 animate-pulse" />
          <div className="h-3 w-32 rounded bg-surface-secondary/40 animate-pulse" />
          <div className="h-3 w-28 rounded bg-surface-secondary/30 animate-pulse mt-1" />
        </div>
        <div className="space-y-1 text-right">
          <div className="h-7 w-24 rounded bg-surface-secondary/50 animate-pulse" />
          <div className="h-3 w-16 rounded bg-surface-secondary/40 animate-pulse" />
        </div>
      </div>

      <div className="rounded-lg bg-surface-secondary/25 border border-border/15 p-4 space-y-3">
        <div className="h-3 w-32 rounded bg-surface-secondary/40 animate-pulse" />
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <div className="h-3 w-20 rounded bg-surface-secondary/30 animate-pulse" />
            <div className="h-6 w-16 rounded bg-surface-secondary/40 animate-pulse" />
          </div>
          <div className="space-y-1">
            <div className="h-3 w-20 rounded bg-surface-secondary/30 animate-pulse" />
            <div className="h-6 w-16 rounded bg-surface-secondary/40 animate-pulse" />
          </div>
        </div>
        <div className="border-t border-border/10 pt-3 space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex justify-between">
              <div className="h-3 w-24 rounded bg-surface-secondary/30 animate-pulse" />
              <div className="h-3 w-12 rounded bg-surface-secondary/30 animate-pulse" />
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-lg bg-surface-secondary/15 border border-border/10 p-4">
        <div className="h-3 w-32 rounded bg-surface-secondary/30 animate-pulse mb-3" />
        <div className="grid grid-cols-2 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex justify-between">
              <div className="h-3 w-20 rounded bg-surface-secondary/30 animate-pulse" />
              <div className="h-3 w-12 rounded bg-surface-secondary/30 animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
