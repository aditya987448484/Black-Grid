'use client';

import { ReactNode, CSSProperties } from 'react';

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  interactive?: boolean;
  glow?: boolean;
  style?: CSSProperties;
}

export function GlassCard({
  children,
  className = '',
  interactive = true,
  glow = false,
  style,
}: GlassCardProps) {
  return (
    <div
      className={`glass rounded-lg p-6 transition-smooth shadow-premium ${
        interactive ? 'glass-hover' : ''
      } ${glow ? 'glow' : ''} ${className}`}
      style={style}
    >
      {children}
    </div>
  );
}

interface DataCardProps {
  label: string;
  value: string | number;
  suffix?: string;
  change?: number;
  changeLabel?: string;
  icon?: ReactNode;
  className?: string;
}

export function DataCard({
  label,
  value,
  suffix,
  change,
  changeLabel,
  icon,
  className = '',
}: DataCardProps) {
  return (
    <GlassCard className={className} interactive>
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-label text-muted-foreground/70">{label}</p>
            <div className="flex items-baseline gap-2 mt-3">
              <p className="text-metric text-foreground">{value}</p>
              {suffix && <span className="text-sm text-muted-foreground/60">{suffix}</span>}
            </div>
          </div>
          {icon && <div className="text-primary/50 flex-shrink-0">{icon}</div>}
        </div>

        {change !== undefined && (
          <div className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-smooth ${
            change >= 0 
              ? 'bg-success/10 text-success border border-success/20' 
              : 'bg-destructive/10 text-destructive border border-destructive/20'
          }`}>
            <span>
              {change >= 0 ? '+' : ''}{change.toFixed(2)}%
            </span>
            {changeLabel && <span className="text-xs text-muted-foreground/60 ml-auto">{changeLabel}</span>}
          </div>
        )}
      </div>
    </GlassCard>
  );
}
