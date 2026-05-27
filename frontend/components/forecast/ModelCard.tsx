'use client';

import { TrendingUp, TrendingDown, Minus, Zap, Clock } from 'lucide-react';
import type { ModelForecastOutput } from '@/lib/types';

interface ModelCardProps {
  model: ModelForecastOutput;
  /** True only during initial data fetch — shows animated skeleton */
  isPlaceholder?: boolean;
}

const SIGNAL_CONFIG = {
  BUY: {
    color: 'text-success',
    mutedColor: 'text-success/40',
    bg: 'bg-success/10',
    border: 'border-success/25',
    icon: TrendingUp,
    label: 'BUY',
  },
  HOLD: {
    color: 'text-amber-400',
    mutedColor: 'text-amber-400/40',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/25',
    icon: Minus,
    label: 'HOLD',
  },
  SELL: {
    color: 'text-destructive',
    mutedColor: 'text-destructive/40',
    bg: 'bg-destructive/10',
    border: 'border-destructive/25',
    icon: TrendingDown,
    label: 'SELL',
  },
} as const;

const CONFIDENCE_COLOR = (c: number) =>
  c >= 70 ? 'bg-success' : c >= 50 ? 'bg-amber-500' : 'bg-destructive/70';

export function ModelCard({ model, isPlaceholder = false }: ModelCardProps) {
  // Skeleton loading state — show animated pulse, no data
  if (isPlaceholder) {
    return (
      <div className="rounded-lg border border-border/20 bg-surface-secondary/20 p-6">
        <div className="mb-6 space-y-2">
          <div className="h-3 w-20 rounded bg-surface-secondary/50 animate-pulse" />
          <div className="h-7 w-14 rounded bg-surface-secondary/50 animate-pulse" />
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-11 rounded-lg bg-surface-secondary/30 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const isLive = model.status === 'ready';
  const signal = SIGNAL_CONFIG[model.signal] ?? SIGNAL_CONFIG.HOLD;
  const SignalIcon = signal.icon;

  return (
    <div
      className={`relative rounded-lg border p-6 transition-all duration-300 ${
        isLive
          ? `${signal.bg} ${signal.border} hover:brightness-110`
          : 'bg-surface-secondary/10 border-border/20 opacity-70 hover:opacity-90'
      }`}
    >
      {/* Top badge row */}
      <div className="mb-4 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/60 truncate">
            {model.model_type === 'baseline'
              ? 'Momentum · Baseline'
              : model.model_type === 'lstm'
              ? 'Deep Learning · RNN'
              : model.model_type === 'tft'
              ? 'Transformer · Attention'
              : 'Weighted · Ensemble'}
          </p>
          <h3 className="mt-0.5 text-base font-bold text-foreground tracking-tight leading-snug">
            {model.model_name}
          </h3>
        </div>

        {/* Live / Coming Soon badge */}
        {isLive ? (
          <span className="flex-shrink-0 flex items-center gap-1 rounded-full bg-success/15 border border-success/30 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-success">
            <Zap className="w-2.5 h-2.5" />
            Live
          </span>
        ) : (
          <span className="flex-shrink-0 flex items-center gap-1 rounded-full bg-surface-secondary/40 border border-border/30 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/50">
            <Clock className="w-2.5 h-2.5" />
            Soon
          </span>
        )}
      </div>

      {/* Signal pill — always visible */}
      <div
        className={`mb-4 flex items-center gap-2 rounded-md px-3 py-2 ${
          isLive ? signal.bg : 'bg-surface-secondary/20'
        } border ${isLive ? signal.border : 'border-border/15'}`}
      >
        <SignalIcon
          className={`h-4 w-4 flex-shrink-0 ${isLive ? signal.color : signal.mutedColor}`}
        />
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/60">
          Signal
        </span>
        <span
          className={`ml-auto text-lg font-extrabold tracking-tight ${
            isLive ? signal.color : signal.mutedColor
          }`}
        >
          {signal.label}
        </span>
      </div>

      {/* Metrics — live models get full data; simulated get locked placeholders */}
      {isLive ? (
        <div className="space-y-3">
          {/* Expected Return */}
          <div className="flex items-center justify-between rounded-lg bg-surface-secondary/30 border border-border/10 px-4 py-3">
            <span className="text-xs text-muted-foreground/70 font-medium">Expected Return</span>
            <span
              className={`text-base font-bold tracking-tight ${
                model.expected_return >= 0 ? 'text-success' : 'text-destructive'
              }`}
            >
              {model.expected_return >= 0 ? '+' : ''}
              {model.expected_return.toFixed(2)}%
            </span>
          </div>

          {/* Confidence bar */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground/70 font-medium">Confidence</span>
              <span className="text-xs font-bold text-foreground">
                {model.confidence.toFixed(0)}%
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-secondary/50">
              <div
                className={`h-full transition-all duration-500 ${CONFIDENCE_COLOR(model.confidence)}`}
                style={{ width: `${Math.min(model.confidence, 100)}%` }}
              />
            </div>
          </div>

          {/* Backtest accuracy */}
          {model.accuracy != null && model.accuracy > 0 && (
            <div className="flex items-center justify-between rounded-lg bg-surface-secondary/30 border border-border/10 px-4 py-3">
              <span className="text-xs text-muted-foreground/70 font-medium">Backtest Accuracy</span>
              <span className="text-base font-bold text-foreground tracking-tight">
                {model.accuracy.toFixed(1)}%
              </span>
            </div>
          )}
        </div>
      ) : (
        /* Simulated model — locked metrics + description note */
        <div className="space-y-3">
          {['Expected Return', 'Confidence', 'Backtest Accuracy'].map((label) => (
            <div
              key={label}
              className="flex items-center justify-between rounded-lg bg-surface-secondary/20 border border-border/10 px-4 py-3"
            >
              <span className="text-xs text-muted-foreground/40 font-medium">{label}</span>
              <span className="text-xs font-semibold text-muted-foreground/30 tracking-widest">
                — —
              </span>
            </div>
          ))}

          {/* Simulation note */}
          <p className="pt-1 text-[11px] leading-relaxed text-muted-foreground/45 italic">
            {model.description || 'Model in development — predictions not yet available.'}
          </p>
        </div>
      )}
    </div>
  );
}
