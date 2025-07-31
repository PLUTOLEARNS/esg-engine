"""
Enhanced ESG Analytics module with stock search, prediction, manipulation detection, and portfolio ranking.
Combines original analytics functionality with enhanced dashboard features.
"""
import os
import sys
import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import requests_cache  
import re
import asyncio
import aiohttp
from aiohttp import ClientTimeout
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

# Import existing modules with proper error handling
try:
    from backend.scrapers.yahoo_client import RobustYahooFinanceClient, validate_and_fetch_portfolio
    from backend.db import ESGDB
    from backend.esg_validator import esg_validator
    
    # Successfully imported real classes
    _IMPORTS_SUCCESSFUL = True
    
except ImportError:
    try:
        from .scrapers.yahoo_client import RobustYahooFinanceClient, validate_and_fetch_portfolio
        from .db import ESGDB
        from .esg_validator import esg_validator
        
        # Successfully imported real classes
        _IMPORTS_SUCCESSFUL = True
        
    except ImportError:
        # Create fallback classes only if imports fail
        _IMPORTS_SUCCESSFUL = False
        
        class RobustYahooFinanceClient:
            def fetch_company_data(self, symbol):
                from datetime import datetime
                return type('CompanyData', (), {
                    'ticker': symbol,
                    'market_cap': 100000000,
                    'roic': 0.15,
                    'environmental': 50,
                    'social': 50,
                    'governance': 50,
                    'esg_score': 50,
                    'is_delisted': False,
                    'data_source': 'fallback',
                    'last_updated': datetime.now().isoformat(),
                    'error_message': ''
                })()
        
        def validate_and_fetch_portfolio(tickers):
            return {}, {'success_rate': 0.0}
        
        class ESGDB:
            def __init__(self):
                pass
            def get_all_records(self):
                return []
            def close(self):
                pass
            def upsert_esg_record(self, record):
                pass
        
        # Dummy validator
        class DummyValidator:
            def validate_esg_score(self, *args, **kwargs):
                return {'is_valid': True, 'warnings': ['Validator not available'], 'confidence_level': 'low'}
            def validate_prediction_model(self, *args, **kwargs):
                return {'is_reliable': False, 'warnings': ['Validator not available'], 'risk_level': 'high'}
            def generate_accuracy_report(self):
                return "⚠️ ESG Validator not available - all results should be treated as unreliable"
        
        esg_validator = DummyValidator()

# Load environment variables
load_dotenv()

# Setup caching for API calls
cache_expire_hours = int(os.getenv('CACHE_EXPIRE_HOURS', 24))
requests_cache.install_cache(
    'esg_dashboard_cache', 
    expire_after=timedelta(hours=cache_expire_hours)
)


def rank_portfolio(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rank portfolio by ESG scores with weighted calculations and z-score analysis.
    
    Args:
        df: DataFrame with columns ['ticker', 'weight'] where weights sum to 1.0
        
    Returns:
        DataFrame sorted descending by esg_score with additional analytics:
        - ticker, weight, esg_score, environmental, social, governance
        - roic, market_cap, weighted_esg, weighted_roic
        - esg_zscore, roic_zscore (vs S&P 500 universe)
    """
    # Validate input
    if not {'ticker', 'weight'}.issubset(df.columns):
        raise ValueError("DataFrame must contain 'ticker' and 'weight' columns")
    
    if not np.isclose(df['weight'].sum(), 1.0, atol=1e-6):
        raise ValueError("Weights must sum to 1.0")
    
    # Get ESG data from database
    db = ESGDB()
    try:
        all_records = db.get_all_records()
        esg_df = pd.DataFrame(all_records)
        
        if esg_df.empty:
            raise ValueError("No ESG data found in database. Run data ingestion first.")
        
        # Left join with portfolio
        result_df = df.merge(esg_df, on='ticker', how='left')
        
        # Check for missing data
        missing_tickers = result_df[result_df['esg_score'].isna()]['ticker'].tolist()
        if missing_tickers:
            print(f"Warning: Missing ESG data for tickers: {missing_tickers}")
        
        # Fill missing values with 0 for calculations
        numeric_cols = ['environmental', 'social', 'governance', 'esg_score', 'roic', 'market_cap']
        result_df[numeric_cols] = result_df[numeric_cols].fillna(0)
        
        # Calculate weighted metrics
        result_df['weighted_esg'] = result_df['weight'] * result_df['esg_score']
        result_df['weighted_roic'] = result_df['weight'] * result_df['roic']
        
        # Calculate z-scores vs S&P 500 universe (all records in DB)
        esg_mean = esg_df['esg_score'].mean()
        esg_std = esg_df['esg_score'].std()
        roic_mean = esg_df['roic'].mean()
        roic_std = esg_df['roic'].std()
        
        # Avoid division by zero
        if esg_std > 0:
            result_df['esg_zscore'] = (result_df['esg_score'] - esg_mean) / esg_std
        else:
            result_df['esg_zscore'] = 0
            
        if roic_std > 0:
            result_df['roic_zscore'] = (result_df['roic'] - roic_mean) / roic_std
        else:
            result_df['roic_zscore'] = 0
        
        # Sort by ESG score descending
        result_df = result_df.sort_values('esg_score', ascending=False)
        
        # Add portfolio-level metrics as summary
        portfolio_weighted_esg = result_df['weighted_esg'].sum()
        portfolio_weighted_roic = result_df['weighted_roic'].sum()
        
        # Add summary row
        summary_row = pd.DataFrame({
            'ticker': ['PORTFOLIO_TOTAL'],
            'weight': [1.0],
            'esg_score': [portfolio_weighted_esg],
            'roic': [portfolio_weighted_roic],
            'weighted_esg': [portfolio_weighted_esg],
            'weighted_roic': [portfolio_weighted_roic],
            'environmental': [0], 'social': [0], 'governance': [0],
            'market_cap': [0], 'esg_zscore': [0], 'roic_zscore': [0],
            'last_updated': [datetime.now().isoformat()]
        })
        
        result_df = pd.concat([result_df, summary_row], ignore_index=True)
        
        return result_df
        
    finally:
        db.close()


async def flag_controversies(ticker: str) -> List[Tuple[str, str, str]]:
    """
    Flag potential ESG controversies for a ticker by scraping SEC RSS feed.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        List of 3-tuples: (date, title, link) for relevant filings
    """
    # SEC RSS feed for 8-K filings
    rss_url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&count=100&output=atom"
    
    # Keywords to flag potential controversies
    controversy_keywords = ["ESG", "cyber", "climate", "lawsuit", "litigation", 
                          "investigation", "violation", "penalty", "fine", 
                          "environmental", "social", "governance"]
    
    controversies = []
    
    try:
        # Use aiohttp for async RSS parsing
        timeout = ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(rss_url) as response:
                rss_content = await response.text()
        
        # Parse RSS/Atom feed manually
        try:
            root = ET.fromstring(rss_content)
            # Handle Atom namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('.//atom:entry', ns)
            
            # If no Atom entries, try RSS format
            if not entries:
                entries = root.findall('.//item')
            
        except ET.ParseError:
            print(f"Error parsing RSS feed for {ticker}")
            return []
        
        # Search through entries
        for entry in entries:
            # Extract title and summary
            title_elem = entry.find('.//atom:title', ns) or entry.find('.//title')
            summary_elem = entry.find('.//atom:summary', ns) or entry.find('.//description')
            
            title = title_elem.text if title_elem is not None else ''
            summary = summary_elem.text if summary_elem is not None else ''
            content = f"{title} {summary}".lower()
            
            # Check if ticker is mentioned
            ticker_pattern = rf'\b{re.escape(ticker.upper())}\b'
            if not re.search(ticker_pattern, content.upper()):
                continue
            
            # Check for controversy keywords
            found_keywords = []
            for keyword in controversy_keywords:
                if keyword.lower() in content:
                    found_keywords.append(keyword)
            
            if found_keywords:
                # Extract date
                date_elem = (entry.find('.//atom:published', ns) or 
                           entry.find('.//atom:updated', ns) or 
                           entry.find('.//pubDate'))
                
                date_str = date_elem.text if date_elem is not None else ''
                try:
                    # Parse date and format as ISO
                    if date_str:
                        if 'T' in date_str:
                            parsed_date = datetime.strptime(date_str[:19], '%Y-%m-%dT%H:%M:%S')
                        else:
                            parsed_date = datetime.strptime(date_str[:10], '%Y-%m-%d')
                        formatted_date = parsed_date.strftime('%Y-%m-%d')
                    else:
                        formatted_date = 'Unknown'
                except:
                    formatted_date = date_str[:10] if date_str else 'Unknown'
                
                # Extract link
                link_elem = entry.find('.//atom:link', ns) or entry.find('.//link')
                if link_elem is not None:
                    link = link_elem.get('href') or link_elem.text or ''
                else:
                    link = ''
                
                # Create title with flagged keywords
                flagged_title = f"{title} [Keywords: {', '.join(found_keywords)}]"
                
                controversies.append((
                    formatted_date,
                    flagged_title,
                    link
                ))
        
        # Sort by date (most recent first)
        controversies.sort(key=lambda x: x[0], reverse=True)
        
        # Limit to most recent 10 controversies
        return controversies[:10]
        
    except Exception as e:
        print(f"Error fetching controversies for {ticker}: {e}")
        return []


def sync_flag_controversies(ticker: str) -> List[Tuple[str, str, str]]:
    """
    Synchronous wrapper for flag_controversies function with enhanced error handling.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        List of 3-tuples: (date, title, link) for relevant filings
    """
    try:
        # Check if there's an existing event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, create a new thread for the async call
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, flag_controversies(ticker))
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(flag_controversies(ticker))
        except RuntimeError:
            # No event loop exists, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(flag_controversies(ticker))
            loop.close()
            return result
    except Exception as e:
        print(f"Error in sync_flag_controversies for {ticker}: {e}")
        # Return fallback controversy data
        return [
            ("2024-01-01", f"Controversy check failed for {ticker}: {str(e)}", ""),
            ("2024-01-01", "Using fallback data - API may be unavailable", "")
        ]


def auto_ingest_portfolio_data(tickers: List[str], force_refresh: bool = False) -> Dict[str, Any]:
    """
    Auto-ingest ESG and financial data for portfolio tickers using robust Yahoo Finance client.
    Handles delisted companies, missing data, and provides comprehensive fallback strategies.
    
    Args:
        tickers: List of stock ticker symbols
        force_refresh: If True, fetch fresh data even if already in database
        
    Returns:
        Dictionary with ingestion results and data quality report
    """
    print(f"🔄 Starting auto-ingestion for {len(tickers)} tickers...")
    
    # Initialize database and Yahoo Finance client
    db = ESGDB()
    yahoo_client = RobustYahooFinanceClient()
    
    try:
        ingestion_results = {
            'successful_ingests': [],
            'failed_ingests': [],
            'delisted_companies': [],
            'updated_companies': [],
            'skipped_companies': [],
            'errors': []
        }
        
        # Check existing data in database
        existing_records = db.get_all_records()
        existing_tickers = {record['ticker'] for record in existing_records}
        
        # Determine which tickers need fetching
        tickers_to_fetch = []
        for ticker in tickers:
            ticker_clean = ticker.upper().strip()
            if force_refresh or ticker_clean not in existing_tickers:
                tickers_to_fetch.append(ticker_clean)
            else:
                ingestion_results['skipped_companies'].append(ticker_clean)
                print(f"⏭️  Skipping {ticker_clean} - already in database")
        
        if not tickers_to_fetch:
            print("✅ All tickers already in database. Use force_refresh=True to update.")
            return ingestion_results
        
        print(f"📡 Fetching data for {len(tickers_to_fetch)} new/updated tickers...")
        
        # Batch fetch data with comprehensive error handling
        results, quality_report = validate_and_fetch_portfolio(tickers_to_fetch)
        
        # Process results and store in database
        for ticker, company_data in results.items():
            try:
                if company_data.error_message:
                    ingestion_results['failed_ingests'].append(ticker)
                    ingestion_results['errors'].append(f"{ticker}: {company_data.error_message}")
                    print(f"❌ Failed to fetch data for {ticker}: {company_data.error_message}")
                    continue
                
                # Convert CompanyData to database record format with enhanced metadata
                record = {
                    'ticker': company_data.ticker,
                    'environmental': company_data.environmental,
                    'social': company_data.social,
                    'governance': company_data.governance,
                    'esg_score': company_data.esg_score,
                    'roic': company_data.roic,
                    'market_cap': company_data.market_cap,
                    'last_updated': company_data.last_updated,
                    'data_source': company_data.data_source,
                    'is_delisted': company_data.is_delisted,
                    'error_message': company_data.error_message
                }
                
                # Add currency and market information based on ticker
                if ticker.endswith('.NS') or ticker.endswith('.BO'):
                    record['currency'] = 'INR'
                    record['market'] = 'India'
                else:
                    record['currency'] = 'USD' 
                    record['market'] = 'US'
                
                # Store in database using upsert
                db.upsert_esg_record(record)
                
                if ticker in existing_tickers:
                    ingestion_results['updated_companies'].append(ticker)
                    print(f"🔄 Updated {ticker} ({company_data.data_source})")
                else:
                    ingestion_results['successful_ingests'].append(ticker)
                    print(f"✅ Ingested {ticker} ({company_data.data_source})")
                
                # Track delisted companies
                if company_data.is_delisted:
                    ingestion_results['delisted_companies'].append(ticker)
                    print(f"⚠️  {ticker} is delisted - using replacement data")
                
            except Exception as e:
                ingestion_results['failed_ingests'].append(ticker)
                ingestion_results['errors'].append(f"{ticker}: Database error - {str(e)}")
                print(f"❌ Database error for {ticker}: {str(e)}")
        
        # Add quality report to results (fix type issue)
        ingestion_results['data_quality_report'] = [quality_report]
        
        # Print summary
        print(f"\n📊 Ingestion Summary:")
        print(f"✅ Successful: {len(ingestion_results['successful_ingests'])}")
        print(f"🔄 Updated: {len(ingestion_results['updated_companies'])}")
        print(f"⏭️  Skipped: {len(ingestion_results['skipped_companies'])}")
        print(f"⚠️  Delisted: {len(ingestion_results['delisted_companies'])}")
        print(f"❌ Failed: {len(ingestion_results['failed_ingests'])}")
        print(f"📈 Success Rate: {quality_report['success_rate']:.1%}")
        
        if ingestion_results['delisted_companies']:
            print(f"\n⚠️  Delisted companies detected: {', '.join(ingestion_results['delisted_companies'])}")
        
        if ingestion_results['errors']:
            print(f"\n❌ Errors encountered:")
            for error in ingestion_results['errors'][:5]:  # Show first 5 errors
                print(f"   • {error}")
        
        return ingestion_results
        
    finally:
        db.close()


def rank_portfolio_with_auto_ingest(df: pd.DataFrame, auto_ingest: bool = True) -> pd.DataFrame:
    """
    Enhanced portfolio ranking with automatic data ingestion for missing tickers.
    
    Args:
        df: DataFrame with columns ['ticker', 'weight']
        auto_ingest: If True, automatically fetch missing ticker data
        
    Returns:
        DataFrame with complete portfolio ranking and ESG analytics
    """
    # Validate input
    if not {'ticker', 'weight'}.issubset(df.columns):
        raise ValueError("DataFrame must contain 'ticker' and 'weight' columns")
    
    if not np.isclose(df['weight'].sum(), 1.0, atol=1e-6):
        raise ValueError("Weights must sum to 1.0")
    
    # Get current tickers from database
    db = ESGDB()
    try:
        existing_records = db.get_all_records()
        existing_tickers = {record['ticker'] for record in existing_records}
        
        # Find missing tickers
        portfolio_tickers = set(df['ticker'].str.upper())
        missing_tickers = portfolio_tickers - existing_tickers
        
        # Auto-ingest missing data if requested
        if auto_ingest and missing_tickers:
            print(f"🔄 Auto-ingesting data for {len(missing_tickers)} missing tickers...")
            auto_ingest_portfolio_data(list(missing_tickers))
        
        # Now proceed with regular ranking
        return rank_portfolio(df)
        
    finally:
        db.close()


class EnhancedESGAnalytics:
    """
    Enhanced ESG Analytics with stock search, prediction, and manipulation detection.
    Builds on the existing ESG Engine infrastructure.
    """
    
    def __init__(self):
        self.yahoo_client = RobustYahooFinanceClient()
        self.db = ESGDB()
        self.news_api_key = os.getenv('NEWS_API_KEY')
        self.alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        
        # Manipulation detection thresholds
        self.volume_threshold = float(os.getenv('VOLUME_SPIKE_THRESHOLD', 2.0))
        self.volatility_threshold = float(os.getenv('VOLATILITY_THRESHOLD', 0.05))
        
        # Indian stock universe for search
        self.indian_stock_universe = self._load_indian_stock_universe()
    
    def _load_indian_stock_universe(self) -> Dict[str, Dict]:
        """Load comprehensive Indian stock database for search functionality."""
        # Major Indian companies with their details for search
        stock_universe = {
            # Banking & Financial Services
            'HDFCBANK.NS': {'name': 'HDFC Bank Limited', 'sector': 'Banking', 'keywords': ['hdfc', 'bank']},
            'ICICIBANK.NS': {'name': 'ICICI Bank Limited', 'sector': 'Banking', 'keywords': ['icici', 'bank']},
            'SBIN.NS': {'name': 'State Bank of India', 'sector': 'Banking', 'keywords': ['sbi', 'state', 'bank']},
            'AXISBANK.NS': {'name': 'Axis Bank Limited', 'sector': 'Banking', 'keywords': ['axis', 'bank']},
            'KOTAKBANK.NS': {'name': 'Kotak Mahindra Bank', 'sector': 'Banking', 'keywords': ['kotak', 'bank']},
            
            # IT Services
            'TCS.NS': {'name': 'Tata Consultancy Services', 'sector': 'IT Services', 'keywords': ['tcs', 'tata', 'consultancy']},
            'INFY.NS': {'name': 'Infosys Limited', 'sector': 'IT Services', 'keywords': ['infosys', 'infy']},
            'WIPRO.NS': {'name': 'Wipro Limited', 'sector': 'IT Services', 'keywords': ['wipro']},
            'HCLTECH.NS': {'name': 'HCL Technologies', 'sector': 'IT Services', 'keywords': ['hcl', 'tech']},
            'TECHM.NS': {'name': 'Tech Mahindra', 'sector': 'IT Services', 'keywords': ['tech', 'mahindra']},
            
            # Oil & Gas
            'RELIANCE.NS': {'name': 'Reliance Industries', 'sector': 'Oil & Gas', 'keywords': ['reliance', 'ril']},
            'ONGC.NS': {'name': 'Oil & Natural Gas Corp', 'sector': 'Oil & Gas', 'keywords': ['ongc', 'oil']},
            'IOC.NS': {'name': 'Indian Oil Corporation', 'sector': 'Oil & Gas', 'keywords': ['ioc', 'indian', 'oil']},
            'BPCL.NS': {'name': 'Bharat Petroleum', 'sector': 'Oil & Gas', 'keywords': ['bpcl', 'bharat', 'petroleum']},
            
            # Automobiles
            'MARUTI.NS': {'name': 'Maruti Suzuki India', 'sector': 'Automobiles', 'keywords': ['maruti', 'suzuki']},
            'TATAMOTORS.NS': {'name': 'Tata Motors Limited', 'sector': 'Automobiles', 'keywords': ['tata', 'motors']},
            'M&M.NS': {'name': 'Mahindra & Mahindra', 'sector': 'Automobiles', 'keywords': ['mahindra']},
            'BAJAJ-AUTO.NS': {'name': 'Bajaj Auto Limited', 'sector': 'Automobiles', 'keywords': ['bajaj', 'auto']},
            'HEROMOTOCO.NS': {'name': 'Hero MotoCorp', 'sector': 'Automobiles', 'keywords': ['hero', 'moto']},
            
            # Pharmaceuticals
            'SUNPHARMA.NS': {'name': 'Sun Pharmaceutical', 'sector': 'Pharmaceuticals', 'keywords': ['sun', 'pharma']},
            'DRREDDY.NS': {'name': 'Dr Reddys Laboratories', 'sector': 'Pharmaceuticals', 'keywords': ['reddy', 'dr']},
            'CIPLA.NS': {'name': 'Cipla Limited', 'sector': 'Pharmaceuticals', 'keywords': ['cipla']},
            'LUPIN.NS': {'name': 'Lupin Limited', 'sector': 'Pharmaceuticals', 'keywords': ['lupin']},
            
            # Consumer Goods
            'HINDUNILVR.NS': {'name': 'Hindustan Unilever', 'sector': 'FMCG', 'keywords': ['hindustan', 'unilever', 'hul']},
            'ITC.NS': {'name': 'ITC Limited', 'sector': 'FMCG', 'keywords': ['itc']},
            'NESTLEIND.NS': {'name': 'Nestle India Limited', 'sector': 'FMCG', 'keywords': ['nestle']},
            'BRITANNIA.NS': {'name': 'Britannia Industries', 'sector': 'FMCG', 'keywords': ['britannia']},
            
            # Adani Group
            'ADANIPORTS.NS': {'name': 'Adani Ports & SEZ', 'sector': 'Infrastructure', 'keywords': ['adani', 'ports']},
            'ADANIENT.NS': {'name': 'Adani Enterprises', 'sector': 'Infrastructure', 'keywords': ['adani', 'enterprises']},
            'ADANIGREEN.NS': {'name': 'Adani Green Energy', 'sector': 'Renewable Energy', 'keywords': ['adani', 'green']},
            
            # Steel & Mining
            'TATASTEEL.NS': {'name': 'Tata Steel Limited', 'sector': 'Steel', 'keywords': ['tata', 'steel']},
            'JSWSTEEL.NS': {'name': 'JSW Steel Limited', 'sector': 'Steel', 'keywords': ['jsw', 'steel']},
            'HINDALCO.NS': {'name': 'Hindalco Industries', 'sector': 'Metals', 'keywords': ['hindalco']},
        }
        
        return stock_universe
    
    def search_stocks(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for stocks by company name, ticker, or sector.
        
        Args:
            query: Search term (e.g., "Tata", "bank", "RELIANCE")
            limit: Maximum number of results to return
            
        Returns:
            List of matching stocks with details
        """
        query = query.lower().strip()
        results = []
        
        # Search in local Indian stock universe first
        for ticker, details in self.indian_stock_universe.items():
            score = 0
            
            # Exact ticker match gets highest score
            if query.upper() == ticker.replace('.NS', ''):
                score = 100
            # Check if query is in company name
            elif query in details['name'].lower():
                score = 80
            # Check if query is in sector
            elif query in details['sector'].lower():
                score = 60
            # Check keywords
            elif any(query in keyword for keyword in details['keywords']):
                score = 70
            
            if score > 0:
                # Get real-time market data for the stock
                try:
                    stock_data = self.yahoo_client.fetch_company_data(ticker)
                    
                    result = {
                        'symbol': ticker,
                        'name': details['name'],
                        'sector': details['sector'],
                        'logo_url': '',  # Add logo URL if available
                        'market_cap': self._format_market_cap(getattr(stock_data, 'market_cap', 0)),
                        'esg_score': getattr(stock_data, 'esg_score', 0),
                        'roic': getattr(stock_data, 'roic', 0),
                        'score': score,
                        'data_source': getattr(stock_data, 'data_source', 'unknown'),
                        'is_delisted': getattr(stock_data, 'is_delisted', False)
                    }
                    results.append(result)
                except Exception as e:
                    # Fallback data
                    result = {
                        'symbol': ticker,
                        'name': details['name'],
                        'sector': details['sector'],
                        'logo_url': '',
                        'market_cap': 'N/A',
                        'esg_score': 0,
                        'roic': 0,
                        'score': score,
                        'data_source': 'fallback',
                        'is_delisted': False
                    }
                    results.append(result)
        
        # Sort by relevance score and limit results
        results = sorted(results, key=lambda x: x['score'], reverse=True)[:limit]
        
        # If we have Alpha Vantage API and fewer than 5 results, try external search
        if len(results) < 5 and self.alpha_vantage_key:
            external_results = self._search_alpha_vantage(query, limit - len(results))
            results.extend(external_results)
        
        return results
    
    def _search_alpha_vantage(self, query: str, limit: int) -> List[Dict]:
        """Search for stocks using Alpha Vantage API."""
        try:
            url = f"https://www.alphavantage.co/query"
            params = {
                'function': 'SYMBOL_SEARCH',
                'keywords': query,
                'apikey': self.alpha_vantage_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            results = []
            if 'bestMatches' in data:
                for match in data['bestMatches'][:limit]:
                    ticker = match.get('1. symbol', '')
                    name = match.get('2. name', '')
                    
                    # Focus on Indian stocks or add .NS if it looks Indian
                    if any(indian_word in name.lower() for indian_word in ['india', 'limited', 'ltd']):
                        if not ticker.endswith('.NS'):
                            ticker += '.NS'
                    
                    results.append({
                        'ticker': ticker,
                        'name': name,
                        'sector': match.get('4. region', 'Unknown'),
                        'market_cap': 0,
                        'market_cap_formatted': 'N/A',
                        'esg_score': 0,
                        'roic': 0,
                        'score': 50,
                        'data_source': 'alpha_vantage',
                        'is_delisted': False
                    })
            
            return results
            
        except Exception as e:
            print(f"Alpha Vantage search error: {e}")
            return []
    
    def get_stock_alternatives(self, ticker: str, count: int = 3) -> List[Dict]:
        """
        Get alternative stocks for delisted or problematic companies.
        
        Args:
            ticker: Original ticker that has issues
            count: Number of alternatives to suggest
            
        Returns:
            List of alternative stocks in the same sector
        """
        # Get sector for the original ticker
        if ticker in self.indian_stock_universe:
            target_sector = self.indian_stock_universe[ticker]['sector']
        else:
            # Try to infer sector from ticker name
            ticker_clean = ticker.replace('.NS', '').upper()
            target_sector = self._infer_sector_from_ticker(ticker_clean)
        
        # Find alternatives in the same sector
        alternatives = []
        for alt_ticker, details in self.indian_stock_universe.items():
            if alt_ticker != ticker and details['sector'] == target_sector:
                stock_data = self.yahoo_client.fetch_company_data(alt_ticker)
                
                alternatives.append({
                    'ticker': alt_ticker,
                    'name': details['name'],
                    'sector': details['sector'],
                    'market_cap_formatted': self._format_market_cap(getattr(stock_data, 'market_cap', 0)),
                    'esg_score': getattr(stock_data, 'esg_score', 0),
                    'roic': getattr(stock_data, 'roic', 0),
                    'data_source': getattr(stock_data, 'data_source', 'unknown'),
                    'reason': f"Alternative to {ticker} in {target_sector} sector"
                })
        
        # Sort by market cap (prefer larger, more stable companies)
        alternatives = sorted(alternatives, key=lambda x: x['esg_score'], reverse=True)
        return alternatives[:count]
    
    def _infer_sector_from_ticker(self, ticker_clean: str) -> str:
        """Infer sector from ticker name patterns."""
        if any(bank in ticker_clean for bank in ['HDFC', 'ICICI', 'SBI', 'AXIS', 'KOTAK']):
            return 'Banking'
        elif any(it in ticker_clean for it in ['TCS', 'INFY', 'WIPRO', 'HCL', 'TECH']):
            return 'IT Services'
        elif any(energy in ticker_clean for energy in ['RELIANCE', 'ONGC', 'IOC', 'BPCL']):
            return 'Oil & Gas'
        elif any(auto in ticker_clean for auto in ['MARUTI', 'TATA', 'BAJAJ', 'HERO']):
            return 'Automobiles'
        elif any(pharma in ticker_clean for pharma in ['SUNPHARMA', 'DRREDDY', 'CIPLA', 'LUPIN']):
            return 'Pharmaceuticals'
        else:
            return 'Unknown'
    
    def predict_stock_price(self, ticker: str, days: int = 30) -> Dict:
        """
        Predict stock price trend using simple machine learning.
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to predict ahead
            
        Returns:
            Dictionary with prediction results
        """
        try:
            import yfinance as yf
            from sklearn.linear_model import LinearRegression
            from sklearn.metrics import mean_absolute_error
            
            # Get historical data (1 year)
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            
            if hist.empty or len(hist) < 50:
                return {
                    'ticker': ticker,
                    'prediction': 'Insufficient data',
                    'confidence': 0,
                    'current_price': 0,
                    'predicted_price': 0,
                    'change_percent': 0,
                    'model': 'N/A'
                }
            
            # Prepare features (using simple technical indicators)
            hist['price_change'] = hist['Close'].pct_change()
            hist['volume_change'] = hist['Volume'].pct_change()
            hist['high_low_ratio'] = hist['High'] / hist['Low']
            hist['days_since_start'] = range(len(hist))
            
            # Remove NaN values
            hist = hist.dropna()
            
            # Features for prediction
            features = ['days_since_start', 'Volume', 'high_low_ratio']
            X = hist[features].values
            y = hist['Close'].values
            
            # Train simple linear regression model
            model = LinearRegression()
            
            # Use 80% for training, 20% for validation
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]
            
            # Convert to numpy arrays to avoid type issues
            X_train = np.array(X_train)
            y_train = np.array(y_train)
            X_test = np.array(X_test)
            y_test = np.array(y_test)
            
            model.fit(X_train, y_train)
            
            # Calculate model accuracy
            y_pred_test = model.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred_test)
            y_test_mean = float(np.mean(np.array(y_test)))
            accuracy = max(0, 1 - (mae / y_test_mean))
            
            # Predict future price
            last_day = len(hist)
            future_day = last_day + days
            last_volume = hist['Volume'].iloc[-1]
            last_ratio = hist['high_low_ratio'].iloc[-1]
            
            future_features = np.array([[future_day, last_volume, last_ratio]])
            predicted_price = model.predict(future_features)[0]
            
            current_price = hist['Close'].iloc[-1]
            change_percent = ((predicted_price - current_price) / current_price) * 100
            
            # Determine prediction confidence based on model accuracy and market volatility
            volatility = hist['price_change'].std()
            confidence = min(0.9, accuracy * (1 - volatility * 10))  # Cap at 90%
            
            return {
                'ticker': ticker,
                'prediction': 'increase' if change_percent > 0 else 'decrease',
                'confidence': round(confidence, 2),
                'current_price': round(current_price, 2),
                'predicted_price': round(predicted_price, 2),
                'change_percent': round(change_percent, 2),
                'model': 'Linear Regression',
                'data_points': len(hist),
                'volatility': round(volatility, 4),
                'validation': esg_validator.validate_prediction_model({
                    'confidence': confidence,
                    'change_percent': change_percent,
                    'data_points': len(hist),
                    'model': 'Linear Regression'
                }),
                'accuracy_warning': '⚠️ This is a statistical estimate only. Not financial advice.'
            }
            
        except Exception as e:
            return {
                'ticker': ticker,
                'prediction': f'Error: {str(e)}',
                'confidence': 0,
                'current_price': 0,
                'predicted_price': 0,
                'change_percent': 0,
                'model': 'Failed'
            }
    
    def detect_manipulation_signals(self, ticker: str) -> Dict:
        """
        Detect potential market manipulation signals.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with manipulation risk assessment
        """
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            
            # Get recent trading data (30 days)
            hist = stock.history(period="30d")
            if hist.empty:
                return {'ticker': ticker, 'risk_level': 'No Data', 'alerts': []}
            
            alerts = []
            risk_score = 0
            
            # Check for volume spikes
            avg_volume = hist['Volume'].mean()
            recent_volume = hist['Volume'].iloc[-1]
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 0
            
            if volume_ratio > self.volume_threshold:
                alerts.append(f"Unusual volume spike: {volume_ratio:.1f}x average")
                risk_score += 30
            
            # Check for price volatility
            price_changes = hist['Close'].pct_change().abs()
            recent_volatility = price_changes.iloc[-1]
            
            if recent_volatility > self.volatility_threshold:
                alerts.append(f"High price volatility: {recent_volatility*100:.1f}% daily change")
                risk_score += 25
            
            # Check for consecutive unusual movements
            large_moves = (price_changes > self.volatility_threshold).sum()
            if large_moves > 5:  # More than 5 large moves in 30 days
                alerts.append(f"Frequent large price movements: {large_moves} occurrences")
                risk_score += 20
            
            # Get news-based alerts
            news_alerts = self._check_manipulation_news(ticker)
            alerts.extend(news_alerts)
            risk_score += len(news_alerts) * 15
            
            # Determine risk level
            if risk_score >= 70:
                risk_level = 'High Risk'
            elif risk_score >= 40:
                risk_level = 'Medium Risk'
            elif risk_score >= 20:
                risk_level = 'Low Risk'
            else:
                risk_level = 'Minimal Risk'
            
            return {
                'ticker': ticker,
                'risk_level': risk_level,
                'risk_score': min(100, risk_score),
                'alerts': alerts,
                'volume_ratio': round(volume_ratio, 2),
                'recent_volatility': round(recent_volatility * 100, 2),
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'ticker': ticker,
                'risk_level': 'Analysis Failed',
                'alerts': [f"Error: {str(e)}"],
                'risk_score': 0
            }
    
    def _check_manipulation_news(self, ticker: str) -> List[str]:
        """Check for manipulation-related news using News API."""
        if not self.news_api_key:
            return []
        
        try:
            from newsapi import NewsApiClient
            
            newsapi = NewsApiClient(api_key=self.news_api_key)
            
            # Get company name for news search
            company_name = ""
            if ticker in self.indian_stock_universe:
                company_name = self.indian_stock_universe[ticker]['name']
            else:
                # Use ticker without .NS
                company_name = ticker.replace('.NS', '')
            
            # Search for regulatory/legal news
            keywords = [
                f"{company_name} investigation",
                f"{company_name} regulatory",
                f"{company_name} ban",
                f"{company_name} fraud",
                f"{company_name} manipulation"
            ]
            
            alerts = []
            for keyword in keywords:
                try:
                    articles = newsapi.get_everything(
                        q=keyword,
                        language='en',
                        sort_by='publishedAt',
                        from_param=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                    )
                    
                    if articles['totalResults'] > 0:
                        alerts.append(f"Recent news: {keyword}")
                        break  # Don't spam with multiple similar alerts
                        
                except Exception:
                    continue
            
            return alerts[:2]  # Limit to 2 news alerts
            
        except Exception as e:
            print(f"News API error: {e}")
            return []
    
    def _format_market_cap(self, market_cap: float) -> str:
        """Format market cap in readable format."""
        if market_cap >= 1e12:
            return f"₹{market_cap/1e12:.1f}T"
        elif market_cap >= 1e9:
            return f"₹{market_cap/1e9:.1f}B"
        elif market_cap >= 1e6:
            return f"₹{market_cap/1e6:.1f}M"
        else:
            return f"₹{market_cap:,.0f}"
    
    def get_comprehensive_analysis(self, ticker: str) -> Dict:
        """
        Get comprehensive analysis including ESG, prediction, and manipulation detection.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Complete analysis dictionary
        """
        # Get basic ESG data
        stock_data = self.yahoo_client.fetch_company_data(ticker)
        
        # Get predictions
        prediction = self.predict_stock_price(ticker)
        
        # Check for manipulation signals
        manipulation = self.detect_manipulation_signals(ticker)
        
        # Get alternatives if problematic
        alternatives = []
        if hasattr(stock_data, 'is_delisted') and hasattr(stock_data, 'error_message'):
            if getattr(stock_data, 'is_delisted', False) or getattr(stock_data, 'error_message', None):
                alternatives = self.get_stock_alternatives(ticker)
        
        return {
            'ticker': ticker,
            'basic_data': {
                'name': self.indian_stock_universe.get(ticker, {}).get('name', 'Unknown'),
                'sector': self.indian_stock_universe.get(ticker, {}).get('sector', 'Unknown'),
                'market_cap': getattr(stock_data, 'market_cap', 0),
                'market_cap_formatted': self._format_market_cap(getattr(stock_data, 'market_cap', 0)),
                'esg_score': getattr(stock_data, 'esg_score', 0),
                'environmental': getattr(stock_data, 'environmental', 0),
                'social': getattr(stock_data, 'social', 0),
                'governance': getattr(stock_data, 'governance', 0),
                'roic': getattr(stock_data, 'roic', 0),
                'is_delisted': getattr(stock_data, 'is_delisted', False),
                'data_source': getattr(stock_data, 'data_source', 'unknown'),
                'error_message': getattr(stock_data, 'error_message', None)
            },
            'prediction': prediction,
            'manipulation_risk': manipulation,
            'alternatives': alternatives,
            'analysis_timestamp': datetime.now().isoformat()
        }


# Initialize the enhanced analytics engine
enhanced_analytics = EnhancedESGAnalytics()
