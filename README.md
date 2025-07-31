# ESG Engine - भारत Edition 🌱

A professional ESG (Environmental, Social, Governance) portfolio analysis platform with **ML-powered predictions** and **market manipulation detection** designed for Indian financial markets. Built with FastAPI backend and Streamlit frontend.

![ESG Engine Demo](https://img.shields.io/badge/Status-Production%20Ready-green)
![Python](https://img.shields.io/badge/Python-3.12+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green)
![Streamlit](https://img.shields.io/badge/Streamlit-Latest-red)
![ML](https://img.shields.io/badge/ML-Scikit--Learn-orange)

## 🚀 Features

### 📊 Core Portfolio Analysis
- **Real-time ESG Scoring**: Comprehensive ESG analysis for Indian stocks (NSE)
- **ROIC Analysis**: Return on Invested Capital calculations with Z-score normalization
- **Risk Assessment**: Controversy detection and regulatory risk flagging
- **Professional PDF Reports**: Export-ready investment reports with KPI cards

### 🤖 Enhanced ML Features
- **Smart Stock Search**: Fuzzy matching for 50+ Indian companies with autocomplete
- **Price Prediction**: Machine learning-powered 30-day stock price forecasting
- **Manipulation Detection**: Advanced market abuse detection using volume/news analysis
- **Confidence Scoring**: ML model reliability indicators for prediction accuracy

### 🇮🇳 Indian Market Focus
- **NSE Integration**: Native support for .NS ticker format
- **Currency Conversion**: INR to USD conversion for international comparisons
- **Local Context**: Hindi/English hybrid branding and Indian regulatory awareness
- **Major Indian Companies**: Pre-configured ESG data for top Indian corporations

### 🎨 Modern UI/UX
- **Dark/Light Themes**: Professional theme switching with user preferences
- **Interactive Charts**: Plotly-powered visualizations with real-time updates
- **Responsive Design**: Mobile-optimized interface for all devices
- **Enhanced Search**: Real-time stock search with intelligent suggestions

## 🏗️ Project Structure

```
esg-engine/
├── backend/
│   ├── __init__.py
│   ├── __main__.py              # CLI entry point
│   ├── app.py                  # FastAPI application with enhanced routes
│   ├── analytics.py            # ESG calculations and ROIC analysis
│   ├── enhanced_analytics.py   # 🆕 ML engine for predictions & search
│   ├── db.py                  # TinyDB database operations
│   ├── ingest.py              # Data ingestion utilities
│   └── scrapers/              # Data collection modules
│       ├── fmp_client.py       # Financial Modeling Prep client
│       ├── sec_rss.py         # SEC filings scraper
│       ├── yahoo_client.py    # Enhanced Yahoo Finance client
│       └── utils.py           # Scraping utilities
├── frontend/
│   └── streamlit_app.py       # 🆕 Enhanced Streamlit app with ML features
├── data/
│   └── esg.json              # ESG data storage
├── tests/                    # Test suite
├── requirements.txt          # 🆕 Updated with ML dependencies
├── .env.example             # 🆕 Enhanced environment variables
└── start.bat               # 🆕 Easy startup for Windows
```

## 🚀 Quick Start

### Prerequisites
- Python 3.12 or higher
- pip package manager
- Virtual environment (recommended)

### Option 1: One-Click Start (Windows)
1. **Double-click `start.bat`** in the project root
2. **Follow the prompts** to install dependencies
3. **Access the app** at http://localhost:8501

### Option 2: Manual Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/PLUTOLEARNS/esg-engine.git
   cd esg-engine
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables (Optional)**
   ```bash
   cp .env.example .env
   # Edit .env file with your API keys for enhanced features:
   # - NEWS_API_KEY for manipulation detection
   # - ALPHA_VANTAGE_API_KEY for enhanced stock data
   # - GROQ_API_KEY for AI analysis
   ```

5. **Start the backend server**
   ```bash
   uvicorn backend.app:app --reload --port 8000
   ```

6. **Launch the frontend application**
   ```bash
   streamlit run frontend/streamlit_app.py --server.port 8501
   ```

7. **Access the application**
   - Frontend: http://localhost:8501
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## 📱 Usage Guide

### Enhanced Features Available:

#### 🔍 Smart Stock Search
- **Type to search**: Try "Tata", "RELIANCE", "banking"
- **Fuzzy matching**: Finds partial matches across company names
- **Instant results**: Real-time suggestions with company details
- **Click to analyze**: One-click detailed analysis for any stock

#### 🤖 ML Price Predictions
- **30-day forecasts**: Machine learning powered price predictions
- **Confidence scores**: Model reliability indicators (60-95% typical)
- **Technical indicators**: Volume trends, volatility analysis
- **Visual charts**: Interactive price prediction graphs

#### 🚨 Manipulation Detection
- **Risk scoring**: 0-1 scale manipulation risk assessment
- **News sentiment**: Real-time news analysis for market abuse
- **Volume alerts**: Unusual trading pattern detection
- **Regulatory flags**: SEC/SEBI filing-based risk indicators

### Portfolio Upload Format
Create a CSV file with the following structure:
```csv
ticker,weight
RELIANCE.NS,0.25
TCS.NS,0.20
INFY.NS,0.15
HDFC.NS,0.15
ITC.NS,0.10
BAJFINANCE.NS,0.15
```

### Key Requirements:
- **ticker**: Use NSE format with `.NS` suffix for Indian stocks
- **weight**: Portfolio weights must sum to 1.0 (±0.01 tolerance)
- **File format**: CSV with comma-separated values

### Enhanced Analysis Output:
- **ESG Score**: Weighted portfolio ESG score (0-100 scale)
- **ML Predictions**: 30-day price forecasts with confidence
- **Risk Assessment**: Manipulation detection and regulatory alerts
- **ROIC Analysis**: Return on Invested Capital with peer comparisons
- **Component Breakdown**: Environmental, Social, Governance sub-scores
- **Professional PDF**: Export-ready investment report

## 🔌 API Endpoints
### Core Endpoints
- `POST /rank`: Portfolio ESG ranking and analysis
- `POST /rank_enhanced`: Enhanced portfolio ranking with auto-ingestion
- `GET /controversy/{ticker}`: Company controversy data
- `POST /ai-analysis`: AI-powered portfolio insights
- `GET /health`: System health check
- `GET /docs`: Interactive API documentation

### 🆕 Enhanced ML Endpoints
- `GET /api/enhanced/search?query={term}`: Smart stock search with fuzzy matching
- `POST /api/enhanced/predict`: ML price prediction for stocks
- `GET /api/enhanced/manipulation?symbol={ticker}`: Market manipulation detection
- `GET /api/enhanced/portfolio-analysis`: Advanced portfolio analysis
- `GET /api/enhanced/health`: Enhanced features availability check

### Data Ingestion
```bash
# Ingest ESG data for specific companies
python -m backend.ingest RELIANCE.NS,TCS.NS,INFY.NS

# Bulk data ingestion
python -m backend.ingest --file tickers.txt
```

## 🎯 Features in Detail

### ESG Scoring Methodology
- **Environmental**: Climate impact, resource efficiency, pollution control
- **Social**: Employee relations, community impact, diversity metrics
- **Governance**: Board composition, transparency, executive compensation

### 🤖 Machine Learning Pipeline
- **Data Collection**: 1+ year historical price/volume data
- **Feature Engineering**: Technical indicators, volatility metrics
- **Model Training**: Scikit-learn linear regression with cross-validation
- **Prediction**: 30-day price forecasts with confidence intervals

### 🚨 Market Manipulation Detection
- **Volume Analysis**: Statistical anomaly detection (2x+ normal volume)
- **News Sentiment**: Real-time news analysis for market abuse keywords
- **Pattern Recognition**: Unusual price/volume correlation detection
- **Risk Scoring**: Multi-factor risk assessment (0-1 scale)

### Risk Assessment Framework
- **Controversy Detection**: Automated flagging of ESG-related controversies
- **Regulatory Compliance**: Indian market regulatory risk assessment
- **Materiality Analysis**: Impact assessment on financial performance
- **Manipulation Risk**: Advanced market abuse detection algorithms

### Professional Reporting
- **KPI Dashboard**: Key performance indicators with traffic-light scoring
- **ML Insights**: Predictive analytics with confidence scoring
- **Visual Analytics**: Interactive charts and data visualizations  
- **PDF Export**: Professional investment reports with executive summaries
- **Indian Context**: Localized branding and regulatory considerations

##  Docker Deployment

```bash
# Build the container
docker build -t esg-engine .

# Run the application
docker run -p 8501:8501 -p 8000:8000 esg-engine
```

##  Testing

```bash
# Run the test suite
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=backend --cov-report=html
```

##  Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

##  License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Yahoo Finance for market data
- Financial Modeling Prep for ESG data sources
- Streamlit and FastAPI communities for excellent frameworks
- Indian financial markets for inspiration and context

## 📞 Support

For questions, issues, or contributions, please:
- Open an issue on GitHub
- Contact the development team
- Check the API documentation at `/docs`

---

**ESG Engine - भारत Edition** | *Professional Investment Analysis for Indian Markets*
