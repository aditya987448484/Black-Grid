"""News sentiment service — NewsAPI integration with geocoding and market-impact scoring."""

from __future__ import annotations

import random
from datetime import datetime
import httpx
from app.core.config import NEWS_API_KEY

# Keywords that map to asset-class sensitivity
ASSET_KEYWORDS = {
    "Oil & Gas": ["oil", "crude", "opec", "pipeline", "lng", "natural gas", "energy", "petroleum"],
    "Shipping": ["shipping", "vessel", "port", "maritime", "freight", "container", "suez", "canal"],
    "Defense": ["military", "defense", "war", "missile", "nato", "arms", "weapon"],
    "Semiconductors": ["chip", "semiconductor", "tsmc", "nvidia", "intel", "fab", "silicon"],
    "Airlines": ["airline", "aviation", "flight", "airport", "travel"],
    "Gold / Safe Havens": ["gold", "safe haven", "treasury", "bond", "refuge"],
    "Equities": ["stock", "market", "index", "s&p", "nasdaq", "equity"],
    "Bonds / Rates": ["interest rate", "fed", "central bank", "inflation", "yield", "bond"],
}

# Country/region name → [lat, lon] for news geocoding
GEO_LOOKUP: dict[str, tuple[float, float]] = {
    "china": (35.86, 104.19), "russia": (61.52, 105.32),
    "ukraine": (48.38, 31.17), "israel": (31.05, 34.85),
    "iran": (32.43, 53.69), "taiwan": (23.70, 120.96),
    "india": (20.59, 78.96), "pakistan": (30.38, 69.35),
    "north korea": (40.34, 127.51), "south korea": (35.91, 127.77),
    "japan": (36.20, 138.25), "saudi arabia": (23.89, 45.08),
    "iraq": (33.22, 43.68), "syria": (34.80, 38.99),
    "turkey": (38.96, 35.24), "egypt": (26.82, 30.80),
    "libya": (26.34, 17.23), "yemen": (15.55, 48.52),
    "gaza": (31.35, 34.31), "lebanon": (33.85, 35.86),
    "sudan": (12.86, 30.22), "ethiopia": (9.15, 40.49),
    "somalia": (5.15, 46.20), "nigeria": (9.08, 8.68),
    "congo": (-4.04, 21.76), "myanmar": (21.91, 95.96),
    "afghanistan": (33.94, 67.71), "venezuela": (6.42, -66.59),
    "mexico": (23.63, -102.55), "brazil": (-14.24, -51.93),
    "usa": (37.09, -95.71), "united states": (37.09, -95.71),
    "europe": (54.53, 15.25), "germany": (51.17, 10.45),
    "france": (46.23, 2.21), "uk": (55.38, -3.44),
    "united kingdom": (55.38, -3.44), "britain": (55.38, -3.44),
    "suez": (30.00, 32.55), "hormuz": (26.56, 56.25),
    "red sea": (20.00, 38.50), "black sea": (43.00, 35.00),
    "south china sea": (12.00, 113.00), "taiwan strait": (24.00, 119.00),
    "persian gulf": (26.00, 51.00), "strait of malacca": (2.50, 101.50),
    "arctic": (71.71, -42.62),
    "nato": (50.85, 4.35), "opec": (24.47, 54.37),
    "beijing": (39.90, 116.40), "moscow": (55.76, 37.62),
    "washington": (38.91, -77.04), "brussels": (50.85, 4.35),
    "tehran": (35.69, 51.39), "kyiv": (50.45, 30.52),
    "seoul": (37.57, 126.98), "tokyo": (35.68, 139.69),
    "london": (51.51, -0.13), "paris": (48.86, 2.35),
}


def _geocode_article(title: str, description: str) -> tuple[float, float] | None:
    """Try to extract a geographic location from news text."""
    text = (title + " " + (description or "")).lower()
    for place, coords in GEO_LOOKUP.items():
        if place in text:
            # Add slight jitter so overlapping events don't stack exactly
            return (
                round(coords[0] + random.uniform(-1.5, 1.5), 4),
                round(coords[1] + random.uniform(-1.5, 1.5), 4),
            )
    return None


def _region_from_coords(coords: tuple[float, float]) -> str:
    lat, lon = coords
    if 25 < lat < 45 and 25 < lon < 60: return "Middle East"
    if lat > 35 and 60 < lon < 145: return "Asia"
    if -10 < lat < 35 and 100 < lon < 145: return "Indo-Pacific"
    if 35 < lat < 72 and -10 < lon < 40: return "Europe"
    if -35 < lat < 35 and -20 < lon < 55: return "Africa"
    if -60 < lat < 15 and -82 < lon < -35: return "Americas"
    if 15 < lat < 75 and -170 < lon < -52: return "Americas"
    return "Global"


def _score_sentiment(title: str, description: str) -> dict:
    """Score news article for market-relevant sentiment and asset-class impact."""
    text = (title + " " + (description or "")).lower()

    # Simple keyword-based sentiment (negative words increase severity)
    neg_words = ["war", "attack", "crisis", "crash", "collapse", "threat", "sanctions",
                 "missile", "conflict", "tensions", "disruption", "shutdown", "default",
                 "strike", "invasion", "bomb", "escalation", "blockade"]
    pos_words = ["deal", "agreement", "growth", "surge", "recovery", "peace", "rally",
                 "ceasefire", "truce", "breakthrough", "cooperation"]

    neg_count = sum(1 for w in neg_words if w in text)
    pos_count = sum(1 for w in pos_words if w in text)
    sentiment = round(max(-1, min(1, (pos_count - neg_count) * 0.2)), 2)
    severity = round(min(1.0, neg_count * 0.15 + 0.2), 2)

    # Match asset classes
    affected = []
    for asset_class, keywords in ASSET_KEYWORDS.items():
        hits = sum(1 for k in keywords if k in text)
        if hits > 0:
            score = round(min(1.0, hits * 0.25 + 0.3), 2)
            affected.append({"assetClass": asset_class, "score": score, "tickers": []})

    if not affected:
        affected = [{"assetClass": "Equities", "score": 0.3, "tickers": ["SPY"]}]

    # Add market direction per asset class
    market_direction: dict[str, str] = {}
    if any(w in text for w in ["attack", "strike", "missile", "conflict", "war", "invasion"]):
        market_direction = {"Oil & Gas": "up", "Defense": "up", "Gold / Safe Havens": "up", "Equities": "down", "Airlines": "down"}
    elif any(w in text for w in ["sanctions", "export ban", "restriction", "blockade"]):
        market_direction = {"Semiconductors": "down", "Equities": "down", "Defense": "up"}
    elif any(w in text for w in ["deal", "agreement", "ceasefire", "peace"]):
        market_direction = {"Equities": "up", "Gold / Safe Havens": "down", "Oil & Gas": "down"}
    elif any(w in text for w in ["rate hike", "hawkish", "inflation high"]):
        market_direction = {"Bonds / Rates": "down", "Equities": "down", "Gold / Safe Havens": "up"}

    for asset in affected:
        asset["direction"] = market_direction.get(asset["assetClass"], "neutral")

    return {
        "sentiment": sentiment,
        "severity": severity,
        "marketImpact": round(severity * 0.8, 2),
        "affectedAssets": affected,
        "marketDirection": market_direction,
    }


# Multiple query categories for broader coverage
MARKET_NEWS_QUERIES = [
    "war OR military conflict OR sanctions OR missile attack",
    "oil price OR crude OR OPEC OR energy supply",
    "shipping disruption OR port closure OR Suez OR Strait of Hormuz",
    "semiconductor shortage OR chip supply OR TSMC",
    "central bank OR interest rates OR inflation OR Federal Reserve",
    "trade war OR tariffs OR sanctions OR export controls",
    "geopolitical risk OR political crisis OR coup OR election",
]


async def fetch_market_news(queries: list[str] | None = None) -> list[dict]:
    """Fetch market-relevant news from NewsAPI, geocode, and score for sentiment/impact."""
    if not NEWS_API_KEY:
        print("[news_sentiment] No NEWS_API_KEY. Skipping.")
        return []

    if queries is None:
        queries = MARKET_NEWS_QUERIES

    all_events: list[dict] = []
    seen_titles: set[str] = set()

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            for q in queries:
                url = "https://newsapi.org/v2/everything"
                params = {
                    "q": q,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 10,
                    "apiKey": NEWS_API_KEY,
                }
                try:
                    resp = await client.get(url, params=params)
                    data = resp.json()
                    articles = data.get("articles", [])
                except Exception:
                    continue

                for i, article in enumerate(articles):
                    title = article.get("title", "")
                    desc = article.get("description", "")
                    if not title or title == "[Removed]" or title in seen_titles:
                        continue
                    seen_titles.add(title)

                    # Geocode — skip articles with no geographic context
                    coords = _geocode_article(title, desc)
                    if coords is None:
                        continue

                    scores = _score_sentiment(title, desc)

                    all_events.append({
                        "id": f"news_{len(all_events)}",
                        "title": title[:120],
                        "latitude": coords[0],
                        "longitude": coords[1],
                        "region": _region_from_coords(coords),
                        "eventType": "news_sentiment",
                        "severity": scores["severity"],
                        "marketImpact": scores["marketImpact"],
                        "sentiment": scores["sentiment"],
                        "affectedAssets": scores["affectedAssets"],
                        "summary": (desc or title)[:300],
                        "timestamp": article.get("publishedAt", datetime.utcnow().isoformat()),
                        "source": article.get("source", {}).get("name", "NewsAPI"),
                    })

        print(f"[news_sentiment] Got {len(all_events)} geocoded articles from {len(queries)} queries")
        return all_events

    except Exception as e:
        print(f"[news_sentiment] Error: {e}")
        return []
