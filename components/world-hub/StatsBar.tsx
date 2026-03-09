"use client";

import { motion } from "framer-motion";
import { Plane, Ship, AlertTriangle, Globe } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatsBarProps {
  flightCount: number;
  shipCount: number;
  eventCount: number;
  globalRisk: number;
  flightSource: string;
  shipSource: string;
  geoSource: string;
}

export default function StatsBar({
  flightCount,
  shipCount,
  eventCount,
  globalRisk,
  flightSource,
  shipSource,
  geoSource,
}: StatsBarProps) {
  const items = [
    {
      icon: Plane,
      label: "Active Flights",
      value: flightCount.toLocaleString(),
      sub: flightSource,
      color: "text-[#00d4ff]",
    },
    {
      icon: Ship,
      label: "Tracked Vessels",
      value: shipCount.toLocaleString(),
      sub: shipSource,
      color: "text-[#22c55e]",
    },
    {
      icon: AlertTriangle,
      label: "Geo Events",
      value: eventCount.toString(),
      sub: geoSource,
      color: "text-[#f59e0b]",
    },
    {
      icon: Globe,
      label: "Global Risk",
      value: `${(globalRisk * 100).toFixed(0)}`,
      sub: globalRisk > 0.6 ? "elevated" : globalRisk > 0.3 ? "moderate" : "low",
      color: globalRisk > 0.6 ? "text-danger" : globalRisk > 0.3 ? "text-warning" : "text-success",
    },
  ];

  return (
    <div className="flex gap-3">
      {items.map((item, i) => (
        <motion.div
          key={item.label}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          className="glass-card px-4 py-2.5 flex items-center gap-3 flex-1"
        >
          <item.icon className={cn("h-4 w-4", item.color)} />
          <div>
            <p className="text-sm font-bold">{item.value}</p>
            <p className="text-[10px] text-text-muted">{item.label} · {item.sub}</p>
          </div>
        </motion.div>
      ))}
    </div>
  );
}
