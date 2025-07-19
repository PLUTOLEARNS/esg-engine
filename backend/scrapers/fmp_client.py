"""
Client for Financial Modeling Prep ESG API.
"""
import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
import aiohttp
from dotenv import load_dotenv

load_dotenv()

FMP_API_KEY = os.getenv("FMP_API_KEY")
BASE_URL = "https://financialmodelingprep.com/api"


async def fetch_esg(ticker: str) -> dict:
    """
    Fetch ESG data for a given ticker from Financial Modeling Prep API.
    Implements retry with exponential backoff on 429 status.
    Stores raw JSON to data/raw_esg/{ticker}_{timestamp}.json
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        dict: ESG data from API
    """
    if not FMP_API_KEY:
        raise ValueError("FMP_API_KEY not found in environment variables")
        
    url = f"{BASE_URL}/v4/esg-environmental-social-governance-data?symbol={ticker}&apikey={FMP_API_KEY}"
    
    async with aiohttp.ClientSession() as session:
        for attempt in range(5):  # Max 5 retries
            try:
                async with session.get(url) as response:
                    if response.status == 429:
                        # Exponential backoff: 1, 2, 4, 8, 16 seconds
                        wait_time = 2 ** attempt
                        await asyncio.sleep(wait_time)
                        continue
                    
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Save raw data
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{ticker}_{timestamp}.json"
                    raw_path = Path("data/raw_esg") / filename
                    raw_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(raw_path, 'w') as f:
                        json.dump(data, f, indent=2)
                    
                    return data
                    
            except aiohttp.ClientError as e:
                if attempt == 4:  # Last attempt
                    raise e
                await asyncio.sleep(2 ** attempt)
    
    raise Exception(f"Failed to fetch ESG data for {ticker} after 5 attempts")


async def fetch_financials(ticker: str) -> dict:
    """
    Fetch financial ratios (TTM) for a given ticker from Financial Modeling Prep API.
    Implements retry with exponential backoff on 429 status.
    Stores raw JSON to data/raw_esg/{ticker}_financials_{timestamp}.json
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        dict: Financial ratios data from API
    """
    if not FMP_API_KEY:
        raise ValueError("FMP_API_KEY not found in environment variables")
        
    url = f"{BASE_URL}/v3/ratios-ttm/{ticker}?apikey={FMP_API_KEY}"
    
    async with aiohttp.ClientSession() as session:
        for attempt in range(5):  # Max 5 retries
            try:
                async with session.get(url) as response:
                    if response.status == 429:
                        # Exponential backoff: 1, 2, 4, 8, 16 seconds
                        wait_time = 2 ** attempt
                        await asyncio.sleep(wait_time)
                        continue
                    
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Save raw data
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{ticker}_financials_{timestamp}.json"
                    raw_path = Path("data/raw_esg") / filename
                    raw_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(raw_path, 'w') as f:
                        json.dump(data, f, indent=2)
                    
                    return data
                    
            except aiohttp.ClientError as e:
                if attempt == 4:  # Last attempt
                    raise e
                await asyncio.sleep(2 ** attempt)
    
    raise Exception(f"Failed to fetch financial data for {ticker} after 5 attempts")
