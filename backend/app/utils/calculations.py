"""
Utility functions for data processing and calculations
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple


def calculate_technical_indicators(prices: List[float], window: int = 20) -> Dict:
    """
    Calculate common technical indicators
    """
    df = pd.DataFrame({'close': prices})
    
    # Simple Moving Average
    df['sma'] = df['close'].rolling(window=window).mean()
    
    # Exponential Moving Average
    df['ema'] = df['close'].ewm(span=window).mean()
    
    # RSI (Relative Strength Index)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema_12 = df['close'].ewm(span=12).mean()
    ema_26 = df['close'].ewm(span=26).mean()
    df['macd'] = ema_12 - ema_26
    df['signal'] = df['macd'].ewm(span=9).mean()
    df['histogram'] = df['macd'] - df['signal']
    
    return df.to_dict(orient='records')


def calculate_returns(prices: List[float]) -> List[float]:
    """Calculate daily returns"""
    prices_array = np.array(prices)
    returns = np.diff(prices_array) / prices_array[:-1]
    return returns.tolist()


def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
    """Calculate Sharpe ratio"""
    returns_array = np.array(returns)
    excess_returns = returns_array - (risk_free_rate / 252)
    sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
    return float(sharpe)


def calculate_max_drawdown(prices: List[float]) -> float:
    """Calculate maximum drawdown"""
    prices_array = np.array(prices)
    cumulative = np.cumprod(1 + np.diff(prices_array) / prices_array[:-1])
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    return float(np.min(drawdown))
