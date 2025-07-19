"""
Analytics module for ESG portfolio ranking and controversy detection.
"""
import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Any
import re
from datetime import datetime
import asyncio
import aiohttp
from aiohttp import ClientTimeout
import xml.etree.ElementTree as ET
from backend.db import ESGDB
from backend.scrapers.yahoo_client import RobustYahooFinanceClient, validate_and_fetch_portfolio


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
    Synchronous wrapper for flag_controversies function.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        List of 3-tuples: (date, title, link) for relevant filings
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(flag_controversies(ticker))


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
                
                # Convert CompanyData to database record format
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
                    'is_delisted': company_data.is_delisted
                }
                
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
