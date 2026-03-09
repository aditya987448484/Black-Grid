export default function ConfidenceMeter({ value }: { value: number }) {
  const pct = Math.round(value * 100);

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-text-muted">Confidence</span>
      <div className="w-24 h-2 rounded-full bg-surface-hover overflow-hidden">
        <div
          className="h-full rounded-full bg-accent transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-semibold">{pct}%</span>
    </div>
  );
}
