from __future__ import annotations

from pydantic import BaseModel
from typing import Optional


class FlightMarker(BaseModel):
    id: str
    callsign: str
    latitude: float
    longitude: float
    altitude: float
    speed: float
    heading: float
    origin: Optional[str] = None
    destination: Optional[str] = None
    airline: Optional[str] = None
    aircraftType: Optional[str] = None
    onGround: bool = False


class ShipMarker(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    speed: float
    heading: float
    shipType: str
    flag: Optional[str] = None
    destination: Optional[str] = None
    status: Optional[str] = None
    mmsi: Optional[str] = None


class AssetSensitivity(BaseModel):
    assetClass: str
    score: float
    tickers: list[str]


class GeopoliticalMarker(BaseModel):
    id: str
    title: str
    latitude: float
    longitude: float
    region: str
    eventType: str
    severity: float
    marketImpact: float
    affectedAssets: list[AssetSensitivity]
    summary: str
    timestamp: str
    source: str


class WorldHubOverview(BaseModel):
    flightCount: int
    shipCount: int
    activeEvents: int
    globalRiskScore: float
    topEvents: list[GeopoliticalMarker]
    assetClassSensitivity: list[AssetSensitivity]


class FlightsResponse(BaseModel):
    flights: list[FlightMarker]
    count: int
    source: str


class ShipsResponse(BaseModel):
    ships: list[ShipMarker]
    count: int
    source: str


class GeopoliticalResponse(BaseModel):
    events: list[GeopoliticalMarker]
    count: int
    globalRiskScore: float
    source: str
