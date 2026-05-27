# Setup Guide - API Configuration

## ⚠️ Security First

Your API keys have been provided and are extremely sensitive. Follow these steps:

### 1. Create `.env` File

```bash
cp .env.example .env
```

### 2. Update `.env` with Your API Keys

```env
# Alpha Vantage - Stock market data
ALPHA_VANTAGE_API_KEY=YOUR_ALPHA_VANTAGE_API_KEY

# FRED - Federal Reserve Economic Data
FRED_API_KEY=YOUR_FRED_API_KEY

# Fin Hub - Financial data aggregator
FIN_HUB_API_KEY=YOUR_FINHUB_API_KEY

# News API - Financial news
NEWS_API_KEY=139f0bcd5fa848998c2b327b5129d8fb

# Groq - LLM for analysis
GROQ_API_KEY=YOUR_GROQ_API_KEY
```

### 3. Verify `.env` is Ignored

The `.gitignore` file has been updated to exclude:
- `.env` files
- `.env.*.local`
- All environment-specific configs

**Never commit `.env` to version control.**

### 4. Rotate Your Keys

Since these keys were shared in chat:
1. ⚠️ **Regenerate all API keys** from their respective services
2. Update your `.env` with the new keys
3. Immediately revoke the old keys if possible

### 5. Enable Real Data Providers

Update `backend/app/core/config.py` or `.env` to use real providers:

```python
# In .env
MARKET_DATA_PROVIDER=fin_hub  # Instead of "mock"
```

Or in code:
```python
from app.services.real_data_providers import FinHubProvider

provider = FinHubProvider(api_key="your_key")
```

## API Provider Mapping

| Service | Provider Class | Env Variable | Uses |
|---------|---|---|---|
| Alpha Vantage | `AlphaVantageProvider` | `ALPHA_VANTAGE_API_KEY` | Stock data, OHLCV |  
| FRED | `FREDProvider` | `FRED_API_KEY` | Economic indicators |
| Fin Hub | `FinHubProvider` | `FIN_HUB_API_KEY` | Aggregated market data |
| News API | `NewsAPIProvider` | `NEWS_API_KEY` | Financial news |
| Groq | `GroqAnalystProvider` | `GROQ_API_KEY` | AI report generation |

## File Structure

```
backend/
├── app/
│   ├── core/
│   │   └── config.py          # Updated with new API key configs
│   └── services/
│       ├── mock_data.py        # Mock data (development)
│       ├── real_data_providers.py  # Real API providers
│       └── groq_provider.py    # Groq LLM integration
│
├── .env                        # ← Your secure config (DO NOT COMMIT)
├── .env.example                # ← Template for setup
└── .gitignore                  # ← Updated to ignore .env
```

## Usage Examples

### Using Real Alpha Vantage Provider
```python
from app.services.real_data_providers import AlphaVantageProvider

provider = AlphaVantageProvider(api_key="your_key")
asset = await provider.get_asset_detail("AAPL")
```

### Switching Between Mock and Real Data

In your routes, you can conditionally use providers:

```python
from app.core.config import get_settings
from app.services import mock_data, real_data_providers

settings = get_settings()

if settings.market_data_provider == "mock":
    data = mock_data.get_mock_asset_detail("AAPL")
else:
    provider = real_data_providers.AlphaVantageProvider(
        settings.alpha_vantage_key
    )
    data = await provider.get_asset_detail("AAPL")
```

### Using Groq for AI Reports
```python
from app.services.groq_provider import get_groq_provider
from app.core.config import get_settings

settings = get_settings()
groq = get_groq_provider(settings.groq_api_key)

if groq:
    report = await groq.generate_analyst_report(
        ticker="AAPL",
        context={"price": 189.45, "pe_ratio": 28.4}
    )
else:
    # Fall back to mock data
    report = mock_data.get_mock_analyst_report("AAPL")
```

## Testing the Integration

```bash
# Test with environment variables
export ALPHA_VANTAGE_API_KEY="your_key"
export GROQ_API_KEY="your_key"

# Run tests
pytest backend/tests/test_providers.py

# Or test manually
python3 backend/scripts/test_real_providers.py
```

## API Rate Limits

⚠️ Each API has rate limits. Monitor the following:

| API | Free Tier Limit | Cost |
|-----|---|---|
| Alpha Vantage | 5 req/min | $$$$ for premium |
| FRED | 120 req/min | Free |
| Fin Hub | 60 req/min | $$$$ for real-time |
| News API | 100 req/day | Free tier available |
| Groq | 30 req/min | Free tier available |

## Recommendations

1. **Development**: Use mock data + Alpha Vantage (higher limits available)
2. **Production**: Use Fin Hub (aggregates multiple sources) + Groq (superior inference)
3. **Caching**: Implement aggressive caching to minimize API calls
4. **Fallbacks**: Always fall back to mock data when real API fails

## Next Steps

1. Copy `.env.example` → `.env` with real keys
2. Test one provider at a time
3. Implement caching strategy
4. Add error handling and retry logic
5. Monitor API usage and costs
