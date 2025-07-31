"""
Database connection for ESG Engine backend.
Uses TinyDB or SQLite.
"""
import os
from datetime import datetime
from typing import Dict, List, Optional
from tinydb import TinyDB, Query
from dotenv import load_dotenv

load_dotenv()


class ESGDB:
    """
    TinyDB wrapper for ESG data storage with upsert functionality.
    Ensures idempotency - re-running with same tickers updates, never duplicates.
    """
    
    def __init__(self, db_path: str = "data/esg.json"):
        """Initialize the ESG database."""
        self.db = TinyDB(db_path)
        self.table = self.db.table('esg_data')
    
    def upsert_esg_record(self, record: Dict) -> None:
        """
        Upsert an ESG record. Updates existing record if ticker exists, 
        otherwise inserts new record.
        
        Args:
            record: Dictionary containing ESG data with required fields:
                - ticker: str
                - environmental: float
                - social: float  
                - governance: float
                - esg_score: float
                - roic: float
                - market_cap: float
                - last_updated: iso8601 string
                - data_source: str (optional)
                - is_delisted: bool (optional)
                - error_message: str (optional)
                - currency: str (optional)
        """
        # Validate required fields
        required_fields = [
            'ticker', 'environmental', 'social', 'governance', 
            'esg_score', 'roic', 'market_cap', 'last_updated'
        ]
        
        for field in required_fields:
            if field not in record:
                raise ValueError(f"Missing required field: {field}")
        
        # Ensure last_updated is ISO format
        if isinstance(record['last_updated'], datetime):
            record['last_updated'] = record['last_updated'].isoformat()
        
        # Upsert based on ticker
        ESG = Query()
        self.table.upsert(record, ESG.ticker == record['ticker'])
    
    def get_esg_record(self, ticker: str) -> Optional[Dict]:
        """
        Get ESG record for a specific ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dict with ESG data or None if not found
        """
        ESG = Query()
        result = self.table.search(ESG.ticker == ticker)
        return result[0] if result else None
    
    def get_all_records(self) -> List[Dict]:
        """
        Get all ESG records.
        
        Returns:
            List of all ESG records
        """
        # Convert TinyDB Documents to regular dictionaries
        return [dict(doc) for doc in self.table.all()]
    
    def delete_record(self, ticker: str) -> bool:
        """
        Delete ESG record for a specific ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            True if record was deleted, False if not found
        """
        ESG = Query()
        deleted = self.table.remove(ESG.ticker == ticker)
        return len(deleted) > 0
    
    def close(self) -> None:
        """Close the database connection."""
        self.db.close()


# Standalone wrapper functions for functional imports
def get_all_esg_records(db_path: str = "data/esg.json") -> List[Dict]:
    """Get all ESG records from database."""
    db = ESGDB(db_path)
    try:
        return db.get_all_records()
    finally:
        db.close()


def upsert_esg_record(record: Dict, db_path: str = "data/esg.json") -> None:
    """Upsert an ESG record to database."""
    db = ESGDB(db_path)
    try:
        db.upsert_esg_record(record)
    finally:
        db.close()


def get_esg_record(ticker: str, db_path: str = "data/esg.json") -> Optional[Dict]:
    """Get a single ESG record by ticker."""
    db = ESGDB(db_path)
    try:
        return db.get_esg_record(ticker)
    finally:
        db.close()


def delete_esg_record(ticker: str, db_path: str = "data/esg.json") -> bool:
    """Delete an ESG record by ticker."""
    db = ESGDB(db_path)
    try:
        return db.delete_record(ticker)
    finally:
        db.close()


# Utility functions
def get_database_path() -> str:
    """Get the default database path."""
    return "data/esg.json"


def create_sample_data() -> None:
    """Create sample ESG data for testing."""
    sample_records = [
        {
            'ticker': 'RELIANCE.NS',
            'environmental': 75,
            'social': 80,
            'governance': 85,
            'esg_score': 80,
            'roic': 0.12,
            'market_cap': 15000000000000,
            'last_updated': datetime.now().isoformat(),
            'data_source': 'sample',
            'is_delisted': False,
            'error_message': '',
            'currency': 'INR'
        },
        {
            'ticker': 'TCS.NS',
            'environmental': 85,
            'social': 90,
            'governance': 95,
            'esg_score': 90,
            'roic': 0.25,
            'market_cap': 12000000000000,
            'last_updated': datetime.now().isoformat(),
            'data_source': 'sample',
            'is_delisted': False,
            'error_message': '',
            'currency': 'INR'
        }
    ]
    
    for record in sample_records:
        upsert_esg_record(record)
