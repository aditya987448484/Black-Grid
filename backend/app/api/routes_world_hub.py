"""World Hub routes — flights, ships, geopolitical intelligence."""

from __future__ import annotations

from fastapi import APIRouter
from app.schemas.world_hub import (
    FlightsResponse,
    ShipsResponse,
    GeopoliticalResponse,
    WorldHubOverview,
)
from app.services.flight_data import get_flights
from app.services.ship_data import get_ships
from app.services.geopolitical_data import get_geopolitical_events
from app.services.world_hub_service import get_world_hub_overview

router = APIRouter(prefix="/api/world-hub", tags=["world-hub"])


@router.get("/flights", response_model=FlightsResponse)
async def world_hub_flights():
    flights, source = await get_flights()
    return {"flights": flights, "count": len(flights), "source": source}


@router.get("/ships", response_model=ShipsResponse)
async def world_hub_ships():
    ships, source = await get_ships()
    return {"ships": ships, "count": len(ships), "source": source}


@router.get("/geopolitical", response_model=GeopoliticalResponse)
async def world_hub_geopolitical():
    events, source = await get_geopolitical_events()
    global_risk = round(sum(e["severity"] * e["marketImpact"] for e in events) / max(len(events), 1), 2)
    return {"events": events, "count": len(events), "globalRiskScore": global_risk, "source": source}


@router.get("/overview", response_model=WorldHubOverview)
async def world_hub_overview():
    return await get_world_hub_overview()
