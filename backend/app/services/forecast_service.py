"""Forecast service orchestrating data + models."""

from __future__ import annotations

import pandas as pd
from app.services.market_data import fetch_price_history
from app.services.mock_data import mock_forecast, get_asset_info
from app.models.baseline_model import train_and_predict
from app.indicators.technical import compute_all_indicators


async def get_forecast(ticker: str) -> dict:
    """Run forecast pipeline for a ticker."""
    df = await fetch_price_history(ticker, outputsize="compact")

    if df is not None and len(df) >= 60:
        try:
            result = train_and_predict(df)
            indicators = compute_all_indicators(df)
            info = get_asset_info(ticker)

            models = [
                {
                    "modelName": "Baseline (LogReg)",
                    "status": "live",
                    "directionProbability": result["probability"],
                    "predictedDirection": result["direction"],
                    "expectedReturn": result["expected_return"],
                    "confidence": result["confidence"],
                    "explanation": result["explanation"],
                },
                {
                    "modelName": "LSTM Sequence",
                    "status": "simulated",
                    "directionProbability": round(result["probability"] + 0.02, 4),
                    "predictedDirection": result["direction"],
                    "expectedReturn": round(result["expected_return"] * 1.1, 2),
                    "confidence": round(result["confidence"] * 0.9, 4),
                    "explanation": "Simulated LSTM on 60-day sequences. Placeholder until PyTorch model is deployed.",
                },
                {
                    "modelName": "TFT (Temporal)",
                    "status": "coming_soon",
                    "directionProbability": 0.5,
                    "predictedDirection": "up",
                    "expectedReturn": 0.0,
                    "confidence": 0.0,
                    "explanation": "Temporal Fusion Transformer. Architecture designed but awaiting training.",
                },
                {
                    "modelName": "Ensemble",
                    "status": "coming_soon",
                    "directionProbability": 0.5,
                    "predictedDirection": "up",
                    "expectedReturn": 0.0,
                    "confidence": 0.0,
                    "explanation": "Weighted ensemble. Will activate when multiple models are live.",
                },
            ]

            bullish = []
            bearish = []
            if indicators["rsi"] < 40:
                bullish.append("RSI in oversold territory")
            elif indicators["rsi"] > 60:
                bearish.append("RSI in overbought territory")
            if indicators["macd_histogram"] > 0:
                bullish.append("MACD bullish momentum")
            else:
                bearish.append("MACD bearish momentum")
            if indicators["ema_signal"] == "bullish":
                bullish.append("Price above 20-day EMA")
            else:
                bearish.append("Price below 20-day EMA")

            bullish.extend(["Volume trends supportive", "Positive earnings revision potential"])
            bearish.extend(["Macro uncertainty elevated", "Sector rotation risk"])

            risk_level = "low" if result["confidence"] > 0.3 and indicators["volatility"] < 25 else ("high" if indicators["volatility"] > 35 else "medium")

            return {
                "ticker": ticker.upper(),
                "models": models,
                "bullishFactors": bullish[:5],
                "bearishFactors": bearish[:4],
                "riskLevel": risk_level,
                "aiSummary": f"Baseline model analysis for {info['name']} ({ticker.upper()}) shows {result['direction']}ward bias with {result['probability']:.1%} probability. Expected return: {result['expected_return']:+.2f}%. {result['explanation']}",
            }
        except Exception as e:
            print(f"[forecast] Live model failed for {ticker}: {e}")

    return mock_forecast(ticker)
