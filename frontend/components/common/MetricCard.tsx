'use client';

/**
 * Metric Card Component - Premium data display
 */
export function MetricCard({
  label,
  value,
  change,
  changePercent,
  icon,
  trend = 'neutral',
}: {
  label: string;
  value: string | number;
  change?: number;
  changePercent?: number;
  icon?: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
}) {
  const isPositive = changePercent && changePercent >= 0;

  const trendColor = {
    up: 'bg-success/10 text-success border-success/30',
    down: 'bg-destructive/10 text-destructive border-destructive/30',
    neutral: 'bg-primary/10 text-primary border-primary/30',
  }[trend];

  return (
    <div className="glass rounded-xl p-6 transition-smooth glass-hover h-full">
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-label">{label}</p>
            <p className="text-3xl font-bold text-foreground mt-3">{value}</p>
          </div>
          {icon && <div className="text-primary/70">{icon}</div>}
        </div>
        
        {changePercent !== undefined && (
          <div className={`inline-flex items-center px-3 py-2 rounded-lg border ${trendColor}`}>
            <span className="text-sm font-semibold">
              {isPositive ? '+' : ''}{(changePercent * 100).toFixed(2)}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
