"""
Pytest configuration for ESG Engine tests.
"""
import pytest
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def anyio_backend():
    """Configure anyio backend for async tests."""
    return "asyncio"


@pytest.fixture
def mock_esg_data():
    """Fixture providing sample ESG data for tests."""
    return [
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
