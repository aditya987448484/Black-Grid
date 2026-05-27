"""Flight data service — Aviationstack + OpenSky + mock fallback."""

from __future__ import annotations

import random
import math
import httpx
from app.core.config import (
    OPENSKY_USERNAME, OPENSKY_PASSWORD,
    AVIATIONSTACK_API_KEY, FLIGHT_DATA_PROVIDER,
)

AIRPORTS = [
    ("JFK", 40.64, -73.78), ("LAX", 33.94, -118.41), ("LHR", 51.47, -0.46),
    ("CDG", 49.01, 2.55), ("DXB", 25.25, 55.36), ("HND", 35.55, 139.78),
    ("SIN", 1.36, 103.99), ("HKG", 22.31, 113.91), ("FRA", 50.03, 8.57),
    ("SYD", -33.95, 151.18), ("PEK", 40.08, 116.58), ("ICN", 37.46, 126.44),
    ("ORD", 41.97, -87.91), ("AMS", 52.31, 4.76), ("IST", 41.26, 28.74),
    ("BOM", 19.09, 72.87), ("GRU", -23.43, -46.47), ("JNB", -26.14, 28.25),
    ("DOH", 25.26, 51.61), ("MIA", 25.79, -80.29),
]
AIRLINES = ["AAL", "UAL", "DAL", "BAW", "AFR", "DLH", "UAE", "SIA", "CPA", "QFA",
            "ANA", "KAL", "THY", "QTR", "ETH", "SWR", "KLM", "TAP", "ACA", "LAN"]
AIRCRAFT = ["B737", "B777", "B787", "A320", "A330", "A350", "A380", "B747", "E190", "B767"]


def _mock_flights(count: int = 120) -> list[dict]:
    flights = []
    for i in range(count):
        origin = random.choice(AIRPORTS)
        dest = random.choice([a for a in AIRPORTS if a != origin])
        t = random.random()
        lat = origin[1] + (dest[1] - origin[1]) * t + random.uniform(-2, 2)
        lon = origin[2] + (dest[2] - origin[2]) * t + random.uniform(-2, 2)
        heading = math.degrees(math.atan2(dest[2] - origin[2], dest[1] - origin[1])) % 360
        flights.append({
            "id": f"FL{i:04d}",
            "callsign": f"{random.choice(AIRLINES)}{random.randint(100, 9999)}",
            "latitude": round(lat, 4), "longitude": round(lon, 4),
            "altitude": round(random.uniform(28000, 41000), 0) if 0.1 < t < 0.9 else round(random.uniform(0, 10000), 0),
            "speed": round(random.uniform(400, 560), 0) if t > 0.15 else round(random.uniform(0, 200), 0),
            "heading": round(heading + random.uniform(-10, 10), 1) % 360,
            "origin": origin[0], "destination": dest[0],
            "airline": random.choice(AIRLINES), "aircraftType": random.choice(AIRCRAFT),
            "onGround": t < 0.02 or t > 0.98,
        })
    return flights


async def _fetch_aviationstack() -> list[dict] | None:
    if not AVIATIONSTACK_API_KEY:
        return None
    url = "http://api.aviationstack.com/v1/flights"
    params = {"access_key": AVIATIONSTACK_API_KEY, "limit": 100, "flight_status": "active"}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, params=params)
            data = resp.json()
        results = data.get("data", [])
        if not results:
            print(f"[flight_data:avstack] No data. Error: {data.get('error', {}).get('message', 'none')}")
            return None
        flights = []
        for f in results:
            live = f.get("live") or {}
            lat = live.get("latitude")
            lon = live.get("longitude")
            if lat is None or lon is None:
                continue
            flights.append({
                "id": f.get("flight", {}).get("icao") or f"AS_{len(flights)}",
                "callsign": f.get("flight", {}).get("iata", "") or f.get("flight", {}).get("icao", ""),
                "latitude": round(float(lat), 4),
                "longitude": round(float(lon), 4),
                "altitude": round(float(live.get("altitude", 0) or 0), 0),
                "speed": round(float(live.get("speed_horizontal", 0) or 0), 0),
                "heading": round(float(live.get("direction", 0) or 0), 1),
                "origin": f.get("departure", {}).get("iata"),
                "destination": f.get("arrival", {}).get("iata"),
                "airline": f.get("airline", {}).get("iata"),
                "aircraftType": f.get("aircraft", {}).get("iata"),
                "onGround": bool(live.get("is_ground", False)),
            })
        print(f"[flight_data:avstack] Got {len(flights)} live flights")
        return flights if flights else None
    except Exception as e:
        print(f"[flight_data:avstack] Error: {e}")
        return None


async def _fetch_opensky() -> list[dict] | None:
    if not OPENSKY_USERNAME:
        return None
    url = "https://opensky-network.org/api/states/all"
    auth = (OPENSKY_USERNAME, OPENSKY_PASSWORD) if OPENSKY_PASSWORD else None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, auth=auth)
            data = resp.json()
        states = data.get("states", [])
        if not states:
            return None
        flights = []
        for s in states[:200]:
            if s[5] is None or s[6] is None:
                continue
            flights.append({
                "id": s[0] or f"ICAO_{len(flights)}",
                "callsign": (s[1] or "").strip(),
                "latitude": round(float(s[6]), 4),
                "longitude": round(float(s[5]), 4),
                "altitude": round(float(s[7] or 0), 0),
                "speed": round(float(s[9] or 0) * 1.944, 0),
                "heading": round(float(s[10] or 0), 1),
                "origin": None, "destination": None,
                "airline": (s[1] or "")[:3] if s[1] else None,
                "aircraftType": None,
                "onGround": bool(s[8]),
            })
        print(f"[flight_data:opensky] Got {len(flights)} flights")
        return flights if flights else None
    except Exception as e:
        print(f"[flight_data:opensky] Error: {e}")
        return None


MIN_FLIGHT_COUNT = 60  # Minimum markers for a rich global view


async def get_flights() -> tuple[list[dict], str]:
    """Get flights from best available provider. Returns (flights, source).

    If the live provider returns fewer than MIN_FLIGHT_COUNT, supplement
    with mock flights so the global map always shows rich air traffic.
    """
    # Try Aviationstack first
    live = await _fetch_aviationstack()
    if live:
        if len(live) >= MIN_FLIGHT_COUNT:
            return live, "aviationstack"
        # Supplement with mock to fill the map
        padding = _mock_flights(MIN_FLIGHT_COUNT - len(live))
        print(f"[flight_data] Supplementing {len(live)} live with {len(padding)} simulated flights")
        return live + padding, "aviationstack+simulated"

    # Try OpenSky
    live = await _fetch_opensky()
    if live:
        if len(live) >= MIN_FLIGHT_COUNT:
            return live, "opensky"
        padding = _mock_flights(MIN_FLIGHT_COUNT - len(live))
        return live + padding, "opensky+simulated"

    print("[flight_data] All providers failed. Using mock.")
    return _mock_flights(120), "mock"
