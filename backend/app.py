"""
FastAPI application entry point for ESG Engine backend.
"""
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv

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
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": pd.Timestamp.now().isoformat()}


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
