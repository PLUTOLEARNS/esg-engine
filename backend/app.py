"""
FastAPI application entry point for ESG Engine backend.
"""
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import os
from datetime import datetime
from dotenv import load_dotenv
import requests
import json

# Import enhanced analytics with fallback
try:
    from backend.analytics import EnhancedESGAnalytics
except ImportError:
    try:
        from analytics import EnhancedESGAnalytics
    except ImportError:
        EnhancedESGAnalytics = None
        print("⚠️ Enhanced analytics not available - running in basic mode")

load_dotenv()

app = FastAPI(title="ESG Engine API", version="1.0.0")

# Add CORS middleware for Streamlit Cloud
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your Streamlit Cloud URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import analytics functions
try:
    from analytics import rank_portfolio, sync_flag_controversies, auto_ingest_portfolio_data, rank_portfolio_with_auto_ingest
except ImportError:
    from backend.analytics import rank_portfolio, sync_flag_controversies, auto_ingest_portfolio_data, rank_portfolio_with_auto_ingest


class PortfolioRequest(BaseModel):
    """Request model for portfolio ranking."""
    tickers: List[str]
    weights: List[float]


class PortfolioResponse(BaseModel):
    """Response model for portfolio ranking."""
    data: List[dict]
    summary: dict


class ControversyResponse(BaseModel):
    """Response model for controversy flags."""
    ticker: str
    controversies: List[dict]


class AIAnalysisRequest(BaseModel):
    """Request model for AI analysis."""
    portfolio_data: List[dict]
    portfolio_esg: float
    portfolio_roic: float
    controversy_count: int


class AIAnalysisResponse(BaseModel):
    """Response model for AI analysis."""
    risk_assessment: str
    esg_explanation: str
    roic_explanation: str


@app.get("/api/status")
async def api_status():
    """
    Detailed API status for monitoring.
    """
    return {
        "api_version": "1.0.0",
        "enhanced_features": EnhancedESGAnalytics is not None,
        "endpoints": {
            "portfolio_analysis": "/api/portfolio/analyze",
            "stock_search": "/api/enhanced/search",
            "stock_prediction": "/api/enhanced/predict",
            "manipulation_detection": "/api/enhanced/manipulation"
        },
        "status": "operational",
        "accuracy_disclaimer": "All predictions and ESG scores are estimates. Not financial advice."
    }

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "ESG Engine API", "version": "1.0.0"}


@app.post("/rank", response_model=PortfolioResponse)
async def rank_portfolio_endpoint(request: PortfolioRequest):
    """
    Rank portfolio by ESG scores with weighted calculations.
    
    Args:
        request: Portfolio with tickers and weights
        
    Returns:
        Ranked portfolio data with analytics
    """
    try:
        # Validate input
        if len(request.tickers) != len(request.weights):
            raise HTTPException(
                status_code=400, 
                detail="Number of tickers must match number of weights"
            )
        
        if abs(sum(request.weights) - 1.0) > 1e-6:
            raise HTTPException(
                status_code=400,
                detail="Weights must sum to 1.0"
            )
        
        # Create DataFrame
        df = pd.DataFrame({
            'ticker': [t.upper() for t in request.tickers],
            'weight': request.weights
        })
        
        # Rank portfolio
        ranked_df = rank_portfolio(df)
        
        # Separate portfolio summary from individual holdings
        portfolio_row = ranked_df[ranked_df['ticker'] == 'PORTFOLIO_TOTAL'].iloc[0]
        holdings_df = ranked_df[ranked_df['ticker'] != 'PORTFOLIO_TOTAL']
        
        # Convert to response format
        holdings_data = holdings_df.to_dict('records')
        
        summary = {
            "total_holdings": len(holdings_df),
            "portfolio_weighted_esg": float(portfolio_row['weighted_esg']),
            "portfolio_weighted_roic": float(portfolio_row['weighted_roic']),
            "top_esg_ticker": holdings_df.iloc[0]['ticker'] if not holdings_df.empty else None,
            "bottom_esg_ticker": holdings_df.iloc[-1]['ticker'] if not holdings_df.empty else None
        }
        
        return PortfolioResponse(data=holdings_data, summary=summary)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/flags/{ticker}", response_model=ControversyResponse)
async def get_controversy_flags(ticker: str):
    """
    Get ESG controversy flags for a specific ticker.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        List of potential controversies from SEC filings
    """
    try:
        ticker = ticker.upper()
        controversies = sync_flag_controversies(ticker)
        
        # Convert to response format
        controversy_data = [
            {
                "date": date,
                "title": title, 
                "link": link
            }
            for date, title, link in controversies
        ]
        
        return ControversyResponse(
            ticker=ticker,
            controversies=controversy_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching controversies: {str(e)}")


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring services.
    Uptime Robot will ping this endpoint to verify the service is running.
    """
    try:
        # Test enhanced analytics (if available)
        enhanced_status = "available" if EnhancedESGAnalytics else "unavailable"
        
        # Test API keys (without exposing them)
        api_keys_status = {
            "news_api": bool(os.getenv('NEWS_API_KEY')),
            "alpha_vantage": bool(os.getenv('ALPHA_VANTAGE_API_KEY')),
        }
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "services": {
                "enhanced_analytics": enhanced_status,
                "api_keys": api_keys_status
            },
            "uptime": "Service is running normally"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail=f"Service unhealthy: {str(e)}"
        )


@app.post("/ingest")
async def ingest_portfolio_data(request: PortfolioRequest):
    """
    Auto-ingest ESG and financial data for portfolio tickers.
    Handles delisted companies and provides comprehensive error handling.
    
    Args:
        request: Portfolio request with tickers and weights
        
    Returns:
        Ingestion results and data quality report
    """
    try:
        tickers = [ticker.upper().strip() for ticker in request.tickers]
        
        # Perform auto-ingestion
        results = auto_ingest_portfolio_data(tickers, force_refresh=False)
        
        return {
            "message": "Auto-ingestion completed",
            "results": results,
            "total_tickers": len(tickers),
            "success_rate": results.get('data_quality_report', [{}])[0].get('success_rate', 0) if results.get('data_quality_report') else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion error: {str(e)}")


@app.post("/rank_enhanced", response_model=PortfolioResponse) 
async def rank_portfolio_enhanced(request: PortfolioRequest):
    """
    Enhanced portfolio ranking with automatic data ingestion for missing tickers.
    
    Args:
        request: Portfolio request with tickers and weights
        
    Returns:
        Portfolio ranking with comprehensive ESG analytics
    """
    try:
        # Validate input
        if len(request.tickers) != len(request.weights):
            raise HTTPException(status_code=400, detail="Tickers and weights must have same length")
        
        if not (0.99 <= sum(request.weights) <= 1.01):
            raise HTTPException(status_code=400, detail="Weights must sum to approximately 1.0")
        
        # Create portfolio DataFrame
        df = pd.DataFrame({
            'ticker': [ticker.upper() for ticker in request.tickers],
            'weight': request.weights
        })
        
        # Use enhanced ranking with auto-ingestion
        result_df = rank_portfolio_with_auto_ingest(df, auto_ingest=True)
        
        # Separate holdings from portfolio summary
        holdings_df = result_df[result_df['ticker'] != 'PORTFOLIO_TOTAL']
        portfolio_row = result_df[result_df['ticker'] == 'PORTFOLIO_TOTAL']
        
        # Convert to response format
        holdings_data = holdings_df.to_dict('records')
        
        # Summary data
        summary = {
            "portfolio_esg_score": portfolio_row['esg_score'].iloc[0] if not portfolio_row.empty else 0,
            "portfolio_roic": portfolio_row['roic'].iloc[0] if not portfolio_row.empty else 0,
            "total_holdings": len(holdings_data),
            "top_esg_performer": holdings_df.iloc[0]['ticker'] if not holdings_df.empty else None,
            "bottom_esg_performer": holdings_df.iloc[-1]['ticker'] if not holdings_df.empty else None,
            "avg_esg_zscore": holdings_df['esg_zscore'].mean() if not holdings_df.empty else 0,
            "avg_roic_zscore": holdings_df['roic_zscore'].mean() if not holdings_df.empty else 0
        }
        
        return PortfolioResponse(data=holdings_data, summary=summary)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Request/Response models for enhanced features
class StockSearchResponse(BaseModel):
    symbol: str
    name: str
    sector: str
    logo_url: str
    market_cap: str

class PredictionResponse(BaseModel):
    symbol: str
    current_price: float
    predicted_price: float
    confidence: float
    prediction_date: str
    technical_indicators: Dict[str, Any]

class ManipulationResponse(BaseModel):
    symbol: str
    risk_score: float
    risk_level: str
    alerts: List[str]
    news_sentiment: float


# Enhanced API Routes
@app.get("/api/enhanced/search", response_model=List[StockSearchResponse])
async def search_stocks_enhanced(query: str):
    """Enhanced stock search with fuzzy matching"""
    if not EnhancedESGAnalytics:
        raise HTTPException(status_code=503, detail="Enhanced analytics not available")
    
    try:
        analytics = EnhancedESGAnalytics()
        results = analytics.search_stocks(query)
        
        return [StockSearchResponse(
            symbol=stock['symbol'],
            name=stock['name'],
            sector=stock.get('sector', 'Unknown'),
            logo_url=stock.get('logo_url', ''),
            market_cap=stock.get('market_cap', 'N/A')
        ) for stock in results]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/api/enhanced/predict/{symbol}", response_model=PredictionResponse)
async def predict_stock_price(symbol: str):
    """ML-powered stock price prediction"""
    if not EnhancedESGAnalytics:
        raise HTTPException(status_code=503, detail="Enhanced analytics not available")
    
    try:
        analytics = EnhancedESGAnalytics()
        prediction = analytics.predict_stock_price(symbol)
        
        return PredictionResponse(
            symbol=symbol,
            current_price=prediction.get('current_price', 0),
            predicted_price=prediction.get('predicted_price', 0),
            confidence=prediction.get('confidence', 0),
            prediction_date=datetime.now().isoformat(),  # Use current date since prediction doesn't return this
            technical_indicators=prediction  # Return the full prediction as technical indicators
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.get("/api/enhanced/manipulation/{symbol}", response_model=ManipulationResponse)
async def detect_manipulation(symbol: str):
    """Market manipulation detection"""
    if not EnhancedESGAnalytics:
        raise HTTPException(status_code=503, detail="Enhanced analytics not available")
    
    try:
        analytics = EnhancedESGAnalytics()
        analysis = analytics.detect_manipulation_signals(symbol)
        
        return ManipulationResponse(
            symbol=symbol,
            risk_score=analysis.get('risk_score', 0),
            risk_level=analysis.get('risk_level', 'Unknown'),
            alerts=analysis.get('alerts', []),
            news_sentiment=0.0  # Default value since this field doesn't exist in our analysis
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manipulation detection failed: {str(e)}")


@app.get("/api/enhanced/portfolio-analysis")
async def analyze_portfolio_enhanced(symbols: str):
    """Enhanced portfolio analysis with ML insights"""
    if not EnhancedESGAnalytics:
        raise HTTPException(status_code=503, detail="Enhanced analytics not available")
    
    try:
        symbol_list = symbols.split(',')
        analytics = EnhancedESGAnalytics()
        
        results = []
        for symbol in symbol_list:
            symbol = symbol.strip()
            
            # Get basic ESG data using existing rank_portfolio function
            try:
                df = pd.DataFrame({'ticker': [symbol], 'weight': [1.0]})
                basic_data = rank_portfolio(df)
                esg_data = basic_data[basic_data['ticker'] == symbol].to_dict('records')[0] if not basic_data.empty else {}
            except:
                esg_data = {'ticker': symbol, 'esg_score': 0, 'roic': 0}
            
            # Add enhanced ML predictions
            prediction = analytics.predict_stock_price(symbol)
            manipulation = analytics.detect_manipulation_signals(symbol)
            
            results.append({
                'symbol': symbol,
                'esg_data': esg_data,
                'ml_prediction': prediction,
                'manipulation_risk': manipulation
            })
        
        return {
            'portfolio_analysis': results,
            'summary': {
                'total_stocks': len(results),
                'high_risk_count': sum(1 for r in results if r['manipulation_risk']['risk_score'] > 0.7),
                'avg_prediction_confidence': sum(r['ml_prediction']['confidence'] for r in results) / len(results) if results else 0
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Portfolio analysis failed: {str(e)}")


# Health check for enhanced features
@app.get("/api/enhanced/health")
async def enhanced_health_check():
    """Check if enhanced features are available"""
    return {
        'enhanced_analytics_available': EnhancedESGAnalytics is not None,
        'features': {
            'stock_search': True,
            'ml_predictions': True,
            'manipulation_detection': True,
            'enhanced_portfolio_analysis': True
        } if EnhancedESGAnalytics else {},
        'status': 'healthy' if EnhancedESGAnalytics else 'limited'
    }