"""Geopolitical event and hotspot data service with GDELT support and curated fallback."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
import httpx


# ── Curated geopolitical hotspots with market relevance ──────────────────────

CURATED_HOTSPOTS: list[dict] = [
    {
        "id": "hormuz",
        "title": "Strait of Hormuz - Shipping Tensions",
        "latitude": 26.56,
        "longitude": 56.25,
        "region": "Middle East",
        "eventType": "trade_chokepoint",
        "severity": 0.82,
        "marketImpact": 0.88,
        "affectedAssets": [
            {"assetClass": "Oil & Gas", "score": 0.95, "tickers": ["XLE", "CL=F", "USO"]},
            {"assetClass": "Shipping", "score": 0.85, "tickers": ["SBLK", "DAC", "ZIM"]},
            {"assetClass": "Defense", "score": 0.60, "tickers": ["LMT", "RTX", "NOC"]},
            {"assetClass": "Gold / Safe Havens", "score": 0.70, "tickers": ["GLD", "TLT"]},
        ],
        "summary": "The Strait of Hormuz handles ~21% of global oil transit. Heightened naval activity and regional tensions increase disruption risk to energy supply chains, directly affecting crude benchmarks and tanker rates.",
        "source": "curated_intelligence",
    },
    {
        "id": "suez",
        "title": "Red Sea / Suez Canal - Route Disruption",
        "latitude": 13.50,
        "longitude": 42.80,
        "region": "Middle East / Africa",
        "eventType": "trade_chokepoint",
        "severity": 0.78,
        "marketImpact": 0.82,
        "affectedAssets": [
            {"assetClass": "Shipping", "score": 0.92, "tickers": ["ZIM", "SBLK", "DAC"]},
            {"assetClass": "Oil & Gas", "score": 0.75, "tickers": ["XLE", "CL=F"]},
            {"assetClass": "Equities", "score": 0.45, "tickers": ["SPY"]},
            {"assetClass": "Airlines", "score": 0.35, "tickers": ["AAL", "DAL", "UAL"]},
        ],
        "summary": "Houthi attacks on commercial shipping in the Red Sea have forced major carriers to reroute around the Cape of Good Hope, adding 10-14 days transit time and increasing freight costs by 200-300%.",
        "source": "curated_intelligence",
    },
    {
        "id": "taiwan",
        "title": "Taiwan Strait - Semiconductor Supply Risk",
        "latitude": 24.50,
        "longitude": 118.80,
        "region": "Indo-Pacific",
        "eventType": "geopolitical_tension",
        "severity": 0.85,
        "marketImpact": 0.92,
        "affectedAssets": [
            {"assetClass": "Semiconductors", "score": 0.98, "tickers": ["TSM", "NVDA", "AMD", "INTC"]},
            {"assetClass": "Equities", "score": 0.80, "tickers": ["SPY", "QQQ", "EWT"]},
            {"assetClass": "Defense", "score": 0.75, "tickers": ["LMT", "RTX", "BA"]},
            {"assetClass": "Gold / Safe Havens", "score": 0.85, "tickers": ["GLD", "TLT", "JPY=X"]},
        ],
        "summary": "Taiwan produces ~65% of global advanced semiconductors. Any escalation threatens the backbone of the AI/chip supply chain, with cascading effects across tech, defense, and global equity markets.",
        "source": "curated_intelligence",
    },
    {
        "id": "scs",
        "title": "South China Sea - Maritime Disputes",
        "latitude": 15.50,
        "longitude": 114.00,
        "region": "Indo-Pacific",
        "eventType": "geopolitical_tension",
        "severity": 0.72,
        "marketImpact": 0.68,
        "affectedAssets": [
            {"assetClass": "Shipping", "score": 0.80, "tickers": ["ZIM", "SBLK"]},
            {"assetClass": "Oil & Gas", "score": 0.55, "tickers": ["XLE", "CL=F"]},
            {"assetClass": "Equities", "score": 0.50, "tickers": ["EWH", "EWS", "SPY"]},
            {"assetClass": "Defense", "score": 0.60, "tickers": ["LMT", "GD"]},
        ],
        "summary": "Territorial disputes in the South China Sea affect $5.3T in annual trade flows. Ongoing military posturing between China, Philippines, and other claimants elevates shipping insurance and rerouting risk.",
        "source": "curated_intelligence",
    },
    {
        "id": "panama",
        "title": "Panama Canal - Drought Capacity Constraints",
        "latitude": 9.08,
        "longitude": -79.68,
        "region": "Americas",
        "eventType": "trade_chokepoint",
        "severity": 0.58,
        "marketImpact": 0.55,
        "affectedAssets": [
            {"assetClass": "Shipping", "score": 0.82, "tickers": ["ZIM", "SBLK", "DAC"]},
            {"assetClass": "Oil & Gas", "score": 0.40, "tickers": ["LNG", "CL=F"]},
            {"assetClass": "Equities", "score": 0.25, "tickers": ["SPY"]},
        ],
        "summary": "Drought conditions have reduced Panama Canal daily transits from ~38 to ~24 vessels. LNG and container vessel queues extend to 20+ days, raising costs and disrupting US East Coast supply chains.",
        "source": "curated_intelligence",
    },
    {
        "id": "blacksea",
        "title": "Black Sea - Conflict & Grain Corridor",
        "latitude": 44.00,
        "longitude": 34.00,
        "region": "Europe",
        "eventType": "active_conflict",
        "severity": 0.88,
        "marketImpact": 0.75,
        "affectedAssets": [
            {"assetClass": "Oil & Gas", "score": 0.70, "tickers": ["XLE", "CL=F", "NG=F"]},
            {"assetClass": "Gold / Safe Havens", "score": 0.75, "tickers": ["GLD", "TLT"]},
            {"assetClass": "Defense", "score": 0.85, "tickers": ["LMT", "RTX", "NOC", "GD"]},
            {"assetClass": "Equities", "score": 0.55, "tickers": ["SPY", "VGK"]},
        ],
        "summary": "The Russia-Ukraine conflict continues to disrupt Black Sea shipping, energy pipelines, and grain exports. European energy security remains fragile, and defense spending across NATO is accelerating.",
        "source": "curated_intelligence",
    },
    {
        "id": "nordstream",
        "title": "Baltic / Nord Stream Pipeline Corridor",
        "latitude": 55.50,
        "longitude": 15.00,
        "region": "Europe",
        "eventType": "energy_route",
        "severity": 0.52,
        "marketImpact": 0.60,
        "affectedAssets": [
            {"assetClass": "Oil & Gas", "score": 0.85, "tickers": ["NG=F", "XLE", "EQNR"]},
            {"assetClass": "Equities", "score": 0.40, "tickers": ["VGK", "EWG"]},
            {"assetClass": "Bonds / Rates", "score": 0.35, "tickers": ["TLT", "BUND"]},
        ],
        "summary": "The Nord Stream pipeline sabotage reshaped European energy security. Baltic infrastructure remains under heightened surveillance. European gas prices stay structurally elevated compared to pre-2022 levels.",
        "source": "curated_intelligence",
    },
    {
        "id": "tsmc_fabs",
        "title": "Hsinchu - TSMC Advanced Fab Cluster",
        "latitude": 24.80,
        "longitude": 120.97,
        "region": "Indo-Pacific",
        "eventType": "critical_infrastructure",
        "severity": 0.65,
        "marketImpact": 0.90,
        "affectedAssets": [
            {"assetClass": "Semiconductors", "score": 0.98, "tickers": ["TSM", "NVDA", "AAPL", "AMD"]},
            {"assetClass": "Equities", "score": 0.70, "tickers": ["QQQ", "SMH", "SOXX"]},
        ],
        "summary": "TSMC's Hsinchu campus houses the world's most advanced chip fabrication facilities (3nm/2nm). A single disruption event could impact $500B+ in global tech supply chains within weeks.",
        "source": "curated_intelligence",
    },
    {
        "id": "ras_tanura",
        "title": "Ras Tanura - Saudi Oil Export Hub",
        "latitude": 26.64,
        "longitude": 50.16,
        "region": "Middle East",
        "eventType": "energy_route",
        "severity": 0.60,
        "marketImpact": 0.78,
        "affectedAssets": [
            {"assetClass": "Oil & Gas", "score": 0.95, "tickers": ["CL=F", "XLE", "USO"]},
            {"assetClass": "Airlines", "score": 0.45, "tickers": ["AAL", "DAL", "LUV"]},
            {"assetClass": "Gold / Safe Havens", "score": 0.55, "tickers": ["GLD"]},
        ],
        "summary": "Ras Tanura is the world's largest oil export terminal, handling ~7M bbl/day. Past drone/missile attacks demonstrated vulnerability. Any sustained disruption would cause an immediate crude supply shock.",
        "source": "curated_intelligence",
    },
    {
        "id": "malacca",
        "title": "Strait of Malacca - Asia's Lifeline",
        "latitude": 2.50,
        "longitude": 101.20,
        "region": "Indo-Pacific",
        "eventType": "trade_chokepoint",
        "severity": 0.65,
        "marketImpact": 0.72,
        "affectedAssets": [
            {"assetClass": "Shipping", "score": 0.88, "tickers": ["ZIM", "SBLK"]},
            {"assetClass": "Oil & Gas", "score": 0.70, "tickers": ["CL=F", "XLE"]},
            {"assetClass": "Equities", "score": 0.40, "tickers": ["EWS", "EWM"]},
        ],
        "summary": "The Strait of Malacca is the shortest sea route between the Indian and Pacific Oceans, carrying ~25% of all traded goods. Piracy incidents and congestion remain persistent risks.",
        "source": "curated_intelligence",
    },
    {
        "id": "lng_qatar",
        "title": "Qatar LNG Export Corridor",
        "latitude": 25.90,
        "longitude": 51.53,
        "region": "Middle East",
        "eventType": "energy_route",
        "severity": 0.55,
        "marketImpact": 0.65,
        "affectedAssets": [
            {"assetClass": "Oil & Gas", "score": 0.90, "tickers": ["LNG", "NG=F"]},
            {"assetClass": "Shipping", "score": 0.50, "tickers": ["FLNG"]},
        ],
        "summary": "Qatar is the world's largest LNG exporter. Its North Field expansion will add 64 MTPA by 2027. Export routes through the Strait of Hormuz make supply vulnerable to regional escalation.",
        "source": "curated_intelligence",
    },
    {
        "id": "korea_dmz",
        "title": "Korean DMZ - Nuclear Tensions",
        "latitude": 37.95,
        "longitude": 126.95,
        "region": "Indo-Pacific",
        "eventType": "geopolitical_tension",
        "severity": 0.70,
        "marketImpact": 0.65,
        "affectedAssets": [
            {"assetClass": "Defense", "score": 0.75, "tickers": ["LMT", "RTX"]},
            {"assetClass": "Semiconductors", "score": 0.60, "tickers": ["005930.KS", "SKM"]},
            {"assetClass": "Gold / Safe Havens", "score": 0.65, "tickers": ["GLD"]},
            {"assetClass": "Equities", "score": 0.50, "tickers": ["EWY"]},
        ],
        "summary": "North Korea's nuclear and missile programs create periodic escalation risk. South Korea's semiconductor industry (Samsung, SK Hynix) represents critical supply chain exposure for global memory markets.",
        "source": "curated_intelligence",
    },
]


def _build_mock_events() -> list[dict]:
    """Return curated hotspots with randomized timestamps."""
    now = datetime.utcnow()
    events = []
    for h in CURATED_HOTSPOTS:
        event = dict(h)
        hours_ago = random.randint(1, 72)
        event["timestamp"] = (now - timedelta(hours=hours_ago)).isoformat() + "Z"
        # Add slight severity jitter for realism
        event["severity"] = round(min(1.0, max(0.1, h["severity"] + random.uniform(-0.05, 0.05))), 2)
        event["marketImpact"] = round(min(1.0, max(0.1, h["marketImpact"] + random.uniform(-0.05, 0.05))), 2)
        events.append(event)
    return events


async def fetch_gdelt_events() -> list[dict] | None:
    """Fetch georeferenced events from GDELT API."""
    url = "https://api.gdeltproject.org/api/v2/geo/geo"
    params = {
        "query": "conflict OR military OR shipping OR energy",
        "mode": "PointData",
        "format": "GeoJSON",
        "maxpoints": 50,
        "last": "24h",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()

        features = data.get("features", [])
        if not features:
            return None

        events = []
        for f in features[:30]:
            props = f.get("properties", {})
            coords = f.get("geometry", {}).get("coordinates", [0, 0])
            events.append({
                "id": f"gdelt_{len(events)}",
                "title": props.get("name", "GDELT Event")[:80],
                "latitude": round(float(coords[1]), 4),
                "longitude": round(float(coords[0]), 4),
                "region": props.get("countrycode", "Unknown"),
                "eventType": "gdelt_event",
                "severity": round(random.uniform(0.3, 0.7), 2),
                "marketImpact": round(random.uniform(0.2, 0.6), 2),
                "affectedAssets": [
                    {"assetClass": "Equities", "score": 0.4, "tickers": ["SPY"]},
                ],
                "summary": props.get("html", "Event detected via GDELT monitoring.")[:300],
                "timestamp": props.get("dateadded", datetime.utcnow().isoformat()) + "Z",
                "source": "gdelt",
            })
        return events if events else None

    except Exception as e:
        print(f"[geopolitical_data] GDELT error: {e}")
        return None


async def get_geopolitical_events() -> tuple[list[dict], str]:
    """Get geopolitical events from best available source. Returns (events, source)."""
    # Always include curated hotspots
    curated = _build_mock_events()

    # Try to supplement with GDELT
    gdelt = await fetch_gdelt_events()
    if gdelt:
        combined = curated + gdelt
        return combined, "curated+gdelt"

    return curated, "curated"
