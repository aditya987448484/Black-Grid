"""News sentiment service — NewsAPI integration with market-impact scoring."""

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


def _score_sentiment(title: str, description: str) -> dict:
    """Score news article for market-relevant sentiment and asset-class impact."""
    text = (title + " " + (description or "")).lower()

    # Simple keyword-based sentiment (negative words increase severity)
    neg_words = ["war", "attack", "crisis", "crash", "collapse", "threat", "sanctions",
                 "missile", "conflict", "tensions", "disruption", "shutdown", "default"]
    pos_words = ["deal", "agreement", "growth", "surge", "recovery", "peace", "rally"]

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

    return {
        "sentiment": sentiment,
        "severity": severity,
        "marketImpact": round(severity * 0.8, 2),
        "affectedAssets": affected,
    }


async def fetch_market_news(query: str = "geopolitics OR oil OR shipping OR military OR semiconductor") -> list[dict]:
    """Fetch market-relevant news from NewsAPI and score for sentiment/impact."""
    if not NEWS_API_KEY:
        print("[news_sentiment] No NEWS_API_KEY. Skipping.")
        return []

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 20,
        "apiKey": NEWS_API_KEY,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            data = resp.json()

        articles = data.get("articles", [])
        if not articles:
            print(f"[news_sentiment] No articles. Status: {data.get('status')}")
            return []

        events = []
        for i, article in enumerate(articles):
            title = article.get("title", "")
            desc = article.get("description", "")
            if not title or title == "[Removed]":
                continue

            scores = _score_sentiment(title, desc)

            events.append({
                "id": f"news_{i}",
                "title": title[:120],
                "latitude": 0,  # Will be geocoded or filtered out
                "longitude": 0,
                "region": "Global",
                "eventType": "news_sentiment",
                "severity": scores["severity"],
                "marketImpact": scores["marketImpact"],
                "sentiment": scores["sentiment"],
                "affectedAssets": scores["affectedAssets"],
                "summary": (desc or title)[:300],
                "timestamp": article.get("publishedAt", datetime.utcnow().isoformat()),
                "source": article.get("source", {}).get("name", "NewsAPI"),
            })

        print(f"[news_sentiment] Got {len(events)} scored articles")
        return events

    except Exception as e:
        print(f"[news_sentiment] Error: {e}")
        return []
