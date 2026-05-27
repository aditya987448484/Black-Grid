"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { Brain, Lock, Zap } from "lucide-react";
import type { ForecastModelOutput } from "@/types/asset";

const statusIcons: Record<string, React.ElementType> = {
  live: Zap,
  simulated: Brain,
  coming_soon: Lock,
};

export default function ModelCard({ model }: { model: ForecastModelOutput }) {
  const Icon = statusIcons[model.status] || Brain;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "glass-card p-4 relative overflow-hidden",
        model.status === "coming_soon" && "opacity-60"
      )}
    >
      {model.status === "coming_soon" && (
        <div className="absolute inset-0 bg-surface/60 backdrop-blur-sm z-10 flex items-center justify-center">
          <span className="text-xs font-medium text-text-muted">Coming Soon</span>
        </div>
      )}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-accent" />
          <span className="text-sm font-semibold">{model.modelName}</span>
        </div>
        <span
          className={cn(
            "text-xs rounded-full px-2 py-0.5 font-medium",
            model.status === "live" && "bg-success/10 text-success",
            model.status === "simulated" && "bg-accent/10 text-accent",
            model.status === "coming_soon" && "bg-text-muted/10 text-text-muted"
          )}
        >
          {model.status.replace("_", " ")}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <p className="text-xs text-text-muted">Direction</p>
          <p className={cn("text-lg font-bold", model.predictedDirection === "up" ? "text-success" : "text-danger")}>
            {model.predictedDirection === "up" ? "Bullish" : "Bearish"}
          </p>
        </div>
        <div>
          <p className="text-xs text-text-muted">Probability</p>
          <p className="text-lg font-bold">{(model.directionProbability * 100).toFixed(1)}%</p>
        </div>
        <div>
          <p className="text-xs text-text-muted">Exp. Return</p>
          <p className={cn("text-sm font-semibold", model.expectedReturn >= 0 ? "text-success" : "text-danger")}>
            {model.expectedReturn >= 0 ? "+" : ""}{model.expectedReturn.toFixed(2)}%
          </p>
        </div>
        <div>
          <p className="text-xs text-text-muted">Confidence</p>
          <p className="text-sm font-semibold">{(model.confidence * 100).toFixed(0)}%</p>
        </div>
      </div>
      <p className="text-xs text-text-muted mt-3">{model.explanation}</p>
    </motion.div>
  );
}
