# Integration with Existing FastAPI Backend
# Add these routes to your existing backend/app.py on Render

from fastapi import HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import sys
import os

# Add the dashboard directory to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'dashboard'))

try:
    from enhanced_analytics import EnhancedESGAnalytics
except ImportError:
    # Fallback if enhanced_analytics is not available
    EnhancedESGAnalytics = None

# Request/Response models
class StockSearchResponse(BaseModel):
    symbol: str
    name: str
    sector: str
    logo_url: str
    market_cap: str

class PredictionResponse(BaseModel):
    symbol: str
    current_price: float
    predicted_price: float
    confidence: float
    prediction_date: str
    technical_indicators: Dict[str, Any]

class ManipulationResponse(BaseModel):
    symbol: str
    risk_score: float
    risk_level: str
    alerts: List[str]
    news_sentiment: float

# Enhanced API Routes - Add these to your existing FastAPI app

@app.get("/api/enhanced/search", response_model=List[StockSearchResponse])
async def search_stocks_enhanced(query: str):
    """Enhanced stock search with fuzzy matching"""
    if not EnhancedESGAnalytics:
        raise HTTPException(status_code=503, detail="Enhanced analytics not available")
    
    try:
        analytics = EnhancedESGAnalytics()
        results = analytics.search_stocks(query)
        
        return [StockSearchResponse(
            symbol=stock['symbol'],
            name=stock['name'],
            sector=stock.get('sector', 'Unknown'),
            logo_url=stock.get('logo_url', ''),
            market_cap=stock.get('market_cap', 'N/A')
        ) for stock in results]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/api/enhanced/predict", response_model=PredictionResponse)
async def predict_stock_price(symbol: str):
    """ML-powered stock price prediction"""
    if not EnhancedESGAnalytics:
        raise HTTPException(status_code=503, detail="Enhanced analytics not available")
    
    try:
        analytics = EnhancedESGAnalytics()
        prediction = analytics.predict_stock_price(symbol)
        
        return PredictionResponse(
            symbol=symbol,
            current_price=prediction['current_price'],
            predicted_price=prediction['predicted_price'],
            confidence=prediction['confidence'],
            prediction_date=prediction['prediction_date'],
            technical_indicators=prediction['technical_indicators']
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.get("/api/enhanced/manipulation", response_model=ManipulationResponse)
async def detect_manipulation(symbol: str):
    """Market manipulation detection"""
    if not EnhancedESGAnalytics:
        raise HTTPException(status_code=503, detail="Enhanced analytics not available")
    
    try:
        analytics = EnhancedESGAnalytics()
        analysis = analytics.detect_manipulation_signals(symbol)
        
        return ManipulationResponse(
            symbol=symbol,
            risk_score=analysis['risk_score'],
            risk_level=analysis['risk_level'],
            alerts=analysis['alerts'],
            news_sentiment=analysis['news_sentiment']
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manipulation detection failed: {str(e)}")

@app.get("/api/enhanced/portfolio-analysis")
async def analyze_portfolio_enhanced(symbols: str):
    """Enhanced portfolio analysis with ML insights"""
    if not EnhancedESGAnalytics:
        raise HTTPException(status_code=503, detail="Enhanced analytics not available")
    
    try:
        symbol_list = symbols.split(',')
        analytics = EnhancedESGAnalytics()
        
        results = []
        for symbol in symbol_list:
            # Get basic ESG data (from your existing function)
            esg_data = await get_esg_analysis(symbol)  # Your existing function
            
            # Add enhanced ML predictions
            prediction = analytics.predict_stock_price(symbol.strip())
            manipulation = analytics.detect_manipulation_signals(symbol.strip())
            
            results.append({
                'symbol': symbol.strip(),
                'esg_data': esg_data,
                'ml_prediction': prediction,
                'manipulation_risk': manipulation
            })
        
        return {
            'portfolio_analysis': results,
            'summary': {
                'total_stocks': len(results),
                'high_risk_count': sum(1 for r in results if r['manipulation_risk']['risk_score'] > 0.7),
                'avg_prediction_confidence': sum(r['ml_prediction']['confidence'] for r in results) / len(results)
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Portfolio analysis failed: {str(e)}")

# Health check for enhanced features
@app.get("/api/enhanced/health")
async def enhanced_health_check():
    """Check if enhanced features are available"""
    return {
        'enhanced_analytics_available': EnhancedESGAnalytics is not None,
        'features': {
            'stock_search': True,
            'ml_predictions': True,
            'manipulation_detection': True,
            'enhanced_portfolio_analysis': True
        } if EnhancedESGAnalytics else {},
        'status': 'healthy' if EnhancedESGAnalytics else 'limited'
    }
