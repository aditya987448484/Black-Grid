export interface FlightMarker {
  id: string;
  callsign: string;
  latitude: number;
  longitude: number;
  altitude: number;
  speed: number;
  heading: number;
  origin?: string;
  destination?: string;
  airline?: string;
  aircraftType?: string;
  onGround: boolean;
}

export interface ShipMarker {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  speed: number;
  heading: number;
  shipType: string;
  flag?: string;
  destination?: string;
  status?: string;
  mmsi?: string;
}

export interface AssetSensitivity {
  assetClass: string;
  score: number;
  tickers: string[];
}

export interface GeopoliticalMarker {
  id: string;
  title: string;
  latitude: number;
  longitude: number;
  region: string;
  eventType: string;
  severity: number;
  marketImpact: number;
  affectedAssets: AssetSensitivity[];
  summary: string;
  timestamp: string;
  source: string;
}

export interface WorldHubOverview {
  flightCount: number;
  shipCount: number;
  activeEvents: number;
  globalRiskScore: number;
  topEvents: GeopoliticalMarker[];
  assetClassSensitivity: AssetSensitivity[];
}

export interface FlightsResponse {
  flights: FlightMarker[];
  count: number;
  source: string;
}

export interface ShipsResponse {
  ships: ShipMarker[];
  count: number;
  source: string;
}

export interface GeopoliticalResponse {
  events: GeopoliticalMarker[];
  count: number;
  globalRiskScore: number;
  source: string;
}

export interface LayerToggleState {
  flights: boolean;
  ships: boolean;
  geopolitical: boolean;
  newsSentiment: boolean;
  chokepoints: boolean;
  energyRoutes: boolean;
}
