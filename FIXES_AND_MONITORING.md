# 🔧 ESG Engine Fixes & Monitoring Guide

## 🚨 Issues Resolved

### 1. Enhanced Features Unavailable
**Problem**: "Enhanced features unavailable" error even with API keys configured.

**Solution**: 
- Fixed import paths in `backend/app.py` and `enhanced_analytics.py`
- Added proper fallback mechanisms
- Enhanced error handling for missing dependencies

### 2. Controversy Check Failures  
**Problem**: All controversy checks returning "500" errors.

**Solution**:
- Fixed async/sync compatibility issues in `analytics.py`
- Added better error handling for SEC RSS feed parsing
- Implemented fallback controversy data when API fails

### 3. ESG Score Accuracy Concerns
**Problem**: ESG scores and predictions could cause financial damage if inaccurate.

**Solution**:
- Created `ESGScoreValidator` class with industry benchmarks
- Added validation warnings for suspicious patterns
- Implemented accuracy disclaimers and confidence adjustments

## 🔍 Uptime Robot Monitoring Setup

### Step 1: Get API Keys
1. **Uptime Robot**: Sign up at https://uptimerobot.com
2. **News API**: Get free key at https://newsapi.org/
3. **Alpha Vantage**: Get free key at https://www.alphavantage.co/

### Step 2: Set Environment Variables

**For Streamlit Cloud**:
```
Go to app settings → Advanced settings → Secrets management
Add these variables:
- NEWS_API_KEY = your_news_api_key
- ALPHA_VANTAGE_API_KEY = your_alpha_vantage_key
```

**For Render**:
```
Go to service dashboard → Environment
Add these variables:
- NEWS_API_KEY = your_news_api_key  
- ALPHA_VANTAGE_API_KEY = your_alpha_vantage_key
```

### Step 3: Run Monitoring Setup
```bash
python uptime_monitoring.py
```

This will:
- Create monitors for your Streamlit and Render deployments
- Set up email alerts for downtime
- Configure health check endpoints

### Step 4: Monitor These Endpoints
- **Streamlit Frontend**: `https://your-app.streamlit.app`
- **Render Backend**: `https://your-api.onrender.com/health`
- **API Status**: `https://your-api.onrender.com/api/status`

## ⚠️ Critical Accuracy Warnings

### ESG Scores
- **Estimates Only**: Scores are based on limited public data
- **Not Investment Advice**: Should not be sole basis for financial decisions
- **Validation Required**: All scores include confidence levels and warnings
- **Industry Benchmarks**: Scores are validated against sector averages

### Stock Predictions
- **Maximum Confidence**: 70% (anything higher is unrealistic)
- **Model Limitations**: Simple linear regression has high uncertainty
- **Volatility Warnings**: Large predicted changes (>10%) are flagged
- **Data Requirements**: Minimum 6 months of data needed

### Market Manipulation Detection
- **Statistical Analysis Only**: Cannot detect sophisticated manipulation
- **False Positives Common**: Unusual activity doesn't always mean manipulation
- **Professional Review Required**: Regulatory concerns need expert analysis

## 🧪 Formula Validation

### ESG Score Calculation
```python
# Composite ESG Score
esg_score = (environmental + social + governance) / 3

# Validation checks:
- Component scores within industry range (e.g., Banking: E:15-85, S:20-90, G:25-95)
- Deviation from sector average <50%
- No suspicious patterns (all identical scores, all perfect scores)
```

### Stock Prediction Model
```python
# Features used:
- days_since_start (time trend)
- Volume (trading activity)  
- high_low_ratio (daily volatility)

# Model: Simple Linear Regression
# Confidence calculation:
confidence = min(0.7, accuracy * (1 - volatility * 10))

# Validation:
- Max confidence: 70%
- Min data points: 150
- Change magnitude warnings: >10%
```

### Manipulation Risk Score
```python
# Risk factors:
- Volume spike: recent_volume / average_volume > 2.0 (+30 points)
- Price volatility: daily_change > 5% (+25 points)  
- Frequent large moves: >5 moves >5% in 30 days (+20 points)
- News alerts: regulatory keywords found (+15 points each)

# Risk levels:
- High Risk: ≥70 points
- Medium Risk: 40-69 points
- Low Risk: 20-39 points
- Minimal Risk: <20 points
```

## 🚀 Deployment Health Checks

### Backend Health Check
```
GET /health
Response: {
  "status": "healthy",
  "services": {
    "enhanced_analytics": "available/unavailable",
    "api_keys": {"news_api": true, "alpha_vantage": true}
  }
}
```

### API Status Check  
```
GET /api/status
Response: {
  "enhanced_features": true,
  "endpoints": {...},
  "accuracy_disclaimer": "All predictions and ESG scores are estimates..."
}
```

## 🔧 Troubleshooting

### Enhanced Features Still Unavailable
1. Check environment variables are set correctly
2. Verify API keys are valid (not expired)
3. Check service logs for import errors
4. Restart the service after adding env vars

### Controversy Checks Still Failing
1. Check internet connectivity from server
2. SEC RSS feed may be temporarily down
3. Async loop conflicts in some environments
4. Falls back to dummy data when API fails

### Monitoring Alerts Too Frequent
1. Increase check interval (5-15 minutes)
2. Set up maintenance windows
3. Use keyword monitoring for specific errors
4. Configure alert escalation rules

## 📊 Performance Optimization

### API Rate Limits
- **News API**: 1000 requests/day (free tier)
- **Alpha Vantage**: 500 requests/day, 5/minute
- **Caching**: 24-hour default cache to reduce API calls

### Memory Usage
- **Enhanced Analytics**: ~50MB additional memory
- **Cache Storage**: ~10MB for 1000 stocks
- **Database**: TinyDB lightweight, <5MB

### Response Times  
- **Basic ESG**: <500ms
- **With Predictions**: 2-5 seconds (depends on yfinance)
- **Full Analysis**: 5-10 seconds (with news/manipulation check)

## 🛡️ Security Considerations

### API Key Security
- Never commit `.env` files to git
- Use different keys for dev/prod
- Rotate keys regularly
- Monitor usage for unauthorized access

### Data Privacy
- No personal/financial data stored
- Only public market data used
- Comply with data retention policies
- Log access for audit purposes

---

## 📞 Support

If you encounter issues:
1. Check the health endpoints first
2. Review environment variables
3. Check service logs
4. Contact support with specific error messages

**Remember**: This system provides estimates and analysis tools, not financial advice. Always consult qualified professionals for investment decisions.
