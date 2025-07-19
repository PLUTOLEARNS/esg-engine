"""
Simple test runner for ESG Engine (without pytest dependencies).
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.analytics import rank_portfolio, sync_flag_controversies
from backend.db import ESGDB


def test_portfolio_ranking():
    """Test portfolio ranking functionality."""
    print("Testing portfolio ranking...")
    
    # Create test database
    db = ESGDB("test_esg.json")
    
    # Add test data
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
        }
    ]
    
    for record in test_records:
        db.upsert_esg_record(record)
    
    # Test portfolio ranking
    df = pd.DataFrame({
        'ticker': ['AAPL', 'MSFT'],
        'weight': [0.6, 0.4]
    })
    
    try:
        result = rank_portfolio(df)
        print(f"✅ Portfolio ranking successful. Result shape: {result.shape}")
        print(f"   Columns: {list(result.columns)}")
        
        # Check portfolio total
        portfolio_row = result[result['ticker'] == 'PORTFOLIO_TOTAL']
        if len(portfolio_row) == 1:
            print(f"✅ Portfolio total calculated: ESG={portfolio_row.iloc[0]['weighted_esg']:.2f}")
        else:
            print("❌ Portfolio total row missing")
            
    except Exception as e:
        print(f"❌ Portfolio ranking failed: {e}")
    finally:
        db.close()
        Path("test_esg.json").unlink(missing_ok=True)


def test_controversy_flags():
    """Test controversy flagging functionality."""
    print("\nTesting controversy flags...")
    
    try:
        # Test with a known ticker (this will make real API call)
        controversies = sync_flag_controversies("AAPL")
        print(f"✅ Controversy flagging successful. Found {len(controversies)} potential issues")
        
        if controversies:
            print(f"   Latest controversy: {controversies[0][1][:50]}...")
        
    except Exception as e:
        print(f"❌ Controversy flagging failed: {e}")


def test_api_endpoints():
    """Test API endpoints."""
    print("\nTesting API endpoints...")
    
    try:
        from fastapi.testclient import TestClient
        from backend.app import app
        
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/health")
        if response.status_code == 200:
            print("✅ Health endpoint working")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
        
        # Test root endpoint
        response = client.get("/")
        if response.status_code == 200:
            print("✅ Root endpoint working")
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            
    except ImportError:
        print("⚠️  FastAPI not available for endpoint testing")
    except Exception as e:
        print(f"❌ API endpoint testing failed: {e}")


if __name__ == "__main__":
    print("ESG Engine Test Suite")
    print("=" * 40)
    
    test_portfolio_ranking()
    test_controversy_flags()
    test_api_endpoints()
    
    print("\n" + "=" * 40)
    print("Test suite completed!")
