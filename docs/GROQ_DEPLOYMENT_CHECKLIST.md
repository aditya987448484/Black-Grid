# Groq Reasoning Layer - Deployment Checklist

> Complete checklist for deploying and maintaining the Groq reasoning layer

---

## ✅ Pre-Deployment Verification

### Code Quality & Safety

- [ ] **Syntax Validation**
  ```bash
  python -m py_compile backend/app/services/reasoning_provider.py
  python -m py_compile backend/app/api/routes/report.py
  ```
  Expected: No output (success)

- [ ] **Type Checking**
  ```bash
  cd backend && mypy app/services/reasoning_provider.py --ignore-missing-imports
  cd backend && mypy app/api/routes/report.py --ignore-missing-imports
  ```
  Expected: No type errors

- [ ] **Import Verification**
  ```bash
  python -c "from app.services.reasoning_provider import GroqReasoningProvider"
  python -c "from app.api.routes.report import get_report"
  ```
  Expected: No import errors

- [ ] **Backend Startup**
  ```bash
  cd backend && uvicorn app.main:app --reload
  ```
  Expected: Server starts on port 8000, no errors

### Code Review

- [ ] **reasoning_provider.py**
  - [ ] `generate_analyst_report()` method exists
  - [ ] All 9 prompt builders present
  - [ ] All 9 response parsers present
  - [ ] Error handling in each section
  - [ ] Logging statements in place
  - [ ] Type hints on all methods
  - [ ] Docstrings comprehensive

- [ ] **report.py**
  - [ ] 6-source data aggregation present
  - [ ] Try/except on each data source
  - [ ] 3-level fallback chain implemented
  - [ ] Groq call with all 6 parameters
  - [ ] Error handling and logging
  - [ ] Response wrapped in correct schema
  - [ ] Docstring explains data flow

### Configuration

- [ ] **Environment Setup**
  ```bash
  # Check if .env file exists
  ls -la backend/.env
  
  # Verify it's not tracked by git
  git check-ignore backend/.env
  ```
  Expected: File exists and is ignored

- [ ] **GROQ_API_KEY Present**
  ```bash
  grep GROQ_API_KEY backend/.env
  ```
  Expected: `GROQ_API_KEY=gsk_...`

- [ ] **.env Not Committed**
  ```bash
  git log --oneline | grep -i env
  ```
  Expected: No commits with .env

### Schema & Data

- [ ] **AnalystReportResponse Schema**
  ```bash
  grep -A5 "class AnalystReportResponse" backend/app/schemas/schemas.py
  ```
  Expected: Schema fields defined

- [ ] **AnalystReport Schema**
  ```bash
  grep -A30 "class AnalystReport" backend/app/schemas/schemas.py
  ```
  Expected: All 9 sections defined

- [ ] **Mock Provider Compatible**
  ```bash
  python -c "from app.services.reasoning_provider import MockReasoningProvider"
  ```
  Expected: No import errors

### Documentation

- [ ] **GROQ_REASONING_LAYER.md** exists
- [ ] **GROQ_QUICK_REFERENCE.md** exists
- [ ] **GROQ_TESTING_GUIDE.md** exists
- [ ] **GROQ_IMPLEMENTATION_SUMMARY.md** exists
- [ ] All links valid (no 404s)
- [ ] Code examples runnable
- [ ] API key instructions clear

---

## 🧪 Pre-Deployment Testing

### Level 1: Mock Provider Testing

```bash
# Terminal 1: Start backend with NO API key
GROQ_API_KEY="" uvicorn app.main:app --reload --log-level debug

# Terminal 2: Run tests
```

- [ ] **Mock Report Generation**
  ```bash
  curl -s http://localhost:8000/api/report/AAPL | jq '.data.ticker'
  ```
  Expected: `"AAPL"` (instant response)

- [ ] **All Sections Present**
  ```bash
  curl -s http://localhost:8000/api/report/AAPL | jq '.data | keys | length'
  ```
  Expected: `14` (all sections)

- [ ] **Valid Confidence Score**
  ```bash
  curl -s http://localhost:8000/api/report/AAPL | jq '.data.confidence_score'
  ```
  Expected: Number between 0-100

- [ ] **Bull/Bear Probabilities Sum~100%**
  ```bash
  curl -s http://localhost:8000/api/report/AAPL | \
    jq '.data | {bull: .bull_case.probability, bear: .bear_case.probability, sum: (.bull_case.probability + .bear_case.probability)}'
  ```
  Expected: Sum ≈ 100

- [ ] **Multiple Tickers Work**
  ```bash
  for ticker in AAPL MSFT GOOGL; do
    echo "$ticker:"
    curl -s http://localhost:8000/api/report/$ticker | jq '.data.ticker'
  done
  ```
  Expected: Each returns matching ticker

- [ ] **Fast Response Times**
  ```bash
  time curl -s http://localhost:8000/api/report/AAPL > /dev/null
  ```
  Expected: < 100ms

- [ ] **Logs Show Mock Provider**
  ```bash
  # Check Terminal 1 logs for:
  # "Using mock reasoning provider"
  ```
  Expected: Message appears in logs

### Level 2: Groq API Testing

```bash
# Add GROQ_API_KEY to backend/.env
echo "GROQ_API_KEY=gsk_YOUR_KEY" >> backend/.env

# Restart backend
uvicorn app.main:app --reload --log-level debug
```

- [ ] **Real Report Generation**
  ```bash
  curl -s http://localhost:8000/api/report/AAPL | jq '.data.executive_summary' | head -c 100
  ```
  Expected: AI-generated text (not mock placeholder)

- [ ] **Reasonable Generation Time**
  ```bash
  time curl -s http://localhost:8000/api/report/AAPL > /dev/null
  ```
  Expected: 15-20 seconds

- [ ] **Quality Check**
  ```bash
  curl -s http://localhost:8000/api/report/AAPL | jq '.data.technical_view.summary' -r
  ```
  Expected: Substantive technical analysis (not generic)

- [ ] **Logs Show Groq Provider**
  ```bash
  # Check logs for:
  # "Successfully generated AI analyst report"
  # "Groq API request successful"
  ```
  Expected: Messages indicate Groq used

- [ ] **All Sections Have Content**
  ```bash
  curl -s http://localhost:8000/api/report/AAPL | jq '.data | with_entries(select(.value == null or .value == "")) | length'
  ```
  Expected: `0` (no empty sections)

- [ ] **Rating Matches Technicals**
  ```bash
  curl -s http://localhost:8000/api/report/AAPL | jq '.data | {recommendation: .final_rating.recommendation, signal_strength: .technical_view.signal_strength}'
  ```
  Expected: BUY when signal_strength high, SELL when low, etc.

### Level 3: Error Handling Testing

- [ ] **Invalid API Key Falls Back to Mock**
  ```bash
  # Edit backend/.env to have invalid key
  echo "GROQ_API_KEY=invalid_key_12345" > backend/.env
  
  # Restart backend
  uvicorn app.main:app --reload
  
  # Test - should still return valid report
  curl -s http://localhost:8000/api/report/AAPL | jq '.data.ticker'
  ```
  Expected: Returns mock report (not error)

- [ ] **Missing API Key Falls Back to Mock**
  ```bash
  # Remove API key
  echo "GROQ_API_KEY=" >> backend/.env
  
  # Restart backend
  # Test
  curl -s http://localhost:8000/api/report/AAPL | jq '.data.ticker'
  ```
  Expected: Returns mock report

- [ ] **Network Error Handling**
  ```bash
  # Simulate network error by providing unreachable endpoint
  # (Groq API has timeout, will fall back to mock)
  ```
  Expected: Falls back to mock gracefully

- [ ] **Logs Show Fallback**(in case of error)
  ```bash
  # Check logs for fallback messages
  ```
  Expected: Appropriate warning/error messages

### Level 4: Performance Testing

- [ ] **Rate Limit Awareness**
  ```bash
  # Try 31 rapid requests
  for i in {1..31}; do
    curl -s http://localhost:8000/api/report/AAPL > /dev/null &
  done
  wait
  
  # Check logs for rate limit handling
  ```
  Expected: No crashes, graceful handling

- [ ] **Memory Usage Reasonable**
  ```bash
  # Monitor memory while generating reports
  top -b -n 1 | grep python
  
  # Generate reports and check memory doesn't spike excessively
  ```
  Expected: Memory usage stable < 200MB

- [ ] **No Timeouts Under 60s**
  ```bash
  timeout 60 curl -s http://localhost:8000/api/report/AAPL > /dev/null
  ```
  Expected: Completes before timeout

### Level 5: Frontend Integration Testing

```bash
# Terminal 1: Backend running
cd backend && uvicorn app.main:app --reload

# Terminal 2: Frontend running
cd frontend && npm run dev
```

- [ ] **Report Page Loads**
  ```bash
  curl http://localhost:3000/report | grep -q "Report" && echo "✅ Page loaded"
  ```
  Expected: Page loads without errors

- [ ] **Search Functionality Works**
  - [ ] Navigate to http://localhost:3000/report
  - [ ] Enter "AAPL" in search
  - [ ] Click search
  - [ ] Expected: Report loads with sections

- [ ] **All Sections Display**
  - [ ] Executive Summary visible
  - [ ] Investment Highlight visible
  - [ ] Technical View visible
  - [ ] Fundamental Snapshot visible
  - [ ] Macro Context visible
  - [ ] Bull Case visible
  - [ ] Bear Case visible
  - [ ] Risks visible
  - [ ] Catalysts visible
  - [ ] Final Rating visible

- [ ] **Loading States Work**
  - [ ] Slow down network (DevTools)
  - [ ] Refresh page
  - [ ] Expected: Shows loading skeleton

- [ ] **Error States Handled**
  - [ ] Stop backend
  - [ ] Try to load report
  - [ ] Expected: Shows error message (not crash)

---

## 🚀 Deployment Steps

### Step 1: Pre-Deployment Check

```bash
# Run full checklist above
# Verify all items pass

# Run tests
python GROQ_TESTING_GUIDE.md  # (conceptual - run actual test scripts)
```

- [ ] All pre-deployment tests pass
- [ ] No errors in logs
- [ ] Performance acceptable
- [ ] Error handling verified

### Step 2: Production Configuration

```bash
# Production backend/.env
cat > backend/.env << EOF
GROQ_API_KEY=gsk_YOUR_PRODUCTION_KEY
DATABASE_URL=postgresql://user:pass@host/db
LOG_LEVEL=info
EOF

# Verify no secrets leaked
git diff backend/.env  # Should show nothing tracked
```

- [ ] GROQ_API_KEY set to production key
- [ ] Database URL correct
- [ ] Other config values correct
- [ ] .env not tracked by git

### Step 3: Code Deployment

```bash
# Tag release
git tag -a v1.4.0-groq -m "Release: Groq reasoning layer"

# Push to production
git push origin v1.4.0-groq

# Deploy
# (deployment process depends on infrastructure)
```

- [ ] Code pushed to repository
- [ ] Version tagged appropriately
- [ ] Deployment pipeline triggered

### Step 4: Production Verification

```bash
# On production box
curl https://api.production.com/api/report/AAPL

# Check logs
tail -f /var/log/app.log | grep -E "Groq|analyst"
```

- [ ] API endpoint responds
- [ ] Reports generate successfully
- [ ] Logs show successful generation
- [ ] No errors in production logs

### Step 5: Monitoring Setup

- [ ] Set up alerts for Groq API errors
- [ ] Monitor report generation times
- [ ] Track rate limit usage
- [ ] Monitor error rates
- [ ] Set up performance dashboards

---

## 📊 Post-Deployment Monitoring

### Daily Checks

- [ ] **API Status**
  ```bash
  curl https://api.production.com/health
  ```
  Expected: 200 OK

- [ ] **Report Generation Success Rate**
  ```bash
  # Check logs for error count
  grep "Failed to generate" /var/log/app.log | wc -l
  ```
  Expected: 0 or very low

- [ ] **Average Generation Time**
  ```bash
  # Monitor report generation latency
  # Expected: 15-20 seconds for Groq
  ```

- [ ] **Groq API Status**
  ```bash
  # Check status page
  curl https://status.groq.com
  ```
  Expected: All systems operational

### Weekly Checks

- [ ] **Error Log Review**
  - [ ] Look for patterns in errors
  - [ ] Check for rate limit hits
  - [ ] Review timeout occurrences
  - [ ] Monitor mock fallback usage

- [ ] **Performance Metrics**
  - [ ] Average response time still 15-20s?
  - [ ] Memory leaks detected?
  - [ ] CPU usage reasonable?

- [ ] **Cost Analysis**
  - [ ] API calls within budget?
  - [ ] Rate limiting necessary?
  - [ ] Usage trend analysis

- [ ] **Prompt Quality**
  - [ ] Check sample reports
  - [ ] Verify analysis quality
  - [ ] Look for hallucinations
  - [ ] Monitor user feedback

### Monthly Reviews

- [ ] **Report Quality Audit**
  - [ ] Sample 10 reports
  - [ ] Grade quality 1-10
  - [ ] Document feedback
  - [ ] Plan prompt improvements

- [ ] **Performance Optimization**
  - [ ] Identify bottlenecks
  - [ ] Plan optimizations
  - [ ] Test improvements
  - [ ] Deploy if beneficial

- [ ] **Cost Optimization**
  - [ ] Review API spending
  - [ ] Evaluate caching benefits
  - [ ] Consider batch processing
  - [ ] Optimize token usage

- [ ] **Security Audit**
  - [ ] Check API key exposure
  - [ ] Verify .env file permissions
  - [ ] Review access logs
  - [ ] Update any exposed keys

---

## 🔧 Maintenance Tasks

### Regular Backups

- [ ] **Database Backups**
  ```bash
  # Daily automatic backups
  # Verify: ls -la /backups/db/
  ```
  Expected: Recent backup files exist

- [ ] **Configuration Backups**
  ```bash
  # Backup .env files
  # Verify: ls -la /backups/config/
  ```
  Expected: Configuration backed up

### Log Management

- [ ] **Log Rotation**
  ```bash
  # Set up logrotate for app logs
  # Verify: cat /etc/logrotate.d/axiom
  ```
  Expected: Rotation configured

- [ ] **Log Archival**
  - [ ] Archive logs older than 30 days
  - [ ] Store in S3 or equivalent
  - [ ] Keep for 90 days minimum

### Dependency Updates

- [ ] **Python Dependencies**
  ```bash
  # Check for updates
  pip list --outdated
  
  # Test updates on staging
  # Deploy to production if safe
  ```
  Expected: Dependencies kept current

- [ ] **Front-End Dependencies**
  ```bash
  # Check for updates
  npm outdated
  
  # Test updates
  npm audit
  ```
  Expected: No critical vulnerabilities

### Prompt Tuning

- [ ] **Weekly Prompt Review**
  - [ ] Read 5 generated reports
  - [ ] Note issues or improvements
  - [ ] Update prompts based on feedback
  - [ ] Test changes on staging

- [ ] **Monthly Prompt Optimization**
  - [ ] Analyze common issues
  - [ ] Refine prompt language
  - [ ] Add examples if needed
  - [ ] Deploy improved versions

---

## ⚠️ Troubleshooting During Deployment

| Issue | Diagnosis | Resolution |
|-------|-----------|-----------|
| Import errors | Missing dependencies | `pip install -r requirements.txt` |
| API key not found | .env not loaded | Check path, restart server |
| Slow API calls | Rate limited | Check usage, wait 60s |
| Invalid JSON response | Parser issue | Check logs, test with mock |
| High memory usage | Possible leak | Restart server, check logs |
| Timeout errors | Groq API slow | Check status page, add retry |
| Reports missing sections | Data fetch failed | Check data sources, logs |

---

## 📋 Final Sign-Off

Before going live, confirm:

### Security
- [ ] No secrets in code
- [ ] .env file not tracked
- [ ] API keys secured
- [ ] Database credentials safe
- [ ] HTTPS/TLS enabled
- [ ] CORS configured properly

### Performance
- [ ] Response times acceptable
- [ ] Memory usage reasonable
- [ ] CPU usage normal
- [ ] Database queries optimized
- [ ] Rate limiting working

### Reliability
- [ ] Error handling comprehensive
- [ ] Logging enabled
- [ ] Monitoring set up
- [ ] Alerts configured
- [ ] Backup procedures in place

### Quality
- [ ] Tests passing
- [ ] Code reviewed
- [ ] Documentation complete
- [ ] Deployed on staging first
- [ ] User acceptance testing done

### Compliance
- [ ] Data privacy respected
- [ ] API terms complied with
- [ ] Licenses verified
- [ ] Audit logs enabled
- [ ] Regulations followed

---

## ✨ Success Criteria

### Deployment Successful When:

✅ User can request report and receive valid JSON response
✅ Report contains all 9 sections with substantive content
✅ Report generation time 15-20 seconds (Groq) or <100ms (mock)
✅ Error handling works (graceful fallback to mock)
✅ Frontend displays report sections correctly
✅ No errors in server logs
✅ Monitoring shows normal operation
✅ Rate limits respected
✅ Security best practices followed

### Ready for Production When:

✅ All deployment checklist items complete
✅ All tests passing on production environment
✅ Monitoring dashboards active
✅ Alert system working
✅ Backup procedures verified
✅ Security audit complete
✅ Performance metrics acceptable
✅ Team trained on maintenance

---

**Deployment Package Ready for Release**

Everything is in place for safe, reliable deployment of the Groq reasoning layer. Follow this checklist for seamless production rollout.

Good luck! 🚀
