"""World Hub orchestrator — aggregates flights, ships, geopolitical, and news data."""

from __future__ import annotations

from app.services.flight_data import get_flights
from app.services.ship_data import get_ships
from app.services.geopolitical_data import get_geopolitical_events
from app.services.news_sentiment import fetch_market_news


async def get_world_hub_overview() -> dict:
    """Aggregate all World Hub data sources into a unified overview."""
    flights, flight_src = await get_flights()
    ships, ship_src = await get_ships()
    events, geo_src = await get_geopolitical_events()

    # Also pull in scored news articles
    news = await fetch_market_news()
    all_events = events + [n for n in news if n.get("severity", 0) > 0.3]

    # Compute global risk score
    if all_events:
        global_risk = round(sum(e["severity"] * e.get("marketImpact", 0.3) for e in all_events) / len(all_events), 2)
    else:
        global_risk = 0.0

    # Aggregate asset-class sensitivity
    sensitivity_map: dict[str, dict] = {}
    for event in all_events:
        for a in event.get("affectedAssets", []):
            ac = a["assetClass"]
            if ac not in sensitivity_map:
                sensitivity_map[ac] = {"assetClass": ac, "score": 0.0, "tickers": set()}
            sensitivity_map[ac]["score"] = max(sensitivity_map[ac]["score"], a["score"])
            sensitivity_map[ac]["tickers"].update(a.get("tickers", []))

    asset_sensitivity = [
        {"assetClass": v["assetClass"], "score": round(v["score"], 2), "tickers": sorted(v["tickers"])}
        for v in sorted(sensitivity_map.values(), key=lambda x: x["score"], reverse=True)
    ]

    # Top events sorted by market impact
    top_events = sorted(all_events, key=lambda e: e.get("marketImpact", 0), reverse=True)[:10]

    return {
        "flightCount": len(flights),
        "shipCount": len(ships),
        "activeEvents": len(all_events),
        "globalRiskScore": global_risk,
        "topEvents": top_events,
        "assetClassSensitivity": asset_sensitivity,
    }
