"""
Feature Pipeline for Forecast Models
Builds reusable technical indicator features from OHLCV data
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class FeatureColumns:
    """Schema for computed features"""
    daily_returns: str = "daily_returns"
    rolling_returns_5d: str = "rolling_returns_5d"
    rolling_returns_10d: str = "rolling_returns_10d"
    rolling_returns_20d: str = "rolling_returns_20d"
    sma_20: str = "sma_20"
    sma_50: str = "sma_50"
    ema_12: str = "ema_12"
    ema_26: str = "ema_26"
    rsi_14: str = "rsi_14"
    macd: str = "macd"
    macd_signal: str = "macd_signal"
    macd_histogram: str = "macd_histogram"
    atr_14: str = "atr_14"
    rolling_volatility_20: str = "rolling_volatility_20"
    volume_change: str = "volume_change"


class FeaturePipeline:
    """
    Modular feature engineering pipeline for forecasting models
    
    Builds technical indicators and features from OHLCV data.
    Designed to be easily extended with additional feature types.
    
    Features computed:
    - Momentum: Daily/rolling returns, RSI, MACD
    - Trend: SMA, EMA
    - Volatility: ATR, rolling volatility
    - Volume: Volume change
    """
    
    def __init__(self):
        self.features = FeatureColumns()
        self.min_required_rows = 100  # Minimum data points for feature computation
    
    def build_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        Build all features from OHLCV dataframe
        
        Args:
            df: DataFrame with columns [Open, High, Low, Close, Volume]
                Must be sorted by date (ascending)
        
        Returns:
            Tuple of (features_df with all computed features, feature_names list)
        
        Raises:
            ValueError: If insufficient data or missing OHLCV columns
        """
        # Validate input
        required_cols = {"Open", "High", "Low", "Close", "Volume"}
        if not required_cols.issubset(df.columns):
            raise ValueError(
                f"DataFrame must contain {required_cols}. Got: {set(df.columns)}"
            )
        
        if len(df) < self.min_required_rows:
            raise ValueError(
                f"Insufficient data: {len(df)} rows. Need minimum {self.min_required_rows}"
            )
        
        # Create copy to avoid modifying original
        df = df.copy()
        df = df.sort_index()  # Ensure time series is sorted
        
        # Build features in order
        logger.debug(f"Building features for {len(df)} rows")
        
        self._build_returns(df)
        self._build_moving_averages(df)
        self._build_rsi(df)
        self._build_macd(df)
        self._build_atr(df)
        self._build_volatility(df)
        self._build_volume_features(df)
        
        # Remove rows with NaN features (from rolling windows)
        df = df.dropna()
        
        # Get feature columns (exclude OHLCV)
        feature_cols = [
            self.features.daily_returns,
            self.features.rolling_returns_5d,
            self.features.rolling_returns_10d,
            self.features.rolling_returns_20d,
            self.features.sma_20,
            self.features.sma_50,
            self.features.ema_12,
            self.features.ema_26,
            self.features.rsi_14,
            self.features.macd,
            self.features.macd_signal,
            self.features.macd_histogram,
            self.features.atr_14,
            self.features.rolling_volatility_20,
            self.features.volume_change,
        ]
        
        logger.debug(f"Generated {len(feature_cols)} features from {len(df)} rows")
        
        return df, feature_cols
    
    def _build_returns(self, df: pd.DataFrame) -> None:
        """
        Build return-based features
        
        Computes:
        - Daily returns: (Close_t - Close_t-1) / Close_t-1
        - Rolling returns: Returns over 5, 10, 20 day windows
        """
        # Daily returns
        df[self.features.daily_returns] = df["Close"].pct_change()
        
        # Rolling window returns
        # Formula: (Close_today - Close_n_days_ago) / Close_n_days_ago
        for window in [5, 10, 20]:
            col_name = f"rolling_returns_{window}d"
            df[col_name] = df["Close"].pct_change(periods=window)
    
    def _build_moving_averages(self, df: pd.DataFrame) -> None:
        """
        Build Simple and Exponential Moving Averages
        
        Computes:
        - SMA 20: 20-day simple moving average
        - SMA 50: 50-day simple moving average
        - EMA 12: 12-day exponential moving average
        - EMA 26: 26-day exponential moving average
        
        Used for trend identification and mean reversion signals
        """
        df[self.features.sma_20] = df["Close"].rolling(window=20).mean()
        df[self.features.sma_50] = df["Close"].rolling(window=50).mean()
        df[self.features.ema_12] = df["Close"].ewm(span=12, adjust=False).mean()
        df[self.features.ema_26] = df["Close"].ewm(span=26, adjust=False).mean()
    
    def _build_rsi(self, df: pd.DataFrame, period: int = 14) -> None:
        """
        Build Relative Strength Index (RSI)
        
        Momentum oscillator measuring speed/magnitude of price changes
        Range: 0-100. Overbought >70, Oversold <30
        
        Formula:
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss (over period)
        """
        delta = df["Close"].diff()
        
        # Separate gains and losses
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        # Calculate average gains and losses
        avg_gains = gains.rolling(window=period).mean()
        avg_losses = losses.rolling(window=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gains / avg_losses
        df[self.features.rsi_14] = 100 - (100 / (1 + rs))
    
    def _build_macd(
        self,
        df: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> None:
        """
        Build MACD (Moving Average Convergence Divergence)
        
        Trend-following momentum indicator
        
        Components:
        - MACD Line: EMA(12) - EMA(26)
        - Signal Line: EMA(9) of MACD Line
        - MACD Histogram: MACD Line - Signal Line
        """
        ema_fast = df["Close"].ewm(span=fast_period, adjust=False).mean()
        ema_slow = df["Close"].ewm(span=slow_period, adjust=False).mean()
        
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=signal_period, adjust=False).mean()
        histogram = macd - signal
        
        df[self.features.macd] = macd
        df[self.features.macd_signal] = signal
        df[self.features.macd_histogram] = histogram
    
    def _build_atr(self, df: pd.DataFrame, period: int = 14) -> None:
        """
        Build Average True Range (ATR)
        
        Measures market volatility based on price range
        
        True Range = max(
            High - Low,
            abs(High - Close_prev),
            abs(Low - Close_prev)
        )
        ATR = SMA(True Range, period)
        """
        high_low = df["High"] - df["Low"]
        high_close = (df["High"] - df["Close"].shift()).abs()
        low_close = (df["Low"] - df["Close"].shift()).abs()
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df[self.features.atr_14] = true_range.rolling(window=period).mean()
    
    def _build_volatility(self, df: pd.DataFrame, period: int = 20) -> None:
        """
        Build Rolling Volatility
        
        Standard deviation of daily returns over rolling window
        Annualized using 252 trading days per year
        """
        returns = df["Close"].pct_change()
        rolling_std = returns.rolling(window=period).std()
        
        # Annualize: daily_vol * sqrt(252)
        df[self.features.rolling_volatility_20] = rolling_std * np.sqrt(252)
    
    def _build_volume_features(self, df: pd.DataFrame) -> None:
        """
        Build Volume-based features
        
        Computes:
        - Volume Change: Percentage change in volume vs previous period
        """
        df[self.features.volume_change] = df["Volume"].pct_change()
    
    def get_recent_features(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        lookback_days: int = 60,
    ) -> np.ndarray:
        """
        Extract recent feature window for model inference
        
        Args:
            df: DataFrame with computed features
            feature_cols: List of feature column names
            lookback_days: Number of recent days to extract
        
        Returns:
            numpy array of shape (lookback_days, n_features)
        """
        if len(df) < lookback_days:
            raise ValueError(
                f"Insufficient data: {len(df)} rows. Need {lookback_days}"
            )
        
        # Get last lookback_days rows
        recent = df[feature_cols].iloc[-lookback_days:].values
        
        logger.debug(f"Extracted {recent.shape} feature matrix")
        
        return recent
    
    def normalize_features(
        self,
        X: np.ndarray,
        mean: Optional[np.ndarray] = None,
        std: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Normalize features using z-score normalization
        
        Args:
            X: Feature array of shape (n_samples, n_features)
            mean: Precomputed mean (for test data). If None, computed from X
            std: Precomputed std (for test data). If None, computed from X
        
        Returns:
            Tuple of (normalized_X, mean, std)
        """
        if mean is None:
            mean = np.nanmean(X, axis=0)
        if std is None:
            std = np.nanstd(X, axis=0)
        
        # Avoid division by zero
        std = np.where(std == 0, 1, std)
        
        X_normalized = (X - mean) / std
        
        return X_normalized, mean, std
    
    def flatten_features(self, X: np.ndarray) -> np.ndarray:
        """
        Flatten 3D feature array for traditional ML models
        (not needed for LSTM/GRU which expect sequences)
        
        Args:
            X: Array of shape (batch, lookback, n_features)
        
        Returns:
            Flattened array of shape (batch, lookback * n_features)
        """
        batch_size = X.shape[0]
        return X.reshape(batch_size, -1)
