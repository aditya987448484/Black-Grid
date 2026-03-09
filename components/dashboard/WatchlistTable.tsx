"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import type { WatchlistItem } from "@/types/market";

function ChangeCell({ value }: { value: number }) {
  return (
    <span className={cn("text-xs font-medium", value >= 0 ? "text-success" : "text-danger")}>
      {value >= 0 ? "+" : ""}{value.toFixed(2)}%
    </span>
  );
}

export default function WatchlistTable({ items }: { items: WatchlistItem[] }) {
  if (!items.length) {
    return <p className="text-sm text-text-muted">Watchlist empty.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-border text-xs text-text-muted">
            <th className="pb-2 font-medium">Ticker</th>
            <th className="pb-2 font-medium">Price</th>
            <th className="pb-2 font-medium">1D</th>
            <th className="pb-2 font-medium">5D</th>
            <th className="pb-2 font-medium">Signal</th>
            <th className="pb-2 font-medium">Confidence</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.ticker} className="border-b border-border/50 hover:bg-surface-hover transition-colors">
              <td className="py-2.5">
                <Link href={`/assets/${item.ticker}`} className="font-semibold text-accent hover:underline">
                  {item.ticker}
                </Link>
              </td>
              <td className="py-2.5">${item.price.toFixed(2)}</td>
              <td className="py-2.5"><ChangeCell value={item.change1d} /></td>
              <td className="py-2.5"><ChangeCell value={item.change5d} /></td>
              <td className="py-2.5">
                <span className={cn(
                  "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                  item.signal === "bullish" && "bg-success/10 text-success",
                  item.signal === "bearish" && "bg-danger/10 text-danger",
                  item.signal === "neutral" && "bg-warning/10 text-warning"
                )}>
                  {item.signal}
                </span>
              </td>
              <td className="py-2.5 text-xs text-text-secondary">{item.confidence}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
