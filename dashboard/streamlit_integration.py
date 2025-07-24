# Enhanced Streamlit Integration
# Add these components to your existing frontend/streamlit_app.py

import streamlit as st
import requests
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd

# Configuration
ENHANCED_API_BASE = "http://localhost:8000/api/enhanced"  # Your FastAPI backend
# For production: ENHANCED_API_BASE = "https://your-render-backend.onrender.com/api/enhanced"

def check_enhanced_features():
    """Check if enhanced features are available"""
    try:
        response = requests.get(f"{ENHANCED_API_BASE}/health", timeout=5)
        return response.json().get('enhanced_analytics_available', False)
    except:
        return False

def enhanced_stock_search():
    """Enhanced stock search component"""
    st.subheader("🔍 Enhanced Stock Search")
    
    query = st.text_input("Search for stocks (try 'Tata', 'RELIANCE', 'banking')")
    
    if query:
        try:
            response = requests.get(f"{ENHANCED_API_BASE}/search", params={'query': query})
            if response.status_code == 200:
                stocks = response.json()
                
                if stocks:
                    st.write(f"Found {len(stocks)} matches:")
                    
                    # Display as cards
                    cols = st.columns(min(3, len(stocks)))
                    for idx, stock in enumerate(stocks[:6]):  # Show max 6 results
                        with cols[idx % 3]:
                            with st.container():
                                st.write(f"**{stock['symbol']}**")
                                st.write(f"{stock['name']}")
                                st.write(f"Sector: {stock['sector']}")
                                
                                if st.button(f"Analyze {stock['symbol']}", key=f"analyze_{stock['symbol']}"):
                                    st.session_state.selected_stock = stock['symbol']
                                    st.rerun()
                else:
                    st.info("No stocks found. Try a different search term.")
            else:
                st.error("Search failed. Make sure the enhanced backend is running.")
        except Exception as e:
            st.error(f"Search error: {str(e)}")

def enhanced_stock_analysis(symbol):
    """Enhanced stock analysis with ML predictions"""
    st.subheader(f"📊 Enhanced Analysis: {symbol}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### 🤖 ML Price Prediction")
        try:
            response = requests.post(f"{ENHANCED_API_BASE}/predict", json={'symbol': symbol})
            if response.status_code == 200:
                prediction = response.json()
                
                # Display prediction
                current_price = prediction['current_price']
                predicted_price = prediction['predicted_price']
                confidence = prediction['confidence']
                
                # Price change calculation
                price_change = predicted_price - current_price
                price_change_pct = (price_change / current_price) * 100
                
                # Metrics
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Current Price", f"₹{current_price:.2f}")
                with col_b:
                    st.metric("Predicted Price", f"₹{predicted_price:.2f}", 
                             delta=f"{price_change_pct:+.1f}%")
                with col_c:
                    st.metric("Confidence", f"{confidence:.1%}")
                
                # Technical indicators
                if 'technical_indicators' in prediction:
                    with st.expander("Technical Indicators"):
                        indicators = prediction['technical_indicators']
                        for key, value in indicators.items():
                            st.write(f"**{key}**: {value}")
                
            else:
                st.error("Prediction failed")
        except Exception as e:
            st.error(f"Prediction error: {str(e)}")
    
    with col2:
        st.write("### 🚨 Manipulation Detection")
        try:
            response = requests.get(f"{ENHANCED_API_BASE}/manipulation", params={'symbol': symbol})
            if response.status_code == 200:
                manipulation = response.json()
                
                risk_score = manipulation['risk_score']
                risk_level = manipulation['risk_level']
                alerts = manipulation['alerts']
                news_sentiment = manipulation['news_sentiment']
                
                # Risk score gauge
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number+delta",
                    value = risk_score * 100,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "Risk Score"},
                    delta = {'reference': 50},
                    gauge = {
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "darkred" if risk_score > 0.7 else "orange" if risk_score > 0.4 else "green"},
                        'steps': [
                            {'range': [0, 40], 'color': "lightgreen"},
                            {'range': [40, 70], 'color': "yellow"},
                            {'range': [70, 100], 'color': "red"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 90
                        }
                    }
                ))
                fig.update_layout(height=250)
                st.plotly_chart(fig, use_container_width=True)
                
                # Risk level
                if risk_level == "HIGH":
                    st.error(f"⚠️ **HIGH RISK** - Score: {risk_score:.2f}")
                elif risk_level == "MEDIUM":
                    st.warning(f"⚠️ **MEDIUM RISK** - Score: {risk_score:.2f}")
                else:
                    st.success(f"✅ **LOW RISK** - Score: {risk_score:.2f}")
                
                # Alerts
                if alerts:
                    st.write("**Alerts:**")
                    for alert in alerts:
                        st.write(f"• {alert}")
                
                # News sentiment
                sentiment_color = "green" if news_sentiment > 0 else "red" if news_sentiment < 0 else "gray"
                st.write(f"**News Sentiment**: <span style='color:{sentiment_color}'>{news_sentiment:+.2f}</span>", unsafe_allow_html=True)
                
            else:
                st.error("Manipulation detection failed")
        except Exception as e:
            st.error(f"Manipulation detection error: {str(e)}")

def enhanced_portfolio_analysis(symbols):
    """Enhanced portfolio analysis"""
    st.subheader("📈 Enhanced Portfolio Analysis")
    
    try:
        symbols_str = ','.join(symbols)
        response = requests.get(f"{ENHANCED_API_BASE}/portfolio-analysis", params={'symbols': symbols_str})
        
        if response.status_code == 200:
            analysis = response.json()
            portfolio_data = analysis['portfolio_analysis']
            summary = analysis['summary']
            
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Stocks", summary['total_stocks'])
            with col2:
                st.metric("High Risk Stocks", summary['high_risk_count'])
            with col3:
                st.metric("Avg Prediction Confidence", f"{summary['avg_prediction_confidence']:.1%}")
            
            # Detailed analysis table
            df_data = []
            for stock in portfolio_data:
                df_data.append({
                    'Symbol': stock['symbol'],
                    'Current Price': f"₹{stock['ml_prediction']['current_price']:.2f}",
                    'Predicted Price': f"₹{stock['ml_prediction']['predicted_price']:.2f}",
                    'Confidence': f"{stock['ml_prediction']['confidence']:.1%}",
                    'Risk Score': f"{stock['manipulation_risk']['risk_score']:.2f}",
                    'Risk Level': stock['manipulation_risk']['risk_level']
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
            
            # Risk distribution chart
            risk_counts = pd.Series([stock['manipulation_risk']['risk_level'] for stock in portfolio_data]).value_counts()
            fig = px.pie(values=risk_counts.values, names=risk_counts.index, 
                        title="Portfolio Risk Distribution",
                        color_discrete_map={'LOW': 'green', 'MEDIUM': 'orange', 'HIGH': 'red'})
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.error("Portfolio analysis failed")
    except Exception as e:
        st.error(f"Portfolio analysis error: {str(e)}")

# Main integration function - add this to your existing streamlit_app.py
def add_enhanced_features():
    """Add enhanced features to existing Streamlit app"""
    
    # Check if enhanced features are available
    enhanced_available = check_enhanced_features()
    
    if enhanced_available:
        st.success("🚀 Enhanced Analytics Available!")
        
        # Add to sidebar
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 🌟 Enhanced Features")
            enable_enhanced = st.checkbox("Enable Enhanced Analytics", value=True)
        
        if enable_enhanced:
            # Add enhanced search
            enhanced_stock_search()
            
            # If a stock is selected, show enhanced analysis
            if 'selected_stock' in st.session_state:
                enhanced_stock_analysis(st.session_state.selected_stock)
            
            # Add enhanced portfolio analysis if portfolio exists
            if 'portfolio_symbols' in st.session_state and st.session_state.portfolio_symbols:
                enhanced_portfolio_analysis(st.session_state.portfolio_symbols)
    
    else:
        with st.sidebar:
            st.warning("⚠️ Enhanced features unavailable")
            st.info("Start the enhanced backend to access ML predictions and advanced analytics")

# Add this call to your main streamlit app
# add_enhanced_features()
