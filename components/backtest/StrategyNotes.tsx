import type { BacktestModelResult } from "@/types/backtest";

export default function StrategyNotes({ models }: { models: BacktestModelResult[] }) {
  return (
    <div className="glass-card p-5">
      <h3 className="text-sm font-semibold mb-4">Strategy Descriptions</h3>
      <div className="space-y-3">
        {models.map((m) => (
          <div key={m.modelName}>
            <p className="text-sm font-semibold text-accent">{m.modelName}</p>
            <p className="text-xs text-text-secondary mt-1">{m.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
