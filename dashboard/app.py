"""
Enhanced ESG Portfolio Analytics Dashboard
A modern Flask-based dashboard extending the existing ESG Engine with new features.
"""
import os
import sys
import json
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Add parent directory to access existing backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import enhanced analytics
try:
    from enhanced_analytics import enhanced_analytics
except ImportError:
    # Fallback if dependencies not installed
    enhanced_analytics = None

load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')

@app.route('/api/search/<query>')
def search_stocks(query):
    """Search for stocks by company name, ticker, or sector."""
    try:
        if not enhanced_analytics:
            return jsonify({'error': 'Enhanced analytics not available. Install dependencies.'}), 500
        
        limit = request.args.get('limit', 10, type=int)
        results = enhanced_analytics.search_stocks(query, limit)
        return jsonify({'results': results, 'query': query})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze/<ticker>')
def analyze_stock(ticker):
    """Get comprehensive analysis for a stock."""
    try:
        if not enhanced_analytics:
            return jsonify({'error': 'Enhanced analytics not available. Install dependencies.'}), 500
        
        analysis = enhanced_analytics.get_comprehensive_analysis(ticker)
        return jsonify(analysis)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/predict/<ticker>')
def predict_stock(ticker):
    """Get stock price prediction."""
    try:
        if not enhanced_analytics:
            return jsonify({'error': 'Enhanced analytics not available. Install dependencies.'}), 500
        
        days = request.args.get('days', 30, type=int)
        prediction = enhanced_analytics.predict_stock_price(ticker, days)
        return jsonify(prediction)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/manipulation/<ticker>')
def check_manipulation(ticker):
    """Check for manipulation signals."""
    try:
        if not enhanced_analytics:
            return jsonify({'error': 'Enhanced analytics not available. Install dependencies.'}), 500
        
        manipulation = enhanced_analytics.detect_manipulation_signals(ticker)
        return jsonify(manipulation)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/alternatives/<ticker>')
def get_alternatives(ticker):
    """Get alternative stocks for delisted/problematic companies."""
    try:
        if not enhanced_analytics:
            return jsonify({'error': 'Enhanced analytics not available. Install dependencies.'}), 500
        
        count = request.args.get('count', 3, type=int)
        alternatives = enhanced_analytics.get_stock_alternatives(ticker, count)
        return jsonify({'alternatives': alternatives, 'original_ticker': ticker})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'enhanced_analytics': enhanced_analytics is not None,
        'timestamp': os.getenv('FLASK_ENV', 'production')
    })

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
