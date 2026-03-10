"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import AlertBadge from "./AlertBadge";
import type { PortfolioItem } from "@/types/portfolio";

function ChangeCell({ value }: { value: number }) {
  return (
    <span className={cn("text-xs font-medium", value >= 0 ? "text-success" : "text-danger")}>
      {value >= 0 ? "+" : ""}{value.toFixed(2)}%
    </span>
  );
}

export default function PortfolioTable({ items }: { items: PortfolioItem[] }) {
  return (
    <div className="glass-card p-5 overflow-x-auto">
      <h3 className="text-sm font-semibold mb-4">Watchlist Intelligence</h3>
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-border text-xs text-text-muted">
            <th className="pb-2 font-medium">Ticker</th>
            <th className="pb-2 font-medium">Price</th>
            <th className="pb-2 font-medium">1D</th>
            <th className="pb-2 font-medium">5D</th>
            <th className="pb-2 font-medium">1M</th>
            <th className="pb-2 font-medium">Signal</th>
            <th className="pb-2 font-medium">Confidence</th>
            <th className="pb-2 font-medium">Risk</th>
            <th className="pb-2 font-medium">Alloc.</th>
            <th className="pb-2 font-medium">Alert</th>
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
              <td className="py-2.5"><ChangeCell value={item.change1m} /></td>
              <td className="py-2.5">
                <div className="flex items-center gap-1">
                  <div className="w-8 h-1.5 rounded-full bg-surface-hover overflow-hidden">
                    <div className="h-full rounded-full bg-accent" style={{ width: `${item.signalScore}%` }} />
                  </div>
                  <span className="text-xs">{item.signalScore}</span>
                </div>
              </td>
              <td className="py-2.5 text-xs">{item.confidence}%</td>
              <td className="py-2.5">
                <span className={cn(
                  "text-xs font-medium",
                  item.riskScore <= 30 && "text-success",
                  item.riskScore > 30 && item.riskScore <= 60 && "text-warning",
                  item.riskScore > 60 && "text-danger"
                )}>
                  {item.riskScore}
                </span>
              </td>
              <td className="py-2.5 text-xs">{item.allocation}%</td>
              <td className="py-2.5">
                {item.alert && <AlertBadge alert={item.alert} />}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
