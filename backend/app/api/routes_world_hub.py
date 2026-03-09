"""World Hub routes — flights, ships, geopolitical intelligence, news, and AI analysis."""

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
from app.services.news_sentiment import fetch_market_news

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


@router.get("/news")
async def world_hub_news():
    """Live geocoded news with market sentiment scores."""
    news = await fetch_market_news()
    geo_news = [n for n in news if n.get("latitude", 0) != 0 or n.get("longitude", 0) != 0]
    return {"articles": geo_news, "count": len(geo_news)}


@router.get("/event-impact/{event_id}")
async def event_market_impact(event_id: str):
    """Get detailed AI-generated market impact analysis for a specific event."""
    from app.services.geopolitical_data import CURATED_HOTSPOTS
    from app.services.ai_analyst_service import _call_anthropic, ANALYST_SYSTEM

    # Search in curated hotspots
    event = next((e for e in CURATED_HOTSPOTS if e["id"] == event_id), None)

    if not event:
        return {"error": f"Event '{event_id}' not found"}

    prompt = f"""You are a geopolitical risk analyst. Write a concise 3-paragraph market impact
analysis for this event: {event['title']} in {event['region']}.

Event summary: {event['summary']}
Severity: {event['severity']*100:.0f}%
Market Impact Score: {event['marketImpact']*100:.0f}%
Affected assets: {[a['assetClass'] for a in event['affectedAssets']]}

Paragraph 1: What is happening and why it matters to markets RIGHT NOW.
Paragraph 2: Which specific sectors/tickers are most exposed and in which direction (up/down).
Paragraph 3: Key watchpoints — what would escalate or de-escalate the risk.

Be specific, decisive, and brief. No hedging. No filler."""

    try:
        analysis = await _call_anthropic(
            ANALYST_SYSTEM,
            [{"role": "user", "content": prompt}],
        )
        return {
            "eventId": event_id,
            "title": event["title"],
            "analysis": analysis,
            "affectedAssets": event["affectedAssets"],
            "severity": event["severity"],
            "marketImpact": event["marketImpact"],
        }
    except Exception as e:
        return {"error": str(e)}
