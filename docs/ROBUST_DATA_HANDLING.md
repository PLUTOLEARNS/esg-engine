# Robust Data Handling in ESG Engine

## Overview

The ESG Engine now includes a comprehensive **Robust Yahoo Finance Client** that handles edge cases and data availability issues commonly encountered in financial data analysis. This system ensures reliable portfolio analysis even when dealing with delisted companies, missing data, or data source failures.

## Key Features

### 🔧 Robust Data Fetching
- **Primary Data Source**: Yahoo Finance with comprehensive error handling
- **Fallback Mechanisms**: Multiple strategies for handling data unavailability
- **Sector-Based Defaults**: Industry-appropriate ESG scores when no data is available
- **Alternative Ticker Formats**: Automatic testing of different exchange formats

### 🏭 Indian Market Specialization
- **NSE/BSE Format Handling**: Supports `.NS` and `.BO` ticker formats
- **Sector Classification**: Intelligent sector detection for Indian companies
- **Regional ESG Scoring**: India-specific ESG score benchmarks
- **Currency Handling**: Automatic INR to USD conversion for market cap

### ⚠️ Delisted Company Management
- **Replacement Mapping**: Automatic substitution for known delisted companies
- **Historical Data Validation**: Checks for recent trading activity
- **Transparent Reporting**: Clear indication when replacement data is used

## Supported Edge Cases

### 1. Delisted Companies
```python
# Known delisted companies with automatic replacements
DHFL.NS → HDFCBANK.NS        # DHFL delisted, use HDFC Bank
JETAIRWAYS.NS → INDIGO.NS    # Jet Airways delisted, use IndiGo
IL&FS.NS → HDFCBANK.NS       # IL&FS delisted
```

### 2. Missing/Invalid Tickers
- **Sector Default Scoring**: When no data is available, applies industry-appropriate ESG scores
- **Market Cap Estimation**: Provides reasonable market cap estimates based on sector
- **ROIC Benchmarking**: Sector-specific ROIC defaults

### 3. Alternative Data Sources
The system is designed to easily integrate additional data sources:
- Alpha Vantage (for fallback financial data)
- Quandl/NASDAQ Data Link (for alternative ESG metrics)
- IEX Cloud (for real-time market data)

## Data Quality Reporting

### Comprehensive Quality Metrics
```python
{
    "total_tickers": 10,
    "successful_fetches": 8,
    "success_rate": 0.8,
    "delisted_count": 1,
    "error_count": 1,
    "data_sources": {
        "yahoo_finance": 6,
        "yahoo_finance_replacement": 1,
        "sector_defaults": 2,
        "error": 1
    },
    "problematic_tickers": ["DHFL.NS", "INVALID123.NS"]
}
```

### Data Source Transparency
Every data point includes source attribution:
- `yahoo_finance`: Fresh data from Yahoo Finance
- `yahoo_finance_replacement_TICKER`: Replacement for delisted company
- `yahoo_finance_alternative_TICKER`: Alternative ticker format used
- `sector_defaults`: Industry-based estimates
- `error`: Failed data fetch with error details

## API Enhancements

### New Endpoints

#### 1. Enhanced Portfolio Ranking
```
POST /rank_enhanced
```
- Automatic data ingestion for missing tickers
- Comprehensive error handling
- Transparent data source reporting

#### 2. Manual Data Ingestion
```
POST /ingest
```
- Force refresh of portfolio data
- Batch processing with quality reporting
- Detailed error diagnostics

#### 3. Data Quality Monitoring
```
GET /health
```
- System health check
- Data source availability
- Performance metrics

### Enhanced Frontend Features

#### 🚀 Enhanced Analysis Mode
- Checkbox option for robust data fetching
- Real-time ingestion progress
- Data source transparency

#### 📊 Data Source Reporting
- Visual indicators for data quality
- Delisted company warnings
- Error diagnostics and suggestions

#### 🔄 Manual Data Refresh
- One-click data refresh for entire portfolio
- Progress tracking and error reporting
- Success/failure metrics

## Implementation Example

### Basic Usage
```python
from backend.scrapers.yahoo_client import RobustYahooFinanceClient

client = RobustYahooFinanceClient()
result = client.fetch_company_data("DHFL.NS")

print(f"Data Source: {result.data_source}")
print(f"Is Delisted: {result.is_delisted}")
print(f"ESG Score: {result.esg_score}")
```

### Batch Portfolio Processing
```python
from backend.analytics import auto_ingest_portfolio_data

tickers = ["RELIANCE.NS", "TCS.NS", "DHFL.NS", "INVALID123.NS"]
results = auto_ingest_portfolio_data(tickers)

print(f"Success Rate: {results['data_quality_report']['success_rate']:.1%}")
```

### Enhanced Portfolio Ranking
```python
from backend.analytics import rank_portfolio_with_auto_ingest

df = pd.DataFrame({
    'ticker': ['RELIANCE.NS', 'TCS.NS', 'DHFL.NS'],
    'weight': [0.4, 0.4, 0.2]
})

ranking = rank_portfolio_with_auto_ingest(df, auto_ingest=True)
```

## Testing Edge Cases

The system includes comprehensive test coverage for edge cases:

```bash
cd /path/to/esg-engine
python tests/test_edge_cases.py
```

Test scenarios include:
- ✅ Valid Indian companies (RELIANCE.NS, TCS.NS)
- ✅ Delisted companies with replacements (DHFL.NS)
- ✅ Invalid tickers with sector defaults (INVALID123.NS)
- ✅ Alternative ticker formats (WIPRO.BO, INFY)
- ✅ Network errors and timeouts
- ✅ Malformed data responses

## Sector-Based Default Scores

### Indian Market Sectors
| Sector | Environmental | Social | Governance | Default ROIC |
|--------|--------------|---------|------------|--------------|
| Banking | 12.0 | 15.0 | 18.0 | 12% |
| IT | 20.0 | 22.0 | 25.0 | 25% |
| Energy | 8.0 | 10.0 | 12.0 | 8% |
| FMCG | 15.0 | 18.0 | 20.0 | 18% |
| Auto | 10.0 | 14.0 | 16.0 | 10% |
| Pharma | 16.0 | 19.0 | 21.0 | 15% |
| Telecom | 14.0 | 16.0 | 18.0 | 6% |

### Sector Detection Logic
The system automatically detects sectors based on ticker patterns:
- **Banking**: HDFC, ICICI, SBI, AXIS, KOTAK, etc.
- **IT**: TCS, INFY, WIPRO, HCL, TECH, INFO, etc.
- **Energy**: RELIANCE, ONGC, IOC, BPCL, etc.
- **FMCG**: HINDUNIL, ITC, NESTLE, BRITANNIA, etc.

## Error Handling Strategy

### 1. Progressive Fallback
1. **Primary**: Yahoo Finance with original ticker
2. **Secondary**: Known delisted company replacements
3. **Tertiary**: Alternative ticker formats (.BO, without suffix)
4. **Quaternary**: Sector-based default scores
5. **Final**: Error state with detailed diagnostics

### 2. Graceful Degradation
- System continues to function even with partial data failures
- Clear indication of data quality and sources
- User guidance for resolving data issues

### 3. Comprehensive Logging
- Detailed error messages for debugging
- Data source attribution for transparency
- Performance metrics for monitoring

## Production Considerations

### Performance Optimization
- **Rate Limiting**: Automatic delays between Yahoo Finance requests
- **Caching**: Database storage to avoid repeated API calls
- **Batch Processing**: Efficient handling of multiple tickers

### Reliability Features
- **Timeout Handling**: Configurable timeouts for external APIs
- **Retry Logic**: Automatic retries with exponential backoff
- **Circuit Breaker**: Temporary disable failing data sources

### Monitoring & Alerting
- **Health Checks**: Regular verification of data source availability
- **Quality Metrics**: Continuous monitoring of success rates
- **Error Tracking**: Detailed logging for issue resolution

## Future Enhancements

### Additional Data Sources
1. **Alpha Vantage**: For enhanced financial metrics
2. **Refinitiv/LSEG**: For professional ESG scores
3. **Bloomberg API**: For institutional-grade data
4. **NSE/BSE Direct**: For Indian market data

### Advanced Features
1. **Machine Learning**: Predictive ESG scoring for new companies
2. **Real-time Updates**: WebSocket connections for live data
3. **Historical Analysis**: Time-series ESG trend analysis
4. **Benchmark Comparison**: Industry and regional benchmarking

### Data Quality Improvements
1. **Automated Validation**: Cross-reference multiple data sources
2. **Anomaly Detection**: Identify unusual ESG score changes
3. **Data Lineage**: Track data source and transformation history
4. **Quality Scoring**: Confidence metrics for each data point

---

This robust data handling system ensures that your ESG Engine provides reliable, transparent, and comprehensive portfolio analysis regardless of data availability challenges in the Indian and global markets.
