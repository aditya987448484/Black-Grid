"use client";

import { TrendingUp, TrendingDown } from "lucide-react";

interface FactorsPanelProps {
  bullish: string[];
  bearish: string[];
}

export default function FactorsPanel({ bullish, bearish }: FactorsPanelProps) {
  return (
    <div className="glass-card p-5">
      <h3 className="text-sm font-semibold mb-4">Bullish vs Bearish Factors</h3>
      <div className="grid grid-cols-2 gap-6">
        <div>
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="h-4 w-4 text-success" />
            <span className="text-xs font-semibold text-success">Bull Case</span>
          </div>
          <ul className="space-y-2">
            {bullish.map((f, i) => (
              <li key={i} className="text-xs text-text-secondary flex items-start gap-2">
                <span className="text-success mt-0.5">+</span>
                {f}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="flex items-center gap-2 mb-3">
            <TrendingDown className="h-4 w-4 text-danger" />
            <span className="text-xs font-semibold text-danger">Bear Case</span>
          </div>
          <ul className="space-y-2">
            {bearish.map((f, i) => (
              <li key={i} className="text-xs text-text-secondary flex items-start gap-2">
                <span className="text-danger mt-0.5">-</span>
                {f}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
