"""Comprehensive mock data service. Returns realistic fallback data for all endpoints."""

from __future__ import annotations

import random
import math
from datetime import datetime, timedelta


def _generate_sparkline(base: float, n: int = 20) -> list[float]:
    vals = [base]
    for _ in range(n - 1):
        vals.append(vals[-1] * (1 + random.uniform(-0.008, 0.008)))
    return [round(v, 2) for v in vals]


def _generate_price_history(base: float, days: int = 365) -> list[dict]:
    history = []
    price = base * (1 - random.uniform(0.05, 0.15))
    for i in range(days):
        date = (datetime.now() - timedelta(days=days - i)).strftime("%Y-%m-%d")
        daily_return = random.gauss(0.0003, 0.015)
        price *= (1 + daily_return)
        high = price * (1 + abs(random.gauss(0, 0.008)))
        low = price * (1 - abs(random.gauss(0, 0.008)))
        vol = random.randint(20_000_000, 80_000_000)
        history.append({
            "date": date,
            "open": round(price * (1 + random.uniform(-0.005, 0.005)), 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(price, 2),
            "volume": vol,
        })
    return history


def _generate_equity_curve(days: int = 200) -> list[dict]:
    curve = []
    value = 100.0
    for i in range(days):
        date = (datetime.now() - timedelta(days=days - i)).strftime("%Y-%m-%d")
        value *= (1 + random.gauss(0.0005, 0.012))
        curve.append({"date": date, "value": round(value, 2)})
    return curve


ASSET_DB = {
    "AAPL": {"name": "Apple Inc.", "sector": "Technology", "base_price": 189.50, "mcap": 2_950_000_000_000},
    "MSFT": {"name": "Microsoft Corp.", "sector": "Technology", "base_price": 420.30, "mcap": 3_100_000_000_000},
    "GOOGL": {"name": "Alphabet Inc.", "sector": "Technology", "base_price": 175.80, "mcap": 2_180_000_000_000},
    "AMZN": {"name": "Amazon.com Inc.", "sector": "Consumer Cyclical", "base_price": 198.20, "mcap": 2_050_000_000_000},
    "NVDA": {"name": "NVIDIA Corp.", "sector": "Technology", "base_price": 875.40, "mcap": 2_160_000_000_000},
    "TSLA": {"name": "Tesla Inc.", "sector": "Consumer Cyclical", "base_price": 245.60, "mcap": 780_000_000_000},
    "META": {"name": "Meta Platforms Inc.", "sector": "Technology", "base_price": 530.20, "mcap": 1_350_000_000_000},
    "SPY": {"name": "S&P 500 ETF", "sector": "ETF", "base_price": 525.40, "mcap": 0},
    "QQQ": {"name": "Nasdaq 100 ETF", "sector": "ETF", "base_price": 445.80, "mcap": 0},
    "GLD": {"name": "Gold ETF", "sector": "Commodity", "base_price": 212.50, "mcap": 0},
    "RKLB": {"name": "Rocket Lab USA Inc.", "sector": "Aerospace & Defense", "base_price": 22.50, "mcap": 11_000_000_000},
}


def get_asset_info(ticker: str) -> dict:
    """Resolve asset info from ASSET_DB or the live universe cache."""
    t = ticker.upper()
    if t in ASSET_DB:
        return ASSET_DB[t]

    # Try the live universe cache (imported lazily to avoid circular imports)
    from app.services.market_universe import get_company_info_from_universe
    uni = get_company_info_from_universe(t)
    if uni and uni.get("name") and uni["name"] != t:
        return {
            "name": uni.get("name", t),
            "sector": uni.get("sector") or "Unknown",
            "base_price": 100.0,
            "mcap": 0,
        }

    # Last resort — return minimal info, fundamentals fetch will populate later
    return {"name": t, "sector": "Unknown", "base_price": 100.0, "mcap": 0}


def mock_market_overview() -> dict:
    indices = [
        {"symbol": "SPY", "name": "S&P 500", "base": 5320.15},
        {"symbol": "QQQ", "name": "Nasdaq 100", "base": 18750.40},
        {"symbol": "IWM", "name": "Russell 2000", "base": 2040.80},
        {"symbol": "DIA", "name": "Dow Jones", "base": 39450.20},
        {"symbol": "GLD", "name": "Gold", "base": 2380.50},
    ]

    index_metrics = []
    for idx in indices:
        change = round(random.uniform(-1.5, 2.0), 2)
        change_pct = round(change / idx["base"] * 100, 2)
        index_metrics.append({
            "symbol": idx["symbol"],
            "name": idx["name"],
            "price": round(idx["base"] + change, 2),
            "change": change,
            "changePercent": change_pct,
            "volume": random.randint(50_000_000, 200_000_000),
            "sparkline": _generate_sparkline(idx["base"]),
        })

    signals = [
        {"ticker": "NVDA", "name": "NVIDIA Corp.", "signal": "bullish", "confidence": 78, "expectedReturn": 2.35},
        {"ticker": "AAPL", "name": "Apple Inc.", "signal": "bullish", "confidence": 72, "expectedReturn": 1.15},
        {"ticker": "MSFT", "name": "Microsoft Corp.", "signal": "neutral", "confidence": 65, "expectedReturn": 0.45},
        {"ticker": "TSLA", "name": "Tesla Inc.", "signal": "bearish", "confidence": 68, "expectedReturn": -1.80},
        {"ticker": "META", "name": "Meta Platforms", "signal": "bullish", "confidence": 70, "expectedReturn": 1.65},
    ]

    macro = [
        {"name": "10Y Treasury", "value": 4.28, "unit": "%", "trend": "rising"},
        {"name": "Fed Funds Rate", "value": 5.33, "unit": "%", "trend": "stable"},
        {"name": "CPI YoY", "value": 3.2, "unit": "%", "trend": "falling"},
        {"name": "Unemployment", "value": 3.7, "unit": "%", "trend": "stable"},
        {"name": "GDP Growth", "value": 2.8, "unit": "%", "trend": "rising"},
    ]

    watchlist = []
    for ticker in ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"]:
        info = get_asset_info(ticker)
        sig = random.choice(["bullish", "bearish", "neutral"])
        watchlist.append({
            "ticker": ticker,
            "name": info["name"],
            "price": round(info["base_price"] * (1 + random.uniform(-0.02, 0.02)), 2),
            "change1d": round(random.uniform(-3, 3), 2),
            "change5d": round(random.uniform(-5, 5), 2),
            "change1m": round(random.uniform(-8, 10), 2),
            "signal": sig,
            "signalScore": round(random.uniform(30, 90), 1),
            "confidence": round(random.uniform(50, 85), 1),
            "riskScore": round(random.uniform(20, 75), 1),
            "alert": random.choice([None, None, "breakout", "warning"]),
        })

    recent_reports = [
        {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "rating": "Buy",
            "confidence": 0.74,
            "generatedAt": datetime.now().isoformat(),
            "summary": "Strong revenue growth driven by Services segment and iPhone upgrades. Technical momentum supports near-term upside.",
        },
        {
            "ticker": "NVDA",
            "name": "NVIDIA Corp.",
            "rating": "Strong Buy",
            "confidence": 0.82,
            "generatedAt": datetime.now().isoformat(),
            "summary": "AI infrastructure demand continues to accelerate. Data center revenue outlook remains exceptionally strong.",
        },
        {
            "ticker": "TSLA",
            "name": "Tesla Inc.",
            "rating": "Hold",
            "confidence": 0.58,
            "generatedAt": datetime.now().isoformat(),
            "summary": "Mixed signals with margin compression concerns offset by FSD progress and energy storage growth.",
        },
    ]

    return {
        "indices": index_metrics,
        "signals": signals,
        "macro": macro,
        "watchlist": watchlist,
        "recentReports": recent_reports,
    }


def mock_asset_detail(ticker: str) -> dict:
    info = get_asset_info(ticker)
    price = round(info["base_price"] * (1 + random.uniform(-0.02, 0.02)), 2)
    change = round(random.uniform(-4, 4), 2)
    return {
        "ticker": ticker.upper(),
        "name": info["name"],
        "sector": info["sector"],
        "price": price,
        "change": change,
        "changePercent": round(change / price * 100, 2),
        "volume": random.randint(20_000_000, 80_000_000),
        "marketCap": info["mcap"],
        "signal": random.choice(["bullish", "bearish", "neutral"]),
        "signalScore": round(random.uniform(40, 85), 1),
        "priceHistory": _generate_price_history(info["base_price"]),
    }


def mock_technicals(ticker: str) -> dict:
    info = get_asset_info(ticker)
    base = info["base_price"]

    rsi_val = round(random.uniform(30, 70), 2)
    rsi_signal = "bullish" if rsi_val < 40 else ("bearish" if rsi_val > 60 else "neutral")

    macd_val = round(random.uniform(-2, 2), 4)
    macd_signal_val = round(macd_val + random.uniform(-0.5, 0.5), 4)

    atr_val = round(base * random.uniform(0.01, 0.03), 2)
    vol_val = round(random.uniform(15, 35), 2)

    # EMA values anchored to the asset's base price
    ema_20 = round(base * random.uniform(0.96, 1.02), 2)
    ema_50 = round(base * random.uniform(0.93, 1.00), 2)
    ema_signal = "bullish" if base > ema_20 else "bearish"

    indicators = [
        {"name": "RSI (14)", "value": rsi_val, "signal": rsi_signal, "description": f"Relative Strength Index at {rsi_val:.1f}. {'Oversold territory.' if rsi_val < 35 else 'Overbought territory.' if rsi_val > 65 else 'Neutral zone.'}"},
        {"name": "EMA (20)", "value": ema_20, "signal": ema_signal, "description": f"20-day EMA at ${ema_20:.2f}. {'Short-term momentum positive.' if ema_signal == 'bullish' else 'Short-term momentum negative.'}"},
        {"name": "EMA (50)", "value": ema_50, "signal": ema_signal, "description": f"50-day EMA at ${ema_50:.2f}. {'Medium-term trend intact.' if ema_signal == 'bullish' else 'Medium-term trend weakening.'}"},
        {"name": "MACD", "value": macd_val, "signal": "bullish" if macd_val > macd_signal_val else "bearish", "description": f"MACD {'above' if macd_val > macd_signal_val else 'below'} signal line. {'Bullish momentum.' if macd_val > macd_signal_val else 'Bearish momentum.'}"},
        {"name": "ATR (14)", "value": atr_val, "signal": "neutral", "description": f"Average True Range of ${atr_val:.2f}. {'Elevated' if atr_val > base * 0.025 else 'Normal'} volatility."},
        {"name": "Volatility", "value": vol_val, "signal": "neutral" if vol_val < 25 else "bearish", "description": f"Annualized volatility at {vol_val:.1f}%. {'Within normal range.' if vol_val < 25 else 'Above average.'}"},
    ]

    return {
        "ticker": ticker.upper(),
        "indicators": indicators,
        "ema": [{"period": 20, "value": ema_20}, {"period": 50, "value": ema_50}],
        "rsi": rsi_val,
        "macd": {"macd": macd_val, "signal": macd_signal_val, "histogram": round(macd_val - macd_signal_val, 4)},
        "atr": atr_val,
        "volatility": vol_val,
    }


def mock_forecast(ticker: str) -> dict:
    base_prob = random.uniform(0.45, 0.72)
    direction = "up" if base_prob > 0.5 else "down"
    expected_ret = round(random.uniform(-2, 3), 2)

    models = [
        {
            "modelName": "Baseline (LogReg)",
            "status": "live",
            "directionProbability": round(base_prob, 3),
            "predictedDirection": direction,
            "expectedReturn": expected_ret,
            "confidence": round(random.uniform(0.55, 0.75), 3),
            "explanation": "Logistic regression on 30-day technical features. Signal based on RSI, MACD crossover, and volume trends.",
        },
        {
            "modelName": "LSTM Sequence",
            "status": "simulated",
            "directionProbability": round(base_prob + random.uniform(-0.05, 0.05), 3),
            "predictedDirection": direction,
            "expectedReturn": round(expected_ret + random.uniform(-0.5, 0.5), 2),
            "confidence": round(random.uniform(0.50, 0.70), 3),
            "explanation": "Simulated LSTM on 60-day price sequences. Placeholder until PyTorch model is trained.",
        },
        {
            "modelName": "TFT (Temporal)",
            "status": "coming_soon",
            "directionProbability": 0.5,
            "predictedDirection": "up",
            "expectedReturn": 0.0,
            "confidence": 0.0,
            "explanation": "Temporal Fusion Transformer. Architecture designed but awaiting training infrastructure.",
        },
        {
            "modelName": "Ensemble",
            "status": "coming_soon",
            "directionProbability": 0.5,
            "predictedDirection": "up",
            "expectedReturn": 0.0,
            "confidence": 0.0,
            "explanation": "Weighted ensemble of all models. Will be activated when multiple models are live.",
        },
    ]

    bullish = [
        "RSI recovering from oversold territory",
        "MACD bullish crossover forming",
        "Price holding above 50-day EMA",
        "Volume increasing on up days",
        "Positive earnings revision trend",
    ]
    bearish = [
        "Elevated macro uncertainty (rate expectations)",
        "Sector rotation away from growth names",
        "ATR expanding suggesting increasing volatility",
        "Weakening breadth in related names",
    ]

    random.shuffle(bullish)
    random.shuffle(bearish)

    info = get_asset_info(ticker)
    return {
        "ticker": ticker.upper(),
        "models": models,
        "bullishFactors": bullish[:random.randint(3, 5)],
        "bearishFactors": bearish[:random.randint(2, 4)],
        "riskLevel": random.choice(["low", "medium", "high"]),
        "aiSummary": f"Based on our baseline model analysis, {info['name']} ({ticker.upper()}) shows a {direction}ward directional bias with {round(base_prob * 100, 1)}% probability. The expected short-term return is {expected_ret:+.2f}%. Key technical drivers include RSI momentum and MACD signal alignment. Risk remains {'elevated' if random.random() > 0.5 else 'moderate'} given current market conditions.",
    }


def mock_report(ticker: str) -> dict:
    info = get_asset_info(ticker)
    rating = random.choice(["Strong Buy", "Buy", "Hold", "Sell"])
    confidence = round(random.uniform(0.55, 0.85), 2)
    now = datetime.now().isoformat()

    return {
        "ticker": ticker.upper(),
        "name": info["name"],
        "generatedAt": now,
        "rating": rating,
        "confidenceScore": confidence,
        "sections": [],
        "executiveSummary": f"{info['name']} presents a {rating.lower()} opportunity based on our multi-factor analysis. The stock trades at ${info['base_price']:.2f} with {info['sector']} sector tailwinds. Our baseline model suggests a directional probability of {round(random.uniform(52, 72), 1)}% for upward movement over the next 5 trading days. Key drivers include technical momentum alignment and constructive fundamental positioning.",
        "technicalView": f"Technical analysis reveals a constructive setup for {ticker.upper()}. The 20-day EMA is trending above the 50-day EMA, confirming medium-term bullish momentum. RSI sits at {round(random.uniform(40, 65), 1)}, indicating room for further upside before reaching overbought conditions. MACD histogram is positive and expanding, supporting the bullish thesis. ATR-based volatility is within normal historical ranges, suggesting orderly price action.",
        "fundamentalSnapshot": f"{info['name']} reported solid fundamentals in the most recent quarter. Revenue growth continues at a healthy pace with improving margin trends. The company's balance sheet remains strong with manageable debt levels. Free cash flow generation supports ongoing capital return programs. Sector positioning in {info['sector']} provides both cyclical tailwinds and structural growth opportunities.",
        "macroContext": "The current macro regime is characterized by moderating inflation (CPI trending toward 3%), stable employment markets, and a Federal Reserve approaching the end of its tightening cycle. The 10Y Treasury yield at ~4.3% creates a competitive discount rate environment. GDP growth remains resilient at 2.8%, supporting corporate earnings. Key risk: timing of rate cuts and geopolitical disruptions.",
        "forecastView": f"Our baseline logistic regression model forecasts a {round(random.uniform(52, 68), 1)}% probability of positive returns over the next trading day. The 5-day expected return range is {round(random.uniform(-1.5, 3.0), 2):+.2f}% based on current feature inputs. Bull scenario: strong sector rotation and positive catalyst drive 3-5% upside. Base case: gradual appreciation in line with market. Bear scenario: macro deterioration or company-specific headwind causes 2-4% pullback.",
        "bullCase": f"Multiple catalysts support upside for {ticker.upper()}: (1) Strong product cycle momentum, (2) Expanding market share in key segments, (3) Favorable technical setup with breakout potential above resistance, (4) Constructive institutional positioning and fund flows, (5) Potential for positive earnings revisions ahead of next report.",
        "bearCase": f"Key risks to monitor: (1) Macro tightening could compress multiples further, (2) Competitive pressures in core markets, (3) Supply chain or execution risks, (4) Regulatory overhang in {info['sector']} sector, (5) Valuation premium relative to peers creates downside vulnerability if growth decelerates.",
        "risksCatalysts": f"Near-term catalysts: Upcoming earnings report, product announcements, sector conferences. Risk factors: Interest rate sensitivity, currency headwinds for international revenue, regulatory developments. The risk/reward profile is {'favorable' if rating in ['Strong Buy', 'Buy'] else 'balanced' if rating == 'Hold' else 'unfavorable'} at current levels.",
    }


def mock_backtest_summary() -> dict:
    """Mock backtest with correct model names and all required fields."""
    rng = random.Random(42)

    def _mock_model(name, drift, vol_s, desc):
        curve = _generate_equity_curve(252)
        ret = (curve[-1]["value"] / 100) - 1
        max_dd = round(rng.uniform(0.05, 0.20), 4)
        sharpe = round(rng.uniform(0.1, 1.2), 2)
        return {
            "modelName": name,
            "accuracy": round(rng.uniform(0.48, 0.58), 3),
            "cumulativeReturn": round(ret, 4),
            "winRate": round(rng.uniform(0.48, 0.56), 4),
            "sharpeRatio": sharpe,
            "maxDrawdown": max_dd,
            "volatility": round(rng.uniform(0.12, 0.25), 4),
            "calmarRatio": round(ret / max_dd, 2) if max_dd > 0 else 0.0,
            "totalTrades": rng.randint(12, 120),
            "description": f"MOCK DATA \u2014 {desc}",
            "insufficientData": False,
            "equityCurve": curve,
        }

    models = [
        _mock_model("RSI Mean Reversion", 0.0004, 0.010, "Buy RSI<30, short RSI>70."),
        _mock_model("MACD Trend Following", 0.0003, 0.011, "MACD histogram crossover with EMA50 filter."),
        _mock_model("Bollinger Squeeze", 0.0005, 0.013, "Breakout from low-volatility squeeze."),
        _mock_model("ATR Volatility Channel", 0.0002, 0.009, "ATR channel breakout with trailing stop."),
        _mock_model("RSI+MACD+Volume", 0.0006, 0.008, "Triple confirmation strategy."),
        _mock_model("Buy & Hold", 0.0003, 0.012, "Passive benchmark, 100% invested."),
    ]
    models.sort(key=lambda x: x["sharpeRatio"], reverse=True)

    return {
        "models": models,
        "benchmarkReturn": next((m["cumulativeReturn"] for m in models if m["modelName"] == "Buy & Hold"), 0.0),
        "period": "2024-01-01 to 2024-12-31 (MOCK)",
        "ticker": "MOCK",
        "dataPoints": 252,
    }


def mock_watchlist() -> dict:
    items = []
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"]
    alloc_base = 100.0 / len(tickers)

    for ticker in tickers:
        info = get_asset_info(ticker)
        items.append({
            "ticker": ticker,
            "name": info["name"],
            "price": round(info["base_price"] * (1 + random.uniform(-0.02, 0.02)), 2),
            "change1d": round(random.uniform(-3, 3), 2),
            "change5d": round(random.uniform(-5, 5), 2),
            "change1m": round(random.uniform(-8, 10), 2),
            "signalScore": round(random.uniform(30, 90), 1),
            "confidence": round(random.uniform(50, 85), 1),
            "riskScore": round(random.uniform(20, 75), 1),
            "alert": random.choice([None, None, "breakout", "warning", "info"]),
            "allocation": round(alloc_base + random.uniform(-3, 3), 1),
        })

    total_alloc = sum(i["allocation"] for i in items)
    for i in items:
        i["allocation"] = round(i["allocation"] / total_alloc * 100, 1)

    total_val = sum(i["price"] * 100 for i in items)
    daily_change = round(random.uniform(-500, 800), 2)

    return {
        "items": items,
        "summary": {
            "totalValue": round(total_val, 2),
            "dailyChange": daily_change,
            "dailyChangePercent": round(daily_change / total_val * 100, 2),
            "topSignal": max(items, key=lambda x: x["signalScore"])["ticker"],
            "riskLevel": random.choice(["low", "medium", "high"]),
        },
    }
