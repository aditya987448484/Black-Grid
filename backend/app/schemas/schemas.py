"""
Pydantic schemas for API request/response validation
Organized by domain for clarity and maintainability

Response Structure:
- All API responses include a 'status' field ('success' or 'error')
- Responses are wrapped with optional 'timestamp' and 'message' fields
- Nested data structures use domain-specific models
- All enums use string values for JSON serialization

Available Response Types:
- MarketOverviewResponse: List of market metrics with index data
- AssetDetailResponse: Individual asset fundamental data
- AssetTechnicalResponse: Historical OHLCV data with technical indicators
- AssetForecastResponse: ML model predictions with consensus metrics
- AnalystReportResponse: Comprehensive institutional research report
- BacktestSummaryResponse: Strategy backtest results and metrics
- WatchlistResponse: User watchlist with current metrics
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class RecommendationType(str, Enum):
    """Buy/Hold/Sell recommendations"""
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"


class AssetType(str, Enum):
    """Asset types supported by the platform"""
    STOCK = "stock"
    ETF = "etf"
    BOND = "bond"
    COMMODITY = "commodity"


# ============================================================================
# RESPONSE WRAPPERS
# ============================================================================

class APIResponse(BaseModel):
    """Standard API response wrapper"""
    status: str = Field(..., description="Response status: success or error")
    message: str = Field(default="", description="Optional message")
    data: Optional[dict] = Field(default=None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class APIErrorResponse(BaseModel):
    """Standard error response"""
    status: str = "error"
    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(default=None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# MARKET DATA SCHEMAS
# ============================================================================

class MarketMetric(BaseModel):
    """Single market metric"""
    symbol: str = Field(..., description="Asset ticker symbol")
    price: float = Field(..., description="Current price")
    change: float = Field(..., description="Absolute price change")
    change_percent: float = Field(..., description="Percentage change")
    timestamp: datetime = Field(..., description="Data timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "price": 189.45,
                "change": 5.12,
                "change_percent": 0.0325,
                "timestamp": "2026-03-05T12:00:00"
            }
        }


class MarketOverviewResponse(BaseModel):
    """Market overview response wrapper"""
    status: str = Field(default="success", description="Response status: success/error")
    data: List[MarketMetric] = Field(..., description="List of market metrics")
    market_time: datetime = Field(default_factory=datetime.utcnow, description="Market time for metrics")
    total_results: int = Field(..., description="Number of results")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "data": [
                    {
                        "symbol": "SPY",
                        "price": 450.00,
                        "change": 5.00,
                        "change_percent": 0.0112
                    }
                ],
                "total_results": 1
            }
        }


# ============================================================================
# ASSET DETAIL SCHEMAS
# ============================================================================

class CandleData(BaseModel):
    """OHLCV candle data"""
    date: datetime = Field(..., description="Candle date")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="Highest price")
    low: float = Field(..., description="Lowest price")
    close: float = Field(..., description="Closing price")
    volume: int = Field(..., description="Trading volume")


class TechnicalIndicators(BaseModel):
    """Technical analysis indicators"""
    sma_20: Optional[float] = Field(None, description="20-period Simple Moving Average")
    sma_50: Optional[float] = Field(None, description="50-period Simple Moving Average")
    ema_12: Optional[float] = Field(None, description="12-period Exponential Moving Average")
    rsi_14: Optional[float] = Field(None, description="Relative Strength Index (14)")
    macd: Optional[float] = Field(None, description="MACD line")
    macd_signal: Optional[float] = Field(None, description="MACD signal line")
    macd_histogram: Optional[float] = Field(None, description="MACD histogram")


class AssetDetail(BaseModel):
    """Detailed asset information"""
    ticker: str = Field(..., description="Ticker symbol")
    name: str = Field(..., description="Company name")
    asset_type: AssetType = Field(..., description="Asset type")
    price: float = Field(..., description="Current price")
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    pe_ratio: Optional[float] = Field(None, description="Price-to-Earnings ratio")
    dividend_yield: Optional[float] = Field(None, description="Dividend yield")
    fifty_two_week_high: Optional[float] = Field(None, description="52-week high")
    fifty_two_week_low: Optional[float] = Field(None, description="52-week low")
    avg_volume: Optional[int] = Field(None, description="Average daily volume")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "asset_type": "stock",
                "price": 189.45,
                "market_cap": 2950000000000,
                "pe_ratio": 28.4,
                "dividend_yield": 0.0042,
                "timestamp": "2026-03-05T12:00:00"
            }
        }


class TechnicalDataResponse(BaseModel):
    """Technical analysis data response with OHLCV candles and indicators"""
    status: str = Field(default="success", description="Response status")
    ticker: str = Field(..., description="Ticker symbol")
    data: List[CandleData] = Field(..., description="OHLCV candle data")
    indicators: Optional[TechnicalIndicators] = Field(None, description="Technical indicators")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "ticker": "AAPL",
                "data": [
                    {
                        "date": "2026-03-03T00:00:00",
                        "open": 185.50,
                        "high": 186.75,
                        "low": 185.25,
                        "close": 186.20,
                        "volume": 52340000
                    },
                    {
                        "date": "2026-03-04T00:00:00",
                        "open": 186.20,
                        "high": 189.80,
                        "low": 186.10,
                        "close": 189.45,
                        "volume": 68920000
                    }
                ],
                "indicators": {
                    "sma_20": 187.30,
                    "sma_50": 185.10,
                    "ema_12": 188.95,
                    "rsi_14": 68.5,
                    "macd": 2.15,
                    "macd_signal": 1.85,
                    "macd_histogram": 0.30
                },
                "updated_at": "2026-03-05T15:30:00Z"
            }
        }


class AssetDetailResponse(BaseModel):
    """Asset detail response wrapper"""
    status: str = Field(default="success", description="Response status")
    data: AssetDetail = Field(..., description="Asset details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "data": {
                    "ticker": "AAPL",
                    "name": "Apple Inc.",
                    "asset_type": "stock",
                    "price": 189.45
                }
            }
        }


class AssetTechnicalResponse(TechnicalDataResponse):
    """Technical analysis response (alias for consistency)"""
    pass


# ============================================================================
# FORECAST SCHEMAS - MODEL-AGNOSTIC
# ============================================================================

class ForecastModelStatus(str, Enum):
    """Model status enumeration"""
    READY = "ready"
    TRAINING = "training"
    STALE = "stale"
    ERROR = "error"


class ModelForecastOutput(BaseModel):
    """Individual model forecast output"""
    model_name: str = Field(..., description="Name of the model (Baseline, LSTM, TFT, Ensemble)")
    model_type: str = Field(..., description="Type: baseline, lstm, gru, tft, ensemble")
    signal: RecommendationType = Field(..., description="Forecasted signal: BUY/HOLD/SELL")
    expected_return: float = Field(..., description="Expected return percentage")
    confidence: float = Field(..., ge=0, le=100, description="Confidence score 0-100")
    status: ForecastModelStatus = Field(..., description="Model readiness status")
    accuracy: Optional[float] = Field(None, ge=0, le=100, description="Backtest accuracy if available")
    last_updated: datetime = Field(..., description="Last training/update timestamp")
    description: str = Field(..., description="Model description and architecture notes")

    class Config:
        json_schema_extra = {
            "example": {
                "model_name": "LSTM/GRU",
                "model_type": "lstm",
                "signal": "BUY",
                "expected_return": 5.8,
                "confidence": 78.5,
                "status": "ready",
                "accuracy": 61.2,
                "last_updated": "2026-03-05T14:22:00",
                "description": "2-layer LSTM with attention mechanism"
            }
        }


class ForecastConsensus(BaseModel):
    """Consensus metrics across all models"""
    consensus_signal: RecommendationType = Field(..., description="Most likely signal")
    consensus_probability: float = Field(..., ge=0, le=100, description="Probability of consensus")
    average_confidence: float = Field(..., ge=0, le=100, description="Mean confidence across models")
    average_return: float = Field(..., description="Mean expected return across models")
    best_model: str = Field(..., description="Model with highest accuracy")
    most_optimistic: str = Field(..., description="Model with highest expected return")
    most_conservative: str = Field(..., description="Model with lowest expected return")
    model_agreement: str = Field(..., description="Agreement level: Low/Medium/High")


class ForecastResponse(BaseModel):
    """Comprehensive forecast comparison response"""
    status: str = Field(default="success", description="Response status: success/error")
    ticker: str = Field(..., description="Ticker symbol")
    current_price: float = Field(..., description="Current share price")
    horizon_days: int = Field(default=30, description="Forecast horizon in days")
    
    # Individual model forecasts
    models: List[ModelForecastOutput] = Field(..., description="Forecasts from all models")
    
    # Consensus metrics
    consensus: ForecastConsensus = Field(..., description="Consensus across models")
    
    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Report generation time")
    next_update: datetime = Field(..., description="Scheduled next update time")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "ticker": "AAPL",
                "current_price": 189.45,
                "horizon_days": 30,
                "models": [
                    {
                        "model_name": "Baseline",
                        "model_type": "baseline",
                        "signal": "HOLD",
                        "expected_return": 2.1,
                        "confidence": 52.3,
                        "status": "ready",
                        "accuracy": 52.3,
                        "last_updated": "2026-03-05T14:22:00",
                        "description": "Simple momentum indicator based on recent price action"
                    },
                    {
                        "model_name": "LSTM/GRU",
                        "model_type": "lstm",
                        "signal": "BUY",
                        "expected_return": 5.8,
                        "confidence": 78.5,
                        "status": "ready",
                        "accuracy": 61.2,
                        "last_updated": "2026-03-05T14:22:00",
                        "description": "2-layer LSTM with attention mechanism for sequence learning"
                    }
                ],
                "consensus": {
                    "consensus_signal": "BUY",
                    "consensus_probability": 72.5,
                    "average_confidence": 77.73,
                    "average_return": 5.42,
                    "best_model": "Ensemble",
                    "most_optimistic": "TFT",
                    "most_conservative": "Baseline",
                    "model_agreement": "High"
                },
                "generated_at": "2026-03-05T15:30:00",
                "next_update": "2026-03-05T16:30:00"
            }
        }


class AssetForecastResponse(BaseModel):
    """Asset forecast response wrapper"""
    status: str = Field(default="success", description="Response status")
    data: ForecastResponse = Field(..., description="Forecast comparison data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


# ============================================================================
# ANALYST REPORT SCHEMAS
# ============================================================================

class TechnicalViewpoint(BaseModel):
    """Technical analysis section"""
    trend: str = Field(..., description="Overall trend: Uptrend/Downtrend/Sideways")
    key_levels: List[float] = Field(..., description="Key support/resistance levels")
    signal_strength: float = Field(..., ge=0, le=100, description="Signal strength 0-100")
    momentum: str = Field(..., description="Momentum assessment: Strong/Neutral/Weak")
    ma_alignment: str = Field(..., description="Moving average alignment")
    summary: str = Field(..., description="Technical analysis summary")


class FundamentalSnapshot(BaseModel):
    """Fundamental analysis section"""
    eps: Optional[float] = Field(None, description="Earnings per share")
    revenue_growth: Optional[float] = Field(None, description="Revenue growth %")
    profit_margin: Optional[float] = Field(None, description="Profit margin %")
    roe: Optional[float] = Field(None, description="Return on Equity %")
    debt_to_equity: Optional[float] = Field(None, description="Debt to equity ratio")
    valuation_assessment: str = Field(..., description="Overvalued/Fairly/Undervalued")
    quality_score: float = Field(..., ge=0, le=100, description="Quality score 0-100")


class MacroContext(BaseModel):
    """Macro-economic context"""
    sector_performance: str = Field(..., description="Sector performance vs market")
    industry_tailwinds: List[str] = Field(..., description="Industry tailwinds")
    macro_headwinds: List[str] = Field(..., description="Macro headwinds")
    correlation_market: float = Field(..., description="Market correlation")
    macro_outlook: str = Field(..., description="Positive/Neutral/Negative")


class InvestmentCase(BaseModel):
    """Bull or bear investment case"""
    thesis: str = Field(..., description="Core thesis")
    key_catalysts: List[str] = Field(..., description="Supporting catalysts")
    timeline: str = Field(..., description="Expected timeframe")
    probability: float = Field(..., ge=0, le=100, description="Probability %")


class RiskAndCatalyst(BaseModel):
    """Risk factor with severity"""
    description: str = Field(..., description="Risk description")
    severity: str = Field(..., description="Low/Medium/High")
    mitigation: Optional[str] = Field(None, description="Risk mitigation strategy")


class FinalRating(BaseModel):
    """Final investment rating"""
    recommendation: RecommendationType = Field(..., description="Buy/Hold/Sell")
    target_price: float = Field(..., description="12-month price target")
    price_upside: float = Field(..., description="Upside potential %")
    conviction: str = Field(..., description="High/Medium/Low conviction")
    rationale: str = Field(..., description="Rating rationale")


class AnalystReport(BaseModel):
    """Comprehensive AI-generated analyst report"""
    ticker: str = Field(..., description="Ticker symbol")
    company_name: str = Field(..., description="Company name")
    report_date: datetime = Field(default_factory=datetime.utcnow, description="Report generation date")
    current_price: float = Field(..., description="Current share price")
    
    # Executive Summary
    executive_summary: str = Field(..., description="High-level analysis summary")
    investment_highlight: str = Field(..., description="Key investment point")
    
    # Core Analysis Sections
    technical_view: TechnicalViewpoint = Field(..., description="Technical analysis")
    fundamental_snapshot: FundamentalSnapshot = Field(..., description="Fundamental metrics")
    macro_context: MacroContext = Field(..., description="Macro-economic context")
    bull_case: InvestmentCase = Field(..., description="Bull investment case")
    bear_case: InvestmentCase = Field(..., description="Bear investment case")
    
    # Risk & Catalysts
    risks: List[RiskAndCatalyst] = Field(..., description="Risk factors")
    catalysts: List[RiskAndCatalyst] = Field(..., description="Near-term catalysts")
    
    # Final Rating
    final_rating: FinalRating = Field(..., description="Final recommendation and target")
    confidence_score: float = Field(..., ge=0, le=100, description="Overall confidence 0-100")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "current_price": 189.45,
                "executive_summary": "Apple demonstrates strong fundamentals...",
                "confidence_score": 85.0
            }
        }


class AnalystReportResponse(BaseModel):
    """Analyst report response wrapper with comprehensive research note"""
    status: str = Field(default="success", description="Response status: success/error")
    data: AnalystReport = Field(..., description="Comprehensive analyst report data")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Report generation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "data": {
                    "ticker": "AAPL",
                    "company_name": "Apple Inc.",
                    "report_date": "2026-03-05T15:30:00",
                    "current_price": 189.45,
                    "executive_summary": "Apple demonstrates strong fundamentals with robust cash flow and expanding services revenue...",
                    "investment_highlight": "Attractive valuation entering 2026 with AI integration driving margin expansion",
                    "technical_view": {
                        "trend": "Uptrend",
                        "key_levels": [185.50, 195.00, 205.00],
                        "signal_strength": 78.5,
                        "momentum": "Strong",
                        "ma_alignment": "Bullish (20>50>200 SMA)",
                        "summary": "Break above daily resistance confirms uptrend continuation"
                    },
                    "fundamental_snapshot": {
                        "eps": 6.05,
                        "revenue_growth": 8.5,
                        "profit_margin": 28.2,
                        "roe": 88.5,
                        "debt_to_equity": 1.8,
                        "valuation_assessment": "Fairly Valued",
                        "quality_score": 92.0
                    },
                    "final_rating": {
                        "recommendation": "BUY",
                        "target_price": 215.00,
                        "price_upside": 13.5,
                        "conviction": "High",
                        "rationale": "Strong fundamentals, positive technicals, AI catalyst"
                    },
                    "confidence_score": 87.5
                },
                "generated_at": "2026-03-05T15:30:00Z"
            }
        }


# ============================================================================
# BACKTEST SCHEMAS
# ============================================================================

class BacktestMetrics(BaseModel):
    """Backtest performance metrics"""
    total_return: float = Field(..., description="Total return percentage")
    annual_return: Optional[float] = Field(None, description="Annualized return")
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    sortino_ratio: Optional[float] = Field(None, description="Sortino ratio")
    max_drawdown: float = Field(..., description="Maximum drawdown")
    volatility: Optional[float] = Field(None, description="Volatility/std dev")
    win_rate: float = Field(..., description="Win rate percentage")
    trades_count: int = Field(..., description="Number of trades")
    profit_factor: Optional[float] = Field(None, description="Profit factor")


class BacktestResult(BaseModel):
    """Backtest result with full metrics"""
    backtest_id: str = Field(..., description="Unique backtest ID")
    strategy: str = Field(..., description="Strategy name")
    strategy_description: Optional[str] = Field(None, description="Human-readable strategy description for display")
    ticker: str = Field(..., description="Asset ticker")
    start_date: str = Field(..., description="Backtest start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="Backtest end date (YYYY-MM-DD)")
    initial_capital: float = Field(..., description="Initial capital amount")
    final_value: Optional[float] = Field(None, description="Final portfolio value")
    total_return: float = Field(..., description="Total return %")
    annual_return: Optional[float] = Field(None, description="Annualized return %")
    sharpe_ratio: float = Field(..., description="Sharpe ratio (risk-adjusted return)")
    sortino_ratio: Optional[float] = Field(None, description="Sortino ratio (downside risk-adjusted)")
    max_drawdown: float = Field(..., description="Maximum drawdown %")
    volatility: Optional[float] = Field(None, description="Volatility/standard deviation %")
    trades_count: int = Field(..., description="Number of trades executed")
    win_rate: float = Field(..., description="Win rate %")
    direction_accuracy: Optional[float] = Field(None, description="Next-day direction accuracy %")
    status: str = Field(default="completed", description="Backtest status: completed/running/error")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "backtest_id": "bt_AAPL_1709643600.0",
                "strategy": "Moving Average Crossover",
                "ticker": "AAPL",
                "start_date": "2024-01-01",
                "end_date": "2026-03-05",
                "initial_capital": 100000.0,
                "final_value": 125436.50,
                "total_return": 25.44,
                "annual_return": 11.89,
                "sharpe_ratio": 1.45,
                "sortino_ratio": 2.12,
                "max_drawdown": -12.34,
                "volatility": 18.5,
                "trades_count": 42,
                "win_rate": 55.0,
                "status": "completed"
            }
        }


class BacktestSummaryResponse(BaseModel):
    """Backtest summary response wrapper with full metrics"""
    status: str = Field(default="success", description="Response status: success/error")
    data: List[BacktestResult] = Field(..., description="List of backtest results")
    total_results: int = Field(..., description="Number of results returned")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "data": [
                    {
                        "backtest_id": "bt_AAPL_1709643600.0",
                        "strategy": "Moving Average Crossover",
                        "ticker": "AAPL",
                        "start_date": "2024-01-01",
                        "end_date": "2026-03-05",
                        "initial_capital": 100000.0,
                        "final_value": 125436.50,
                        "total_return": 25.44,
                        "annual_return": 11.89,
                        "sharpe_ratio": 1.45,
                        "sortino_ratio": 2.12,
                        "max_drawdown": -12.34,
                        "volatility": 18.5,
                        "trades_count": 42,
                        "win_rate": 55.0,
                        "status": "completed",
                        "created_at": "2026-03-05T14:30:00"
                    }
                ],
                "total_results": 1,
                "timestamp": "2026-03-05T16:45:00Z"
            }
        }


# ============================================================================
# PORTFOLIO SCHEMAS
# ============================================================================

class WatchlistItem(BaseModel):
    """Watchlist item with current metrics"""
    ticker: str = Field(..., description="Ticker symbol (uppercase)")
    name: str = Field(..., description="Asset name/company name")
    current_price: float = Field(..., description="Current share price")
    change_24h: Optional[float] = Field(None, description="24-hour price change percentage")
    added_date: datetime = Field(..., description="Date item was added to watchlist")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "current_price": 189.45,
                "change_24h": 1.25,
                "added_date": "2026-03-01T14:30:00"
            }
        }


class PeriodChangesData(BaseModel):
    """Period-over-period price changes"""
    change_1d: float = Field(..., description="1-day percentage change")
    change_5d: float = Field(..., description="5-day percentage change")
    change_1m: float = Field(..., description="1-month percentage change")
    
    class Config:
        json_schema_extra = {
            "example": {
                "change_1d": 2.15,
                "change_5d": 5.33,
                "change_1m": 12.80,
            }
        }


class WatchlistIntelligenceItem(BaseModel):
    """Extended watchlist item with intelligence metrics"""
    ticker: str = Field(..., description="Ticker symbol (uppercase)")
    name: str = Field(..., description="Asset name/company name")
    current_price: float = Field(..., description="Current share price")
    change_24h: Optional[float] = Field(None, description="24-hour price change percentage")
    added_date: datetime = Field(..., description="Date item was added to watchlist")
    
    # Intelligence scores
    signal_score: Optional[float] = Field(None, description="Buy/Sell signal (-1 to 1)")
    confidence_score: Optional[float] = Field(None, description="Forecast confidence (0-100)")
    risk_score: Optional[float] = Field(None, description="Risk metric (0-100, higher=riskier)")
    
    # Period changes
    period_changes: Optional[PeriodChangesData] = Field(None, description="Price changes over periods")
    
    # Alert status
    alert_level: str = Field(..., description="Alert level: critical/warning/info/none")
    alert_message: str = Field(..., description="Alert message or reason")
    
    # Allocation
    allocation_weight: Optional[float] = Field(None, description="Suggested allocation % (0-100)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "current_price": 189.45,
                "change_24h": 1.25,
                "added_date": "2026-03-01T14:30:00",
                "signal_score": 0.65,
                "confidence_score": 78.5,
                "risk_score": 42.3,
                "period_changes": {
                    "change_1d": 1.25,
                    "change_5d": 3.42,
                    "change_1m": 8.15,
                },
                "alert_level": "info",
                "alert_message": "Strong bullish signal",
                "allocation_weight": 15.5,
            }
        }


class WatchlistIntelligenceResponse(BaseModel):
    """Watchlist response with intelligence metrics for each item"""
    status: str = Field(default="success", description="Response status: success/error")
    data: List[WatchlistIntelligenceItem] = Field(..., description="List of watchlist items with intelligence")
    total_items: int = Field(..., description="Total number of items in watchlist")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last watchlist update timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "data": [
                    {
                        "ticker": "AAPL",
                        "name": "Apple Inc.",
                        "current_price": 189.45,
                        "change_24h": 1.25,
                        "added_date": "2026-03-01T14:30:00",
                        "signal_score": 0.65,
                        "confidence_score": 78.5,
                        "risk_score": 42.3,
                        "period_changes": {
                            "change_1d": 1.25,
                            "change_5d": 3.42,
                            "change_1m": 8.15,
                        },
                        "alert_level": "info",
                        "alert_message": "Strong bullish signal",
                        "allocation_weight": 25.5,
                    }
                ],
                "total_items": 1,
                "updated_at": "2026-03-06T14:30:00Z"
            }
        }


class WatchlistResponse(BaseModel):
    """Watchlist response wrapper with tracked assets"""
    status: str = Field(default="success", description="Response status: success/error")
    data: List[WatchlistItem] = Field(..., description="List of watchlist items")
    total_items: int = Field(..., description="Total number of items in watchlist")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last watchlist update timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "data": [
                    {
                        "ticker": "AAPL",
                        "name": "Apple Inc.",
                        "current_price": 189.45,
                        "change_24h": 1.25,
                        "added_date": "2026-03-01T14:30:00"
                    },
                    {
                        "ticker": "MSFT",
                        "name": "Microsoft Corporation",
                        "current_price": 380.25,
                        "change_24h": -0.80,
                        "added_date": "2026-02-28T10:15:00"
                    },
                    {
                        "ticker": "NVDA",
                        "name": "NVIDIA Corporation",
                        "current_price": 875.50,
                        "change_24h": 3.42,
                        "added_date": "2026-02-25T09:00:00"
                    }
                ],
                "total_items": 3,
                "updated_at": "2026-03-15T16:45:00Z"
            }
        }


# ============================================================================
# REQUEST SCHEMAS (Input validation)
# ============================================================================

class BacktestRequest(BaseModel):
    """Backtest creation request"""
    strategy: str = Field(..., description="Strategy name", min_length=1)
    ticker: str = Field(..., description="Ticker symbol", min_length=1, max_length=10)
    start_date: datetime = Field(..., description="Start date")
    end_date: datetime = Field(..., description="End date")
    initial_capital: float = Field(default=10000.0, gt=0, description="Initial capital")
    
    class Config:
        json_schema_extra = {
            "example": {
                "strategy": "Moving Average Crossover",
                "ticker": "AAPL",
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2026-03-05T00:00:00",
                "initial_capital": 100000.0
            }
        }


class TickerRequest(BaseModel):
    """Ticker validation request"""
    ticker: str = Field(..., description="Ticker symbol", min_length=1, max_length=10, pattern="^[A-Z0-9]+$")

    class Config:
        json_schema_extra = {"example": {"ticker": "AAPL"}}
