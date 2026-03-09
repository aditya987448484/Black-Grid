"""Asset detail, technicals, forecast, and report routes."""

from __future__ import annotations

from fastapi import APIRouter
from app.schemas.asset import AssetDetailResponse, AssetTechnicalResponse, AssetForecastResponse
from app.schemas.report import AnalystReportResponse
from app.services.mock_data import mock_asset_detail, mock_technicals, mock_forecast, mock_report
from app.services.market_data import fetch_price_history, fetch_quote, fetch_quote_and_history
from app.services.macro_data import fetch_macro_indicators
from app.services.forecast_service import get_forecast
from app.services.sec_data import fetch_company_facts
from app.services.fundamental_service import build_fundamental_summary
from app.indicators.technical import compute_all_indicators
from app.reports.generator import generate_report

router = APIRouter(prefix="/api/asset", tags=["asset"])


@router.get("/{ticker}", response_model=AssetDetailResponse)
async def asset_detail(ticker: str):
    ticker = ticker.upper()
    print(f"[route:asset] Fetching detail for {ticker}")

    # Start with mock scaffold (provides name, sector, marketCap, signal etc.)
    data = mock_asset_detail(ticker)

    # Fetch live quote + history together (minimizes API calls, avoids rate limits)
    quote, df = await fetch_quote_and_history(ticker)

    # Overlay live quote onto the response
    if quote:
        data["price"] = quote["price"]
        data["change"] = quote["change"]
        data["changePercent"] = quote["changePercent"]
        if quote.get("volume"):
            data["volume"] = quote["volume"]
        print(f"[route:asset] {ticker} live price: ${quote['price']}")

    # Overlay live history — this is the chart data
    if df is not None and len(df) > 0:
        history = df.to_dict("records")
        for row in history:
            row["date"] = str(row["date"])[:10]
            row["volume"] = int(row["volume"])
        data["priceHistory"] = history
        print(f"[route:asset] {ticker} live chart: {len(history)} points, {history[0]['date']} to {history[-1]['date']}")

        # CONSISTENCY CHECK: if we have live history but the quote failed,
        # set price from the last history bar so header and chart agree
        if not quote:
            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else last
            data["price"] = round(float(last["close"]), 2)
            data["change"] = round(float(last["close"] - prev["close"]), 2)
            data["changePercent"] = round(float((last["close"] - prev["close"]) / prev["close"] * 100), 2)
            data["volume"] = int(last["volume"])
            print(f"[route:asset] {ticker} price derived from chart: ${data['price']}")
    else:
        # No live history — mock history is already in `data` from mock_asset_detail,
        # but it uses random walks from an old base_price. Anchor it to the live price.
        if quote:
            _anchor_mock_history(data, quote["price"])
            print(f"[route:asset] {ticker} mock history anchored to live price ${quote['price']}")

    return data


def _anchor_mock_history(data: dict, live_price: float):
    """Adjust mock price history so the last close matches the live price."""
    history = data.get("priceHistory", [])
    if not history:
        return
    mock_last_close = history[-1]["close"]
    if mock_last_close == 0:
        return
    ratio = live_price / mock_last_close
    for row in history:
        row["open"] = round(row["open"] * ratio, 2)
        row["high"] = round(row["high"] * ratio, 2)
        row["low"] = round(row["low"] * ratio, 2)
        row["close"] = round(row["close"] * ratio, 2)


@router.get("/{ticker}/technicals", response_model=AssetTechnicalResponse)
async def asset_technicals(ticker: str):
    ticker = ticker.upper()
    print(f"[route:technicals] Fetching technicals for {ticker}")

    # Use compact (100 days) — sufficient for all indicators, avoids AV premium wall
    df = await fetch_price_history(ticker, outputsize="compact")
    if df is not None and len(df) >= 60:
        try:
            ind = compute_all_indicators(df)
            print(f"[route:technicals] {ticker} live indicators: RSI={ind['rsi']:.1f}")
            return {
                "ticker": ticker,
                "indicators": [
                    {"name": "RSI (14)", "value": ind["rsi"], "signal": ind["rsi_signal"],
                     "description": f"Relative Strength Index at {ind['rsi']:.1f}."},
                    {"name": "EMA (20)", "value": ind["ema_20"], "signal": ind["ema_signal"],
                     "description": f"20-day EMA at ${ind['ema_20']:.2f}."},
                    {"name": "EMA (50)", "value": ind["ema_50"], "signal": ind["ema_signal"],
                     "description": f"50-day EMA at ${ind['ema_50']:.2f}."},
                    {"name": "MACD", "value": ind["macd_val"], "signal": ind["macd_signal"],
                     "description": f"MACD at {ind['macd_val']:.4f}. {'Bullish' if ind['macd_signal'] == 'bullish' else 'Bearish'} momentum."},
                    {"name": "ATR (14)", "value": ind["atr"], "signal": "neutral",
                     "description": f"Average True Range of ${ind['atr']:.2f}."},
                    {"name": "Volatility", "value": ind["volatility"], "signal": "neutral" if ind["volatility"] < 25 else "bearish",
                     "description": f"Annualized volatility at {ind['volatility']:.1f}%."},
                ],
                "ema": [{"period": 20, "value": ind["ema_20"]}, {"period": 50, "value": ind["ema_50"]}],
                "rsi": ind["rsi"],
                "macd": {"macd": ind["macd_val"], "signal": ind["macd_signal_val"], "histogram": ind["macd_histogram"]},
                "atr": ind["atr"],
                "volatility": ind["volatility"],
            }
        except Exception as e:
            print(f"[route:technicals] Live technicals failed for {ticker}: {e}")

    print(f"[route:technicals] {ticker} falling back to mock")
    return mock_technicals(ticker)


@router.get("/{ticker}/forecast", response_model=AssetForecastResponse)
async def asset_forecast(ticker: str):
    return await get_forecast(ticker.upper())


@router.get("/{ticker}/report", response_model=AnalystReportResponse)
async def asset_report(ticker: str):
    ticker = ticker.upper()

    try:
        forecast = await get_forecast(ticker)

        technicals_dict = None
        df = await fetch_price_history(ticker, outputsize="compact")
        if df is not None and len(df) >= 60:
            try:
                technicals_dict = compute_all_indicators(df)
            except Exception:
                pass

        sec_data = await fetch_company_facts(ticker)
        fundamentals = build_fundamental_summary(sec_data, ticker)
        macro = await fetch_macro_indicators()

        report = await generate_report(
            ticker=ticker,
            technicals=technicals_dict,
            forecast=forecast,
            macro=macro,
            fundamentals=fundamentals,
        )
        return report
    except Exception as e:
        print(f"[route:report] Report generation failed for {ticker}: {e}")
        return mock_report(ticker)
