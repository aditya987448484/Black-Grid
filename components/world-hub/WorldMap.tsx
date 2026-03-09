"use client";

import { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import type { FlightMarker, ShipMarker, GeopoliticalMarker, LayerToggleState } from "@/types/world-hub";

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN || "";

interface WorldMapProps {
  flights: FlightMarker[];
  ships: ShipMarker[];
  events: GeopoliticalMarker[];
  layers: LayerToggleState;
  onEventSelect: (event: GeopoliticalMarker) => void;
}

function flightsToGeoJSON(flights: FlightMarker[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: flights.map((f) => ({
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [f.longitude, f.latitude] },
      properties: {
        id: f.id, callsign: f.callsign, altitude: f.altitude, speed: f.speed,
        heading: f.heading, origin: f.origin || "—", destination: f.destination || "—",
        airline: f.airline || "—", aircraftType: f.aircraftType || "—", onGround: f.onGround,
      },
    })),
  };
}

function shipsToGeoJSON(ships: ShipMarker[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: ships.map((s) => ({
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [s.longitude, s.latitude] },
      properties: {
        id: s.id, name: s.name, speed: s.speed, heading: s.heading,
        shipType: s.shipType, flag: s.flag || "—", destination: s.destination || "—",
        status: s.status || "—",
      },
    })),
  };
}

function eventsToGeoJSON(events: GeopoliticalMarker[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: events.map((e) => ({
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [e.longitude, e.latitude] },
      properties: {
        id: e.id, title: e.title, region: e.region, eventType: e.eventType,
        severity: e.severity, marketImpact: e.marketImpact, summary: e.summary, source: e.source,
      },
    })),
  };
}

function eventColor(t: string): string {
  switch (t) {
    case "active_conflict": return "#ef4444";
    case "geopolitical_tension": return "#f59e0b";
    case "trade_chokepoint": return "#00d4ff";
    case "energy_route": return "#8b5cf6";
    case "critical_infrastructure": return "#22c55e";
    case "news_sentiment": return "#ec4899";
    default: return "#f59e0b";
  }
}

export default function WorldMap({ flights, ships, events, layers, onEventSelect }: WorldMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const popupRef = useRef<mapboxgl.Popup | null>(null);

  // ── Initialize map ────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    if (!MAPBOX_TOKEN) return;

    mapboxgl.accessToken = MAPBOX_TOKEN;

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/satellite-streets-v12",
      center: [20, 15],
      zoom: 1.8,
      projection: "globe",
      attributionControl: false,
    });

    map.addControl(new mapboxgl.NavigationControl({ showCompass: true }), "bottom-right");

    // Atmosphere / fog for the globe
    map.on("style.load", () => {
      map.setFog({
        color: "rgb(10, 10, 15)",
        "high-color": "rgb(20, 20, 40)",
        "horizon-blend": 0.08,
        "space-color": "rgb(5, 5, 12)",
        "star-intensity": 0.4,
      });
    });

    map.on("load", () => {

      // ═══════════════════════════════════════════════════════════════════
      //  FLIGHTS — cyan, visible from global zoom
      // ═══════════════════════════════════════════════════════════════════
      map.addSource("flights", {
        type: "geojson",
        data: flightsToGeoJSON([]),
        cluster: true,
        clusterMaxZoom: 8,
        clusterRadius: 35,
      });

      // Cluster circles
      map.addLayer({
        id: "flights-cluster",
        type: "circle",
        source: "flights",
        filter: ["has", "point_count"],
        paint: {
          "circle-color": "#00d4ff",
          "circle-opacity": 0.7,
          "circle-radius": ["step", ["get", "point_count"], 14, 10, 20, 50, 28],
          "circle-stroke-width": 2,
          "circle-stroke-color": "rgba(0, 212, 255, 0.35)",
        },
      });

      map.addLayer({
        id: "flights-cluster-count",
        type: "symbol",
        source: "flights",
        filter: ["has", "point_count"],
        layout: { "text-field": "{point_count_abbreviated}", "text-size": 11, "text-font": ["DIN Pro Medium", "Arial Unicode MS Regular"] },
        paint: { "text-color": "#ffffff" },
      });

      // Individual flight markers — visible from zoom 0+
      map.addLayer({
        id: "flights-point",
        type: "circle",
        source: "flights",
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-color": "#00d4ff",
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 1, 3, 4, 4, 8, 6],
          "circle-opacity": 0.9,
          "circle-stroke-width": 1.5,
          "circle-stroke-color": "rgba(0, 212, 255, 0.5)",
        },
      });

      // Glow halo around flight markers
      map.addLayer({
        id: "flights-glow",
        type: "circle",
        source: "flights",
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-color": "#00d4ff",
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 1, 8, 4, 10, 8, 14],
          "circle-opacity": 0.12,
        },
      }, "flights-point");

      // ═══════════════════════════════════════════════════════════════════
      //  SHIPS — green, visible from global zoom
      // ═══════════════════════════════════════════════════════════════════
      map.addSource("ships", {
        type: "geojson",
        data: shipsToGeoJSON([]),
        cluster: true,
        clusterMaxZoom: 8,
        clusterRadius: 35,
      });

      map.addLayer({
        id: "ships-cluster",
        type: "circle",
        source: "ships",
        filter: ["has", "point_count"],
        paint: {
          "circle-color": "#22c55e",
          "circle-opacity": 0.7,
          "circle-radius": ["step", ["get", "point_count"], 14, 10, 20, 50, 28],
          "circle-stroke-width": 2,
          "circle-stroke-color": "rgba(34, 197, 94, 0.35)",
        },
      });

      map.addLayer({
        id: "ships-cluster-count",
        type: "symbol",
        source: "ships",
        filter: ["has", "point_count"],
        layout: { "text-field": "{point_count_abbreviated}", "text-size": 11, "text-font": ["DIN Pro Medium", "Arial Unicode MS Regular"] },
        paint: { "text-color": "#ffffff" },
      });

      map.addLayer({
        id: "ships-point",
        type: "circle",
        source: "ships",
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-color": "#22c55e",
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 1, 3, 4, 4.5, 8, 6],
          "circle-opacity": 0.9,
          "circle-stroke-width": 1.5,
          "circle-stroke-color": "rgba(34, 197, 94, 0.5)",
        },
      });

      map.addLayer({
        id: "ships-glow",
        type: "circle",
        source: "ships",
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-color": "#22c55e",
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 1, 8, 4, 10, 8, 14],
          "circle-opacity": 0.12,
        },
      }, "ships-point");

      // ═══════════════════════════════════════════════════════════════════
      //  GEOPOLITICAL — color-coded, always visible
      // ═══════════════════════════════════════════════════════════════════
      map.addSource("geopolitical", {
        type: "geojson",
        data: eventsToGeoJSON([]),
      });

      // Outer pulse ring
      map.addLayer({
        id: "geo-pulse",
        type: "circle",
        source: "geopolitical",
        paint: {
          "circle-color": ["match", ["get", "eventType"],
            "active_conflict", "#ef4444",
            "geopolitical_tension", "#f59e0b",
            "trade_chokepoint", "#00d4ff",
            "energy_route", "#8b5cf6",
            "critical_infrastructure", "#22c55e",
            "news_sentiment", "#ec4899",
            "#f59e0b",
          ],
          "circle-radius": ["interpolate", ["linear"], ["zoom"],
            1, ["interpolate", ["linear"], ["get", "severity"], 0.3, 8, 1.0, 18],
            5, ["interpolate", ["linear"], ["get", "severity"], 0.3, 16, 1.0, 32],
          ],
          "circle-opacity": 0.18,
          "circle-stroke-width": 0,
        },
      });

      // Inner marker
      map.addLayer({
        id: "geo-point",
        type: "circle",
        source: "geopolitical",
        paint: {
          "circle-color": ["match", ["get", "eventType"],
            "active_conflict", "#ef4444",
            "geopolitical_tension", "#f59e0b",
            "trade_chokepoint", "#00d4ff",
            "energy_route", "#8b5cf6",
            "critical_infrastructure", "#22c55e",
            "news_sentiment", "#ec4899",
            "#f59e0b",
          ],
          "circle-radius": ["interpolate", ["linear"], ["zoom"],
            1, ["interpolate", ["linear"], ["get", "severity"], 0.3, 4, 1.0, 7],
            5, ["interpolate", ["linear"], ["get", "severity"], 0.3, 6, 1.0, 12],
          ],
          "circle-opacity": 0.95,
          "circle-stroke-width": 2,
          "circle-stroke-color": "rgba(255,255,255,0.4)",
        },
      });

      // Labels (appear at closer zoom)
      map.addLayer({
        id: "geo-label",
        type: "symbol",
        source: "geopolitical",
        layout: {
          "text-field": ["get", "title"],
          "text-size": ["interpolate", ["linear"], ["zoom"], 2, 9, 6, 11],
          "text-offset": [0, 1.8],
          "text-anchor": "top",
          "text-max-width": 14,
          "text-font": ["DIN Pro Medium", "Arial Unicode MS Regular"],
        },
        paint: {
          "text-color": "#f0f0f5",
          "text-halo-color": "rgba(0,0,0,0.85)",
          "text-halo-width": 1.5,
        },
        minzoom: 2.5,
      });

      // ═══════════════════════════════════════════════════════════════════
      //  POPUPS
      // ═══════════════════════════════════════════════════════════════════
      const popup = new mapboxgl.Popup({
        closeButton: true,
        closeOnClick: true,
        maxWidth: "300px",
        className: "blackgrid-popup",
        offset: 12,
      });
      popupRef.current = popup;

      map.on("click", "flights-point", (e) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties!;
        popup
          .setLngLat((f.geometry as GeoJSON.Point).coordinates as [number, number])
          .setHTML(`
            <div style="font-family:system-ui;color:#f0f0f5;font-size:12px">
              <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px">
                <div style="width:8px;height:8px;border-radius:50%;background:#00d4ff;box-shadow:0 0 6px #00d4ff"></div>
                <span style="font-weight:700;font-size:14px;color:#00d4ff">${p.callsign || "Unknown"}</span>
              </div>
              <div style="color:#8a8a9a;margin-bottom:8px;font-size:11px">${p.airline} &middot; ${p.aircraftType}</div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 12px;font-size:11px">
                <div><span style="color:#5a5a6a">Route</span><br/><span style="color:#ccc">${p.origin} &rarr; ${p.destination}</span></div>
                <div><span style="color:#5a5a6a">Altitude</span><br/><span style="color:#ccc">${Number(p.altitude).toLocaleString()} ft</span></div>
                <div><span style="color:#5a5a6a">Speed</span><br/><span style="color:#ccc">${p.speed} kts</span></div>
                <div><span style="color:#5a5a6a">Heading</span><br/><span style="color:#ccc">${p.heading}&deg;</span></div>
              </div>
            </div>
          `)
          .addTo(map);
      });

      map.on("click", "ships-point", (e) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties!;
        popup
          .setLngLat((f.geometry as GeoJSON.Point).coordinates as [number, number])
          .setHTML(`
            <div style="font-family:system-ui;color:#f0f0f5;font-size:12px">
              <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px">
                <div style="width:8px;height:8px;border-radius:50%;background:#22c55e;box-shadow:0 0 6px #22c55e"></div>
                <span style="font-weight:700;font-size:14px;color:#22c55e">${p.name}</span>
              </div>
              <div style="color:#8a8a9a;margin-bottom:8px;font-size:11px">${p.shipType} &middot; ${p.flag}</div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 12px;font-size:11px">
                <div><span style="color:#5a5a6a">Status</span><br/><span style="color:#ccc">${p.status}</span></div>
                <div><span style="color:#5a5a6a">Destination</span><br/><span style="color:#ccc">${p.destination}</span></div>
                <div><span style="color:#5a5a6a">Speed</span><br/><span style="color:#ccc">${p.speed} kts</span></div>
                <div><span style="color:#5a5a6a">Heading</span><br/><span style="color:#ccc">${p.heading}&deg;</span></div>
              </div>
            </div>
          `)
          .addTo(map);
      });

      map.on("click", "geo-point", (e) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties!;
        const c = eventColor(p.eventType as string);
        popup
          .setLngLat((f.geometry as GeoJSON.Point).coordinates as [number, number])
          .setHTML(`
            <div style="font-family:system-ui;color:#f0f0f5;font-size:12px">
              <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px">
                <div style="width:8px;height:8px;border-radius:50%;background:${c};box-shadow:0 0 6px ${c}"></div>
                <span style="font-weight:700;font-size:13px;color:${c}">${p.title}</span>
              </div>
              <div style="color:#8a8a9a;margin-bottom:8px;font-size:11px">${p.region} &middot; ${String(p.eventType).replace(/_/g, " ")}</div>
              <div style="display:flex;gap:16px;margin-bottom:8px;font-size:11px">
                <div><span style="color:#5a5a6a">Severity</span><br/><span style="color:${c};font-weight:600">${(Number(p.severity)*100).toFixed(0)}%</span></div>
                <div><span style="color:#5a5a6a">Mkt Impact</span><br/><span style="font-weight:600">${(Number(p.marketImpact)*100).toFixed(0)}%</span></div>
              </div>
              <div style="color:#9a9aaa;font-size:11px;line-height:1.5">${String(p.summary).slice(0, 180)}${String(p.summary).length > 180 ? "..." : ""}</div>
            </div>
          `)
          .addTo(map);
      });

      // Cursor on hover
      for (const layer of ["flights-point", "ships-point", "geo-point", "flights-cluster", "ships-cluster"]) {
        map.on("mouseenter", layer, () => { map.getCanvas().style.cursor = "pointer"; });
        map.on("mouseleave", layer, () => { map.getCanvas().style.cursor = ""; });
      }

      // Click cluster → zoom in
      for (const src of ["flights", "ships"]) {
        map.on("click", `${src}-cluster`, (e) => {
          const features = map.queryRenderedFeatures(e.point, { layers: [`${src}-cluster`] });
          const clusterId = features[0]?.properties?.cluster_id;
          if (clusterId === undefined) return;
          (map.getSource(src) as mapboxgl.GeoJSONSource).getClusterExpansionZoom(clusterId, (err, zoom) => {
            if (err || zoom === undefined || zoom === null) return;
            map.easeTo({
              center: (features[0].geometry as GeoJSON.Point).coordinates as [number, number],
              zoom,
              duration: 500,
            });
          });
        });
      }
    });

    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
  }, []);

  // ── Update data when props/layers change ──────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const flightSrc = map.getSource("flights") as mapboxgl.GeoJSONSource | undefined;
    if (flightSrc) flightSrc.setData(flightsToGeoJSON(layers.flights ? flights : []));

    const shipSrc = map.getSource("ships") as mapboxgl.GeoJSONSource | undefined;
    if (shipSrc) shipSrc.setData(shipsToGeoJSON(layers.ships ? ships : []));

    const filteredEvents = events.filter((e) => {
      if (layers.geopolitical && ["active_conflict", "geopolitical_tension", "critical_infrastructure", "gdelt_event"].includes(e.eventType)) return true;
      if (layers.newsSentiment && e.eventType === "news_sentiment") return true;
      if (layers.chokepoints && e.eventType === "trade_chokepoint") return true;
      if (layers.energyRoutes && e.eventType === "energy_route") return true;
      return false;
    });
    const geoSrc = map.getSource("geopolitical") as mapboxgl.GeoJSONSource | undefined;
    if (geoSrc) geoSrc.setData(eventsToGeoJSON(filteredEvents));
  }, [flights, ships, events, layers]);

  return (
    <div ref={containerRef} className="w-full h-full rounded-xl overflow-hidden">
      {!MAPBOX_TOKEN && (
        <div className="w-full h-full flex items-center justify-center bg-surface text-text-muted text-sm">
          <div className="text-center">
            <p className="font-semibold text-text-secondary mb-2">Mapbox token required</p>
            <p>Set NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN in .env.local</p>
          </div>
        </div>
      )}
    </div>
  );
}
