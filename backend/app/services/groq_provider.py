"""
Groq LLM provider for AI-powered financial analysis
Generates comprehensive analyst reports using Groq's fast inference API
"""

import httpx
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class GroqAnalystProvider:
    """Groq API for AI-generated analyst reports"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1"
        self.model = "mixtral-8x7b-32768"
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def generate_analyst_report(self, ticker: str, context: Dict[str, Any]) -> str:
        """
        Generate comprehensive analyst report using Groq LLM
        
        Args:
            ticker: Stock ticker
            context: Dictionary with market data, technicals, fundamentals
        
        Returns:
            Generated analyst report text
        """
        try:
            # Build prompt with context
            prompt = self._build_report_prompt(ticker, context)
            
            # Call Groq API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert financial analyst writing institutional-grade research reports. Provide comprehensive, data-driven analysis with clear recommendations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000,
                "top_p": 0.9
            }
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
        
        except Exception as e:
            logger.error(f"Groq error generating report for {ticker}: {str(e)}")
            raise
    
    def _build_report_prompt(self, ticker: str, context: Dict) -> str:
        """Build detailed prompt for analyst report generation"""
        
        current_price = context.get("price", "N/A")
        pe_ratio = context.get("pe_ratio", "N/A")
        market_cap = context.get("market_cap", "N/A")
        dividend_yield = context.get("dividend_yield", "N/A")
        
        return f"""
Generate a comprehensive analyst report for {ticker} using the following market data:

Current Price: ${current_price}
PE Ratio: {pe_ratio}
Market Cap: ${market_cap}B
Dividend Yield: {dividend_yield}%

Please provide:

1. EXECUTIVE SUMMARY (2-3 sentences)
   - One-line investment thesis
   - Key highlight

2. TECHNICAL ANALYSIS
   - Current trend (Uptrend/Downtrend/Sideways)
   - Key resistance and support levels
   - Signal strength (0-100)
   - Momentum assessment

3. FUNDAMENTAL ANALYSIS
   - EPS growth outlook
   - Profit margin trends
   - ROE and valuation metrics
   - Quality assessment (0-100)

4. MACRO CONTEXT
   - Sector performance relative to market
   - Industry tailwinds and headwinds
   - Overall macro outlook

5. INVESTMENT CASES
   - Bull case thesis with 2-3 catalysts
   - Bear case thesis with risks
   - Probability estimates for each

6. RISKS AND CATALYSTS
   - Top 3 risks (rated Low/Medium/High)
   - Near-term catalysts (trading in 3-6 months)

7. FINAL RATING
   - Recommendation: BUY/HOLD/SELL
   - Price target (12-month)
   - Upside/downside potential
   - Conviction level: High/Medium/Low
   - Confidence score (0-100)

Format as structured JSON-compatible response with clear sections.
"""
    
    async def generate_sentiment_analysis(self, ticker: str, news_articles: list) -> Dict[str, Any]:
        """
        Generate sentiment analysis from news articles
        
        Args:
            ticker: Stock ticker
            news_articles: List of news article dicts with title, description
        
        Returns:
            Sentiment analysis with score and key themes
        """
        try:
            # Prepare news summary
            articles_text = "\n".join([
                f"- {article['title']}: {article['description'][:100]}..."
                for article in news_articles[:5]
            ])
            
            prompt = f"""
Analyze the sentiment of recent news about {ticker}:

{articles_text}

Provide:
1. Overall sentiment (Positive/Negative/Neutral)
2. Sentiment score (-100 to +100)
3. Key themes and topics
4. Investment implications

Format as structured response.
"""
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.5,
                "max_tokens": 500
            }
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            analysis_text = result["choices"][0]["message"]["content"]
            
            return {
                "ticker": ticker,
                "analysis": analysis_text,
                "generated_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Groq error analyzing sentiment for {ticker}: {str(e)}")
            raise
    
    async def generate_investment_thesis(self, ticker: str, sectors: Dict) -> str:
        """
        Generate investment thesis based on sector analysis
        
        Args:
            ticker: Stock ticker
            sectors: Dict with sector performance data
        
        Returns:
            Investment thesis text
        """
        try:
            prompt = f"""
Create a concise investment thesis for {ticker} considering:

Sector Data:
{json.dumps(sectors, indent=2)}

Provide:
1. Core thesis statement (1-2 sentences)
2. Key catalysts (2-3 items)
3. Timeline and conviction
4. Risk factors
5. Target price rationale
"""
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.6,
                "max_tokens": 1000
            }
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
        
        except Exception as e:
            logger.error(f"Groq error generating thesis for {ticker}: {str(e)}")
            raise
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


def get_groq_provider(api_key: Optional[str]) -> Optional[GroqAnalystProvider]:
    """
    Factory function to get Groq provider if API key is available
    
    Args:
        api_key: Groq API key from settings
    
    Returns:
        GroqAnalystProvider instance or None if key not configured
    """
    if api_key:
        return GroqAnalystProvider(api_key)
    else:
        logger.warning("Groq API key not configured - AI analyst reports will use mock data")
        return None
