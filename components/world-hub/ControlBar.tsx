"use client";

import { cn } from "@/lib/utils";
import { Plane, Ship, AlertTriangle, Anchor, Fuel, Newspaper } from "lucide-react";
import type { LayerToggleState } from "@/types/world-hub";

interface ControlBarProps {
  layers: LayerToggleState;
  onToggle: (layer: keyof LayerToggleState) => void;
  region: string;
  onRegionChange: (region: string) => void;
  riskFilter: string;
  onRiskFilterChange: (risk: string) => void;
  assetFilter: string;
  onAssetFilterChange: (asset: string) => void;
}

const layerButtons: { key: keyof LayerToggleState; label: string; icon: React.ElementType; color: string }[] = [
  { key: "flights", label: "Flights", icon: Plane, color: "text-[#00d4ff]" },
  { key: "ships", label: "Ships", icon: Ship, color: "text-[#22c55e]" },
  { key: "geopolitical", label: "Geopolitical", icon: AlertTriangle, color: "text-[#f59e0b]" },
  { key: "newsSentiment", label: "News", icon: Newspaper, color: "text-[#ec4899]" },
  { key: "chokepoints", label: "Chokepoints", icon: Anchor, color: "text-[#00d4ff]" },
  { key: "energyRoutes", label: "Energy", icon: Fuel, color: "text-[#8b5cf6]" },
];

const regions = ["All", "Middle East", "Indo-Pacific", "Europe", "Americas", "Africa"];
const riskLevels = ["All", "Critical", "High", "Medium", "Low"];
const assetClasses = ["All", "Oil & Gas", "Shipping", "Semiconductors", "Defense", "Airlines", "Gold / Safe Havens", "Equities", "Bonds / Rates"];

export default function ControlBar({
  layers,
  onToggle,
  region,
  onRegionChange,
  riskFilter,
  onRiskFilterChange,
  assetFilter,
  onAssetFilterChange,
}: ControlBarProps) {
  return (
    <div className="glass-card px-4 py-3 flex items-center gap-4 flex-wrap">
      {/* Layer toggles */}
      <div className="flex items-center gap-1.5">
        {layerButtons.map((btn) => (
          <button
            key={btn.key}
            onClick={() => onToggle(btn.key)}
            className={cn(
              "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-all border",
              layers[btn.key]
                ? "bg-white/5 border-white/10"
                : "bg-transparent border-transparent text-text-muted hover:text-text-secondary"
            )}
          >
            <btn.icon className={cn("h-3.5 w-3.5", layers[btn.key] ? btn.color : "")} />
            {btn.label}
          </button>
        ))}
      </div>

      <div className="w-px h-6 bg-border" />

      {/* Region filter */}
      <select
        value={region}
        onChange={(e) => onRegionChange(e.target.value)}
        className="bg-transparent text-xs text-text-secondary border border-border rounded-lg px-2.5 py-1.5 outline-none focus:border-accent/50"
      >
        {regions.map((r) => (
          <option key={r} value={r} className="bg-surface">
            {r === "All" ? "All Regions" : r}
          </option>
        ))}
      </select>

      {/* Risk filter */}
      <select
        value={riskFilter}
        onChange={(e) => onRiskFilterChange(e.target.value)}
        className="bg-transparent text-xs text-text-secondary border border-border rounded-lg px-2.5 py-1.5 outline-none focus:border-accent/50"
      >
        {riskLevels.map((r) => (
          <option key={r} value={r} className="bg-surface">
            {r === "All" ? "All Risk Levels" : `${r} Risk`}
          </option>
        ))}
      </select>

      {/* Asset-class filter */}
      <select
        value={assetFilter}
        onChange={(e) => onAssetFilterChange(e.target.value)}
        className="bg-transparent text-xs text-text-secondary border border-border rounded-lg px-2.5 py-1.5 outline-none focus:border-accent/50"
      >
        {assetClasses.map((a) => (
          <option key={a} value={a} className="bg-surface">
            {a === "All" ? "All Asset Classes" : a}
          </option>
        ))}
      </select>
    </div>
  );
}
