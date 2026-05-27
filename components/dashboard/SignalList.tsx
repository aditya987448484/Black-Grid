"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import type { SignalItem } from "@/types/market";

function SignalBadge({ signal }: { signal: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        signal === "bullish" && "bg-success/10 text-success",
        signal === "bearish" && "bg-danger/10 text-danger",
        signal === "neutral" && "bg-warning/10 text-warning"
      )}
    >
      {signal}
    </span>
  );
}

export default function SignalList({ signals }: { signals: SignalItem[] }) {
  if (!signals.length) {
    return <p className="text-sm text-text-muted">No signals available.</p>;
  }

  return (
    <div className="space-y-2">
      {signals.map((s) => (
        <Link
          key={s.ticker}
          href={`/assets/${s.ticker}`}
          className="flex items-center justify-between rounded-lg px-3 py-2 transition-colors hover:bg-surface-hover"
        >
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold text-text-primary">{s.ticker}</span>
            <span className="text-xs text-text-muted">{s.name}</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-text-secondary">
              {s.expectedReturn >= 0 ? "+" : ""}
              {s.expectedReturn.toFixed(2)}%
            </span>
            <SignalBadge signal={s.signal} />
          </div>
        </Link>
      ))}
    </div>
  );
}
