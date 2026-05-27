"""
Technical Indicator Service
Calculates technical analysis indicators using pandas/numpy
"""
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import logging

from app.schemas.schemas import TechnicalIndicators

logger = logging.getLogger(__name__)


class IndicatorService:
    """Service for calculating technical indicators"""

    @staticmethod
    def calculate_sma(prices: List[float], window: int) -> List[Optional[float]]:
        """Calculate Simple Moving Average"""
        if len(prices) < window:
            return [None] * len(prices)

        series = pd.Series(prices)
        sma = series.rolling(window=window).mean()
        return sma.tolist()

    @staticmethod
    def calculate_ema(prices: List[float], span: int) -> List[Optional[float]]:
        """Calculate Exponential Moving Average"""
        if len(prices) < span:
            return [None] * len(prices)

        series = pd.Series(prices)
        ema = series.ewm(span=span, adjust=False).mean()
        return ema.tolist()

    @staticmethod
    def calculate_rsi(prices: List[float], window: int = 14) -> List[Optional[float]]:
        """
        Calculate Relative Strength Index
        
        RSI = 100 - (100 / (1 + RS))
        where RS = Average Gain / Average Loss
        """
        if len(prices) < window + 1:
            return [None] * len(prices)

        series = pd.Series(prices)
        delta = series.diff()

        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # Calculate average gain and loss
        avg_gain = gain.rolling(window=window).mean()
        avg_loss = loss.rolling(window=window).mean()

        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi.tolist()

    @staticmethod
    def calculate_macd(
        prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Dict[str, List[Optional[float]]]:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        MACD Line = 12-period EMA - 26-period EMA
        Signal Line = 9-period EMA of MACD
        MACD Histogram = MACD Line - Signal Line
        """
        if len(prices) < slow + signal:
            return {
                "macd": [None] * len(prices),
                "signal": [None] * len(prices),
                "histogram": [None] * len(prices),
            }

        series = pd.Series(prices)
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return {
            "macd": macd_line.tolist(),
            "signal": signal_line.tolist(),
            "histogram": histogram.tolist(),
        }

    @staticmethod
    def calculate_bollinger_bands(
        prices: List[float], window: int = 20, num_std: float = 2.0
    ) -> Dict[str, List[Optional[float]]]:
        """
        Calculate Bollinger Bands
        
        Middle Band = 20-period SMA
        Upper Band = Middle Band + 2 * Std Deviation
        Lower Band = Middle Band - 2 * Std Deviation
        """
        if len(prices) < window:
            return {
                "upper": [None] * len(prices),
                "middle": [None] * len(prices),
                "lower": [None] * len(prices),
            }

        series = pd.Series(prices)
        middle = series.rolling(window=window).mean()
        std = series.rolling(window=window).std()

        upper = middle + (num_std * std)
        lower = middle - (num_std * std)

        return {
            "upper": upper.tolist(),
            "middle": middle.tolist(),
            "lower": lower.tolist(),
        }

    @staticmethod
    def calculate_atr(
        highs: List[float], lows: List[float], closes: List[float], window: int = 14
    ) -> List[Optional[float]]:
        """
        Calculate Average True Range
        
        True Range = max(
            High - Low,
            abs(High - Previous Close),
            abs(Low - Previous Close)
        )
        ATR = Average of True Range over window period
        """
        if len(highs) < window + 1:
            return [None] * len(highs)

        tr_values = []
        for i in range(len(highs)):
            if i == 0:
                tr = highs[i] - lows[i]
            else:
                tr = max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i - 1]),
                    abs(lows[i] - closes[i - 1]),
                )
            tr_values.append(tr)

        atr = pd.Series(tr_values).rolling(window=window).mean()
        return atr.tolist()

    @staticmethod
    def calculate_agg_indicators(
        prices: List[float], highs: List[float], lows: List[float]
    ) -> TechnicalIndicators:
        """Calculate multiple indicators at once"""
        try:
            # Calculate all indicators
            sma_20 = IndicatorService.calculate_sma(prices, 20)
            sma_50 = IndicatorService.calculate_sma(prices, 50)
            ema_12 = IndicatorService.calculate_ema(prices, 12)
            rsi_14 = IndicatorService.calculate_rsi(prices, 14)
            macd_data = IndicatorService.calculate_macd(prices)

            # Get latest values (most recent)
            return TechnicalIndicators(
                sma_20=sma_20[-1] if sma_20 and sma_20[-1] is not None else None,
                sma_50=sma_50[-1] if sma_50 and sma_50[-1] is not None else None,
                ema_12=ema_12[-1] if ema_12 and ema_12[-1] is not None else None,
                rsi_14=rsi_14[-1] if rsi_14 and rsi_14[-1] is not None else None,
                macd=macd_data["macd"][-1] if macd_data["macd"] else None,
                macd_signal=macd_data["signal"][-1] if macd_data["signal"] else None,
                macd_histogram=macd_data["histogram"][-1]
                if macd_data["histogram"]
                else None,
            )
        except Exception as e:
            logger.error(f"Error calculating indicators: {str(e)}")
            return TechnicalIndicators()


class AnalysisService:
    """Service for financial analysis and calculations"""

    @staticmethod
    def calculate_returns(prices: List[float]) -> List[float]:
        """Calculate daily returns"""
        prices_array = np.array(prices)
        returns = np.diff(prices_array) / prices_array[:-1]
        return returns.tolist()

    @staticmethod
    def calculate_sharpe_ratio(
        returns: List[float], risk_free_rate: float = 0.02
    ) -> float:
        """
        Calculate Sharpe Ratio
        
        Sharpe = (Mean Return - Risk Free Rate) / Std Dev of Returns
        Annualized: Sharpe * sqrt(252)
        """
        returns_array = np.array(returns)
        excess_returns = returns_array - (risk_free_rate / 252)
        
        if len(excess_returns) < 2:
            return 0.0
            
        sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
        return float(sharpe) if not np.isnan(sharpe) else 0.0

    @staticmethod
    def calculate_max_drawdown(prices: List[float]) -> float:
        """
        Calculate Maximum Drawdown
        
        Drawdown = (Current Value - Peak Value) / Peak Value
        Max Drawdown = Lowest drawdown value
        """
        if len(prices) < 2:
            return 0.0

        prices_array = np.array(prices)
        cumulative = np.cumprod(1 + np.diff(prices_array) / prices_array[:-1])
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        return float(np.min(drawdown)) if len(drawdown) > 0 else 0.0

    @staticmethod
    def calculate_sortino_ratio(
        returns: List[float], target_return: float = 0.0, risk_free_rate: float = 0.02
    ) -> float:
        """
        Calculate Sortino Ratio
        
        Similar to Sharpe but only considers downside volatility
        Sortino = (Mean Return - Target Return) / Downside Deviation
        """
        returns_array = np.array(returns)
        excess_returns = returns_array - (risk_free_rate / 252)

        downside_returns = excess_returns[excess_returns < 0]
        if len(downside_returns) < 2:
            return 0.0

        downside_std = np.std(downside_returns)
        if downside_std == 0:
            return 0.0

        sortino = np.mean(excess_returns) / downside_std * np.sqrt(252)
        return float(sortino) if not np.isnan(sortino) else 0.0

    @staticmethod
    def calculate_volatility(returns: List[float], periods: int = 252) -> float:
        """
        Calculate annualized volatility
        
        Annualized Volatility = Daily Volatility * sqrt(252)
        """
        returns_array = np.array(returns)
        daily_vol = np.std(returns_array)
        annual_vol = daily_vol * np.sqrt(periods)
        return float(annual_vol)
