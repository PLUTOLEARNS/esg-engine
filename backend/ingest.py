"""
CLI entry-point for ESG data ingestion.
Usage: python -m backend.ingest AAPL,MSFT,NVDA
"""
import sys
import asyncio
from datetime import datetime
from typing import List
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.scrapers.fmp_client import fetch_esg, fetch_financials
from backend.db import ESGDB


def parse_esg_data(esg_data: dict | None, financials_data: dict | None, ticker: str) -> dict:
    """
    Parse and extract relevant ESG and financial data.
    
    Args:
        esg_data: Raw ESG data from FMP API
        financials_data: Raw financial ratios from FMP API  
        ticker: Stock ticker symbol
        
    Returns:
        Parsed record ready for database storage
    """
    # Default values in case data is missing
    record = {
        "ticker": ticker.upper(),
        "environmental": 0.0,
        "social": 0.0,
        "governance": 0.0,
        "esg_score": 0.0,
        "roic": 0.0,
        "market_cap": 0.0,
        "last_updated": datetime.now().isoformat()
    }
    
    # Parse ESG data (structure may vary by API response)
    if esg_data and isinstance(esg_data, list) and len(esg_data) > 0:
        esg_item = esg_data[0]  # Take most recent
        record.update({
            "environmental": float(esg_item.get("environmentalScore", 0)),
            "social": float(esg_item.get("socialScore", 0)),
            "governance": float(esg_item.get("governanceScore", 0)),
            "esg_score": float(esg_item.get("ESGScore", 0)),
        })
    elif esg_data and isinstance(esg_data, dict):
        record.update({
            "environmental": float(esg_data.get("environmentalScore", 0)),
            "social": float(esg_data.get("socialScore", 0)),
            "governance": float(esg_data.get("governanceScore", 0)),
            "esg_score": float(esg_data.get("ESGScore", 0)),
        })
    
    # Parse financial data
    if financials_data and isinstance(financials_data, list) and len(financials_data) > 0:
        fin_item = financials_data[0]  # Take most recent
        record.update({
            "roic": float(fin_item.get("returnOnCapitalEmployedTTM", 0)),
            "market_cap": float(fin_item.get("marketCapTTM", 0)),
        })
    elif financials_data and isinstance(financials_data, dict):
        record.update({
            "roic": float(financials_data.get("returnOnCapitalEmployedTTM", 0)),
            "market_cap": float(financials_data.get("marketCapTTM", 0)),
        })
    
    return record


async def ingest_ticker(ticker: str, db: ESGDB) -> None:
    """
    Ingest ESG and financial data for a single ticker.
    
    Args:
        ticker: Stock ticker symbol
        db: Database instance
    """
    try:
        print(f"Fetching data for {ticker}...")
        
        # Fetch data concurrently
        esg_task = fetch_esg(ticker)
        financials_task = fetch_financials(ticker)
        
        esg_data, financials_data = await asyncio.gather(
            esg_task, financials_task, return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(esg_data, Exception):
            print(f"Error fetching ESG data for {ticker}: {esg_data}")
            esg_data = None
        
        if isinstance(financials_data, Exception):
            print(f"Error fetching financial data for {ticker}: {financials_data}")
            financials_data = None
        # Parse and store data
        record = parse_esg_data(esg_data, financials_data, ticker)
        db.upsert_esg_record(record)
        
        print(f"Successfully ingested data for {ticker}")
        
    except Exception as e:
        print(f"Failed to ingest data for {ticker}: {e}")


async def ingest_tickers(tickers: List[str]) -> None:
    """
    Concurrently ingest ESG data for multiple tickers.
    
    Args:
        tickers: List of stock ticker symbols
    """
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    
    # Initialize database
    db = ESGDB()
    
    try:
        # Process tickers concurrently
        tasks = [ingest_ticker(ticker.strip().upper(), db) for ticker in tickers]
        await asyncio.gather(*tasks)
        
        print(f"\nIngestion complete. Processed {len(tickers)} tickers.")
        
        # Show summary
        all_records = db.get_all_records()
        print(f"Total records in database: {len(all_records)}")
        
    finally:
        db.close()


def main():
    """Main CLI entry point."""
    if len(sys.argv) != 2:
        print("Usage: python -m backend.ingest AAPL,MSFT,NVDA")
        sys.exit(1)
    
    ticker_string = sys.argv[1]
    tickers = [t.strip() for t in ticker_string.split(',') if t.strip()]
    
    if not tickers:
        print("Error: No valid tickers provided")
        sys.exit(1)
    
    print(f"Starting ingestion for tickers: {', '.join(tickers)}")
    
    # Run async ingestion
    asyncio.run(ingest_tickers(tickers))


if __name__ == "__main__":
    main()
