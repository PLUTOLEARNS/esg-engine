"""
AI analysis endpoint for ESG Engine backend.
"""

def get_groq_analysis(prompt: str, max_tokens: int = 500) -> str:
    """Get AI-powered analysis using Groq API."""
    import os
    import requests
    
    groq_api_key = os.getenv("GROQ_API_KEY")
    
    if not groq_api_key:
        return "AI analysis not available (API key not configured)"
    
    try:
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert ESG (Environmental, Social, Governance) investment analyst specializing in Indian markets. Provide professional, actionable insights in a concise format suitable for investment reports."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "model": "llama3-8b-8192",
            "max_tokens": max_tokens,
            "temperature": 0.3
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        else:
            return f"AI analysis unavailable (API error: {response.status_code})"
            
    except Exception as e:
        return f"AI analysis unavailable ({str(e)})"
