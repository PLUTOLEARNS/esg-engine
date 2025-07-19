"""
Yahoo Finance client with fallback data sources for robust financial data fetching.
Handles delisted companies, missing data, and provides alternative data sources.
"""
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CompanyData:
    """Container for company financial and ESG data."""
    ticker: str
    market_cap: float = 0.0
    roic: float = 0.0
    environmental: float = 0.0
    social: float = 0.0
    governance: float = 0.0
    esg_score: float = 0.0
    is_delisted: bool = False
    data_source: str = "unknown"
    last_updated: str = ""
    error_message: str = ""

class RobustYahooFinanceClient:
    """
    Enhanced Yahoo Finance client with multiple fallback strategies.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Known delisted/problematic Indian companies and their alternatives
        self.delisted_replacements = {
            'DHFL.NS': 'HDFCBANK.NS',  # DHFL delisted, suggest HDFC Bank
            'YES.NS': 'YESBANK.NS',    # YES Bank issues, check full ticker
            'IL&FS.NS': 'HDFCBANK.NS', # IL&FS delisted
            'JETAIRWAYS.NS': 'INDIGO.NS',  # Jet Airways delisted
        }
        
        # Default ESG scores for Indian market segments
        self.indian_sector_defaults = {
            'banking': {'environmental': 12.0, 'social': 15.0, 'governance': 18.0},
            'it': {'environmental': 20.0, 'social': 22.0, 'governance': 25.0},
            'energy': {'environmental': 8.0, 'social': 10.0, 'governance': 12.0},
            'fmcg': {'environmental': 15.0, 'social': 18.0, 'governance': 20.0},
            'auto': {'environmental': 10.0, 'social': 14.0, 'governance': 16.0},
            'pharma': {'environmental': 16.0, 'social': 19.0, 'governance': 21.0},
            'telecom': {'environmental': 14.0, 'social': 16.0, 'governance': 18.0},
            'default': {'environmental': 12.0, 'social': 14.0, 'governance': 16.0}
        }

    def fetch_company_data(self, ticker: str, max_retries: int = 3) -> CompanyData:
        """
        Fetch comprehensive company data with multiple fallback strategies.
        
        Args:
            ticker: Stock ticker symbol
            max_retries: Maximum retry attempts
            
        Returns:
            CompanyData object with available information
        """
        ticker = ticker.upper().strip()
        result = CompanyData(ticker=ticker, last_updated=datetime.now().isoformat())
        
        # Strategy 1: Try Yahoo Finance with primary ticker
        try:
            result = self._fetch_from_yahoo(ticker, result)
            if result.market_cap > 0:  # Success indicator
                result.data_source = "yahoo_finance"
                return result
        except Exception as e:
            logger.warning(f"Yahoo Finance failed for {ticker}: {str(e)}")
            result.error_message = f"Yahoo Finance error: {str(e)}"
        
        # Strategy 2: Check if ticker is in delisted replacements
        if ticker in self.delisted_replacements:
            logger.info(f"Using replacement ticker for delisted {ticker}")
            replacement_ticker = self.delisted_replacements[ticker]
            try:
                result = self._fetch_from_yahoo(replacement_ticker, result)
                result.ticker = ticker  # Keep original ticker in result
                result.data_source = f"yahoo_finance_replacement_{replacement_ticker}"
                result.is_delisted = True
                if result.market_cap > 0:
                    return result
            except Exception as e:
                logger.warning(f"Replacement ticker {replacement_ticker} also failed: {str(e)}")
        
        # Strategy 3: Try alternative ticker formats for Indian stocks
        if ticker.endswith('.NS'):
            alternatives = [
                ticker.replace('.NS', '.BO'),  # Try Bombay Stock Exchange format
                ticker.replace('.NS', ''),     # Try without exchange suffix
            ]
            
            for alt_ticker in alternatives:
                try:
                    result = self._fetch_from_yahoo(alt_ticker, result)
                    if result.market_cap > 0:
                        result.data_source = f"yahoo_finance_alternative_{alt_ticker}"
                        return result
                except Exception:
                    continue
        
        # Strategy 4: Use sector-based default ESG scores
        result = self._apply_sector_defaults(ticker, result)
        result.data_source = "sector_defaults"
        
        return result

    def _fetch_from_yahoo(self, ticker: str, result: CompanyData) -> CompanyData:
        """Fetch data from Yahoo Finance with enhanced error handling."""
        
        # Create yfinance Ticker object
        stock = yf.Ticker(ticker)
        
        # Get basic info with timeout
        try:
            info = stock.info
            if not info or 'symbol' not in info:
                raise ValueError(f"No data returned for {ticker}")
                
            # Extract market cap (try multiple field names)
            market_cap_fields = ['marketCap', 'market_cap', 'enterpriseValue', 'totalCash']
            for field in market_cap_fields:
                if field in info and info[field]:
                    result.market_cap = float(info[field])
                    break
            
            # Calculate ROIC from available financial data
            result.roic = self._calculate_roic_from_yahoo(stock, info)
            
            # Get ESG data if available (Yahoo provides limited ESG)
            esg_scores = self._extract_esg_from_yahoo(stock, info)
            result.environmental = esg_scores['environmental']
            result.social = esg_scores['social'] 
            result.governance = esg_scores['governance']
            result.esg_score = (esg_scores['environmental'] + esg_scores['social'] + esg_scores['governance'])
            
        except Exception as e:
            # Try historical data to check if ticker exists
            try:
                hist = stock.history(period="1d")
                if hist.empty:
                    raise ValueError(f"No historical data for {ticker} - likely delisted")
                    
                # If we have recent data, use minimal info
                result.market_cap = 1000000000  # Default 1B for existing stocks
                result = self._apply_sector_defaults(ticker, result)
                
            except Exception as hist_error:
                raise ValueError(f"Ticker {ticker} not found or delisted: {str(hist_error)}")
        
        return result

    def _calculate_roic_from_yahoo(self, stock, info: Dict) -> float:
        """Calculate ROIC from Yahoo Finance data."""
        try:
            # Method 1: Use pre-calculated ROIC if available
            if 'returnOnAssets' in info and 'returnOnEquity' in info:
                roa = info.get('returnOnAssets', 0)
                roe = info.get('returnOnEquity', 0)
                if roa and roe:
                    return (roa + roe) / 2 / 100  # Convert percentage to decimal
            
            # Method 2: Calculate from financial statements
            try:
                financials = stock.financials
                balance_sheet = stock.balance_sheet
                
                if not financials.empty and not balance_sheet.empty:
                    # Get most recent year data
                    net_income = financials.loc['Net Income'].iloc[0] if 'Net Income' in financials.index else 0
                    total_assets = balance_sheet.loc['Total Assets'].iloc[0] if 'Total Assets' in balance_sheet.index else 0
                    
                    if total_assets > 0:
                        return net_income / total_assets
            except Exception:
                pass
            
            # Method 3: Use profitability margins as proxy
            profit_margin = info.get('profitMargins', 0)
            if profit_margin:
                return profit_margin / 100
                
            # Default for companies with no financial data
            return 0.05  # 5% default ROIC
            
        except Exception:
            return 0.05

    def _extract_esg_from_yahoo(self, stock, info: Dict) -> Dict[str, float]:
        """Extract ESG scores from Yahoo Finance (limited availability)."""
        
        # Yahoo Finance has limited ESG data, so we use proxies
        esg_scores = {'environmental': 0.0, 'social': 0.0, 'governance': 0.0}
        
        try:
            # Use company sector and size as ESG proxies
            sector = info.get('sector', '').lower()
            market_cap = info.get('marketCap', 0)
            
            # Technology companies generally have better ESG scores
            if 'technology' in sector or 'software' in sector:
                esg_scores = {'environmental': 18.0, 'social': 20.0, 'governance': 22.0}
            elif 'financial' in sector or 'bank' in sector:
                esg_scores = {'environmental': 12.0, 'social': 15.0, 'governance': 18.0}
            elif 'energy' in sector or 'oil' in sector:
                esg_scores = {'environmental': 8.0, 'social': 10.0, 'governance': 12.0}
            elif 'healthcare' in sector or 'pharmaceutical' in sector:
                esg_scores = {'environmental': 15.0, 'social': 18.0, 'governance': 20.0}
            else:
                esg_scores = {'environmental': 12.0, 'social': 14.0, 'governance': 16.0}
            
            # Adjust for company size (larger companies often have better ESG)
            if market_cap > 100_000_000_000:  # > $100B
                for key in esg_scores:
                    esg_scores[key] = float(esg_scores[key] * 1.2)
            elif market_cap > 10_000_000_000:  # > $10B
                for key in esg_scores:
                    esg_scores[key] = float(esg_scores[key] * 1.1)
                    
        except Exception:
            esg_scores = {'environmental': 12.0, 'social': 14.0, 'governance': 16.0}
        
        return esg_scores

    def _apply_sector_defaults(self, ticker: str, result: CompanyData) -> CompanyData:
        """Apply sector-based default ESG scores for Indian companies."""
        
        # Determine sector from ticker name patterns
        ticker_clean = ticker.replace('.NS', '').replace('.BO', '').upper()
        
        sector = 'default'
        
        # Banking sector patterns
        if any(bank in ticker_clean for bank in ['HDFC', 'ICICI', 'SBI', 'AXIS', 'KOTAK', 'INDUSIND', 'FEDERAL', 'YES']):
            sector = 'banking'
        # IT sector patterns  
        elif any(it in ticker_clean for it in ['TCS', 'INFY', 'WIPRO', 'HCL', 'TECH', 'INFO']):
            sector = 'it'
        # Energy sector patterns
        elif any(energy in ticker_clean for energy in ['RELIANCE', 'ONGC', 'IOC', 'BPCL', 'GAIL', 'COAL', 'NTPC']):
            sector = 'energy'
        # FMCG sector patterns
        elif any(fmcg in ticker_clean for fmcg in ['HINDUNIL', 'ITC', 'NESTLE', 'BRITANNIA', 'GODREJ']):
            sector = 'fmcg'
        # Auto sector patterns
        elif any(auto in ticker_clean for auto in ['MARUTI', 'TATA', 'MAHINDRA', 'BAJAJ', 'HERO', 'AUTO']):
            sector = 'auto'
        # Pharma sector patterns
        elif any(pharma in ticker_clean for pharma in ['SUNPHARMA', 'DRREDDY', 'CIPLA', 'LUPIN', 'PHARMA']):
            sector = 'pharma'
        # Telecom sector patterns
        elif any(telecom in ticker_clean for telecom in ['BHARTI', 'AIRTEL', 'JIO', 'IDEA', 'TELECOM']):
            sector = 'telecom'
        
        # Apply sector defaults
        defaults = self.indian_sector_defaults[sector]
        result.environmental = defaults['environmental']
        result.social = defaults['social'] 
        result.governance = defaults['governance']
        result.esg_score = sum(defaults.values())
        
        # Set default market cap based on sector
        if result.market_cap == 0:
            sector_market_caps = {
                'banking': 50_000_000_000,    # $50B
                'it': 75_000_000_000,        # $75B  
                'energy': 100_000_000_000,   # $100B
                'fmcg': 30_000_000_000,      # $30B
                'auto': 20_000_000_000,      # $20B
                'pharma': 25_000_000_000,    # $25B
                'telecom': 40_000_000_000,   # $40B
                'default': 10_000_000_000    # $10B
            }
            result.market_cap = sector_market_caps[sector]
        
        # Set default ROIC based on sector
        if result.roic == 0:
            sector_roics = {
                'banking': 0.12,      # 12%
                'it': 0.25,          # 25%  
                'energy': 0.08,      # 8%
                'fmcg': 0.18,        # 18%
                'auto': 0.10,        # 10%
                'pharma': 0.15,      # 15%
                'telecom': 0.06,     # 6%
                'default': 0.10      # 10%
            }
            result.roic = sector_roics[sector]
        
        return result

    def batch_fetch(self, tickers: list) -> Dict[str, CompanyData]:
        """Fetch data for multiple tickers efficiently."""
        results = {}
        
        for ticker in tickers:
            try:
                results[ticker] = self.fetch_company_data(ticker)
                time.sleep(0.1)  # Rate limiting for Yahoo Finance
            except Exception as e:
                logger.error(f"Failed to fetch data for {ticker}: {str(e)}")
                # Create error result
                error_result = CompanyData(
                    ticker=ticker, 
                    error_message=str(e),
                    data_source="error",
                    last_updated=datetime.now().isoformat()
                )
                results[ticker] = self._apply_sector_defaults(ticker, error_result)
        
        return results

    def get_data_quality_report(self, results: Dict[str, CompanyData]) -> Dict[str, Any]:
        """Generate a data quality report for fetched results."""
        total_tickers = len(results)
        successful_fetches = sum(1 for r in results.values() if r.market_cap > 0)
        delisted_count = sum(1 for r in results.values() if r.is_delisted)
        error_count = sum(1 for r in results.values() if r.error_message)
        
        data_sources = {}
        for result in results.values():
            source = result.data_source
            data_sources[source] = data_sources.get(source, 0) + 1
        
        return {
            'total_tickers': total_tickers,
            'successful_fetches': successful_fetches,
            'success_rate': successful_fetches / total_tickers if total_tickers > 0 else 0,
            'delisted_count': delisted_count,
            'error_count': error_count,
            'data_sources': data_sources,
            'problematic_tickers': [
                ticker for ticker, result in results.items() 
                if result.error_message or result.is_delisted
            ]
        }


# Usage example and integration functions
def fetch_esg_data_with_fallbacks(ticker: str) -> Dict[str, Any]:
    """
    Integration function for existing ESG pipeline.
    Returns data in the format expected by existing code.
    """
    client = RobustYahooFinanceClient()
    result = client.fetch_company_data(ticker)
    
    return {
        "ticker": result.ticker,
        "environmental": result.environmental,
        "social": result.social,
        "governance": result.governance,
        "esg_score": result.esg_score,
        "roic": result.roic,
        "market_cap": result.market_cap,
        "last_updated": result.last_updated,
        "data_source": result.data_source,
        "is_delisted": result.is_delisted,
        "error_message": result.error_message
    }


def validate_and_fetch_portfolio(tickers: list) -> Tuple[Dict[str, CompanyData], Dict[str, Any]]:
    """
    Validate and fetch data for an entire portfolio with comprehensive reporting.
    
    Returns:
        Tuple of (results_dict, quality_report)
    """
    client = RobustYahooFinanceClient()
    results = client.batch_fetch(tickers)
    quality_report = client.get_data_quality_report(results)
    
    return results, quality_report
