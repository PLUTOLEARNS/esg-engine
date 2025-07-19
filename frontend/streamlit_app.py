"""
Streamlit app entry point for ESG Engine frontend.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import io
import base64

load_dotenv()

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
CACHE_DURATION = timedelta(minutes=30)

# Page configuration
st.set_page_config(
    page_title="ESG Engine",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
def load_css():
    """Load custom CSS styles."""
    st.markdown("""
    <style>
    .metric-card {
        background-color: var(--background-color);
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid var(--secondary-background-color);
        margin: 0.5rem 0;
    }
    
    .metric-title {
        font-size: 0.8rem;
        color: var(--text-color);
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        margin: 0;
    }
    
    .metric-green { color: #28a745; }
    .metric-yellow { color: #ffc107; }
    .metric-red { color: #dc3545; }
    
    .stDataFrame {
        border: 1px solid var(--secondary-background-color);
        border-radius: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

def check_backend_health():
    """Check if backend is available."""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def upload_and_rank_portfolio(df: pd.DataFrame):
    """Upload portfolio and get ranking from backend."""
    try:
        # Prepare request data
        request_data = {
            "tickers": df['ticker'].tolist(),
            "weights": df['weight'].tolist()
        }
        
        # POST to backend
        response = requests.post(
            f"{BACKEND_URL}/rank",
            json=request_data,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Backend error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        st.error(f"Network error: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        return None

def get_controversy_data(ticker: str):
    """Get controversy data for a ticker."""
    try:
        response = requests.get(f"{BACKEND_URL}/flags/{ticker}", timeout=10)
        if response.status_code == 200:
            return response.json()
        return {"ticker": ticker, "controversies": []}
    except:
        return {"ticker": ticker, "controversies": []}

def create_kpi_cards(summary_data, controversy_count, theme="light"):
    """Create KPI cards with traffic light colors."""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        esg_score = summary_data.get("portfolio_weighted_esg", 0)
        
        # Traffic light logic for ESG score
        if esg_score >= 80:
            color_class = "metric-green"
            status = "🟢 Excellent"
        elif esg_score >= 60:
            color_class = "metric-yellow" 
            status = "🟡 Good"
        else:
            color_class = "metric-red"
            status = "🔴 Needs Improvement"
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Portfolio ESG Score</div>
            <div class="metric-value {color_class}">{esg_score:.1f}</div>
            <div style="font-size: 0.9rem; margin-top: 0.5rem;">{status}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        roic = summary_data.get("portfolio_weighted_roic", 0) * 100
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Weighted ROIC</div>
            <div class="metric-value">{roic:.1f}%</div>
            <div style="font-size: 0.9rem; margin-top: 0.5rem;">Return on Invested Capital</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        color_class = "metric-red" if controversy_count > 0 else "metric-green"
        status = f"🚨 {controversy_count} Issues" if controversy_count > 0 else "✅ Clean"
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Controversy Count</div>
            <div class="metric-value {color_class}">{controversy_count}</div>
            <div style="font-size: 0.9rem; margin-top: 0.5rem;">{status}</div>
        </div>
        """, unsafe_allow_html=True)

def create_radar_chart(portfolio_data, theme="light"):
    """Create radar chart comparing portfolio vs market benchmark."""
    if not portfolio_data or len(portfolio_data) == 0:
        st.warning("No data available for radar chart")
        return
    
    # Calculate portfolio averages (excluding PORTFOLIO_TOTAL row)
    df = pd.DataFrame(portfolio_data)
    holdings_df = df[df['ticker'] != 'PORTFOLIO_TOTAL']
    
    if holdings_df.empty:
        st.warning("No holdings data available")
        return
    
    # Calculate weighted averages for portfolio
    portfolio_env = (holdings_df['environmental'] * holdings_df['weight']).sum()
    portfolio_social = (holdings_df['social'] * holdings_df['weight']).sum()
    portfolio_gov = (holdings_df['governance'] * holdings_df['weight']).sum()
    
    # Determine market type and benchmark
    indian_stocks = holdings_df['ticker'].str.contains('.NS').sum()
    total_stocks = len(holdings_df)
    is_indian_focused = indian_stocks > total_stocks / 2
    
    # Use appropriate benchmark
    if is_indian_focused:
        # Indian market benchmarks (approximate NIFTY 50 ESG averages)
        benchmark_env = 15.0
        benchmark_social = 12.0 
        benchmark_gov = 18.0
        benchmark_name = "NIFTY 50 Average"
    else:
        # Global/US market benchmarks
        benchmark_env = 20.0
        benchmark_social = 15.0
        benchmark_gov = 22.0
        benchmark_name = "S&P 500 Average"
    
    # Create radar chart
    categories = ['Environmental', 'Social', 'Governance']
    
    fig = go.Figure()
    
    # Portfolio data
    fig.add_trace(go.Scatterpolar(
        r=[portfolio_env, portfolio_social, portfolio_gov],
        theta=categories,
        fill='toself',
        name='Your Portfolio',
        line_color='#1f77b4'
    ))
    
    # Market benchmark
    fig.add_trace(go.Scatterpolar(
        r=[benchmark_env, benchmark_social, benchmark_gov],
        theta=categories,
        fill='toself',
        name=benchmark_name,
        line_color='#ff7f0e',
        opacity=0.6
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 50]  # Adjusted for ESG score ranges
            )),
        showlegend=True,
        title=f"ESG Profile: Portfolio vs {benchmark_name}",
        template="plotly_white" if theme == "light" else "plotly_dark"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_esg_ranking_chart(portfolio_data, theme="light"):
    """Create bar chart of ALL holdings ranked by ESG score."""
    if not portfolio_data:
        st.warning("No data available for ESG ranking chart")
        return
    
    df = pd.DataFrame(portfolio_data)
    holdings_df = df[df['ticker'] != 'PORTFOLIO_TOTAL']
    
    if holdings_df.empty:
        st.warning("No holdings data available")
        return
    
    # Sort by ESG score (ascending - worst to best)
    holdings_df = holdings_df.sort_values('esg_score', ascending=True)
    
    # Create color mapping based on ESG score
    colors = ['#d73027' if score < 20 else '#f46d43' if score < 30 else '#fdae61' if score < 40 else '#74add1' if score < 50 else '#313695' 
              for score in holdings_df['esg_score']]
    
    # Create bar chart
    fig = px.bar(
        holdings_df,
        x='esg_score',
        y='ticker',
        orientation='h',
        title="Holdings Ranked by ESG Score",
        hover_data={
            'market_cap': ':,.0f',
            'weight': ':.1%',
            'environmental': ':.1f',
            'social': ':.1f', 
            'governance': ':.1f'
        },
        color='esg_score',
        color_continuous_scale='RdYlGn'
    )
    
    fig.update_layout(
        xaxis_title="ESG Score",
        yaxis_title="Holdings",
        template="plotly_white" if theme == "light" else "plotly_dark",
        height=max(400, len(holdings_df) * 40)  # Dynamic height based on number of holdings
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_portfolio_datatable(portfolio_data):
    """Create interactive datatable with sorting and filtering."""
    if not portfolio_data:
        st.warning("No data available for datatable")
        return
    
    df = pd.DataFrame(portfolio_data)
    holdings_df = df[df['ticker'] != 'PORTFOLIO_TOTAL'].copy()
    
    if holdings_df.empty:
        st.warning("No holdings data available")
        return
    
    # Format columns for display
    holdings_df['weight'] = holdings_df['weight'].apply(lambda x: f"{x:.1%}")
    holdings_df['esg_score'] = holdings_df['esg_score'].apply(lambda x: f"{x:.1f}")
    holdings_df['roic'] = holdings_df['roic'].apply(lambda x: f"{x:.1%}")
    holdings_df['market_cap'] = holdings_df['market_cap'].apply(lambda x: f"${x/1e9:.1f}B")
    holdings_df['esg_zscore'] = holdings_df['esg_zscore'].apply(lambda x: f"{x:.2f}")
    holdings_df['roic_zscore'] = holdings_df['roic_zscore'].apply(lambda x: f"{x:.2f}")
    
    # Select and rename columns for display
    display_df = holdings_df[[
        'ticker', 'weight', 'esg_score', 'environmental', 'social', 'governance',
        'roic', 'market_cap', 'esg_zscore', 'roic_zscore'
    ]].copy()
    
    display_df.columns = [
        'Ticker', 'Weight', 'ESG Score', 'Environmental', 'Social', 'Governance',
        'ROIC', 'Market Cap', 'ESG Z-Score', 'ROIC Z-Score'
    ]
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

def generate_pdf_report(portfolio_data, summary_data, controversy_count):
    """Generate professional PDF report using reportlab with enhanced design."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.colors import HexColor, black, white
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm, mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.graphics.shapes import Drawing, Rect, String
        from reportlab.graphics.charts.barcharts import VerticalBarChart
        from reportlab.graphics.charts.piecharts import Pie
        from reportlab.graphics import renderPDF
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        from io import BytesIO
        import base64
        
        # Create PDF buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=15*mm, 
            leftMargin=15*mm,
            topMargin=15*mm, 
            bottomMargin=15*mm
        )
        
        # Define modern color palette
        colors = {
            'primary': HexColor('#2E7D32'),      # Material Green
            'secondary': HexColor('#1976D2'),     # Material Blue
            'accent': HexColor('#FF6F00'),        # Material Orange
            'danger': HexColor('#D32F2F'),        # Material Red
            'success': HexColor('#388E3C'),       # Success Green
            'light_gray': HexColor('#F5F5F5'),    
            'medium_gray': HexColor('#E0E0E0'),   
            'dark_gray': HexColor('#616161'),     
            'text_primary': HexColor('#212121'),  
            'text_secondary': HexColor('#757575') 
        }
        
        # Enhanced styles
        styles = getSampleStyleSheet()
        
        # Custom title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=20,
            spaceBefore=10,
            textColor=colors['primary'],
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Subtitle style
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=30,
            textColor=colors['text_secondary'],
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        # Section heading style
        section_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=15,
            spaceBefore=20,
            textColor=colors['secondary'],
            fontName='Helvetica-Bold',
            leftIndent=0,
            borderPadding=5
        )
        
        # KPI style
        kpi_style = ParagraphStyle(
            'KPIStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors['text_primary'],
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        story = []
        
        # Header Section with Better Design
        header_spacer = Spacer(1, 10*mm)
        story.append(header_spacer)
        
        # Title
        title = Paragraph("ESG Portfolio Report", title_style)
        story.append(title)
        
        subtitle = Paragraph(
            f"<b>India Edition</b> | Generated on {datetime.now().strftime('%B %d, %Y')}<br/>Professional Investment Analysis for Indian Markets",
            subtitle_style
        )
        story.append(subtitle)
        
        # Add decorative spacing
        story.append(Spacer(1, 10*mm))
        
        # Executive Summary with KPI Cards
        exec_title = Paragraph("Executive Summary", section_style)
        story.append(exec_title)
        
        # Calculate key metrics
        portfolio_esg = summary_data.get('portfolio_weighted_esg', 0)
        portfolio_roic = summary_data.get('portfolio_weighted_roic', 0) * 100
        total_holdings = summary_data.get('total_holdings', 0)
        total_market_cap = sum(h.get('market_cap', 0) for h in portfolio_data if h.get('ticker') != 'PORTFOLIO_TOTAL') / 1e12
        
        # Determine colors and ratings
        if portfolio_esg >= 70:
            esg_color, esg_rating = colors['success'], "Excellent"
        elif portfolio_esg >= 50:
            esg_color, esg_rating = colors['accent'], "Good"
        elif portfolio_esg >= 30:
            esg_color, esg_rating = colors['accent'], "Fair"
        else:
            esg_color, esg_rating = colors['danger'], "Poor"
        
        roic_color = colors['success'] if portfolio_roic >= 15 else colors['accent'] if portfolio_roic >= 10 else colors['danger']
        controversy_color = colors['danger'] if controversy_count > 0 else colors['success']
        
        # Enhanced KPI Cards Table
        kpi_data = [
            # Headers
            ['Portfolio ESG Score', 'Weighted ROIC', 'Total Holdings', 'Risk Flags'],
            # Values with better formatting
            [f"{portfolio_esg:.1f}/100", f"{portfolio_roic:.1f}%", f"{total_holdings}", f"{controversy_count}"],
            # Descriptions
            [f"{esg_rating}", "Return on Investment Capital", "Companies Analyzed", "Controversies Detected"]
        ]
        
        kpi_table = Table(kpi_data, colWidths=[45*mm, 45*mm, 45*mm, 45*mm])
        kpi_table.setStyle(TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), colors['medium_gray']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors['text_primary']),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Value row styling with colors
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 16),
            ('TEXTCOLOR', (0, 1), (0, 1), esg_color),      # ESG score color
            ('TEXTCOLOR', (1, 1), (1, 1), roic_color),     # ROIC color  
            ('TEXTCOLOR', (2, 1), (2, 1), colors['secondary']), # Holdings color
            ('TEXTCOLOR', (3, 1), (3, 1), controversy_color),   # Controversy color
            ('ROWBACKGROUNDS', (0, 1), (-1, 1), [white]),
            
            # Description row styling
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica'),
            ('FONTSIZE', (0, 2), (-1, 2), 9),
            ('TEXTCOLOR', (0, 2), (-1, 2), colors['text_secondary']),
            ('ROWBACKGROUNDS', (0, 2), (-1, 2), [colors['light_gray']]),
            
            # General table styling
            ('GRID', (0, 0), (-1, -1), 0.5, colors['medium_gray']),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(kpi_table)
        story.append(Spacer(1, 15*mm))
        
        # Portfolio Composition Section
        portfolio_title = Paragraph("Portfolio Composition & Analysis", section_style)
        story.append(portfolio_title)
        
        # Enhanced holdings table
        if portfolio_data:
            # Prepare table data
            holdings_data = [
                ['Company', 'Weight', 'ESG Score', 'ROIC', 'Environment', 'Social', 'Governance', 'Market Cap (₹B)']
            ]
            
            for holding in portfolio_data:
                if holding.get('ticker') != 'PORTFOLIO_TOTAL':
                    ticker = holding.get('ticker', '').replace('.NS', '').upper()
                    weight = f"{holding.get('weight', 0)*100:.1f}%"
                    esg_score = f"{holding.get('esg_score', 0):.1f}"
                    roic = f"{holding.get('roic', 0)*100:.1f}%"
                    env = f"{holding.get('environmental', 0):.1f}"
                    social = f"{holding.get('social', 0):.1f}"
                    governance = f"{holding.get('governance', 0):.1f}"
                    market_cap = f"{holding.get('market_cap', 0)/1e9:.0f}"
                    
                    holdings_data.append([ticker, weight, esg_score, roic, env, social, governance, market_cap])
            
            # Create holdings table with enhanced styling
            holdings_table = Table(holdings_data, colWidths=[25*mm, 18*mm, 18*mm, 18*mm, 18*mm, 18*mm, 20*mm, 20*mm])
            holdings_table.setStyle(TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors['secondary']),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # Company name column (left-aligned)
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (0, 1), (0, -1), colors['primary']),
                
                # Data rows
                ('FONTNAME', (1, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, colors['light_gray']]),
                
                # Grid and padding
                ('GRID', (0, 0), (-1, -1), 0.5, colors['medium_gray']),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ]))
            
            story.append(holdings_table)
        
        story.append(Spacer(1, 10*mm))
        
        # ESG Breakdown Section
        esg_title = Paragraph("ESG Component Analysis", section_style)
        story.append(esg_title)
        
        if portfolio_data:
            # Calculate weighted ESG components
            total_env = sum(h.get('environmental', 0) * h.get('weight', 0) for h in portfolio_data if h.get('ticker') != 'PORTFOLIO_TOTAL')
            total_social = sum(h.get('social', 0) * h.get('weight', 0) for h in portfolio_data if h.get('ticker') != 'PORTFOLIO_TOTAL')
            total_gov = sum(h.get('governance', 0) * h.get('weight', 0) for h in portfolio_data if h.get('ticker') != 'PORTFOLIO_TOTAL')
            
            # ESG breakdown table
            esg_breakdown_data = [
                ['ESG Component', 'Weighted Score', 'Rating', 'Impact Areas'],
                ['Environmental', f"{total_env:.1f}", 
                 "Good" if total_env >= 15 else "Fair" if total_env >= 8 else "Poor",
                 "Climate change, resource efficiency, pollution control"],
                ['Social', f"{total_social:.1f}",
                 "Good" if total_social >= 12 else "Fair" if total_social >= 6 else "Poor", 
                 "Employee relations, community impact, diversity"],
                ['Governance', f"{total_gov:.1f}",
                 "Good" if total_gov >= 12 else "Fair" if total_gov >= 6 else "Poor",
                 "Board composition, transparency, executive compensation"]
            ]
            
            esg_breakdown_table = Table(esg_breakdown_data, colWidths=[40*mm, 30*mm, 25*mm, 85*mm])
            esg_breakdown_table.setStyle(TableStyle([
                # Header
                ('BACKGROUND', (0, 0), (-1, 0), colors['accent']),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                
                # Data
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (0, 0), (2, -1), 'CENTER'),
                ('ALIGN', (3, 0), (3, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, colors['light_gray']]),
                
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors['medium_gray']),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ]))
            
            story.append(esg_breakdown_table)
        
        story.append(Spacer(1, 10*mm))
        
        # Risk Assessment Section
        risk_title = Paragraph("Risk Assessment & Recommendations", section_style)
        story.append(risk_title)
        
        # Risk summary with better formatting
        if controversy_count > 0:
            risk_status = "High Risk"
            risk_bg_color = colors['danger']
            risk_text_color = white
            risk_description = f"""
            <b>Status:</b> {controversy_count} controversy(ies) detected in portfolio holdings.<br/>
            <b>Impact:</b> Potential reputational, regulatory, and financial risks affecting long-term performance.<br/>
            <b>Recommendation:</b> Immediate review of ESG policies and strategic rebalancing of affected positions.<br/>
            <b>Action Items:</b> Conduct comprehensive due diligence, engage with management, assess materiality.<br/>
            <b>Timeline:</b> Implement risk mitigation strategies within 30-60 days of detection.
            """
        else:
            risk_status = "Low Risk"
            risk_bg_color = colors['success']
            risk_text_color = white
            risk_description = """
            <b>Status:</b> No significant controversies detected in current holdings.<br/>
            <b>Assessment:</b> Portfolio demonstrates strong ESG compliance and risk management.<br/>
            <b>Recommendation:</b> Continue monitoring emerging ESG risks and maintain current standards.<br/>
            <b>Action Items:</b> Implement quarterly ESG review process and stakeholder engagement.<br/>
            <b>Future Focus:</b> Consider climate transition risks and social impact measurement.
            """
        
        risk_data = [
            [f"Risk Level: {risk_status}"],
            [risk_description]
        ]
        
        risk_table = Table(risk_data, colWidths=[180*mm])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), risk_bg_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), risk_text_color),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, 1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors['medium_gray']),
        ]))
        
        story.append(risk_table)
        story.append(Spacer(1, 15*mm))
        
        # Footer Section
        footer_text = f"""
        <b>ESG Engine - भारत Edition</b> | Professional Investment Analysis Platform<br/>
        <i>Total Portfolio Value: ₹{total_market_cap:.2f} Trillion • Analysis Date: {datetime.now().strftime('%Y-%m-%d')}</i><br/>
        <i>Data sources: Yahoo Finance & Financial data providers</i><br/>
        <i>Disclaimer: This report is for informational purposes only. Please conduct additional due diligence.</i>
        """
        
        footer_para = Paragraph(footer_text, ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors['text_secondary'],
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))
        
        story.append(footer_para)
        
        # Build the PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
        
    except ImportError as e:
        st.error(f"Required library not available: {str(e)}. Please ensure reportlab and matplotlib are installed.")
        return None
    except Exception as e:
        st.error(f"Error generating PDF: {str(e)}")
        return None

# Main app
def main():
    load_css()
    
    # Sidebar
    st.sidebar.title("🌱 ESG Engine")
    
    # Theme toggle
    dark_mode = st.sidebar.toggle("Dark Mode", value=False)
    theme = "dark" if dark_mode else "light"
    
    # Check backend health
    if not check_backend_health():
        st.error("⚠️ Backend service is not available. Please ensure the FastAPI server is running.")
        st.stop()
    
    # Initialize session state
    if 'portfolio_result' not in st.session_state:
        st.session_state.portfolio_result = None
    if 'upload_time' not in st.session_state:
        st.session_state.upload_time = None
    
    # Check cache expiration
    if (st.session_state.upload_time and 
        datetime.now() - st.session_state.upload_time > CACHE_DURATION):
        st.session_state.portfolio_result = None
        st.session_state.upload_time = None
    
    # Main title
    st.title("🌱 ESG Engine - भारत Edition (India)")
    st.markdown("Upload your portfolio and get instant ESG analysis for Indian markets")
    
    # === UPLOAD SECTION ===
    st.header("📤 Upload Portfolio")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type="csv",
        help="CSV must contain 'ticker' and 'weight' columns. Use .NS suffix for Indian stocks (e.g., RELIANCE.NS)"
    )
    
    if uploaded_file is not None:
        try:
            # Read CSV
            df = pd.read_csv(uploaded_file)
            
            # Validate columns
            if not {'ticker', 'weight'}.issubset(df.columns):
                st.error("❌ CSV must contain 'ticker' and 'weight' columns")
                st.stop()
            
            # Display uploaded data
            st.subheader("📋 Uploaded Portfolio")
            st.dataframe(df, use_container_width=True)
            
            # Validate weights
            weight_sum = df['weight'].sum()
            weight_diff = abs(weight_sum - 1.0)
            
            if weight_diff > 0.01:
                st.error(f"❌ Weights must sum to 1.0 ± 0.01. Current sum: {weight_sum:.3f}")
                st.stop()
            else:
                st.success(f"✅ Weights validated. Sum: {weight_sum:.3f}")
            
            # Upload and rank portfolio
            if st.button("🚀 Analyze Portfolio", type="primary"):
                with st.spinner("Analyzing portfolio..."):
                    result = upload_and_rank_portfolio(df)
                    
                    if result:
                        st.session_state.portfolio_result = result
                        st.session_state.upload_time = datetime.now()
                        st.success("✅ Portfolio analyzed successfully!")
                        st.rerun()  # Refresh to show results immediately
                    else:
                        st.error("❌ Failed to analyze portfolio")
                        
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")
    
    # === RESULTS SECTION ===
    if st.session_state.portfolio_result:
        st.header("📊 ESG Analysis Results")
        
        result = st.session_state.portfolio_result
        portfolio_data = result.get('data', [])
        summary_data = result.get('summary', {})
        # Get controversy data for all tickers
        with st.spinner("Loading controversy data..."):
            df = pd.DataFrame(portfolio_data)
            holdings_df = df[df['ticker'] != 'PORTFOLIO_TOTAL']
            total_controversies = 0
            
            for ticker in holdings_df['ticker']:
                controversy_data = get_controversy_data(ticker)
                total_controversies += len(controversy_data.get('controversies', []))
        
        # Cache expiration info
        if st.session_state.upload_time:
            cache_expires = st.session_state.upload_time + CACHE_DURATION
            st.info(f"📅 Data cached until {cache_expires.strftime('%H:%M:%S')}")
        
        # KPI Cards
        st.subheader("📈 Key Performance Indicators")
        create_kpi_cards(summary_data, total_controversies, theme)
        
        # Charts section
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 ESG Profile Comparison")
            create_radar_chart(portfolio_data, theme)
        
        with col2:
            st.subheader("📊 ESG Rankings")
            create_esg_ranking_chart(portfolio_data, theme)
        
        # Data table
        st.subheader("📋 Portfolio Holdings")
        create_portfolio_datatable(portfolio_data)
        
        # PDF Download
        st.subheader("📄 Export Professional Report")
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if st.button("📥 Download PDF Report", type="secondary"):
                with st.spinner("Generating professional PDF report..."):
                    pdf_bytes = generate_pdf_report(portfolio_data, summary_data, total_controversies)
                    
                    if pdf_bytes:
                        st.download_button(
                            label="💾 Save PDF Report",
                            data=pdf_bytes,
                            file_name=f"esg_portfolio_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf"
                        )
        
        with col2:
            st.info("💡 Professional PDF report with KPI cards, portfolio analysis, and risk assessment.")
    
    else:
        # Show example portfolio for Indian stocks
        st.header("💡 Example Portfolio")
        st.markdown("Try uploading this sample Indian portfolio:")
        
        sample_data = {
            'ticker': ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ITC.NS', 'HINDUNILVR.NS', 'ADANIPORTS.NS'],
            'weight': [0.25, 0.20, 0.15, 0.15, 0.10, 0.10, 0.05]
        }
        sample_df = pd.DataFrame(sample_data)
        st.dataframe(sample_df, use_container_width=True)
        
        # Download sample CSV
        csv_buffer = io.StringIO()
        sample_df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="📥 Download Sample Portfolio",
            data=csv_buffer.getvalue(),
            file_name="sample_indian_portfolio.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()
