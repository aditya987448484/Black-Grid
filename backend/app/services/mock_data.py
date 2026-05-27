"""
Mock data service for financial dashboard
Generates realistic financial data for testing and development
All returned data matches API schema definitions
"""

from datetime import datetime, timedelta
import random
from typing import Dict, List, Any, Optional


# ============================================================================
# HELPER FUNCTIONS - Price & Market Data
# ============================================================================

def _generate_realistic_price(base_price: float, volatility: float = 0.02) -> float:
    """Generate realistic price movement"""
    change = random.uniform(-volatility, volatility)
    return round(base_price * (1 + change), 2)


def _generate_ohlcv_candles(ticker: str, num_candles: int = 20, start_price: float = None) -> List[Dict[str, Any]]:
    """Generate realistic OHLCV candle data"""
    if start_price is None:
        price_map = {
            "AAPL": 189.45, "MSFT": 380.25, "NVDA": 875.50, "GOOGL": 142.30,
            "AMZN": 168.75, "META": 485.20, "TSLA": 245.80
        }
        start_price = price_map.get(ticker, 150.00)
    
    candles = []
    current_price = start_price
    base_date = datetime.utcnow() - timedelta(days=num_candles)
    
    for i in range(num_candles):
        date = base_date + timedelta(days=i)
        
        # Simulate realistic daily movement
        daily_return = random.uniform(-0.03, 0.03)
        open_price = current_price
        close_price = current_price * (1 + daily_return)
        high_price = max(open_price, close_price) * random.uniform(1.002, 1.008)
        low_price = min(open_price, close_price) * random.uniform(0.992, 0.998)
        volume = random.randint(40000000, 80000000)
        
        candles.append({
            "date": date.isoformat(),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": volume
        })
        
        current_price = close_price
    
    return candles


def _generate_technical_indicators(close_prices: List[float]) -> Dict[str, float]:
    """Generate realistic technical indicators"""
    if len(close_prices) < 50:
        close_prices = close_prices + [close_prices[-1]] * (50 - len(close_prices))
    
    # SMA 20 and 50
    sma_20 = round(sum(close_prices[-20:]) / 20, 2)
    sma_50 = round(sum(close_prices[-50:]) / 50, 2)
    
    # EMA 12 (simplified)
    ema_12 = round(close_prices[-1] * 0.99 + sma_20 * 0.01, 2)
    
    # RSI 14 (simplified - between 30-70 for normal, extremes for overbought/oversold)
    price_change = close_prices[-1] - close_prices[-2]
    rsi = min(85, max(30, 50 + (price_change / close_prices[-2] * 100)))
    rsi = round(rsi, 1)
    
    # MACD (simplified)
    ema_12_val = close_prices[-1]
    ema_26_val = sum(close_prices[-26:]) / 26
    macd = round(ema_12_val - ema_26_val, 2)
    macd_signal = round(macd * 0.9, 2)
    macd_histogram = round(macd - macd_signal, 2)
    
    return {
        "sma_20": sma_20,
        "sma_50": sma_50,
        "ema_12": ema_12,
        "rsi_14": rsi,
        "macd": macd,
        "macd_signal": macd_signal,
        "macd_histogram": macd_histogram
    }


# ============================================================================
# MARKET OVERVIEW
# ============================================================================

def get_mock_market_overview() -> Dict[str, Any]:
    """Generate mock market overview data"""
    tickers = ["SPY", "QQQ", "IWM", "VIX"]
    data = []
    
    for ticker in tickers:
        base_prices = {
            "SPY": 450.00,
            "QQQ": 380.50,
            "IWM": 195.30,
            "VIX": 18.75
        }
        price = base_prices.get(ticker, 100.0)
        change_pct = random.uniform(-2, 3)
        change = round(price * change_pct / 100, 2)
        
        data.append({
            "symbol": ticker,
            "price": round(price + change, 2),
            "change": change,
            "change_percent": round(change_pct, 4),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    return {
        "status": "success",
        "data": data,
        "market_time": datetime.utcnow().isoformat(),
        "total_results": len(data)
    }


# ============================================================================
# ASSET DETAIL
# ============================================================================

def get_mock_asset_detail(ticker: str = "AAPL") -> Dict[str, Any]:
    """Generate mock asset detail data"""
    asset_data = {
        "AAPL": {
            "name": "Apple Inc.",
            "price": 189.45,
            "market_cap": 2950000000000,
            "pe_ratio": 28.4,
            "dividend_yield": 0.0042,
            "fifty_two_week_high": 199.62,
            "fifty_two_week_low": 164.08,
            "avg_volume": 52340000
        },
        "MSFT": {
            "name": "Microsoft Corporation",
            "price": 380.25,
            "market_cap": 2850000000000,
            "pe_ratio": 32.1,
            "dividend_yield": 0.0023,
            "fifty_two_week_high": 420.88,
            "fifty_two_week_low": 310.45,
            "avg_volume": 18920000
        },
        "NVDA": {
            "name": "NVIDIA Corporation",
            "price": 875.50,
            "market_cap": 2150000000000,
            "pe_ratio": 65.4,
            "dividend_yield": 0.0005,
            "fifty_two_week_high": 950.25,
            "fifty_two_week_low": 520.00,
            "avg_volume": 38450000
        },
        "GOOGL": {
            "name": "Alphabet Inc.",
            "price": 142.30,
            "market_cap": 1850000000000,
            "pe_ratio": 21.5,
            "dividend_yield": 0.0,
            "fifty_two_week_high": 156.75,
            "fifty_two_week_low": 125.30,
            "avg_volume": 28920000
        }
    }
    
    asset = asset_data.get(ticker, asset_data["AAPL"])
    
    return {
        "status": "success",
        "data": {
            "ticker": ticker,
            "name": asset["name"],
            "asset_type": "stock",
            "price": asset["price"],
            "market_cap": asset["market_cap"],
            "pe_ratio": asset["pe_ratio"],
            "dividend_yield": asset["dividend_yield"],
            "fifty_two_week_high": asset["fifty_two_week_high"],
            "fifty_two_week_low": asset["fifty_two_week_low"],
            "avg_volume": asset["avg_volume"],
            "timestamp": datetime.utcnow().isoformat()
        },
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# TECHNICAL DATA
# ============================================================================

def get_mock_technical_data(ticker: str = "AAPL", num_candles: int = 20) -> Dict[str, Any]:
    """Generate mock technical analysis data"""
    candles = _generate_ohlcv_candles(ticker, num_candles)
    close_prices = [c["close"] for c in candles]
    indicators = _generate_technical_indicators(close_prices)
    
    return {
        "status": "success",
        "ticker": ticker,
        "data": candles,
        "indicators": indicators,
        "updated_at": datetime.utcnow().isoformat()
    }


# ============================================================================
# FORECAST DATA
# ============================================================================

def get_mock_forecast(ticker: str = "AAPL", horizon_days: int = 30) -> Dict[str, Any]:
    """Generate mock forecast response with all 4 models"""
    price_map = {
        "AAPL": 189.45, "MSFT": 380.25, "NVDA": 875.50, "GOOGL": 142.30,
        "AMZN": 168.75, "META": 485.20, "TSLA": 245.80
    }
    current_price = price_map.get(ticker, 150.00)
    
    # Baseline Model
    baseline_return = random.uniform(-2.0, 3.5)
    baseline_signal = "BUY" if baseline_return > 1.5 else ("SELL" if baseline_return < -1.5 else "HOLD")
    baseline_confidence = min(75, max(50, 50 + abs(baseline_return)))
    
    # LSTM Model
    lstm_return = random.uniform(-1.0, 6.5)
    lstm_signal = "BUY" if lstm_return > 2.0 else ("SELL" if lstm_return < -1.0 else "HOLD")
    lstm_confidence = random.uniform(60, 85)
    
    # TFT Model
    tft_return = random.uniform(0.5, 7.5)
    tft_signal = "BUY" if tft_return > 2.5 else ("SELL" if tft_return < 0.5 else "HOLD")
    tft_confidence = random.uniform(65, 90)
    
    # Ensemble Model
    ensemble_return = (baseline_return * 0.10 + lstm_return * 0.35 + tft_return * 0.40 + random.uniform(1, 5) * 0.15)
    ensemble_signal = "BUY" if ensemble_return > 2.0 else ("SELL" if ensemble_return < -0.5 else "HOLD")
    ensemble_confidence = random.uniform(70, 88)
    
    models = [
        {
            "model_name": "Baseline",
            "model_type": "baseline",
            "signal": baseline_signal,
            "expected_return": round(baseline_return, 2),
            "confidence": round(baseline_confidence, 1),
            "status": "ready",
            "accuracy": 52.3,
            "last_updated": datetime.utcnow().isoformat(),
            "description": "Simple momentum indicator based on recent price action"
        },
        {
            "model_name": "LSTM/GRU",
            "model_type": "lstm",
            "signal": lstm_signal,
            "expected_return": round(lstm_return, 2),
            "confidence": round(lstm_confidence, 1),
            "status": "ready",
            "accuracy": 61.2,
            "last_updated": datetime.utcnow().isoformat(),
            "description": "2-layer LSTM with attention mechanism for sequence learning"
        },
        {
            "model_name": "TFT",
            "model_type": "tft",
            "signal": tft_signal,
            "expected_return": round(tft_return, 2),
            "confidence": round(tft_confidence, 1),
            "status": "ready",
            "accuracy": 64.8,
            "last_updated": datetime.utcnow().isoformat(),
            "description": "Temporal Fusion Transformer with multi-head attention"
        },
        {
            "model_name": "Ensemble",
            "model_type": "ensemble",
            "signal": ensemble_signal,
            "expected_return": round(ensemble_return, 2),
            "confidence": round(ensemble_confidence, 1),
            "status": "ready",
            "accuracy": 67.1,
            "last_updated": datetime.utcnow().isoformat(),
            "description": "Weighted ensemble combining TFT (40%), LSTM (35%), and others"
        }
    ]
    
    # Calculate consensus
    buy_votes = sum(1 for m in models if m["signal"] == "BUY")
    consensus_signal = "BUY" if buy_votes >= 2 else ("SELL" if buy_votes == 0 else "HOLD")
    avg_confidence = round(sum(m["confidence"] for m in models) / len(models), 2)
    avg_return = round(sum(m["expected_return"] for m in models) / len(models), 2)
    
    return {
        "status": "success",
        "ticker": ticker,
        "current_price": current_price,
        "horizon_days": horizon_days,
        "models": models,
        "consensus": {
            "consensus_signal": consensus_signal,
            "consensus_probability": round(buy_votes / len(models) * 100, 1),
            "average_confidence": avg_confidence,
            "average_return": avg_return,
            "best_model": "Ensemble",
            "most_optimistic": "TFT",
            "most_conservative": "Baseline",
            "model_agreement": "High" if buy_votes >= 3 else ("Medium" if buy_votes >= 2 else "Low")
        },
        "generated_at": datetime.utcnow().isoformat(),
        "next_update": (datetime.utcnow() + timedelta(hours=1)).isoformat()
    }


# ============================================================================
# ANALYST REPORT
# ============================================================================

def get_mock_analyst_report(ticker: str = "AAPL") -> Dict[str, Any]:
    """Generate mock comprehensive analyst report"""
    company_data = {
        "AAPL": {
            "name": "Apple Inc.",
            "price": 189.45,
            "summary": "Apple demonstrates strong fundamentals with robust cash flow generation and expanding services revenue stream providing sustainable competitive advantages in the premium consumer electronics market.",
            "highlight": "Attractive valuation entering 2026 with AI integration driving margin expansion and installed base monetization"
        },
        "MSFT": {
            "name": "Microsoft Corporation",
            "price": 380.25,
            "summary": "Microsoft continues to benefit from enterprise cloud adoption and AI integration across its product suite, with strong recurring revenue from Office 365 and Azure driving predictable growth.",
            "highlight": "AI/ML capabilities positioning Microsoft as a dominant player in enterprise digital transformation"
        }
    }
    
    company = company_data.get(ticker, company_data["AAPL"])
    
    return {
        "status": "success",
        "data": {
            "ticker": ticker,
            "company_name": company["name"],
            "report_date": datetime.utcnow().isoformat(),
            "current_price": company["price"],
            "executive_summary": company["summary"],
            "investment_highlight": company["highlight"],
            "technical_view": {
                "trend": "Uptrend",
                "key_levels": [185.50, 195.00, 205.00],
                "signal_strength": round(random.uniform(65, 85), 1),
                "momentum": "Strong",
                "ma_alignment": "Bullish (20>50>200 SMA)",
                "summary": "Break above daily resistance confirms uptrend continuation with strong momentum support"
            },
            "fundamental_snapshot": {
                "eps": round(random.uniform(5.5, 7.2), 2),
                "revenue_growth": round(random.uniform(6.0, 12.0), 1),
                "profit_margin": round(random.uniform(25.0, 30.0), 1),
                "roe": round(random.uniform(80.0, 95.0), 1),
                "debt_to_equity": round(random.uniform(1.5, 2.2), 1),
                "valuation_assessment": "Fairly Valued",
                "quality_score": round(random.uniform(85.0, 95.0), 1)
            },
            "macro_context": {
                "sector_performance": "Outperforming",
                "industry_tailwinds": [
                    "Growing enterprise cloud adoption",
                    "AI/ML integration acceleration",
                    "Services expansion opportunities"
                ],
                "macro_headwinds": [
                    "Potential macroeconomic slowdown",
                    "Increasing regulatory scrutiny",
                    "Supply chain normalization"
                ],
                "correlation_market": 0.65,
                "macro_outlook": "Positive"
            },
            "bull_case": {
                "thesis": "Strong cash flow generation combined with AI integration provides sustainable growth runway with margin expansion potential",
                "key_catalysts": [
                    "Q1 2026 earnings beat expectations",
                    "AI product launch acceleration",
                    "Services revenue growth exceeds guidance"
                ],
                "timeline": "6-12 months",
                "probability": round(random.uniform(65, 75), 1)
            },
            "bear_case": {
                "thesis": "Valuation-induced pullback amid macro uncertainty and competitive pressure in AI market",
                "key_catalysts": [
                    "Disappointing guidance on cloud growth",
                    "Regulatory action on market practices",
                    "Macro recession concerns escalate"
                ],
                "timeline": "3-6 months",
                "probability": round(random.uniform(20, 30), 1)
            },
            "risks": [
                {
                    "description": "Geopolitical tensions impacting supply chains",
                    "severity": "Medium",
                    "mitigation": "Diversified manufacturing footprint reduces single-country concentration risk"
                },
                {
                    "description": "Competitive pressure from emerging AI players",
                    "severity": "Medium",
                    "mitigation": "Established ecosystem and user base provide sticky competitive moat"
                },
                {
                    "description": "Macroeconomic recession reducing consumer spending",
                    "severity": "High",
                    "mitigation": "Premium positioning and services revenue provide downside protection"
                }
            ],
            "catalysts": [
                {
                    "description": "Quarterly earnings announcements - potential beats/misses",
                    "severity": "High",
                    "mitigation": "Consistent execution track record provides confidence"
                },
                {
                    "description": "Major product announcements and AI integration updates",
                    "severity": "High",
                    "mitigation": "Strong product pipeline and innovation capabilities"
                }
            ],
            "final_rating": {
                "recommendation": "BUY",
                "target_price": round(company["price"] * random.uniform(1.10, 1.18), 2),
                "price_upside": round(random.uniform(10.0, 18.0), 1),
                "conviction": "High",
                "rationale": "Compelling valuation with strong fundamentals, positive technicals, and multiple growth catalysts"
            },
            "confidence_score": round(random.uniform(82.0, 91.0), 1)
        },
        "generated_at": datetime.utcnow().isoformat()
    }


# ============================================================================
# BACKTEST SUMMARY
# ============================================================================

def get_mock_backtest_summary(ticker: str = "AAPL", num_results: int = 3) -> Dict[str, Any]:
    """Generate mock backtest results"""
    strategies = ["Moving Average Crossover", "RSI Mean Reversion", "Momentum Breakout", "Bollinger Band"]
    strategy_descriptions = [
        "20/50-day SMA crossover strategy. Enters long when SMA-20 crosses above SMA-50; exits on reversal.",
        "RSI mean-reversion: buy oversold (<30), sell overbought (>70). Hold period: 5 trading days.",
        "Breakout above 20-day high with volume confirmation. Trailing stop at 2× ATR.",
        "Buy at lower Bollinger Band touch; exit at midline. Requires RSI < 40 for entry confirmation.",
    ]

    results = []
    for i in range(num_results):
        total_return = round(random.uniform(5.0, 45.0), 2)
        trades = random.randint(15, 60)
        wins = random.randint(int(trades * 0.4), int(trades * 0.65))

        results.append({
            "backtest_id": f"bt_{ticker}_{int(datetime.utcnow().timestamp())}_{i}",
            "strategy": strategies[i % len(strategies)],
            "strategy_description": strategy_descriptions[i % len(strategy_descriptions)],
            "ticker": ticker,
            "start_date": (datetime.utcnow() - timedelta(days=750)).strftime("%Y-%m-%d"),
            "end_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "initial_capital": 100000.0,
            "final_value": round(100000.0 * (1 + total_return / 100), 2),
            "total_return": total_return,
            "annual_return": round(total_return / 2.0, 2),  # ~2 year period
            "sharpe_ratio": round(random.uniform(0.8, 2.0), 2),
            "sortino_ratio": round(random.uniform(1.2, 3.0), 2),
            "max_drawdown": round(random.uniform(-15.0, -5.0), 2),
            "volatility": round(random.uniform(12.0, 22.0), 2),
            "trades_count": trades,
            "win_rate": round(wins / trades * 100, 1),
            "direction_accuracy": None,  # not computed by non-ML mock strategies
            "status": "completed",
            "created_at": datetime.utcnow().isoformat()
        })

    return {
        "status": "success",
        "data": results,
        "total_results": len(results),
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# WATCHLIST
# ============================================================================

def get_mock_watchlist_items() -> Dict[str, Any]:
    """Generate mock watchlist items"""
    tickers = [
        ("AAPL", "Apple Inc.", 189.45),
        ("MSFT", "Microsoft Corporation", 380.25),
        ("NVDA", "NVIDIA Corporation", 875.50),
        ("GOOGL", "Alphabet Inc.", 142.30),
        ("AMZN", "Amazon.com Inc.", 168.75),
        ("META", "Meta Platforms Inc.", 485.20),
        ("TSLA", "Tesla Inc.", 245.80)
    ]
    
    items = []
    for ticker, name, price in tickers[:random.randint(3, 5)]:
        change = round(random.uniform(-3.0, 4.0), 2)
        items.append({
            "ticker": ticker,
            "name": name,
            "current_price": round(price + (price * change / 100), 2),
            "change_24h": change,
            "added_date": (datetime.utcnow() - timedelta(days=random.randint(1, 30))).isoformat()
        })
    
    return {
        "status": "success",
        "data": items,
        "total_items": len(items),
        "updated_at": datetime.utcnow().isoformat()
    }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_all_mock_data() -> Dict[str, Any]:
    """Get all mock data for testing the entire system"""
    return {
        "market_overview": get_mock_market_overview(),
        "asset_detail": get_mock_asset_detail("AAPL"),
        "technical_data": get_mock_technical_data("AAPL"),
        "forecast": get_mock_forecast("AAPL"),
        "analyst_report": get_mock_analyst_report("AAPL"),
        "backtest_summary": get_mock_backtest_summary("AAPL"),
        "watchlist": get_mock_watchlist_items()
    }
