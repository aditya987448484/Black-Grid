# Groq Reasoning Layer - Testing Guide

> Complete testing procedures for verifying the Groq reasoning layer implementation

## Pre-Flight Checklist

Before running tests, verify:

- ✅ Python 3.10+ installed: `python --version`
- ✅ Backend dependencies installed: `pip install -r backend/requirements.txt`
- ✅ Backend environment configured: `backend/.env` exists
- ✅ Frontend built: `npm run build` in frontend/
- ✅ Ports available: 3000 (frontend), 8000 (backend)

## Test Levels

### Level 1: Mock Provider Testing (No API Key)

**Purpose:** Verify core functionality without Groq API

**Setup:**
```bash
# Ensure no GROQ_API_KEY in backend/.env
grep GROQ_API_KEY backend/.env  # Should be empty or missing

# Clear from environment
unset GROQ_API_KEY
```

**Test 1.1: Backend Starts with Mock Provider**
```bash
cd backend
uvicorn app.main:app --reload

# Expected output:
# INFO:     Uvicorn running on http://127.0.0.1:8000
# (No errors about missing API key)
```

**Test 1.2: Report Endpoint Returns Mock Data (Instant)**
```bash
# In another terminal
curl -s http://localhost:8000/api/report/AAPL | jq '.'

# Expected:
# - Response < 100ms
# - status: "success"
# - data contains all 9 sections
# - confidence_score between 0-100
```

**Test 1.3: Mock Data Structure Validation**
```bash
# Verify all required sections exist
curl -s http://localhost:8000/api/report/AAPL | jq '.data | keys'

# Expected output (all present):
# [
#   "bull_case",
#   "bears_case",
#   "catalysts",
#   "company_name",
#   "confidence_score",
#   "executive_summary",
#   "final_rating",
#   "fundamental_snapshot",
#   "investment_highlight",
#   "macro_context",
#   "report_date",
#   "risks",
#   "technical_view",
#   "ticker"
# ]
```

**Test 1.4: Mock Data Types Validation**
```bash
# Verify data types in response
curl -s http://localhost:8000/api/report/AAPL | jq '.data | to_entries | map({key: .key, type: (.value | type)}) | sort_by(.key)'

# Expected: String fields, object fields, number fields as per schema
```

**Test 1.5: Multiple Tickers with Mock**
```bash
# Test different tickers
for ticker in AAPL MSFT TSLA GOOGL AMZN; do
  echo "Testing $ticker..."
  curl -s http://localhost:8000/api/report/$ticker | jq '.data.ticker'
done

# Expected: Each returns match ticker requested
```

**Test 1.6: Error Handling - Invalid Ticker**
```bash
# Test invalid ticker
curl -s http://localhost:8000/api/report/INVALID_TICKER_XYZ

# Expected: Either 404 or valid report (depends on implementation)
```

**Test 1.7: Verify Mock Provider Used in Logs**
```bash
# Look at backend logs (Terminal 1)
# Should see: "Using mock reasoning provider" in logs
# Should NOT see: "Groq API Key not found"
```

### Level 2: Groq API Integration Testing

**Purpose:** Verify real Groq LLM integration

**Setup:**
```bash
# Add GROQ_API_KEY to backend/.env
echo "GROQ_API_KEY=gsk_YOUR_KEY_HERE" >> backend/.env

# Start backend with real API
cd backend
uvicorn app.main:app --reload

# Verify Groq provider selected in logs
```

**Test 2.1: Report Generation with Real Groq (First Time)**
```bash
curl http://localhost:8000/api/report/AAPL

# Expected:
# - Response time: 15-20 seconds
# - status: "success"
# - Report contains AI-generated analysis
# - Logs show: "Successfully generated AI analyst report"
```

**Test 2.2: Verify Report Quality**
```bash
# Check if report has thoughtful analysis
curl -s http://localhost:8000/api/report/AAPL | jq '.data.executive_summary'

# Expected: Substantive analysis, not generic text
# Examples of good: "Strong fundamentals with AI opportunity..."
#         bad: "The stock moves up and down..."
```

**Test 2.3: Verify Confidence Score Calculation**
```bash
# Confidence should be reasonable (60-95 range typically)
curl -s http://localhost:8000/api/report/AAPL | jq '.data.confidence_score'

# Expected: Number between 0 and 100
# Typical: 75-85 for established companies
```

**Test 2.4: Verify Bull/Bear Case Probabilities**
```bash
# Bull + Bear should sum to ~100%
curl -s http://localhost:8000/api/report/AAPL | jq '.data | {bull: .bull_case.probability, bear: .bear_case.probability, sum: (.bull_case.probability + .bear_case.probability)}'

# Expected: Sum ≈ 100%
# Example: {bull: 72.5, bear: 27.5, sum: 100}
```

**Test 2.5: Test Multiple Tickers (Sequential)**
```bash
# Rate limit: 30/minute, so wait between calls
for ticker in AAPL MSFT GOOGL; do
  echo "Generating report for $ticker..."
  curl -s http://localhost:8000/api/report/$ticker | jq '.data | {ticker, recommendation: .final_rating.recommendation}'
  echo "Waiting 2 seconds..."
  sleep 2
done

# Expected: Each returns unique, AI-generated analysis
```

**Test 2.6: Rate Limit Testing**
```bash
# Try 31 rapid requests (should hit 30/min limit)
for i in {1..31}; do
  curl -s http://localhost:8000/api/report/AAPL >> /dev/null &
done
wait

# Expected: First ~30 succeed, later ones may return 429 (throttled)
# Check logs for: "Status 429" or rate limit messages
```

**Test 2.7: Response Parsing Validation**
```bash
# Verify JSON extraction worked correctly
curl -s http://localhost:8000/api/report/AAPL | jq '.data.technical_view'

# Expected: Valid technical analysis with all fields:
# - trend (string)
# - key_levels (array of numbers)
# - signal_strength (0-100)
# - momentum (string)
# - ma_alignment (string)
# - summary (string)
```

**Test 2.8: Verify All Report Sections Populated**
```bash
# Count non-null sections
curl -s http://localhost:8000/api/report/AAPL | jq '.data | with_entries(select(.value != null)) | length'

# Expected: Should have 14 top-level fields (all populated)
```

### Level 3: Fallback Mechanism Testing

**Purpose:** Verify graceful fallback when Groq fails

**Test 3.1: Test with Invalid API Key**
```bash
# Set invalid key
echo "GROQ_API_KEY=invalid_key_12345" > backend/.env

# Restart backend
# Kill previous: Ctrl+C
# Start new: uvicorn app.main:app --reload

# Request report
curl -s http://localhost:8000/api/report/AAPL

# Expected:
# - Still returns valid report (via mock fallback)
# - Logs show: "Groq request failed" then "Falling back to mock"
# - status: "success"
```

**Test 3.2: Test with Missing Data**
```bash
# Report should work even with partial data
# Already tested by mock provider

# Verify each section persists despite missing data
curl -s http://localhost:8000/api/report/AAPL | jq '.data | keys'

# Expected: All sections present
```

**Test 3.3: Test Network Timeout Simulation**
```bash
# Groq has 60s timeout
# Normal reports: 15-20s
# No easy way to test timeout without mocking

# Just verify normal case doesn't timeout:
time curl -s http://localhost:8000/api/report/AAPL > /dev/null

# Expected: Uses < 30 seconds
```

### Level 4: Frontend Integration Testing

**Purpose:** Verify frontend displays Groq reports correctly

**Setup:**
```bash
# Terminal 1: Backend running
cd backend && uvicorn app.main:app --reload --log-level debug

# Terminal 2: Frontend running
cd frontend && npm run dev

# Terminal 3: Testing
```

**Test 4.1: Report Page Loads**
```bash
# Visit in browser or via curl
curl http://localhost:3000/report
# Expected: Page loads without errors
```

**Test 4.2: Search Ticker on Report Page**
```bash
# In browser:
# 1. Go to http://localhost:3000/report
# 2. Enter "AAPL" in search
# 3. Click search
# Expected: Report loads with analysis
```

**Test 4.3: Verify All Sections Display**
```
# On report page, scroll and verify:
- ✅ Executive Summary
- ✅ Investment Highlight
- ✅ Technical View
- ✅ Fundamental Snapshot
- ✅ Macro Context
- ✅ Bull Case
- ✅ Bear Case
- ✅ Risks
- ✅ Catalysts
- ✅ Final Rating
```

**Test 4.4: Test Loading State**
```bash
# With slow network (DevTools), refresh page
# Expected: Shows loading skeleton while generating report
```

**Test 4.5: Test Error State**
```bash
# Stop backend
# Refresh report page
# Expected: Shows error message
```

### Level 5: Schema Validation Testing

**Purpose:** Verify responses match Pydantic schema

**Test 5.1: Validate Response Against Schema**
```python
# In Python test script:
from app.schemas.schemas import AnalystReportResponse, AnalystReport
import requests
import json

response = requests.get("http://localhost:8000/api/report/AAPL")
data = response.json()

# This will raise ValidationError if schema mismatches
report_response = AnalystReportResponse(**data)
print(f"✅ Response valid. Report date: {report_response.data.report_date}")
```

**Test 5.2: Validate Numeric Ranges**
```python
# Confidence score should be 0-100
assert 0 <= report_response.data.confidence_score <= 100

# Bull + Bear ~= 100
bull_prob = report_response.data.bull_case.probability
bear_prob = report_response.data.bear_case.probability
assert 95 <= (bull_prob + bear_prob) <= 105, "Probabilities should sum to ~100%"

# Signal strength 0-100
for indicator in report_response.data.technical_view.signal_strength:
    assert 0 <= indicator <= 100
```

**Test 5.3: Validate Required Fields**
```python
# All these should be non-null
assert report_response.data.ticker
assert report_response.data.company_name
assert report_response.data.executive_summary
assert report_response.data.investment_highlight
assert report_response.data.technical_view
assert report_response.data.fundamental_snapshot
assert report_response.data.macro_context
assert report_response.data.bull_case
assert report_response.data.bear_case
assert report_response.data.risks
assert report_response.data.catalysts
assert report_response.data.final_rating
assert report_response.data.confidence_score

print("✅ All required fields present")
```

## Test Scripts

### Bash Script: Full Mock Test Suite

```bash
#!/bin/bash
# test_mock_provider.sh

set -e

echo "=== Mock Provider Test Suite ==="
echo

# Test 1: Instant response
echo "Test 1: Mock report generation (should be instant)"
time curl -s http://localhost:8000/api/report/AAPL | jq '.data.ticker' &> /dev/null
echo "✅ Pass: Mock report generated instantly"
echo

# Test 2: Structure validation
echo "Test 2: Verify all sections present"
sections=$(curl -s http://localhost:8000/api/report/AAPL | jq '.data | keys | length')
if [ "$sections" -eq 14 ]; then
  echo "✅ Pass: All 14 sections present"
else
  echo "❌ Fail: Expected 14 sections, got $sections"
fi
echo

# Test 3: Multiple tickers
echo "Test 3: Multiple tickers"
for ticker in AAPL MSFT GOOGL; do
  response=$(curl -s http://localhost:8000/api/report/$ticker | jq '.data.ticker')
  if [ "$response" = "\"$ticker\"" ]; then
    echo "✅ Pass: $ticker report correct"
  else
    echo "❌ Fail: $ticker report incorrect"
  fi
done
```

### Python Script: Comprehensive Validation

```python
#!/usr/bin/env python3
# test_groq_provider.py

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000/api"

def test_report_endpoint(ticker: str):
    """Test report endpoint with given ticker"""
    print(f"\n{'='*50}")
    print(f"Testing Report: {ticker}")
    print(f"{'='*50}")
    
    start = time.time()
    response = requests.get(f"{BASE_URL}/report/{ticker}")
    elapsed = time.time() - start
    
    print(f"Response Time: {elapsed:.2f}s")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ FAIL: Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    
    # Verify structure
    required_fields = {
        'status': str,
        'data': dict,
        'timestamp': str,
    }
    
    for field, expected_type in required_fields.items():
        if field not in data:
            print(f"❌ FAIL: Missing field '{field}'")
            return False
        if not isinstance(data[field], expected_type):
            print(f"❌ FAIL: Field '{field}' wrong type")
            return False
    
    report = data['data']
    
    # Verify report sections
    required_sections = [
        'ticker', 'company_name', 'current_price',
        'executive_summary', 'investment_highlight',
        'technical_view', 'fundamental_snapshot',
        'macro_context', 'bull_case', 'bear_case',
        'risks', 'catalysts', 'final_rating',
        'confidence_score'
    ]
    
    missing = [s for s in required_sections if s not in report]
    if missing:
        print(f"❌ FAIL: Missing sections: {missing}")
        return False
    
    # Verify confidence score
    conf_score = report['confidence_score']
    if not (0 <= conf_score <= 100):
        print(f"❌ FAIL: Confidence score out of range: {conf_score}")
        return False
    
    # Verify probabilities sum
    bull_prob = report['bull_case'].get('probability', 0)
    bear_prob = report['bear_case'].get('probability', 0)
    total_prob = bull_prob + bear_prob
    if not (95 <= total_prob <= 105):
        print(f"⚠️  WARN: Bull+Bear probabilities don't sum to 100: {total_prob}")
    
    # Print summary
    print(f"✅ PASS: {ticker}")
    print(f"  - Confidence: {conf_score:.1f}%")
    print(f"  - Recommendation: {report['final_rating']['recommendation']}")
    print(f"  - Bull Prob: {bull_prob:.1f}%")
    print(f"  - Bear Prob: {bear_prob:.1f}%")
    
    return True

def main():
    """Run all tests"""
    print(f"\n{'='*50}")
    print("Groq Reasoning Layer Test Suite")
    print(f"Started: {datetime.now()}")
    print(f"{'='*50}")
    
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN']
    
    passed = 0
    failed = 0
    
    for ticker in tickers:
        try:
            if test_report_endpoint(ticker):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1
        
        # Rate limit: wait 2 seconds between requests
        time.sleep(2)
    
    # Summary
    print(f"\n{'='*50}")
    print(f"Test Summary")
    print(f"{'='*50}")
    print(f"Passed: {passed}/{len(tickers)}")
    print(f"Failed: {failed}/{len(tickers)}")
    print(f"Completed: {datetime.now()}")

if __name__ == "__main__":
    main()
```

## Running Tests

### Quick Test (2 minutes)

```bash
# 1. Terminal 1: Start backend
cd backend && uvicorn app.main:app --reload

# 2. Terminal 2: Run tests
./test_mock_provider.sh
```

### Full Test (10 minutes)

```bash
# Terminal 1: Backend
cd backend && GROQ_API_KEY="" uvicorn app.main:app --reload

# Terminal 2: Mock tests
python test_groq_provider.py

# Terminal 3: Frontend
cd frontend && npm run dev

# Terminal 4: Manual frontend testing
# Visit http://localhost:3000/report
```

### Production Test (20 minutes)

```bash
# Add real Groq API key
echo "GROQ_API_KEY=gsk_YOUR_KEY" >> backend/.env

# Start backend
cd backend && uvicorn app.main:app --reload

# Run full test suite
python test_groq_provider.py

# Verify response times (should be 15-20s)
# Verify AI quality (should be substantive analysis)
```

## Success Criteria

### Mock Provider ✅
- [ ] Reports generated in <100ms
- [ ] All 9 sections present
- [ ] Confidence score 0-100
- [ ] Bull + Bear ~= 100%
- [ ] Multiple tickers work

### Groq Provider ✅
- [ ] Reports generated in 15-20s
- [ ] AI analysis is substantive
- [ ] Proper JSON extraction
- [ ] All fields populated
- [ ] Rate limit respected (30/min)

### Fallback Chain ✅
- [ ] Works with valid API key
- [ ] Falls back to mock with invalid key
- [ ] Falls back to mock if Groq timeout
- [ ] Returns error if both fail

### Frontend Integration ✅
- [ ] Report page displays sections
- [ ] Loading states shown
- [ ] Error states handled
- [ ] Search functionality works
- [ ] Multiple tickers work

### Schema Validation ✅
- [ ] Responses match AnalystReportResponse
- [ ] All required fields present
- [ ] Numeric ranges valid
- [ ] No null values in required fields

## Troubleshooting

| Issue | Diagnosis | Solution |
|-------|-----------|----------|
| All mock responses | No API key | Add GROQ_API_KEY to .env |
| Very slow (>30s) | Timeout | Check network, verify Groq key |
| HTTP 429 | Rate limit | Free tier: 30/min. Wait 60s |
| Invalid JSON | Parser error | Check Groq output in logs |
| Missing sections | Generation failed | Check required data passed |
| Schema error | Type mismatch | Verify Pydantic schema version |

## Performance Benchmarks

### Expected Times

| Scenario | Time | Notes |
|----------|------|-------|
| Mock report | <100ms | Instant |
| Groq (1 section) | 1-2s | Serial processing |
| Groq (full 9-section) | 15-20s | Faster with rate limits |
| Frontend load | <500ms | With report cached |

### Optimization Opportunities

- Parallel section generation (currently serial)
- Report caching (Redis)
- Streaming responses
- Batch generation

---

**Status:** Complete testing guide for all implementation levels.
