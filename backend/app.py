"""
FastAPI application entry point for ESG Engine backend.
"""
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ESG Engine API", version="1.0.0")

# Import analytics functions
from backend.analytics import rank_portfolio, sync_flag_controversies


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
