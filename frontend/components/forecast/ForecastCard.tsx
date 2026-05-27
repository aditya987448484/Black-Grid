'use client';

import { TrendingUp, TrendingDown, AlertCircle, CheckCircle, Clock } from 'lucide-react';

interface ForecastCardProps {
  modelName: string;
  modelType: 'baseline' | 'lstm' | 'gru' | 'tft' | 'ensemble';
  signal: 'BUY' | 'SELL' | 'HOLD';
  expectedReturn: number;
  confidence: number;
  status: 'ready' | 'training' | 'stale' | 'error';
  accuracy?: number;
  lastUpdate?: Date;
  description?: string;
}

const SIGNAL_CONFIG = {
  BUY: { color: 'text-success', bgColor: 'bg-success/10', borderColor: 'border-success/30', icon: TrendingUp },
  SELL: { color: 'text-destructive', bgColor: 'bg-destructive/10', borderColor: 'border-destructive/30', icon: TrendingDown },
  HOLD: { color: 'text-warning', bgColor: 'bg-warning/10', borderColor: 'border-warning/30', icon: AlertCircle },
};

const STATUS_CONFIG = {
  ready: { label: 'Ready', color: 'text-success', bgColor: 'bg-success/10', icon: CheckCircle },
  training: { label: 'Training', color: 'text-primary', bgColor: 'bg-primary/10', icon: Clock },
  stale: { label: 'Stale', color: 'text-warning', bgColor: 'bg-warning/10', icon: AlertCircle },
  error: { label: 'Error', color: 'text-destructive', bgColor: 'bg-destructive/10', icon: AlertCircle },
};

export function ForecastCard({
  modelName,
  modelType,
  signal,
  expectedReturn,
  confidence,
  status,
  accuracy,
  lastUpdate,
  description,
}: ForecastCardProps) {
  const signalConfig = SIGNAL_CONFIG[signal];
  const statusConfig = STATUS_CONFIG[status];
  const SignalIcon = signalConfig.icon;
  const StatusIcon = statusConfig.icon;

  const returnColor = expectedReturn > 0 ? 'text-success' : expectedReturn < 0 ? 'text-destructive' : 'text-muted-foreground';
  const returnBgColor = expectedReturn > 0 ? 'bg-success/5' : expectedReturn < 0 ? 'bg-destructive/5' : 'bg-surface-secondary/30';

  // Confidence gradient visualization
  const getConfidenceColor = (conf: number) => {
    if (conf >= 80) return 'from-success/50 to-success/20';
    if (conf >= 60) return 'from-primary/50 to-primary/20';
    if (conf >= 40) return 'from-warning/50 to-warning/20';
    return 'from-destructive/50 to-destructive/20';
  };

  return (
    <div className="group relative h-full rounded-lg border border-border/50 bg-gradient-to-br from-surface-secondary/30 to-surface-secondary/10 p-6 backdrop-blur-sm transition-all duration-300 hover:border-primary/50 hover:shadow-lg hover:shadow-primary/20">
      {/* Model Header */}
      <div className="mb-5 space-y-2">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-lg font-bold text-foreground">{modelName}</h3>
            <p className="text-xs text-muted-foreground uppercase tracking-wide">{modelType === 'gru' ? 'GRU' : modelType === 'lstm' ? 'LSTM' : modelType === 'tft' ? 'TFT' : modelType.charAt(0).toUpperCase() + modelType.slice(1)}</p>
          </div>
          <div className={`flex h-8 w-8 items-center justify-center rounded-full ${statusConfig.bgColor}`}>
            <StatusIcon className={`h-4 w-4 ${statusConfig.color}`} />
          </div>
        </div>
        {description && (
          <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
        )}
      </div>

      {/* Signal Section */}
      <div className={`mb-5 rounded-lg ${signalConfig.bgColor} border ${signalConfig.borderColor} p-4`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SignalIcon className={`h-5 w-5 ${signalConfig.color}`} />
            <span className="text-sm font-semibold text-muted-foreground">Signal</span>
          </div>
          <span className={`text-xl font-bold ${signalConfig.color}`}>{signal}</span>
        </div>
      </div>

      {/* Expected Return */}
      <div className={`mb-5 rounded-lg ${returnBgColor} p-4`}>
        <p className="text-xs text-muted-foreground font-semibold mb-2">Expected Return</p>
        <p className={`text-2xl font-bold ${returnColor}`}>
          {expectedReturn > 0 ? '+' : ''}{expectedReturn.toFixed(2)}%
        </p>
      </div>

      {/* Confidence Gauge */}
      <div className="mb-5 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground font-semibold uppercase">Confidence</span>
          <span className="text-sm font-bold text-foreground">{confidence.toFixed(0)}%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-surface-secondary">
          <div
            className={`h-full bg-gradient-to-r ${getConfidenceColor(confidence)} transition-all duration-300`}
            style={{ width: `${confidence}%` }}
          />
        </div>
      </div>

      {/* Accuracy & Last Update */}
      <div className="space-y-2 border-t border-border/30 pt-4">
        {accuracy !== undefined && (
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Backtest Accuracy</span>
            <span className="font-semibold text-foreground">{accuracy.toFixed(1)}%</span>
          </div>
        )}
        {lastUpdate && (
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Last Updated</span>
            <span className="font-mono text-muted-foreground">
              {lastUpdate.toLocaleDateString()} {lastUpdate.toLocaleTimeString()}
            </span>
          </div>
        )}
        <div className={`inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-semibold ${statusConfig.bgColor} ${statusConfig.color}`}>
          {statusConfig.label}
        </div>
      </div>

      {/* Hover Indicator */}
      <div className="pointer-events-none absolute inset-0 rounded-lg opacity-0 shadow-inset transition-opacity duration-300 group-hover:opacity-100" />
    </div>
  );
}
