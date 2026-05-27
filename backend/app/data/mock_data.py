"""
Mock data for development and testing
"""
import random
from datetime import datetime, timedelta
from typing import List, Dict


def generate_mock_market_data(ticker: str, days: int = 30) -> List[Dict]:
    """Generate mock OHLCV data"""
    data = []
    base_price = random.uniform(50, 300)
    
    for i in range(days):
        date = datetime.now() - timedelta(days=days-i)
        daily_change = random.uniform(-0.05, 0.05)
        
        open_price = base_price * (1 + random.uniform(-0.02, 0.02))
        close_price = open_price * (1 + daily_change)
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.02))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.02))
        
        data.append({
            'date': date.isoformat(),
            'ticker': ticker,
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': random.randint(1000000, 10000000)
        })
        
        base_price = close_price
    
    return data


def generate_mock_asset_details(ticker: str) -> Dict:
    """Generate mock asset details"""
    return {
        'ticker': ticker,
        'name': f'{ticker} Inc.',
        'price': round(random.uniform(50, 500), 2),
        'market_cap': random.randint(1000000000, 1000000000000),
        'pe_ratio': round(random.uniform(10, 50), 2),
        'dividend_yield': round(random.uniform(0, 0.05), 4),
        'timestamp': datetime.now().isoformat()
    }


def generate_mock_forecast(ticker: str, days: int = 30) -> Dict:
    """Generate mock price forecast"""
    current_price = random.uniform(50, 300)
    forecast = []
    
    for i in range(1, days + 1):
        predicted_price = current_price * (1 + random.uniform(-0.02, 0.02))
        forecast.append({
            'date': (datetime.now() + timedelta(days=i)).isoformat(),
            'predicted_price': round(predicted_price, 2),
            'confidence_interval': round(random.uniform(0.85, 0.99), 4)
        })
        current_price = predicted_price
    
    return {
        'ticker': ticker,
        'current_price': round(current_price, 2),
        'forecast': forecast
    }


def generate_mock_analyst_report(ticker: str) -> Dict:
    """Generate mock analyst report"""
    recommendations = ['BUY', 'HOLD', 'SELL']
    return {
        'ticker': ticker,
        'title': f'Market Analysis: {ticker} - Q1 2026',
        'summary': f'{ticker} shows strong fundamentals with positive technical indicators. Recent earnings beat expectations.',
        'recommendation': random.choice(recommendations),
        'target_price': round(random.uniform(50, 500), 2),
        'generated_at': datetime.now().isoformat()
    }


def generate_mock_backtest_summary() -> List[Dict]:
    """Generate mock backtest results"""
    return [
        {
            'backtest_id': 'bt_001',
            'strategy': 'Moving Average Crossover',
            'total_return': round(random.uniform(-0.2, 0.5), 4),
            'sharpe_ratio': round(random.uniform(0.5, 2.0), 2),
            'max_drawdown': round(random.uniform(-0.3, -0.05), 4),
            'win_rate': round(random.uniform(0.4, 0.8), 2)
        },
        {
            'backtest_id': 'bt_002',
            'strategy': 'RSI Mean Reversion',
            'total_return': round(random.uniform(-0.1, 0.4), 4),
            'sharpe_ratio': round(random.uniform(0.3, 1.5), 2),
            'max_drawdown': round(random.uniform(-0.25, -0.05), 4),
            'win_rate': round(random.uniform(0.45, 0.75), 2)
        }
    ]


def generate_mock_watchlist() -> List[Dict]:
    """Generate mock watchlist items"""
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'SPY']
    return [
        {
            'ticker': ticker,
            'name': f'{ticker} Inc.',
            'current_price': round(random.uniform(50, 500), 2),
            'added_date': (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat()
        }
        for ticker in random.sample(tickers, random.randint(3, 6))
    ]

def get_mock_watchlist_items() -> Dict:
    """Get mock watchlist items in WatchlistResponse format"""
    items = generate_mock_watchlist()
    return {
        'status': 'success',
        'data': [
            {
                'ticker': item['ticker'],
                'name': item['name'],
                'current_price': item['current_price'],
                'change_24h': round(random.uniform(-5, 5), 2),
                'added_date': item['added_date']
            }
            for item in items
        ],
        'total_items': len(items),
        'updated_at': datetime.now().isoformat()
    }