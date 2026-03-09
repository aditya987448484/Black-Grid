"use client";

import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import {
  getWorldHubFlights,
  getWorldHubShips,
  getWorldHubGeopolitical,
  getWorldHubOverview,
} from "@/lib/api";
import type {
  FlightMarker,
  ShipMarker,
  GeopoliticalMarker,
  WorldHubOverview,
  LayerToggleState,
  FlightsResponse,
  ShipsResponse,
  GeopoliticalResponse,
} from "@/types/world-hub";
import WorldMap from "@/components/world-hub/WorldMap";
import ControlBar from "@/components/world-hub/ControlBar";
import IntelPanel from "@/components/world-hub/IntelPanel";
import StatsBar from "@/components/world-hub/StatsBar";

export default function WorldHubPage() {
  const [flights, setFlights] = useState<FlightMarker[]>([]);
  const [ships, setShips] = useState<ShipMarker[]>([]);
  const [events, setEvents] = useState<GeopoliticalMarker[]>([]);
  const [overview, setOverview] = useState<WorldHubOverview | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<GeopoliticalMarker | null>(null);

  const [flightSource, setFlightSource] = useState("loading");
  const [shipSource, setShipSource] = useState("loading");
  const [geoSource, setGeoSource] = useState("loading");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [layers, setLayers] = useState<LayerToggleState>({
    flights: true,
    ships: true,
    geopolitical: true,
    newsSentiment: true,
    chokepoints: true,
    energyRoutes: true,
  });

  const [region, setRegion] = useState("All");
  const [riskFilter, setRiskFilter] = useState("All");
  const [assetFilter, setAssetFilter] = useState("All");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [flightRes, shipRes, geoRes, overviewRes] = await Promise.all([
          getWorldHubFlights().catch(() => null),
          getWorldHubShips().catch(() => null),
          getWorldHubGeopolitical().catch(() => null),
          getWorldHubOverview().catch(() => null),
        ]);

        if (cancelled) return;

        if (flightRes) {
          setFlights(flightRes.flights);
          setFlightSource(flightRes.source);
        }
        if (shipRes) {
          setShips(shipRes.ships);
          setShipSource(shipRes.source);
        }
        if (geoRes) {
          setEvents(geoRes.events);
          setGeoSource(geoRes.source);
        }
        if (overviewRes) {
          setOverview(overviewRes);
        }
      } catch (e: any) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  const toggleLayer = useCallback((layer: keyof LayerToggleState) => {
    setLayers((prev) => ({ ...prev, [layer]: !prev[layer] }));
  }, []);

  const handleEventSelect = useCallback((event: GeopoliticalMarker) => {
    setSelectedEvent((prev) => (prev?.id === event.id ? null : event));
  }, []);

  if (loading) {
    return (
      <div className="space-y-4 h-[calc(100vh-7rem)]">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">World Hub</h2>
        </div>
        <div className="flex gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton h-16 rounded-2xl flex-1" />
          ))}
        </div>
        <div className="skeleton h-12 rounded-2xl" />
        <div className="skeleton flex-1 rounded-2xl" style={{ minHeight: 400 }} />
      </div>
    );
  }

  if (error && !flights.length && !ships.length && !events.length) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold">World Hub</h2>
        <div className="glass-card p-8 text-center">
          <p className="text-text-secondary">Unable to load World Hub data.</p>
          <p className="text-xs text-text-muted mt-2">Ensure the backend is running.</p>
          {error && <p className="text-xs text-danger mt-1">{error}</p>}
        </div>
      </div>
    );
  }

  const globalRisk = overview?.globalRiskScore ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col gap-3 h-[calc(100vh-7rem)]"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">World Hub</h2>
        <span className="text-xs text-text-muted">Global Intelligence &middot; Real-time</span>
      </div>

      <StatsBar
        flightCount={flights.length}
        shipCount={ships.length}
        eventCount={events.length}
        globalRisk={globalRisk}
        flightSource={flightSource}
        shipSource={shipSource}
        geoSource={geoSource}
      />

      <ControlBar
        layers={layers}
        onToggle={toggleLayer}
        region={region}
        onRegionChange={setRegion}
        riskFilter={riskFilter}
        onRiskFilterChange={setRiskFilter}
        assetFilter={assetFilter}
        onAssetFilterChange={setAssetFilter}
      />

      <div className="flex gap-3 flex-1 min-h-0">
        <div className="flex-1 min-w-0">
          <WorldMap
            flights={flights}
            ships={ships}
            events={events}
            layers={layers}
            onEventSelect={handleEventSelect}
          />
        </div>
        <IntelPanel
          overview={overview}
          events={events}
          selectedEvent={selectedEvent}
          onEventSelect={handleEventSelect}
          region={region}
          riskFilter={riskFilter}
          assetFilter={assetFilter}
        />
      </div>
    </motion.div>
  );
}
