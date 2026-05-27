'use client';

import { ReactNode, CSSProperties } from 'react';

interface ChartContainerProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
  tools?: ReactNode;
  style?: CSSProperties;
}

export function ChartContainer({
  title,
  subtitle,
  children,
  className = '',
  tools,
  style,
}: ChartContainerProps) {
  return (
    <div className={`glass rounded-lg p-6 transition-smooth shadow-premium glass-hover ${className}`} style={style}>
      <div className="flex items-start justify-between mb-6 pb-4 border-b border-border/20">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-foreground tracking-tight">{title}</h3>
          {subtitle && <p className="text-sm text-muted-foreground/70 mt-1.5 leading-relaxed">{subtitle}</p>}
        </div>
        {tools && <div className="flex gap-2 ml-4 flex-shrink-0">{tools}</div>}
      </div>

      <div className="w-full h-full">
        {children}
      </div>
    </div>
  );
}

export function ChartPlaceholder({ height = 'h-80' }: { height?: string }) {
  return (
    <div className={`w-full ${height} bg-gradient-to-br from-surface-secondary/20 to-surface/10 rounded-lg flex items-center justify-center border border-border/15 relative overflow-hidden`}>
      <div className="text-center z-10">
        <p className="text-sm text-muted-foreground/60 font-medium">Chart visualization</p>
        <p className="text-xs text-muted-foreground/40 mt-1.5">Loading data...</p>
      </div>
      <div className="absolute inset-0 rounded-lg shimmer" />
    </div>
  );
}
