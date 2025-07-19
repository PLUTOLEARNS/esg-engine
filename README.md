# ESG Engine - भारत Edition

A professional ESG (Environmental, Social, Governance) portfolio analysis platform designed for Indian financial markets. Built with FastAPI backend and Streamlit frontend.

![ESG Engine Demo](https://img.shields.io/badge/Status-Production%20Ready-green)
![Python](https://img.shields.io/badge/Python-3.12+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green)
![Streamlit](https://img.shields.io/badge/Streamlit-Latest-red)

## Features

###  Portfolio Analysis
- **Real-time ESG Scoring**: Comprehensive ESG analysis for Indian stocks (NSE)
- **ROIC Analysis**: Return on Invested Capital calculations with Z-score normalization
- **Risk Assessment**: Controversy detection and regulatory risk flagging
- **Professional PDF Reports**: Export-ready investment reports with KPI cards

###  Indian Market Focus
- **NSE Integration**: Native support for .NS ticker format
- **Currency Conversion**: INR to USD conversion for international comparisons
- **Local Context**: Hindi/English hybrid branding and Indian regulatory awareness
- **Major Indian Companies**: Pre-configured ESG data for top Indian corporations

###  Technical Stack
- **Backend**: FastAPI with async support, TinyDB for data persistence
- **Frontend**: Streamlit with modern UI components and dark/light themes  
- **Data Sources**: Yahoo Finance integration for real-time market data
- **PDF Generation**: Professional reports using ReportLab with enhanced styling

##  Project Structure

```
esg-engine/
├── backend/
│   ├── __init__.py
│   ├── __main__.py          # CLI entry point
│   ├── app.py              # FastAPI application
│   ├── analytics.py        # ESG calculations and ROIC analysis
│   ├── db.py              # TinyDB database operations
│   ├── ingest.py          # Data ingestion utilities
│   └── scrapers/          # Data collection modules
│       ├── fmp_client.py   # Financial Modeling Prep client
│       ├── sec_rss.py     # SEC filings scraper
│       └── utils.py       # Scraping utilities
├── frontend/
│   └── streamlit_app.py   # Main Streamlit application
├── data/
│   └── esg.json          # ESG data storage
├── tests/                # Test suite
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container configuration
└── README.md
```

##  Installation & Setup

### Prerequisites
- Python 3.12 or higher
- pip package manager
- Virtual environment (recommended)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/esg-engine.git
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

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env file with your API keys (optional for basic functionality)
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

##  Usage Guide

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

### Sample Analysis Output:
- **ESG Score**: Weighted portfolio ESG score (0-100 scale)
- **ROIC Analysis**: Return on Invested Capital with peer comparisons
- **Risk Flags**: Controversy detection and compliance alerts
- **Component Breakdown**: Environmental, Social, Governance sub-scores
- **Professional PDF**: Export-ready investment report

##  API Endpoints

### Core Endpoints
- `POST /rank`: Portfolio ESG ranking and analysis
- `GET /controversy/{ticker}`: Company controversy data
- `GET /health`: System health check
- `GET /docs`: Interactive API documentation

### Data Ingestion
```bash
# Ingest ESG data for specific companies
python -m backend.ingest RELIANCE.NS,TCS.NS,INFY.NS

# Bulk data ingestion
python -m backend.ingest --file tickers.txt
```

##  Features in Detail

### ESG Scoring Methodology
- **Environmental**: Climate impact, resource efficiency, pollution control
- **Social**: Employee relations, community impact, diversity metrics
- **Governance**: Board composition, transparency, executive compensation

### Risk Assessment Framework
- **Controversy Detection**: Automated flagging of ESG-related controversies
- **Regulatory Compliance**: Indian market regulatory risk assessment
- **Materiality Analysis**: Impact assessment on financial performance

### Professional Reporting
- **KPI Dashboard**: Key performance indicators with traffic-light scoring
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
