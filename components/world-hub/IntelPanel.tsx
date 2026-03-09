"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { AlertTriangle, TrendingUp, Shield, Activity, ChevronRight } from "lucide-react";
import type { GeopoliticalMarker, AssetSensitivity, WorldHubOverview } from "@/types/world-hub";

interface IntelPanelProps {
  overview: WorldHubOverview | null;
  events: GeopoliticalMarker[];
  selectedEvent: GeopoliticalMarker | null;
  onEventSelect: (event: GeopoliticalMarker) => void;
  region: string;
  riskFilter: string;
  assetFilter: string;
}

function eventTypeColor(t: string): string {
  switch (t) {
    case "active_conflict": return "text-danger";
    case "geopolitical_tension": return "text-warning";
    case "trade_chokepoint": return "text-accent";
    case "energy_route": return "text-accent-violet";
    case "critical_infrastructure": return "text-success";
    default: return "text-warning";
  }
}

function severityLabel(s: number): { label: string; color: string } {
  if (s >= 0.8) return { label: "Critical", color: "text-danger" };
  if (s >= 0.6) return { label: "High", color: "text-warning" };
  if (s >= 0.4) return { label: "Medium", color: "text-accent" };
  return { label: "Low", color: "text-success" };
}

function riskRange(filter: string): [number, number] {
  switch (filter) {
    case "Critical": return [0.8, 1.0];
    case "High": return [0.6, 0.8];
    case "Medium": return [0.4, 0.6];
    case "Low": return [0.0, 0.4];
    default: return [0.0, 1.0];
  }
}

export default function IntelPanel({
  overview,
  events,
  selectedEvent,
  onEventSelect,
  region,
  riskFilter,
  assetFilter,
}: IntelPanelProps) {
  const [minRisk, maxRisk] = riskRange(riskFilter);

  const filtered = events.filter((e) => {
    if (region !== "All" && e.region !== region) return false;
    if (e.severity < minRisk || e.severity > maxRisk) return false;
    if (assetFilter !== "All") {
      const hasAsset = e.affectedAssets.some((a) => a.assetClass === assetFilter);
      if (!hasAsset) return false;
    }
    return true;
  });

  const sorted = [...filtered].sort((a, b) => b.marketImpact - a.marketImpact);

  return (
    <div className="w-[340px] flex flex-col gap-3 overflow-y-auto max-h-full pr-1">
      {/* Global risk score */}
      {overview && (
        <motion.div
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          className="glass-card p-4"
        >
          <div className="flex items-center gap-2 mb-3">
            <Shield className="h-4 w-4 text-accent" />
            <span className="text-xs font-semibold">Global Risk Score</span>
          </div>
          <div className="flex items-center gap-3 mb-3">
            <div className="text-3xl font-bold">
              {(overview.globalRiskScore * 100).toFixed(0)}
            </div>
            <div className="flex-1">
              <div className="h-2 rounded-full bg-surface-hover overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full transition-all",
                    overview.globalRiskScore > 0.7 ? "bg-danger" : overview.globalRiskScore > 0.4 ? "bg-warning" : "bg-success"
                  )}
                  style={{ width: `${overview.globalRiskScore * 100}%` }}
                />
              </div>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <p className="text-lg font-bold text-accent">{overview.flightCount}</p>
              <p className="text-[10px] text-text-muted">Flights</p>
            </div>
            <div>
              <p className="text-lg font-bold text-success">{overview.shipCount}</p>
              <p className="text-[10px] text-text-muted">Ships</p>
            </div>
            <div>
              <p className="text-lg font-bold text-warning">{overview.activeEvents}</p>
              <p className="text-[10px] text-text-muted">Events</p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Asset-class sensitivity */}
      {overview && overview.assetClassSensitivity.length > 0 && (
        <div className="glass-card p-4">
          <div className="flex items-center gap-2 mb-3">
            <Activity className="h-4 w-4 text-accent" />
            <span className="text-xs font-semibold">Asset-Class Sensitivity</span>
          </div>
          <div className="space-y-2">
            {overview.assetClassSensitivity.slice(0, 6).map((a) => (
              <div key={a.assetClass} className="flex items-center gap-2">
                <span className="text-xs text-text-secondary w-28 truncate">{a.assetClass}</span>
                <div className="flex-1 h-1.5 rounded-full bg-surface-hover overflow-hidden">
                  <div
                    className={cn(
                      "h-full rounded-full",
                      a.score > 0.8 ? "bg-danger" : a.score > 0.5 ? "bg-warning" : "bg-accent"
                    )}
                    style={{ width: `${a.score * 100}%` }}
                  />
                </div>
                <span className="text-[10px] text-text-muted w-8 text-right">{(a.score * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Selected event detail */}
      {selectedEvent && (
        <motion.div
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-4 border-accent/20"
        >
          <div className={cn("text-xs font-semibold mb-1", eventTypeColor(selectedEvent.eventType))}>
            {selectedEvent.eventType.replace(/_/g, " ").toUpperCase()}
          </div>
          <h4 className="text-sm font-bold mb-2">{selectedEvent.title}</h4>
          <p className="text-xs text-text-secondary leading-relaxed mb-3">{selectedEvent.summary}</p>
          <div className="flex gap-4 mb-3">
            <div>
              <p className="text-[10px] text-text-muted">Severity</p>
              <p className={cn("text-sm font-bold", severityLabel(selectedEvent.severity).color)}>
                {severityLabel(selectedEvent.severity).label}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-text-muted">Market Impact</p>
              <p className="text-sm font-bold">{(selectedEvent.marketImpact * 100).toFixed(0)}%</p>
            </div>
            <div>
              <p className="text-[10px] text-text-muted">Region</p>
              <p className="text-sm font-semibold text-text-secondary">{selectedEvent.region}</p>
            </div>
          </div>
          <div>
            <p className="text-[10px] text-text-muted mb-1.5">Affected Assets</p>
            <div className="space-y-1.5">
              {selectedEvent.affectedAssets.map((a) => (
                <div key={a.assetClass} className="flex items-center gap-2">
                  <span className="text-[10px] text-text-secondary w-24 truncate">{a.assetClass}</span>
                  <div className="flex-1 h-1 rounded-full bg-surface-hover overflow-hidden">
                    <div
                      className="h-full rounded-full bg-accent"
                      style={{ width: `${a.score * 100}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-text-muted">
                    {a.tickers.slice(0, 3).join(", ")}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      )}

      {/* Events list */}
      <div className="glass-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <AlertTriangle className="h-4 w-4 text-warning" />
          <span className="text-xs font-semibold">Active Events ({sorted.length})</span>
        </div>
        <div className="space-y-1">
          {sorted.length === 0 && (
            <p className="text-xs text-text-muted py-2">No events match current filters.</p>
          )}
          {sorted.map((event) => {
            const sev = severityLabel(event.severity);
            const isSelected = selectedEvent?.id === event.id;
            return (
              <button
                key={event.id}
                onClick={() => onEventSelect(event)}
                className={cn(
                  "w-full text-left rounded-lg px-3 py-2 transition-all flex items-center gap-2",
                  isSelected
                    ? "bg-accent/10 border border-accent/20"
                    : "hover:bg-surface-hover border border-transparent"
                )}
              >
                <div
                  className={cn("w-1.5 h-1.5 rounded-full flex-shrink-0", {
                    "bg-danger": event.severity >= 0.8,
                    "bg-warning": event.severity >= 0.6 && event.severity < 0.8,
                    "bg-accent": event.severity >= 0.4 && event.severity < 0.6,
                    "bg-success": event.severity < 0.4,
                  })}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold truncate">{event.title}</p>
                  <p className="text-[10px] text-text-muted">{event.region} · <span className={sev.color}>{sev.label}</span></p>
                </div>
                <ChevronRight className="h-3 w-3 text-text-muted flex-shrink-0" />
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
