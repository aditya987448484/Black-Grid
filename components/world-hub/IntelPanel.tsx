"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { AlertTriangle, TrendingUp, Shield, Activity, ChevronRight, Zap } from "lucide-react";
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
    case "news_sentiment": return "text-pink-400";
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

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

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
  const [aiAnalysis, setAiAnalysis] = useState<string | null>(null);
  const [loadingAI, setLoadingAI] = useState(false);

  // Reset AI analysis when selected event changes
  useEffect(() => {
    setAiAnalysis(null);
    setLoadingAI(false);
  }, [selectedEvent?.id]);

  const fetchAIAnalysis = async () => {
    if (!selectedEvent) return;
    setLoadingAI(true);
    try {
      const res = await fetch(`${BASE_URL}/api/world-hub/event-impact/${selectedEvent.id}`);
      const data = await res.json();
      setAiAnalysis(data.analysis || data.error || "Unable to load analysis.");
    } catch {
      setAiAnalysis("Unable to load analysis. Check backend connection.");
    } finally {
      setLoadingAI(false);
    }
  };

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

      {/* ═══════════ Selected event detail (rich panel) ═══════════ */}
      {selectedEvent && (
        <motion.div
          key={selectedEvent.id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-4"
        >
          {/* Header */}
          <div className="flex items-start justify-between mb-3">
            <div>
              <div className={cn("text-[10px] font-bold tracking-widest mb-1 uppercase", eventTypeColor(selectedEvent.eventType))}>
                {selectedEvent.eventType.replace(/_/g, " ")}
              </div>
              <h4 className="text-sm font-bold leading-tight">{selectedEvent.title}</h4>
              <p className="text-[10px] text-text-muted mt-0.5">{selectedEvent.region} · {selectedEvent.source}</p>
            </div>
            <div className={cn("text-lg font-black ml-3 flex-shrink-0", severityLabel(selectedEvent.severity).color)}>
              {severityLabel(selectedEvent.severity).label}
            </div>
          </div>

          {/* Severity + Impact meters */}
          <div className="grid grid-cols-2 gap-2 mb-3">
            {[
              { label: "Severity", value: selectedEvent.severity, color: "#ef4444" },
              { label: "Mkt Impact", value: selectedEvent.marketImpact, color: "#00d4ff" },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-surface-hover rounded-lg p-2">
                <p className="text-[10px] text-text-muted mb-1">{label}</p>
                <div className="flex items-center gap-1.5">
                  <div className="flex-1 h-1.5 rounded-full bg-surface overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${value * 100}%`, background: color }} />
                  </div>
                  <span className="text-xs font-bold" style={{ color }}>{(value * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </div>

          {/* Summary */}
          <p className="text-xs text-text-secondary leading-relaxed mb-3 border-l-2 border-accent/30 pl-2">
            {selectedEvent.summary}
          </p>

          {/* Asset class impact — full breakdown */}
          <div className="mb-3">
            <p className="text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-2">
              Market Impact by Asset Class
            </p>
            <div className="space-y-2">
              {[...selectedEvent.affectedAssets]
                .sort((a, b) => b.score - a.score)
                .map((a) => {
                  const impactColor = a.score > 0.8 ? "#ef4444" : a.score > 0.6 ? "#f59e0b" : a.score > 0.4 ? "#00d4ff" : "#22c55e";
                  const direction = selectedEvent.eventType === "active_conflict" || selectedEvent.severity > 0.7 ? "Bearish" : "Bullish";
                  const dirColor = direction === "Bearish" ? "#ef4444" : "#22c55e";
                  const dirArrow = direction === "Bearish" ? "\u25BC" : "\u25B2";
                  return (
                    <div key={a.assetClass} className="bg-surface-hover rounded-lg p-2">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-semibold">{a.assetClass}</span>
                        <span className="text-[10px] font-bold" style={{ color: dirColor }}>{dirArrow} {direction}</span>
                      </div>
                      <div className="flex items-center gap-2 mb-1">
                        <div className="flex-1 h-1 rounded-full bg-surface overflow-hidden">
                          <div className="h-full rounded-full" style={{ width: `${a.score * 100}%`, background: impactColor }} />
                        </div>
                        <span className="text-[10px] font-bold" style={{ color: impactColor }}>{(a.score * 100).toFixed(0)}%</span>
                      </div>
                      {a.tickers.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {a.tickers.slice(0, 5).map((t) => (
                            <span key={t} className="text-[9px] font-mono bg-surface px-1.5 py-0.5 rounded text-accent">
                              {t}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
            </div>
          </div>

          {/* AI Market Analysis button / result */}
          {!aiAnalysis ? (
            <button
              onClick={fetchAIAnalysis}
              disabled={loadingAI}
              className="w-full mt-1 py-1.5 text-xs font-semibold rounded-lg bg-accent/10
                         hover:bg-accent/20 text-accent border border-accent/20 transition-all
                         disabled:opacity-50 flex items-center justify-center gap-1.5"
            >
              {loadingAI ? (
                <><div className="h-3 w-3 rounded-full border-2 border-accent border-t-transparent animate-spin" /> Generating analysis...</>
              ) : (
                <><Zap className="h-3 w-3" /> Get AI Market Analysis</>
              )}
            </button>
          ) : (
            <div className="mt-2 p-3 bg-surface-hover rounded-lg border border-accent/10">
              <p className="text-[10px] font-semibold text-accent mb-2 uppercase tracking-wider">AI Market Analysis</p>
              <p className="text-xs text-text-secondary leading-relaxed whitespace-pre-line">{aiAnalysis}</p>
            </div>
          )}

          {/* Timestamp */}
          {(selectedEvent as any).timestamp && (
            <p className="text-[10px] text-text-muted text-right mt-2">
              Updated: {new Date((selectedEvent as any).timestamp).toLocaleString()}
            </p>
          )}
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
