"""
Uptime Robot Monitoring Setup for ESG Engine
This script helps you set up monitoring for your Streamlit and Render deployments
"""

import requests
import time
import json
from typing import Dict, List
import os
from dotenv import load_dotenv

load_dotenv()

class UptimeRobotSetup:
    """
    Helper class to set up and manage Uptime Robot monitors for your ESG Engine deployments.
    
    Required: Sign up at https://uptimerobot.com and get your API key
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('UPTIMEROBOT_API_KEY')
        self.base_url = "https://api.uptimerobot.com/v2"
        
        if not self.api_key:
            print("⚠️ No Uptime Robot API key found. Get one from https://uptimerobot.com")
    
    def create_monitor(self, url: str, friendly_name: str, monitor_type: int = 1) -> Dict:
        """
        Create a new monitor in Uptime Robot.
        
        Args:
            url: URL to monitor (e.g., https://your-app.streamlit.app)
            friendly_name: Display name for the monitor
            monitor_type: 1 for HTTP(S), 2 for keyword, 3 for ping, 4 for port
        """
        if not self.api_key:
            return {"error": "No API key configured"}
        
        data = {
            "api_key": self.api_key,
            "format": "json",
            "type": monitor_type,
            "url": url,
            "friendly_name": friendly_name,
            "interval": 300,  # Check every 5 minutes
            "timeout": 30,    # 30 second timeout
        }
        
        try:
            response = requests.post(f"{self.base_url}/newMonitor", data=data)
            result = response.json()
            
            if result.get("stat") == "ok":
                print(f"✅ Monitor created: {friendly_name}")
                return result
            else:
                print(f"❌ Failed to create monitor: {result.get('error', {}).get('message', 'Unknown error')}")
                return result
                
        except Exception as e:
            print(f"❌ Error creating monitor: {e}")
            return {"error": str(e)}
    
    def get_monitors(self) -> List[Dict]:
        """Get all existing monitors."""
        if not self.api_key:
            return []
        
        data = {
            "api_key": self.api_key,
            "format": "json"
        }
        
        try:
            response = requests.post(f"{self.base_url}/getMonitors", data=data)
            result = response.json()
            
            if result.get("stat") == "ok":
                return result.get("monitors", [])
            else:
                print(f"❌ Failed to get monitors: {result.get('error', {}).get('message', 'Unknown error')}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting monitors: {e}")
            return []
    
    def create_alert_contact(self, email: str) -> Dict:
        """Create email alert contact."""
        if not self.api_key:
            return {"error": "No API key configured"}
        
        data = {
            "api_key": self.api_key,
            "format": "json",
            "type": 2,  # Email
            "value": email,
            "friendly_name": f"ESG Engine Alerts - {email}"
        }
        
        try:
            response = requests.post(f"{self.base_url}/newAlertContact", data=data)
            result = response.json()
            
            if result.get("stat") == "ok":
                print(f"✅ Alert contact created: {email}")
                return result
            else:
                print(f"❌ Failed to create alert contact: {result.get('error', {}).get('message', 'Unknown error')}")
                return result
                
        except Exception as e:
            print(f"❌ Error creating alert contact: {e}")
            return {"error": str(e)}


def setup_esg_monitoring():
    """
    Interactive setup for ESG Engine monitoring.
    """
    print("🔍 ESG Engine Uptime Monitoring Setup")
    print("=" * 50)
    
    # Get API key
    api_key = input("Enter your Uptime Robot API key (or press Enter to use environment variable): ").strip()
    if not api_key:
        api_key = os.getenv('UPTIMEROBOT_API_KEY')
    
    if not api_key:
        print("\n❌ No API key provided. Please:")
        print("1. Sign up at https://uptimerobot.com")
        print("2. Go to Settings > API Keys")
        print("3. Create a new API key")
        print("4. Set UPTIMEROBOT_API_KEY environment variable or provide it here")
        return
    
    uptime = UptimeRobotSetup(api_key)
    
    # Get deployment URLs
    print("\n📝 Enter your deployment URLs:")
    streamlit_url = input("Streamlit Cloud URL (e.g., https://your-app.streamlit.app): ").strip()
    render_url = input("Render URL (e.g., https://your-app.onrender.com): ").strip()
    
    # Optional: Backend API URL
    api_url = input("Backend API URL (optional, e.g., https://your-api.onrender.com/health): ").strip()
    
    # Email for alerts
    email = input("Email for downtime alerts: ").strip()
    
    print("\n🚀 Creating monitors...")
    
    # Create email alert contact
    if email:
        uptime.create_alert_contact(email)
    
    # Create monitors
    monitors_created = []
    
    if streamlit_url:
        result = uptime.create_monitor(
            url=streamlit_url,
            friendly_name="ESG Engine - Streamlit Frontend"
        )
        if result.get("stat") == "ok":
            monitors_created.append(("Streamlit Frontend", streamlit_url))
    
    if render_url:
        result = uptime.create_monitor(
            url=render_url,
            friendly_name="ESG Engine - Render Backend"
        )
        if result.get("stat") == "ok":
            monitors_created.append(("Render Backend", render_url))
    
    if api_url:
        result = uptime.create_monitor(
            url=api_url,
            friendly_name="ESG Engine - API Health Check"
        )
        if result.get("stat") == "ok":
            monitors_created.append(("API Health", api_url))
    
    # Summary
    print("\n✅ Monitoring Setup Complete!")
    print("=" * 50)
    print(f"Created {len(monitors_created)} monitors:")
    for name, url in monitors_created:
        print(f"  • {name}: {url}")
    
    print(f"\n👀 View your monitors at: https://uptimerobot.com/dashboard")
    print(f"📧 Alerts will be sent to: {email}")
    
    print("\n🔧 Additional Recommendations:")
    print("1. Set check interval to 1-5 minutes for production apps")
    print("2. Configure multiple alert channels (email, SMS, Slack)")
    print("3. Set up keyword monitoring for specific error messages")
    print("4. Monitor both frontend and backend endpoints")
    print("5. Use status pages to communicate with users during outages")
    
    return monitors_created


def create_health_check_endpoint():
    """
    Sample health check endpoint code for your backend.
    Add this to your FastAPI app.py
    """
    health_check_code = '''
# Add this to your FastAPI app.py file

@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring services.
    Uptime Robot will ping this endpoint to verify the service is running.
    """
    try:
        # Test database connection
        db = ESGDB()
        
        # Test enhanced analytics (if available)
        enhanced_status = "available" if EnhancedESGAnalytics else "unavailable"
        
        # Test API keys (without exposing them)
        api_keys_status = {
            "news_api": bool(os.getenv('NEWS_API_KEY')),
            "alpha_vantage": bool(os.getenv('ALPHA_VANTAGE_API_KEY')),
        }
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "services": {
                "database": "connected",
                "enhanced_analytics": enhanced_status,
                "api_keys": api_keys_status
            },
            "uptime": "Service is running normally"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail=f"Service unhealthy: {str(e)}"
        )

@app.get("/api/status")
async def api_status():
    """
    Detailed API status for monitoring.
    """
    return {
        "api_version": "1.0.0",
        "enhanced_features": EnhancedESGAnalytics is not None,
        "endpoints": {
            "portfolio_analysis": "/api/portfolio/analyze",
            "stock_search": "/api/enhanced/search",
            "stock_prediction": "/api/enhanced/predict",
            "manipulation_detection": "/api/enhanced/manipulation"
        },
        "status": "operational"
    }
'''
    
    print("📋 Health Check Endpoint Code:")
    print("=" * 50)
    print(health_check_code)
    print("=" * 50)
    print("Copy the above code to your backend/app.py file")


if __name__ == "__main__":
    print("🌱 ESG Engine Uptime Monitoring Setup")
    print("Choose an option:")
    print("1. Interactive monitor setup")
    print("2. Show health check endpoint code")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        setup_esg_monitoring()
    elif choice == "2":
        create_health_check_endpoint()
    else:
        print("👋 Goodbye!")
