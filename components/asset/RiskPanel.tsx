"use client";

import { cn } from "@/lib/utils";
import { Shield } from "lucide-react";

interface RiskPanelProps {
  riskLevel: "low" | "medium" | "high";
  confidence: number;
  aiSummary: string;
}

export default function RiskPanel({ riskLevel, confidence, aiSummary }: RiskPanelProps) {
  return (
    <div className="glass-card p-5">
      <div className="flex items-center gap-2 mb-4">
        <Shield className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold">Risk & Confidence</h3>
      </div>
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-xs text-text-muted mb-1">Risk Level</p>
          <span
            className={cn(
              "inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold",
              riskLevel === "low" && "bg-success/10 text-success",
              riskLevel === "medium" && "bg-warning/10 text-warning",
              riskLevel === "high" && "bg-danger/10 text-danger"
            )}
          >
            {riskLevel.toUpperCase()}
          </span>
        </div>
        <div>
          <p className="text-xs text-text-muted mb-1">Model Confidence</p>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-2 rounded-full bg-surface-hover overflow-hidden">
              <div
                className="h-full rounded-full bg-accent transition-all"
                style={{ width: `${confidence * 100}%` }}
              />
            </div>
            <span className="text-xs font-semibold">{(confidence * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>
      <div>
        <p className="text-xs text-text-muted mb-1">AI Summary</p>
        <p className="text-xs text-text-secondary leading-relaxed">{aiSummary}</p>
      </div>
    </div>
  );
}
