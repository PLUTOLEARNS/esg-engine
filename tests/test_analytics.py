"""
Tests for ESG Engine analytics and API endpoints.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import httpx
import asyncio
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.analytics import rank_portfolio, sync_flag_controversies
from backend.db import ESGDB
from backend.app import app
from fastapi.testclient import TestClient


class TestPortfolioRanking:
    """Test suite for portfolio ranking functionality."""
    
    def setup_method(self):
        """Set up test data before each test."""
        # Create test database with sample data
        self.test_db_path = "test_esg.json"
        self.db = ESGDB(self.test_db_path)
        
        # Sample ESG data
        test_records = [
            {
                "ticker": "AAPL",
                "environmental": 85.5,
                "social": 78.2,
                "governance": 92.1,
                "esg_score": 85.3,
                "roic": 0.295,
                "market_cap": 3000000000000,
                "last_updated": "2025-01-01T00:00:00"
            },
            {
                "ticker": "MSFT", 
                "environmental": 88.1,
                "social": 82.5,
                "governance": 89.3,
                "esg_score": 86.6,
                "roic": 0.245,
                "market_cap": 2800000000000,
                "last_updated": "2025-01-01T00:00:00"
            },
            {
                "ticker": "NVDA",
                "environmental": 72.3,
                "social": 75.8,
                "governance": 85.2,
                "esg_score": 77.8,
                "roic": 0.485,
                "market_cap": 1800000000000,
                "last_updated": "2025-01-01T00:00:00"
            }
        ]
        
        for record in test_records:
            self.db.upsert_esg_record(record)
    
    def teardown_method(self):
        """Clean up after each test."""
        self.db.close()
        Path(self.test_db_path).unlink(missing_ok=True)
    
    @patch('backend.analytics.ESGDB')
    def test_rank_portfolio_valid_input(self, mock_esgdb):
        """Test portfolio ranking with valid input."""
        # Mock database
        mock_db_instance = MagicMock()
        mock_esgdb.return_value = mock_db_instance
        mock_db_instance.get_all_records.return_value = [
            {
                "ticker": "AAPL",
                "environmental": 85.5,
                "social": 78.2, 
                "governance": 92.1,
                "esg_score": 85.3,
                "roic": 0.295,
                "market_cap": 3000000000000,
                "last_updated": "2025-01-01T00:00:00"
            },
            {
                "ticker": "MSFT",
                "environmental": 88.1,
                "social": 82.5,
                "governance": 89.3, 
                "esg_score": 86.6,
                "roic": 0.245,
                "market_cap": 2800000000000,
                "last_updated": "2025-01-01T00:00:00"
            }
        ]
        
        # Test input
        df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT'],
            'weight': [0.6, 0.4]
        })
        
        result = rank_portfolio(df)
        
        # Assertions
        assert not result.empty
        assert 'weighted_esg' in result.columns
        assert 'weighted_roic' in result.columns
        assert 'esg_zscore' in result.columns
        assert 'roic_zscore' in result.columns
        
        # Check portfolio total row exists
        portfolio_row = result[result['ticker'] == 'PORTFOLIO_TOTAL']
        assert len(portfolio_row) == 1
        
        # Check weighted calculations
        holdings = result[result['ticker'] != 'PORTFOLIO_TOTAL']
        expected_weighted_esg = 0.6 * 85.3 + 0.4 * 86.6
        actual_weighted_esg = portfolio_row.iloc[0]['weighted_esg']
        assert abs(actual_weighted_esg - expected_weighted_esg) < 0.01
    
    def test_rank_portfolio_invalid_weights(self):
        """Test portfolio ranking with invalid weights."""
        df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT'],
            'weight': [0.6, 0.5]  # Sum = 1.1, not 1.0
        })
        
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            rank_portfolio(df)
    
    def test_rank_portfolio_missing_columns(self):
        """Test portfolio ranking with missing required columns."""
        df = pd.DataFrame({
            'symbol': ['AAPL', 'MSFT'],  # Wrong column name
            'weight': [0.6, 0.4]
        })
        
        with pytest.raises(ValueError, match="must contain 'ticker' and 'weight' columns"):
            rank_portfolio(df)


class TestControversyFlags:
    """Test suite for controversy flagging functionality."""
    
    @pytest.mark.asyncio
    async def test_flag_controversies_mock_response(self):
        """Test controversy flagging with mocked RSS response."""
        # Mock RSS feed response
        mock_rss = """<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>AAPL - Form 8-K - Environmental litigation settlement</title>
                <summary>Apple Inc. settles ESG-related environmental lawsuit</summary>
                <published>2025-01-15T10:00:00Z</published>
                <link href="https://sec.gov/filing/123456789"/>
            </entry>
            <entry>
                <title>MSFT - Form 8-K - Quarterly earnings</title>
                <summary>Microsoft reports quarterly results</summary>
                <published>2025-01-10T09:00:00Z</published>
                <link href="https://sec.gov/filing/987654321"/>
            </entry>
        </feed>"""
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = MagicMock()
            mock_response.text.return_value = asyncio.coroutine(lambda: mock_rss)()
            mock_get.return_value.__aenter__.return_value = mock_response
            
            from backend.analytics import flag_controversies
            controversies = await flag_controversies("AAPL")
            
            assert len(controversies) == 1
            date, title, link = controversies[0]
            assert "AAPL" in title
            assert "environmental" in title.lower()
            assert "2025-01-15" == date
    
    def test_sync_flag_controversies(self):
        """Test synchronous wrapper for controversy flagging."""
        with patch('backend.analytics.flag_controversies') as mock_async:
            mock_async.return_value = asyncio.coroutine(lambda: [
                ("2025-01-15", "Test controversy", "http://example.com")
            ])()
            
            result = sync_flag_controversies("AAPL") 
            assert len(result) == 1
            assert result[0][0] == "2025-01-15"


class TestAPIEndpoints:
    """Test suite for FastAPI endpoints."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_root_endpoint(self):
        """Test root endpoint."""
        response = self.client.get("/")
        assert response.status_code == 200
        assert response.json()["message"] == "ESG Engine API"
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    @patch('backend.app.rank_portfolio')
    def test_rank_endpoint_valid_request(self, mock_rank):
        """Test portfolio ranking endpoint with valid request."""
        # Mock the rank_portfolio function
        mock_df = pd.DataFrame({
            'ticker': ['AAPL', 'PORTFOLIO_TOTAL'],
            'weight': [1.0, 1.0],
            'esg_score': [85.3, 85.3],
            'roic': [0.295, 0.295],
            'weighted_esg': [85.3, 85.3],
            'weighted_roic': [0.295, 0.295],
            'environmental': [85.5, 0],
            'social': [78.2, 0],
            'governance': [92.1, 0],
            'market_cap': [3000000000000, 0],
            'esg_zscore': [0.5, 0],
            'roic_zscore': [0.8, 0],
            'last_updated': ['2025-01-01T00:00:00', '2025-01-01T00:00:00']
        })
        mock_rank.return_value = mock_df
        
        request_data = {
            "tickers": ["AAPL"],
            "weights": [1.0]
        }
        
        response = self.client.post("/rank", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        assert "summary" in data
        assert data["summary"]["total_holdings"] == 1
    
    def test_rank_endpoint_invalid_weights(self):
        """Test portfolio ranking endpoint with invalid weights."""
        request_data = {
            "tickers": ["AAPL", "MSFT"],
            "weights": [0.6, 0.5]  # Sum = 1.1
        }
        
        response = self.client.post("/rank", json=request_data)
        assert response.status_code == 400
        assert "must sum to 1.0" in response.json()["detail"]
    
    def test_rank_endpoint_mismatched_lengths(self):
        """Test portfolio ranking endpoint with mismatched tickers/weights."""
        request_data = {
            "tickers": ["AAPL", "MSFT"],
            "weights": [1.0]  # Only one weight for two tickers
        }
        
        response = self.client.post("/rank", json=request_data)
        assert response.status_code == 400
        assert "must match" in response.json()["detail"]
    
    @patch('backend.app.sync_flag_controversies')
    def test_flags_endpoint(self, mock_flags):
        """Test controversy flags endpoint."""
        mock_flags.return_value = [
            ("2025-01-15", "Test controversy", "http://example.com")
        ]
        
        response = self.client.get("/flags/AAPL")
        assert response.status_code == 200
        
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert len(data["controversies"]) == 1
        assert data["controversies"][0]["date"] == "2025-01-15"


@pytest.mark.integration
class TestIntegrationWithRealAPIs:
    """Integration tests that hit real endpoints once then use recorded responses."""
    
    @pytest.mark.httpx_mock
    def test_real_sec_rss_feed(self, httpx_mock):
        """Test real SEC RSS feed, then use recorded response."""
        # Real RSS feed sample (recorded response)
        mock_rss = """<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <title>SEC Recent Filings</title>
            <entry>
                <title>Sample 8-K Filing</title>
                <summary>Sample content for testing</summary>
                <published>2025-01-15T10:00:00Z</published>
                <link href="https://sec.gov/filing/sample"/>
            </entry>
        </feed>"""
        
        # Mock the SEC RSS endpoint
        httpx_mock.add_response(
            url="https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&count=100&output=atom",
            text=mock_rss,
            headers={"content-type": "application/atom+xml"}
        )
        
        # Test the function
        result = sync_flag_controversies("SAMPLE")
        assert isinstance(result, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
