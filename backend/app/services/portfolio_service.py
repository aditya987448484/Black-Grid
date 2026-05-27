"""
Portfolio Intelligence Service
Orchestrates portfolio watchlist analysis with signal, risk, and allocation metrics

Architecture:
- Uses existing asset detail, technical, and forecast services
- Computes intelligent metrics for each watchlist item
- Generates allocation suggestions
- Handles missing data gracefully
- Structured for future portfolio optimization and analytics

Modules:
- signal_score: BUY/HOLD/SELL signals from forecasts
- confidence_score: Model consensus and agreement metrics
- risk_score: Volatility, drawdown, technical indicators
- period_changes: 1D, 5D, 1M price changes
- alert_status: Rule-based alerts (breakouts, extremes, etc.)
- allocation_suggestion: Risk-adjusted position sizing
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
import pandas as pd

from app.schemas.schemas import (
    WatchlistItem,
    WatchlistResponse,
    RecommendationType,
)
from app.services.market_data import MarketDataProvider, TimeInterval

logger = logging.getLogger(__name__)


# ============================================================================
# MODELS & TYPES
# ============================================================================

class AlertLevel:
    """Alert severity levels"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    NONE = "none"


class PeriodChanges:
    """Period-over-period price changes"""
    def __init__(self, change_1d: float, change_5d: float, change_1m: float):
        self.change_1d = change_1d
        self.change_5d = change_5d
        self.change_1m = change_1m
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "change_1d": round(self.change_1d, 2),
            "change_5d": round(self.change_5d, 2),
            "change_1m": round(self.change_1m, 2),
        }


class WatchlistIntelligence:
    """Extended watchlist item with intelligence metrics"""
    def __init__(
        self,
        ticker: str,
        name: str,
        current_price: float,
        change_24h: Optional[float] = None,
        added_date: Optional[datetime] = None,
    ):
        self.ticker = ticker
        self.name = name
        self.current_price = current_price
        self.change_24h = change_24h or 0.0
        self.added_date = added_date or datetime.utcnow()
        
        # Intelligence scores
        self.signal_score: Optional[float] = None  # -1 to 1 (SELL to BUY)
        self.confidence_score: Optional[float] = None  # 0 to 100
        self.risk_score: Optional[float] = None  # 0 to 100 (higher = riskier)
        self.period_changes: Optional[PeriodChanges] = None
        self.alert_level: str = AlertLevel.NONE
        self.alert_message: str = ""
        self.allocation_weight: Optional[float] = None  # 0 to 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "ticker": self.ticker,
            "name": self.name,
            "current_price": round(self.current_price, 2),
            "change_24h": round(self.change_24h, 2),
            "added_date": self.added_date.isoformat(),
            "signal_score": round(self.signal_score, 2) if self.signal_score is not None else None,
            "confidence_score": round(self.confidence_score, 2) if self.confidence_score is not None else None,
            "risk_score": round(self.risk_score, 2) if self.risk_score is not None else None,
            "period_changes": self.period_changes.to_dict() if self.period_changes else None,
            "alert_level": self.alert_level,
            "alert_message": self.alert_message,
            "allocation_weight": round(self.allocation_weight, 2) if self.allocation_weight is not None else None,
        }


# ============================================================================
# PORTFOLIO SERVICE
# ============================================================================

class PortfolioService:
    """
    Portfolio intelligence service
    
    Provides:
    - Watchlist analysis with structured metrics
    - Signal scoring based on ML forecasts
    - Risk assessment from technical indicators
    - Allocation suggestions
    - Alert detection and messaging
    
    Design:
    - Modular helper methods for extensibility
    - Graceful handling of missing data
    - Configurable alert thresholds
    - Future-ready for portfolio optimization
    """
    
    def __init__(self, market_data_provider: MarketDataProvider):
        """
        Initialize portfolio service
        
        Args:
            market_data_provider: Instance of MarketDataProvider
        """
        self.market_data_provider = market_data_provider
        
        # Configuration
        self.risk_score_thresholds = {
            "high_volatility": 0.25,  # > 25% annualized
            "extreme_volatility": 0.40,  # > 40% annualized
            "high_drawdown": -0.15,  # < -15% max drawdown
        }
        
        self.alert_thresholds = {
            "extreme_move": 5.0,  # > 5% 1-day move
            "momentum_strong": 0.75,  # Signal score >= 0.75
            "momentum_weak": -0.75,  # Signal score <= -0.75
            "confidence_low": 40,  # Confidence < 40%
            "volatility_spike": 0.30,  # Volatility > 30%
        }
    
    async def analyze_watchlist(
        self,
        tickers: List[str],
        historical_days: int = 252,
    ) -> List["WatchlistIntelligence"]:
        """
        Analyze multiple tickers and return structured watchlist intelligence
        
        Analysis pipeline:
        1. Fetch asset data, technicals, and forecast for each ticker
        2. Compute signal and confidence scores
        3. Calculate risk metrics
        4. Detect period changes
        5. Evaluate alert conditions
        6. Suggest allocations
        
        Args:
            tickers: List of ticker symbols
            historical_days: Days of data for risk calculation
        
        Returns:
            List of WatchlistIntelligence items with metrics
        """
        logger.info(f"Analyzing watchlist for {len(tickers)} tickers")
        
        watchlist_items = []
        
        for ticker in tickers:
            try:
                item = await self._analyze_ticker(ticker, historical_days)
                if item:
                    watchlist_items.append(item)
            except Exception as e:
                logger.warning(f"Failed to analyze {ticker}: {e}")
                # Create minimal item on error
                item = WatchlistIntelligence(
                    ticker=ticker,
                    name=ticker,
                    current_price=0.0,
                )
                item.alert_level = AlertLevel.CRITICAL
                item.alert_message = f"Data fetch error: {str(e)}"
                watchlist_items.append(item)
        
        # Compute allocations based on metrics
        await self._compute_allocations(watchlist_items)
        
        return watchlist_items
    
    async def _analyze_ticker(
        self,
        ticker: str,
        historical_days: int,
    ) -> Optional[WatchlistIntelligence]:
        """
        Analyze single ticker and compute all intelligence metrics
        
        Args:
            ticker: Stock ticker
            historical_days: Days for historical analysis
        
        Returns:
            WatchlistIntelligence object with computed metrics
        """
        logger.debug(f"Analyzing ticker {ticker}")
        
        try:
            # Fetch current quote
            quote_response = await self.market_data_provider.get_current_quote(ticker)
            if not quote_response:
                raise ValueError(f"No quote data for {ticker}")
            
            # Extract quote data from Alpha Vantage format
            quote_data = quote_response.get("Global Quote", {})
            if not quote_data:
                raise ValueError(f"Invalid quote response format for {ticker}")
            
            # Parse price (key "05. price")
            price_str = quote_data.get("05. price", "0")
            current_price = float(price_str) if price_str else 0.0
            if current_price <= 0:
                raise ValueError(f"Invalid price for {ticker}")
            
            # Parse change percent (key "10. change percent", format "0.8333%")
            change_percent_str = quote_data.get("10. change percent", "0%").rstrip("%")
            change_24h = float(change_percent_str) if change_percent_str else 0.0
            
            # Create base item
            item = WatchlistIntelligence(
                ticker=ticker,
                name=ticker.upper(),  # Name not in quote, use ticker
                current_price=current_price,
                change_24h=change_24h,
            )
            
            # Fetch historical data for metrics
            try:
                historical_data = await self.market_data_provider.get_time_series(
                    ticker,
                    interval=TimeInterval.DAILY,
                    output_size="full",
                )
                df = self._parse_time_series(historical_data, historical_days)
            except Exception as e:
                logger.warning(f"Could not fetch historical data for {ticker}: {e}")
                df = None
            
            # Compute signal score (from mock forecast)
            signal_score = self._compute_signal_score(ticker, item)
            item.signal_score = signal_score
            
            # Compute confidence score
            confidence_score = self._compute_confidence_score(ticker, item)
            item.confidence_score = confidence_score
            
            # Compute risk score from technical indicators
            risk_score = self._compute_risk_score(df, item) if df is not None else 50.0
            item.risk_score = risk_score
            
            # Calculate period changes
            period_changes = self._compute_period_changes(df) if df is not None else None
            item.period_changes = period_changes or PeriodChanges(
                change_1d=0.0,
                change_5d=0.0,
                change_1m=0.0,
            )
            
            # Evaluate alert conditions
            alert_level, alert_msg = self._evaluate_alerts(item)
            item.alert_level = alert_level
            item.alert_message = alert_msg
            
            return item
        
        except Exception as e:
            logger.error(f"Error analyzing {ticker}: {e}")
            return None
    
    def _compute_signal_score(self, ticker: str, item: WatchlistIntelligence) -> float:
        """
        Compute signal score from forecast consensus
        
        Score range: -1 (SELL) to 1 (BUY)
        
        Args:
            ticker: Stock ticker
            item: WatchlistIntelligence item with current data
        
        Returns:
            Signal score -1 to 1
        """
        # In production, this would fetch actual forecast
        # For now, use mock logic based on recent momentum
        change_percent = item.change_24h
        
        # Simple signal: higher recent change = bullish
        score = np.clip(change_percent / 5.0, -1.0, 1.0)
        return score
    
    def _compute_confidence_score(self, ticker: str, item: WatchlistIntelligence) -> float:
        """
        Compute confidence score from forecast model agreement
        
        Score range: 0 (no confidence) to 100 (high confidence)
        
        Args:
            ticker: Stock ticker
            item: WatchlistIntelligence item with current data
        
        Returns:
            Confidence score 0-100
        """
        # In production, compute from forecast consensus
        # For now, base on data quality and price level
        # Use a simple heuristic: higher price = more liquid = higher confidence
        base_confidence = min(item.current_price / 200 * 100, 80)  # Cap at 80
        
        return max(base_confidence, 40)  # At least 40% confidence
    
    def _compute_risk_score(
        self,
        df: Optional[pd.DataFrame],
        item: WatchlistIntelligence,
    ) -> float:
        """
        Compute risk score from technical indicators and volatility
        
        Score range: 0 (safe) to 100 (risky)
        
        Args:
            df: DataFrame with OHLCV data
            item: WatchlistIntelligence item (for reference)
        
        Returns:
            Risk score 0-100
        """
        if df is None or len(df) < 20:
            return 50.0  # Default middle score
        
        risk_score = 0.0
        
        # Volatility component (0-40 points)
        returns = df["close"].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)  # Annualized
        
        vol_score = min(volatility * 100, 40)  # Cap at 40
        risk_score += vol_score
        
        # Drawdown component (0-30 points)
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_dd = abs(drawdown.min())
        
        dd_score = min(max_dd * 100, 30)
        risk_score += dd_score
        
        # Trend risk (0-30 points)
        # Higher relative volatility to trend strength = riskier
        if len(df) >= 50:
            sma_50 = df["close"].rolling(50).mean().iloc[-1]
            current_price = df["close"].iloc[-1]
            distance_from_mean = abs(current_price - sma_50) / sma_50
            
            trend_risk = min(distance_from_mean * 100, 30)
            risk_score += trend_risk
        
        return min(risk_score, 100.0)
    
    def _compute_period_changes(self, df: Optional[pd.DataFrame]) -> Optional[PeriodChanges]:
        """
        Compute 1D, 5D, 1M price changes
        
        Args:
            df: DataFrame with OHLCV data (sorted by date, ascending)
        
        Returns:
            PeriodChanges object or None if insufficient data
        """
        if df is None or len(df) < 1:
            return None
        
        try:
            current_price = df["close"].iloc[-1]
            
            # 1D change
            change_1d = 0.0
            if len(df) >= 1:
                prev_close = df["close"].iloc[-2] if len(df) >= 2 else df["open"].iloc[-1]
                change_1d = (current_price - prev_close) / prev_close * 100
            
            # 5D change
            change_5d = 0.0
            if len(df) >= 5:
                price_5d_ago = df["close"].iloc[-5]
                change_5d = (current_price - price_5d_ago) / price_5d_ago * 100
            
            # 1M change (21 trading days)
            change_1m = 0.0
            if len(df) >= 21:
                price_1m_ago = df["close"].iloc[-21]
                change_1m = (current_price - price_1m_ago) / price_1m_ago * 100
            
            return PeriodChanges(change_1d, change_5d, change_1m)
        
        except Exception as e:
            logger.warning(f"Error computing period changes: {e}")
            return None
    
    def _evaluate_alerts(self, item: WatchlistIntelligence) -> Tuple[str, str]:
        """
        Evaluate alert conditions for watchlist item
        
        Args:
            item: WatchlistIntelligence object
        
        Returns:
            Tuple of (alert_level, alert_message)
        """
        alerts = []
        
        # Check for extreme moves
        if item.period_changes:
            if abs(item.period_changes.change_1d) > self.alert_thresholds["extreme_move"]:
                alerts.append((
                    AlertLevel.WARNING,
                    f"Large 1-day move: {item.period_changes.change_1d:+.2f}%",
                ))
        
        # Check momentum
        if item.signal_score is not None:
            if item.signal_score >= self.alert_thresholds["momentum_strong"]:
                alerts.append((
                    AlertLevel.INFO,
                    f"Strong bullish signal: {item.signal_score:.2f}",
                ))
            elif item.signal_score <= -self.alert_thresholds["momentum_weak"]:
                alerts.append((
                    AlertLevel.WARNING,
                    f"Strong bearish signal: {item.signal_score:.2f}",
                ))
        
        # Check confidence
        if item.confidence_score is not None:
            if item.confidence_score < self.alert_thresholds["confidence_low"]:
                alerts.append((
                    AlertLevel.INFO,
                    f"Low confidence: {item.confidence_score:.0f}%",
                ))
        
        # Check volatility
        if item.risk_score is not None:
            if item.risk_score > self.alert_thresholds["volatility_spike"] * 100:
                alerts.append((
                    AlertLevel.WARNING,
                    f"High volatility: risk score {item.risk_score:.0f}",
                ))
        
        # Determine highest priority alert
        if not alerts:
            return AlertLevel.NONE, ""
        
        # Priority: critical > warning > info
        for level in [AlertLevel.CRITICAL, AlertLevel.WARNING, AlertLevel.INFO]:
            for alert_level, msg in alerts:
                if alert_level == level:
                    return level, msg
        
        return alerts[0][0], alerts[0][1]
    
    async def _compute_allocations(
        self,
        items: List[WatchlistIntelligence],
    ) -> None:
        """
        Compute risk-adjusted allocation weights
        
        Simple strategy:
        - Inverse risk scoring: lower risk = higher allocation
        - Adjusted by confidence level
        - Constrained to 100% total
        
        Args:
            items: List of WatchlistIntelligence items (modified in place)
        """
        if not items:
            return
        
        # Compute weights based on risk-adjusted score
        weights = []
        for item in items:
            if item.risk_score is None or item.confidence_score is None:
                # Default weight for missing data
                weights.append(1.0)
                continue
            
            # Inverse risk (lower risk = higher weight)
            risk_adjusted = max(100 - item.risk_score, 10)
            
            # Confidence adjustment
            confidence_adjusted = (item.confidence_score / 100.0) * risk_adjusted
            
            weights.append(confidence_adjusted)
        
        # Normalize to 100%
        total_weight = sum(weights)
        if total_weight > 0:
            normalized_weights = [w / total_weight * 100 for w in weights]
        else:
            normalized_weights = [100 / len(items) for _ in items]
        
        for item, weight in zip(items, normalized_weights):
            item.allocation_weight = weight
    
    def _parse_time_series(
        self,
        time_series_response: Dict[str, Any],
        historical_days: int,
    ) -> Optional[pd.DataFrame]:
        """
        Parse Alpha Vantage time series response into DataFrame
        
        Args:
            time_series_response: Response from get_time_series()
            historical_days: Number of days to include
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
            Or None if parsing fails
        """
        try:
            time_series = time_series_response.get("Time Series", {})
            if not time_series:
                logger.warning("No time series data in response")
                return None
            
            records = []
            for date_str, ohlcv in time_series.items():
                try:
                    record = {
                        "date": pd.to_datetime(date_str),
                        "open": float(ohlcv.get("1. open", 0)),
                        "high": float(ohlcv.get("2. high", 0)),
                        "low": float(ohlcv.get("3. low", 0)),
                        "close": float(ohlcv.get("4. close", 0)),
                        "volume": int(ohlcv.get("6. volume", 0)),
                    }
                    records.append(record)
                except (ValueError, TypeError) as e:
                    logger.debug(f"Skipping record {date_str}: {e}")
                    continue
            
            if not records:
                logger.warning("No valid OHLCV records found")
                return None
            
            df = pd.DataFrame(records)
            df = df.sort_values("date", ascending=True).reset_index(drop=True)
            
            # Limit to historical_days
            if len(df) > historical_days:
                df = df.tail(historical_days).reset_index(drop=True)
            
            return df
        
        except Exception as e:
            logger.error(f"Error parsing time series: {e}")
            return None
    
    def _prepare_dataframe(
        self,
        historical_data: List[Dict],
    ) -> Optional[pd.DataFrame]:
        """
        Prepare historical data into pandas DataFrame
        
        Args:
            historical_data: List of OHLCV dictionaries
        
        Returns:
            DataFrame with OHLCV columns or None on error
        """
        try:
            if not historical_data:
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(historical_data)
            
            # Ensure required columns
            required_cols = ["close", "high", "low", "open", "volume"]
            for col in required_cols:
                if col not in df.columns:
                    logger.warning(f"Missing column {col} in historical data")
                    return None
            
            # Convert to numeric
            for col in required_cols:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            
            # Sort by date ascending
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date")
            
            return df
        
        except Exception as e:
            logger.warning(f"Error preparing dataframe: {e}")
            return None
