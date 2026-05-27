# Groq Reasoning Layer - Quick Reference

> Fast reference for using and customizing the AI reasoning layer

## Quick Start

### Setup (1 minute)

```bash
# 1. Get Groq API key
# Visit: https://console.groq.com → Sign up → Create API key

# 2. Add to backend/.env
echo "GROQ_API_KEY=gsk_YOUR_KEY" >> backend/.env

# 3. Start backend
cd backend && uvicorn app.main:app --reload
```

### Test It

```bash
# Terminal 1: Start backend
cd backend && uvicorn app.main:app --reload

# Terminal 2: Call report endpoint
curl http://localhost:8000/api/report/AAPL | jq

# Should return full analyst report (15-20 seconds)
```

## Common Tasks

### Get a Reasoning Service

```python
from app.api.service_factory import ServiceFactory

# This automatically selects Groq or Mock based on API key
service = ServiceFactory.get_reasoning_service()
```

### Generate a Report

```python
report = await service.provider.generate_analyst_report(
    ticker="AAPL",
    asset_info={
        "name": "Apple Inc.",
        "price": 189.45,
        "change": 5.12,
    },
    technical_data={
        "trend": "Uptrend",
        "support_levels": [185.50, 180.00],
        "resistance_levels": [195.00, 205.00],
    },
    fundamental_data={
        "eps": 6.05,
        "revenue_growth": 8.5,
        "profit_margin": 28.2,
        "roe": 88.5,
        "debt_to_equity": 1.8,
    },
    macro_context={
        "gdp_growth": 2.5,
        "inflation_rate": 3.2,
        "unemployment_rate": 4.0,
        "fed_rate": 4.5,
    },
    forecast_data={
        "consensus_signal": "BUY",
        "confidence": 78.5,
        "expected_return": 5.8,
    },
    sec_summary={
        "recent_filings": ["10-K", "10-Q"],
        "cik": "000320193",
    }
)

# report contains all 9 sections + confidence score
print(report["technical_view"])
print(report["bull_case"])
print(report["final_rating"])
```

### Analyze Any Data

```python
# Sentiment analysis
analysis = await service.analyze("sentiment", 
    {"text": "Apple stock is outperforming"},
    ticker="AAPL"
)

# Technical analysis
analysis = await service.analyze("technical",
    {"price_data": [...], "volume": [...]},
    ticker="AAPL"
)
```

### Ask Questions

```python
explanation = await service.explain(
    "What will drive Apple's growth in 2026?",
    context={
        "price": 189.45,
        "sector": "Technology",
        "forecast": "BUY"
    }
)
```

## Customizing Prompts

### Edit Prompt for Executive Summary

**File:** `app/services/reasoning_provider.py`

**Find this method:**
```python
def _build_executive_summary_prompt(self, ticker: str, context: Dict[str, Any]) -> str:
```

**Modify the prompt text:**
```python
def _build_executive_summary_prompt(self, ticker: str, context: Dict[str, Any]) -> str:
    """Build executive summary prompt - CUSTOMIZABLE"""
    price = context.get("asset_info", {}).get("price", "unknown")
    
    return f"""
Analyze {ticker} trading at ${price}.
Write a SHORT (2-3 sentence) executive summary.
Include 1 key investment highlight.

Format as JSON:
{{
  "executive_summary": "...",
  "investment_highlight": "...",
  "key_thesis": "..."
}}
"""
```

### Edit Technical Prompt

**Method:** `_build_technical_report_prompt()`

**Common customizations:**
- Add more technical indicators
- Request specific patterns (breakouts, support holds)
- Change output format
- Add price targets

**Example:**
```python
def _build_technical_report_prompt(self, ticker: str, context: Dict[str, Any]) -> str:
    technical = context.get("technical_data", {})
    
    return f"""
Technical Analysis for {ticker}:
- Current Trend: {technical.get('trend')}
- Support: {technical.get('support_levels')}
- Resistance: {technical.get('resistance_levels')}

Analyze:
1. Trend confirmation (is it real?)
2. Likely next move (up or down)
3. Key risk zones
4. Candlestick patterns

Return JSON with: trend, key_levels, signal_strength, momentum, ma_alignment, summary
"""
```

### Edit Fundamental Analysis

**Method:** `_build_fundamental_report_prompt()`

**Customize to emphasize:**
- Specific metrics (profitability vs growth)
- Industry benchmarking
- Valuation focus
- Quality assessment

## Debugging

### Check if Groq is Connected

```python
# In any route or service
reasoning_service = ServiceFactory.get_reasoning_service()
provider_type = type(reasoning_service.provider).__name__

if "Groq" in provider_type:
    print("✅ Using REAL Groq LLM")
else:
    print("⚠️  Using Mock provider - Set GROQ_API_KEY")
```

### View Generated Report Sections

```bash
# Make request with verbose logging
curl -v http://localhost:8000/api/report/AAPL 2>&1 | head -100

# Check backend logs for:
# "Successfully generated AI analyst report"
# "Using mock reasoning provider"
# "JSON parsing failed for section..."
```

### Test with Mock Provider

```bash
# Remove API key (forces mock provider)
GROQ_API_KEY="" uvicorn app.main:app --reload

# Test - should return instantly (< 100ms)
curl http://localhost:8000/api/report/AAPL

# Check logs for: "Using mock reasoning provider"
```

## Schema Reference

### Input Data Structure

```python
{
    "ticker": str,           # "AAPL"
    "asset_info": {          # Company/market info
        "name": str,         # "Apple Inc."
        "price": float,      # 189.45
        "change": float,     # 5.12
        "sector": str,       # "Technology"
    },
    "technical_data": {      # Chart and technicals
        "trend": str,        # "Uptrend"
        "support_levels": [float, ...],
        "resistance_levels": [float, ...],
        "indicators": {
            "rsi_14": float,
            "macd": str,
        }
    },
    "fundamental_data": {    # Company metrics
        "eps": float,        # 6.05
        "revenue_growth": float,     # 8.5
        "profit_margin": float,      # 28.2
        "roe": float,        # 88.5
        "debt_to_equity": float,     # 1.8
    },
    "macro_context": {       # Economic indicators
        "gdp_growth": float,
        "inflation_rate": float,
        "unemployment_rate": float,
        "fed_rate": float,
    },
    "forecast_data": {       # ML predictions
        "consensus_signal": str,     # "BUY"/"HOLD"/"SELL"
        "confidence": float,   # 78.5
        "expected_return": float,    # 5.8
    },
    "sec_summary": {         # Filing info (optional)
        "recent_filings": [str, ...],
        "cik": str,
    }
}
```

### Output Report Structure

```python
{
    "executive_summary": str,
    "investment_highlight": str,
    
    "technical_view": {
        "trend": str,
        "key_levels": [float, ...],
        "signal_strength": float,
        "momentum": str,
        "ma_alignment": str,
        "summary": str,
    },
    
    "fundamental_snapshot": {
        "eps": float,
        "revenue_growth": float,
        "profit_margin": float,
        "roe": float,
        "debt_to_equity": float,
        "valuation_assessment": str,
        "quality_score": float,
    },
    
    "macro_context": {
        "sector_performance": str,
        "industry_tailwinds": [str, ...],
        "macro_headwinds": [str, ...],
        "correlation_market": float,
        "macro_outlook": str,
    },
    
    "bull_case": {
        "thesis": str,
        "key_catalysts": [str, ...],
        "timeline": str,
        "probability": float,
    },
    
    "bear_case": {
        "thesis": str,
        "key_catalysts": [str, ...],
        "timeline": str,
        "probability": float,
    },
    
    "risks": [
        {
            "description": str,
            "severity": str,       # "High"/"Medium"/"Low"
            "mitigation": str,
        }
    ],
    
    "catalysts": [
        {
            "description": str,
            "impact": str,
        }
    ],
    
    "final_rating": {
        "recommendation": str,     # "BUY"/"HOLD"/"SELL"
        "target_price": float,
        "price_upside": float,
        "conviction": str,         # "High"/"Medium"/"Low"
        "rationale": str,
    },
    
    "confidence_score": float,     # 0-100
}
```

## Configuration

### Environment Variables

```bash
# backend/.env

# ✅ Enable real Groq AI (get key from console.groq.com)
GROQ_API_KEY=gsk_YOUR_KEY_HERE

# ❌ Disable real Groq (uses mock) 
GROQ_API_KEY=""

# Optional: Control model and timeout
GROQ_MODEL=mixtral-8x7b-32768
GROQ_TIMEOUT=60
```

### Provider Selection

```python
# Automatic selection based on API key:

if GROQ_API_KEY exists and valid:
    GroqReasoningProvider()  # Real AI
else:
    MockReasoningProvider()  # Development/fallback
```

## Performance

### Groq Free Tier Limits

| Metric | Value |
|--------|-------|
| Model | mixtral-8x7b (fast) |
| Rate Limit | 30 requests/minute |
| Timeout | 60 seconds |
| Cost | Free |

### Generation Times

| Report Section | Time |
|---------|------|
| Single section | 1-2 sec |
| Full report (9) | 15-20 sec |
| Mock report | < 100 ms |

### Tips

- Don't generate >30 reports/minute
- Mock provider is unlimited
- Use mock for development
- Real Groq for staging/production

## Fallback Chain

```
Request Report
    ↓
Try Groq LLM (real AI)
    ├─ ✅ Success → Return report
    ├─ ❌ Error → Log warning
    │
Try Mock Provider
    ├─ ✅ Success → Return report  
    ├─ ❌ Error → Log error
    │
Return HTTP 500
```

## Testing Checklist

- [ ] Backend starts without GROQ_API_KEY
- [ ] Report endpoint returns mock data
- [ ] Add GROQ_API_KEY to .env
- [ ] Restart backend
- [ ] Report endpoint returns real AI report
- [ ] Check confidence_score is 0-100
- [ ] Check bull + bear probabilities ≈ 100%
- [ ] Test with different tickers (AAPL, MSFT, TSLA)
- [ ] Verify all 9 sections populated
- [ ] Check logs for "Successfully generated"

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Mock reports returned | Check GROQ_API_KEY in backend/.env |
| "Status 429" errors | Free tier: 30 req/min limit. Wait 60s |
| Very slow reports | Normal: 15-20 seconds. Check network |
| Invalid JSON error | Check server logs. Parser has fallbacks |
| Reports missing sections | Check if required data passed in |

## Examples

### Full End-to-End Example

```bash
# Terminal 1: Start backend
cd backend && uvicorn app.main:app --reload

# Terminal 2: Generate report
curl -s http://localhost:8000/api/report/AAPL | jq '.data.technical_view'

# Output:
{
  "trend": "Uptrend",
  "key_levels": [185.5, 195, 205],
  "signal_strength": 78.5,
  "momentum": "Strong",
  "ma_alignment": "Bullish",
  "summary": "..."
}
```

### Python Integration

```python
from app.api.service_factory import ServiceFactory
import asyncio

async def get_report(ticker):
    service = ServiceFactory.get_reasoning_service()
    
    report = await service.provider.generate_analyst_report(
        ticker=ticker,
        asset_info={"price": 100.00, "name": ticker},
        technical_data={"trend": "Uptrend"},
        fundamental_data={"eps": 5.0},
        macro_context={},
        forecast_data={"consensus_signal": "BUY"},
    )
    
    return report

# Run
report = asyncio.run(get_report("AAPL"))
print(report["final_rating"]["recommendation"])
```

---

**Key Takeaway:** The Groq reasoning layer provides AI-powered analysis with mock fallback. Start with mock for development, add your API key for real AI.
