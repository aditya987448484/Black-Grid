"""
Reasoning Provider Service
Provides AI-powered reasoning and analysis via Groq LLM
Used for generating insights, analysis, explanations, and recommendations

Features:
- Groq LLM integration for fast, cost-effective reasoning
- Multiple analysis types: sentiment, technical, fundamental, valuation, risk
- Comprehensive analyst report generation with structured output
- Fallback to mock provider if Groq API key missing or API fails
- Modular prompt engineering for easy customization
"""

import httpx
import json
import logging
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AnalysisType(str, Enum):
    """Types of financial analysis"""
    SENTIMENT = "sentiment"  # Analyze sentiment of market data
    TECHNICAL = "technical"  # Technical analysis insights
    FUNDAMENTAL = "fundamental"  # Fundamental analysis
    VALUATION = "valuation"  # Valuation assessment
    RISK = "risk"  # Risk analysis
    SUMMARY = "summary"  # General summary


class ReasoningProvider:
    """Abstract base for reasoning/LLM providers"""
    
    async def reason(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        max_tokens: int = 1000
    ) -> str:
        """Generate reasoning response"""
        raise NotImplementedError
    
    async def analyze(
        self,
        analysis_type: AnalysisType,
        data: Dict[str, Any],
        ticker: str
    ) -> str:
        """Perform financial analysis"""
        raise NotImplementedError


class DeepSeekReasoningProvider(ReasoningProvider):
    """
    DeepSeek API integration for LLM-powered reasoning.
    OpenAI-compatible endpoint — same request/response shape as OpenAI.

    Endpoint: https://api.deepseek.com/v1/chat/completions
    Models:   deepseek-chat (fast), deepseek-reasoner (powerful)
    """

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.deepseek_api_key
        self.base_url = "https://api.deepseek.com/v1"
        self.model = "deepseek-chat"
        self.client = httpx.AsyncClient(timeout=60.0)

        if not self.api_key:
            logger.warning("DeepSeek API key not configured. Provider will not work.")

    async def reason(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        if not self.api_key:
            raise ValueError("DeepSeek API key not configured")

        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert financial analyst and market researcher. Provide insightful, data-driven analysis. Be concise and specific."
                }
            ]

            if context:
                context_str = json.dumps(context, indent=2)
                messages.append({
                    "role": "user",
                    "content": f"Context data:\n{context_str}\n\n{prompt}"
                })
            else:
                messages.append({"role": "user", "content": prompt})

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": 0.9,
            }

            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            result = response.json()

            if result.get("choices") and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                raise ValueError("No response from DeepSeek API")

        except Exception as e:
            logger.error(f"DeepSeek reasoning error: {str(e)}")
            raise

    async def analyze(
        self,
        analysis_type: AnalysisType,
        data: Dict[str, Any],
        ticker: str
    ) -> str:
        prompts = {
            AnalysisType.SENTIMENT: f"Analyze market sentiment for {ticker} based on: {json.dumps(data)}",
            AnalysisType.TECHNICAL: f"Provide technical analysis for {ticker}: {json.dumps(data)}",
            AnalysisType.FUNDAMENTAL: f"Analyze fundamentals for {ticker}: {json.dumps(data)}",
            AnalysisType.VALUATION: f"Assess valuation for {ticker}: {json.dumps(data)}",
            AnalysisType.RISK: f"Identify risks for {ticker}: {json.dumps(data)}",
            AnalysisType.SUMMARY: f"Create investment summary for {ticker}: {json.dumps(data)}",
        }

        prompt = prompts.get(analysis_type, "")
        if not prompt:
            raise ValueError(f"Unknown analysis type: {analysis_type}")

        return await self.reason(prompt, context=data)

    async def close(self):
        if self.client:
            await self.client.aclose()


class GroqReasoningProvider(ReasoningProvider):
    """
    Groq API integration for LLM-powered reasoning
    https://console.groq.com/

    Free tier: 30 requests/minute
    Model: mixtral-8x7b-32768 (fast open-source LLM)
    Great for: analysis, summaries, explanations, reasoning
    """

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.groq_api_key
        self.base_url = "https://api.groq.com/openai/v1"
        self.model = "mixtral-8x7b-32768"
        self.client = httpx.AsyncClient(timeout=60.0)

        if not self.api_key:
            logger.warning("Groq API key not configured. Provider will not work.")
    
    async def reason(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """
        Generate reasoning response from LLM
        
        Args:
            prompt: Question or prompt for the model
            context: Additional context data
            max_tokens: Maximum response length
            temperature: Creativity level (0.0-1.0)
        
        Returns:
            Generated response text
        """
        if not self.api_key:
            raise ValueError("Groq API key not configured")
        
        try:
            # Build messages with context
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert financial analyst and market researcher. Provide insightful, data-driven analysis. Be concise and specific."
                }
            ]
            
            # Add context if provided
            if context:
                context_str = json.dumps(context, indent=2)
                messages.append({
                    "role": "user",
                    "content": f"Context data:\n{context_str}\n\n{prompt}"
                })
            else:
                messages.append({"role": "user", "content": prompt})
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": 0.9,
            }
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Extract message
            if result.get("choices") and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                raise ValueError("No response from Groq API")
        
        except Exception as e:
            logger.error(f"Groq reasoning error: {str(e)}")
            raise
    
    async def analyze(
        self,
        analysis_type: AnalysisType,
        data: Dict[str, Any],
        ticker: str
    ) -> str:
        """
        Perform specialized financial analysis
        
        Args:
            analysis_type: Type of analysis to perform
            data: Financial data for analysis
            ticker: Stock ticker
        
        Returns:
            Analysis results
        """
        prompts = {
            AnalysisType.SENTIMENT: self._build_sentiment_prompt(ticker, data),
            AnalysisType.TECHNICAL: self._build_technical_prompt(ticker, data),
            AnalysisType.FUNDAMENTAL: self._build_fundamental_prompt(ticker, data),
            AnalysisType.VALUATION: self._build_valuation_prompt(ticker, data),
            AnalysisType.RISK: self._build_risk_prompt(ticker, data),
            AnalysisType.SUMMARY: self._build_summary_prompt(ticker, data),
        }
        
        prompt = prompts.get(analysis_type, "")
        if not prompt:
            raise ValueError(f"Unknown analysis type: {analysis_type}")
        
        return await self.reason(prompt, context=data)
    
    def _build_sentiment_prompt(self, ticker: str, data: Dict) -> str:
        """Build sentiment analysis prompt"""
        return f"""
Analyze the market sentiment for {ticker} based on this data:
{json.dumps(data, indent=2)}

Provide:
1. Overall sentiment (Positive/Negative/Neutral)
2. Key sentiment drivers
3. Emotional vs rational factors
4. Investor positioning implications

Be concise and actionable."""
    
    def _build_technical_prompt(self, ticker: str, data: Dict) -> str:
        """Build technical analysis prompt"""
        return f"""
Provide technical analysis for {ticker}:
{json.dumps(data, indent=2)}

Include:
1. Current trend (uptrend/downtrend/sideways)
2. Key support and resistance levels
3. Technical indicators interpretation
4. Short-term price action outlook
5. Trade setup quality (if breakout/breakdown visible)

Be specific with numbers and levels."""
    
    def _build_fundamental_prompt(self, ticker: str, data: Dict) -> str:
        """Build fundamental analysis prompt"""
        return f"""
Analyze fundamentals for {ticker}:
{json.dumps(data, indent=2)}

Evaluate:
1. Revenue and earnings quality
2. Growth trajectory
3. Profit margins and efficiency
4. Cash flow generation
5. Balance sheet strength
6. Competitive advantages

Rate: Strong/Adequate/Weak"""
    
    def _build_valuation_prompt(self, ticker: str, data: Dict) -> str:
        """Build valuation analysis prompt"""
        return f"""
Assess valuation for {ticker}:
{json.dumps(data, indent=2)}

Analyze:
1. Valuation multiples (P/E, P/B, PEG)
2. Valuation vs peers
3. Historical valuation context
4. Fair value estimate
5. Upside/downside potential

Rating: Undervalued/Fair/Overvalued"""
    
    def _build_risk_prompt(self, ticker: str, data: Dict) -> str:
        """Build risk analysis prompt"""
        return f"""
Identify risks for {ticker}:
{json.dumps(data, indent=2)}

Assessment:
1. Business model risks
2. Competitive risks
3. Market/macro risks
4. Financial risks
5. Execution risks
6. Risk/reward ratio

Severity: High/Medium/Low"""
    
    def _build_summary_prompt(self, ticker: str, data: Dict) -> str:
        """Build investment summary prompt"""
        return f"""
Create investment summary for {ticker}:
{json.dumps(data, indent=2)}

Provide:
1. One-sentence investment thesis
2. Key highlights (3-4 bullet points)
3. Primary catalyst
4. Investment recommendation
5. Time horizon
6. Risk/reward profile

Format as executive summary."""
    
    async def generate_analyst_report(
        self,
        ticker: str,
        asset_info: Dict[str, Any],
        technical_data: Dict[str, Any],
        forecast_data: Dict[str, Any],
        fundamental_data: Dict[str, Any],
        macro_context: Dict[str, Any],
        sec_summary: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive analyst report using Groq LLM
        
        Structured input approach:
        - Asset info: name, sector, market cap
        - Technical data: trend, indicators, price levels
        - Forecast: ML model predictions
        - Fundamental data: earnings, margins, ROE, etc.
        - Macro context: economic indicators, sector outlook
        - SEC summary: recent filings, regulatory status
        
        Returns structured report matching AnalystReportResponse schema
        """
        if not self.api_key:
            raise ValueError("Groq API key not configured")
        
        try:
            # Build comprehensive context
            context = {
                "ticker": ticker.upper(),
                "asset_info": asset_info,
                "technical_data": technical_data,
                "forecast_data": forecast_data,
                "fundamental_data": fundamental_data,
                "macro_context": macro_context,
                "sec_summary": sec_summary or {},
            }
            
            # Generate each section of the report
            report_sections = await self._generate_report_sections(
                ticker, context
            )
            
            return report_sections
        
        except Exception as e:
            logger.error(f"Error generating analyst report: {str(e)}")
            raise
    
    async def _generate_report_sections(
        self,
        ticker: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate all report sections using modular prompts
        
        Returns structured dict matching AnalystReport schema
        """
        # Extract base info
        current_price = context.get("asset_info", {}).get("price", 0)
        company_name = context.get("asset_info", {}).get("name", ticker)
        
        # Generate each section in parallel would be better, but for now sequential
        sections = {}
        
        try:
            # 1. Executive Summary & Investment Highlight
            summary_prompt = self._build_executive_summary_prompt(
                ticker, context, current_price
            )
            summary_response = await self.reason(summary_prompt, context, max_tokens=500)
            sections["summary"] = self._parse_summary_response(summary_response)
            
            # 2. Technical Analysis
            tech_prompt = self._build_technical_report_prompt(ticker, context)
            tech_response = await self.reason(tech_prompt, context, max_tokens=600)
            sections["technical_view"] = self._parse_technical_response(
                tech_response, context
            )
            
            # 3. Fundamental Analysis
            fund_prompt = self._build_fundamental_report_prompt(ticker, context)
            fund_response = await self.reason(fund_prompt, context, max_tokens=400)
            sections["fundamental_snapshot"] = self._parse_fundamental_response(
                fund_response, context
            )
            
            # 4. Macro Context
            macro_prompt = self._build_macro_context_prompt(ticker, context)
            macro_response = await self.reason(macro_prompt, context, max_tokens=400)
            sections["macro_context"] = self._parse_macro_response(macro_response, context)
            
            # 5. Bull Case
            bull_prompt = self._build_bull_case_prompt(ticker, context)
            bull_response = await self.reason(bull_prompt, context, max_tokens=500)
            sections["bull_case"] = self._parse_investment_case_response(
                bull_response, "bull"
            )
            
            # 6. Bear Case
            bear_prompt = self._build_bear_case_prompt(ticker, context)
            bear_response = await self.reason(bear_prompt, context, max_tokens=500)
            sections["bear_case"] = self._parse_investment_case_response(
                bear_response, "bear"
            )
            
            # 7. Risks
            risk_prompt = self._build_risk_analysis_prompt(ticker, context)
            risk_response = await self.reason(risk_prompt, context, max_tokens=500)
            sections["risks"] = self._parse_risks_response(risk_response)
            
            # 8. Catalysts
            catalyst_prompt = self._build_catalyst_prompt(ticker, context)
            catalyst_response = await self.reason(catalyst_prompt, context, max_tokens=400)
            sections["catalysts"] = self._parse_catalysts_response(catalyst_response)
            
            # 9. Final Rating
            rating_prompt = self._build_final_rating_prompt(ticker, context, sections)
            rating_response = await self.reason(rating_prompt, context, max_tokens=500)
            sections["final_rating"] = self._parse_final_rating_response(rating_response)
            
            # 10. Calculate confidence score
            sections["confidence_score"] = self._calculate_confidence_score(
                sections, context
            )
            
            # Assemble final report
            report = {
                "ticker": ticker.upper(),
                "company_name": company_name,
                "report_date": datetime.utcnow().isoformat(),
                "current_price": float(current_price),
                "executive_summary": sections["summary"].get(
                    "executive_summary",
                    "AI-generated analysis based on financial data"
                ),
                "investment_highlight": sections["summary"].get(
                    "investment_highlight",
                    "Detailed analysis provided below"
                ),
                "technical_view": sections["technical_view"],
                "fundamental_snapshot": sections["fundamental_snapshot"],
                "macro_context": sections["macro_context"],
                "bull_case": sections["bull_case"],
                "bear_case": sections["bear_case"],
                "risks": sections["risks"],
                "catalysts": sections["catalysts"],
                "final_rating": sections["final_rating"],
                "confidence_score": sections["confidence_score"],
            }
            
            return report
        
        except Exception as e:
            logger.error(f"Error generating report sections: {str(e)}")
            raise
    
    def _build_executive_summary_prompt(
        self,
        ticker: str,
        context: Dict[str, Any],
        current_price: float
    ) -> str:
        """Build executive summary prompt"""
        asset_info = context.get("asset_info", {})
        technical = context.get("technical_data", {})
        forecast = context.get("forecast_data", {})
        
        return f"""
Provide an executive summary and investment highlight for {ticker} ({asset_info.get('name', 'Company')}).

Current Price: ${current_price}

Key Data:
- Technical Trend: {technical.get('trend', 'N/A')}
- Forecast Signal: {forecast.get('consensus_signal', 'HOLD')}
- Consensus Confidence: {forecast.get('confidence', 0)}%

Format your response as JSON with these fields:
{{
  "executive_summary": "2-3 sentence overview of investment thesis",
  "investment_highlight": "Single key investment point or catalyst"
}}

Return ONLY valid JSON, no markdown or explanation."""
    
    def _build_technical_report_prompt(self, ticker: str, context: Dict[str, Any]) -> str:
        """Build technical analysis report prompt"""
        technical = context.get("technical_data", {})
        
        return f"""
Provide technical analysis for {ticker}.

Technical Data Available:
- Trend: {technical.get('trend', 'N/A')}
- Support Levels: {technical.get('support_levels', [])}
- Resistance Levels: {technical.get('resistance_levels', [])}
- Key Indicators: {json.dumps(technical.get('indicators', {}), indent=2)}

Format response as JSON:
{{
  "trend": "Uptrend/Downtrend/Sideways",
  "key_levels": [support_level, resistance_level, next_target],
  "signal_strength": 75.5,
  "momentum": "Strong/Neutral/Weak",
  "ma_alignment": "Bullish/Neutral/Bearish (describe alignment)",
  "summary": "Technical analysis summary"
}}

Return ONLY valid JSON."""
    
    def _build_fundamental_report_prompt(self, ticker: str, context: Dict[str, Any]) -> str:
        """Build fundamental analysis prompt using real SEC EDGAR data."""
        f = context.get("fundamental_data", {})

        # Format large USD numbers for readability
        def fmt_usd(v):
            if v is None:
                return "N/A"
            if abs(v) >= 1e12:
                return f"${v / 1e12:.2f}T"
            if abs(v) >= 1e9:
                return f"${v / 1e9:.2f}B"
            if abs(v) >= 1e6:
                return f"${v / 1e6:.2f}M"
            return f"${v:.2f}"

        def fmt_pct(v, suffix="%"):
            return f"{v:+.1f}{suffix}" if v is not None else "N/A"

        def fmt_num(v, decimals=2):
            return f"{v:.{decimals}f}" if v is not None else "N/A"

        return f"""
Provide fundamental analysis for {ticker}.

SEC EDGAR Financials (most recent annual filing, fiscal year ending {f.get('fiscal_year_end', 'N/A')}):
- Revenue:                {fmt_usd(f.get('revenue'))}
- Net Income:             {fmt_usd(f.get('net_income'))}
- Operating Cash Flow:    {fmt_usd(f.get('operating_cash_flow'))}
- EPS (Diluted):          {fmt_num(f.get('eps_diluted'))}
- Revenue Growth (YoY):   {fmt_pct(f.get('revenue_growth_yoy'))}
- Net Income Growth (YoY):{fmt_pct(f.get('net_income_growth_yoy'))}

Balance Sheet:
- Total Assets:           {fmt_usd(f.get('total_assets'))}
- Total Liabilities:      {fmt_usd(f.get('total_liabilities'))}
- Equity:                 {fmt_usd(f.get('equity'))}
- Debt-to-Assets:         {fmt_num(f.get('debt_to_assets'), 3)}
- Balance-sheet Risk:     {f.get('risk_level', 'unknown')}
- Growth Signal:          {f.get('growth_signal', 'unknown')}

Valuation Multiples:
- P/E Ratio:              {fmt_num(f.get('pe_ratio'))}
- P/S Ratio:              {fmt_num(f.get('ps_ratio'))}
- P/B Ratio:              {fmt_num(f.get('pb_ratio'))}
- Market Cap:             {fmt_usd(f.get('market_cap'))}

Data source: {f.get('data_source', 'N/A')}

Using the above real data, generate your fundamental assessment as JSON:
{{
  "eps": <eps_diluted as float or null>,
  "revenue_growth": <revenue_growth_yoy as float or null>,
  "profit_margin": <net_income / revenue * 100 as float or null>,
  "roe": <estimated ROE as float, derive from net_income / equity * 100>,
  "debt_to_equity": <total_liabilities / equity as float or null>,
  "valuation_assessment": "Undervalued/Fairly Valued/Overvalued",
  "quality_score": <0-100 based on growth signal, risk level, cash generation>
}}

Return ONLY valid JSON with numeric values."""
    
    def _build_macro_context_prompt(self, ticker: str, context: Dict[str, Any]) -> str:
        """Build macro context prompt using real FRED data."""
        m = context.get("macro_context", {})
        asset_info = context.get("asset_info", {})

        def fmt(v, suffix=""):
            return f"{v}{suffix}" if v is not None else "N/A"

        # Interpret yield curve
        spread = m.get("yield_curve_spread")
        curve_note = (
            "inverted (recession signal)" if spread is not None and spread < 0
            else "normal (positive slope)" if spread is not None
            else "N/A"
        )

        return f"""
Provide macro-economic context for {ticker}.

Current FRED Macro Indicators:
- 10-Year Treasury Yield:  {fmt(m.get('treasury_10y'), '%')}
- Fed Funds Rate:          {fmt(m.get('fed_funds_rate'), '%')}
- CPI Inflation (YoY):     {fmt(m.get('cpi_yoy'), '%')}
- Unemployment Rate:       {fmt(m.get('unemployment_rate'), '%')}
- Yield Curve (10Y-2Y):    {fmt(spread, '%')} — {curve_note}

Data source: {m.get('data_source', 'N/A')}

Using the real macro data above, assess the macro-economic environment for {ticker}.
Consider: rate environment impact on valuation, inflation trajectory, labor market health,
and whether the yield curve signals near-term economic pressure.

Generate macro context as JSON:
{{
  "sector_performance": "Outperforming/In-line/Underperforming market",
  "industry_tailwinds": ["tailwind1 (explain why given current rates/inflation)", "tailwind2"],
  "macro_headwinds": ["headwind1 (e.g. high rates compress multiples)", "headwind2"],
  "correlation_market": 0.82,
  "macro_outlook": "Positive/Neutral/Negative"
}}

Return ONLY valid JSON."""
    
    def _build_bull_case_prompt(self, ticker: str, context: Dict[str, Any]) -> str:
        """Build bull case prompt"""
        return f"""
Provide the bull case investment thesis for {ticker}.

Context: {json.dumps({k: v for k, v in context.items() if k in ['asset_info', 'fundamental_data', 'forecast_data']}, indent=2)}

Generate bull case as JSON:
{{
  "thesis": "Core bull thesis (2-3 sentences)",
  "key_catalysts": ["catalyst1", "catalyst2", "catalyst3"],
  "timeline": "Near-term (3-6 months)",
  "probability": 72.5
}}

Return ONLY valid JSON."""
    
    def _build_bear_case_prompt(self, ticker: str, context: Dict[str, Any]) -> str:
        """Build bear case prompt"""
        return f"""
Provide the bear case investment thesis for {ticker}.

Consider potential risks and downside scenarios.

Generate bear case as JSON:
{{
  "thesis": "Core bear thesis (2-3 sentences)",
  "key_catalysts": ["risk1", "risk2", "risk3"],
  "timeline": "Medium-term (6-12 months)",
  "probability": 27.5
}}

Return ONLY valid JSON."""
    
    def _build_risk_analysis_prompt(self, ticker: str, context: Dict[str, Any]) -> str:
        """Build risk analysis prompt"""
        sec = context.get("sec_summary", {})
        
        return f"""
Identify key risk factors for {ticker}.

Generate risks as JSON array:
[
  {{
    "description": "Risk description",
    "severity": "High/Medium/Low",
    "mitigation": "How this risk might be mitigated"
  }}
]

At least 3 risks. Return ONLY valid JSON array."""
    
    def _build_catalyst_prompt(self, ticker: str, context: Dict[str, Any]) -> str:
        """Build near-term catalyst prompt"""
        sec = context.get("sec_summary", {})
        
        return f"""
Identify near-term catalysts for {ticker} (next 3-6 months).

Generate catalysts as JSON array:
[
  {{
    "description": "Catalyst description",
    "severity": "High/Medium/Low",
    "mitigation": "Market impact if positive"
  }}
]

Return ONLY valid JSON array."""
    
    def _build_final_rating_prompt(
        self,
        ticker: str,
        context: Dict[str, Any],
        sections: Dict[str, Any]
    ) -> str:
        """Build final rating/recommendation prompt"""
        current_price = context.get("asset_info", {}).get("price", 100)
        bull_case = sections.get("bull_case", {})
        bear_case = sections.get("bear_case", {})
        technical = sections.get("technical_view", {})
        fundamental = sections.get("fundamental_snapshot", {})
        
        return f"""
Provide final investment rating for {ticker} at ${current_price}.

Analysis Summary:
- Bull Case Probability: {bull_case.get('probability', 50)}%
- Bear Case Probability: {bear_case.get('probability', 50)}%
- Technical Signal Strength: {technical.get('signal_strength', 50)}/100
- Quality Score: {fundamental.get('quality_score', 50)}/100

Generate final rating as JSON:
{{
  "recommendation": "BUY/HOLD/SELL",
  "target_price": {current_price * 1.15},
  "price_upside": 15.0,
  "conviction": "High/Medium/Low",
  "rationale": "Investment rationale (2 sentences)"
}}

Return ONLY valid JSON."""
    
    # ========== Response Parsers ==========
    
    def _parse_summary_response(self, response: str) -> Dict[str, str]:
        """Parse executive summary response"""
        try:
            # Try to extract JSON from response
            json_str = self._extract_json(response)
            if json_str:
                return json.loads(json_str)
        except Exception as e:
            logger.warning(f"Failed to parse summary: {str(e)}")
        
        # Fallback
        return {
            "executive_summary": response[:500],
            "investment_highlight": "AI-generated analysis",
        }
    
    def _parse_technical_response(
        self,
        response: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse technical analysis response"""
        try:
            json_str = self._extract_json(response)
            if json_str:
                data = json.loads(json_str)
                return {
                    "trend": data.get("trend", "Sideways"),
                    "key_levels": data.get("key_levels", [100, 110, 120]),
                    "signal_strength": min(100, max(0, data.get("signal_strength", 50))),
                    "momentum": data.get("momentum", "Neutral"),
                    "ma_alignment": data.get("ma_alignment", "Neutral"),
                    "summary": data.get("summary", "Technical analysis summary"),
                }
        except Exception as e:
            logger.warning(f"Failed to parse technical: {str(e)}")
        
        # Fallback
        technical = context.get("technical_data", {})
        return {
            "trend": technical.get("trend", "Sideways"),
            "key_levels": technical.get("support_levels", []) + technical.get("resistance_levels", []),
            "signal_strength": 50.0,
            "momentum": "Neutral",
            "ma_alignment": "Neutral",
            "summary": "Technical analysis from market data",
        }
    
    def _parse_fundamental_response(self, response: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Parse fundamental analysis response"""
        try:
            json_str = self._extract_json(response)
            if json_str:
                data = json.loads(json_str)
                return {
                    "eps": float(data.get("eps", 6.0)),
                    "revenue_growth": float(data.get("revenue_growth", 8.0)),
                    "profit_margin": float(data.get("profit_margin", 25.0)),
                    "roe": float(data.get("roe", 85.0)),
                    "debt_to_equity": float(data.get("debt_to_equity", 1.5)),
                    "valuation_assessment": data.get("valuation_assessment", "Fairly Valued"),
                    "quality_score": min(100, max(0, float(data.get("quality_score", 70)))),
                }
        except Exception as e:
            logger.warning(f"Failed to parse fundamental: {str(e)}")
        
        # Fallback: derive fields from real SEC data if available
        f = context.get("fundamental_data", {})
        eps = f.get("eps_diluted") or 6.0
        rev_growth = f.get("revenue_growth_yoy") or 8.0
        # Compute profit margin from real income / revenue
        revenue = f.get("revenue")
        net_income = f.get("net_income")
        profit_margin = round(net_income / revenue * 100, 1) if revenue and net_income else 25.0
        # Compute ROE from real equity
        equity = f.get("equity")
        roe = round(net_income / equity * 100, 1) if equity and net_income else 85.0
        # Compute D/E from real balance sheet
        liabilities = f.get("total_liabilities")
        debt_to_equity = round(liabilities / equity, 2) if equity and liabilities else 1.5
        # Quality score based on growth signal and risk level
        growth_signal = f.get("growth_signal", "stable")
        risk_level = f.get("risk_level", "medium")
        quality_base = {"accelerating": 85, "stable": 72, "decelerating": 52, "unknown": 65}.get(growth_signal, 65)
        quality_adj = {"low": +5, "medium": 0, "high": -10, "unknown": 0}.get(risk_level, 0)
        quality_score = min(100, max(0, quality_base + quality_adj))
        return {
            "eps": float(eps),
            "revenue_growth": float(rev_growth),
            "profit_margin": float(profit_margin),
            "roe": float(roe),
            "debt_to_equity": float(debt_to_equity),
            "valuation_assessment": "Fairly Valued",
            "quality_score": float(quality_score),
        }
    
    def _parse_macro_response(self, response: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Parse macro context response"""
        try:
            json_str = self._extract_json(response)
            if json_str:
                data = json.loads(json_str)
                return {
                    "sector_performance": data.get("sector_performance", "In-line"),
                    "industry_tailwinds": data.get("industry_tailwinds", []),
                    "macro_headwinds": data.get("macro_headwinds", []),
                    "correlation_market": min(1.0, max(-1.0, float(data.get("correlation_market", 0.8)))),
                    "macro_outlook": data.get("macro_outlook", "Neutral"),
                }
        except Exception as e:
            logger.warning(f"Failed to parse macro: {str(e)}")
        
        # Fallback: derive outlook from real FRED data
        m = context.get("macro_context", {})
        fed_funds = m.get("fed_funds_rate")
        cpi_yoy = m.get("cpi_yoy")
        spread = m.get("yield_curve_spread")
        # Simple heuristic: inverted curve or high rates → cautious
        if spread is not None and spread < -0.3:
            macro_outlook = "Negative"
        elif fed_funds is not None and fed_funds > 5.0:
            macro_outlook = "Neutral"
        else:
            macro_outlook = "Positive"
        headwinds = []
        tailwinds = []
        if fed_funds and fed_funds > 4.5:
            headwinds.append(f"Elevated fed funds rate ({fed_funds:.2f}%) pressures valuations")
        if cpi_yoy and cpi_yoy > 3.5:
            headwinds.append(f"Above-target inflation ({cpi_yoy:.1f}% YoY) reduces real returns")
        if spread is not None and spread < 0:
            headwinds.append("Inverted yield curve signals potential economic slowdown")
        if cpi_yoy and cpi_yoy < 3.5:
            tailwinds.append("Inflation trending toward Fed target supports rate cut expectations")
        if not tailwinds:
            tailwinds = ["Secular growth trends in the sector", "Resilient consumer demand"]
        if not headwinds:
            headwinds = ["Broader market volatility risk"]
        return {
            "sector_performance": "In-line",
            "industry_tailwinds": tailwinds[:2],
            "macro_headwinds": headwinds[:2],
            "correlation_market": 0.8,
            "macro_outlook": macro_outlook,
        }
    
    def _parse_investment_case_response(
        self,
        response: str,
        case_type: str
    ) -> Dict[str, Any]:
        """Parse bull/bear case response"""
        try:
            json_str = self._extract_json(response)
            if json_str:
                data = json.loads(json_str)
                probability = float(data.get("probability", 50 if case_type == "bull" else 50))
                return {
                    "thesis": data.get("thesis", "Investment case"),
                    "key_catalysts": data.get("key_catalysts", []),
                    "timeline": data.get("timeline", "Medium-term"),
                    "probability": min(100, max(0, probability)),
                }
        except Exception as e:
            logger.warning(f"Failed to parse {case_type} case: {str(e)}")
        
        # Fallback
        return {
            "thesis": f"{case_type.capitalize()} case for investment",
            "key_catalysts": [],
            "timeline": "Medium-term",
            "probability": 50.0,
        }
    
    def _parse_risks_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse risks response"""
        try:
            json_str = self._extract_json(response)
            if json_str:
                risks = json.loads(json_str)
                if isinstance(risks, list):
                    return [
                        {
                            "description": r.get("description", "Risk"),
                            "severity": r.get("severity", "Medium"),
                            "mitigation": r.get("mitigation", ""),
                        }
                        for r in risks[:5]  # Max 5 risks
                    ]
        except Exception as e:
            logger.warning(f"Failed to parse risks: {str(e)}")
        
        # Fallback
        return [
            {
                "description": "Market risk",
                "severity": "Medium",
                "mitigation": "Diversification",
            }
        ]
    
    def _parse_catalysts_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse catalysts response"""
        try:
            json_str = self._extract_json(response)
            if json_str:
                catalysts = json.loads(json_str)
                if isinstance(catalysts, list):
                    return [
                        {
                            "description": c.get("description", "Catalyst"),
                            "severity": c.get("severity", "Medium"),
                            "mitigation": c.get("mitigation", ""),
                        }
                        for c in catalysts[:5]  # Max 5 catalysts
                    ]
        except Exception as e:
            logger.warning(f"Failed to parse catalysts: {str(e)}")
        
        # Fallback
        return [
            {
                "description": "Upcoming earnings announcement",
                "severity": "High",
                "mitigation": "Potential for market surprise",
            }
        ]
    
    def _parse_final_rating_response(self, response: str) -> Dict[str, Any]:
        """Parse final rating response"""
        try:
            json_str = self._extract_json(response)
            if json_str:
                data = json.loads(json_str)
                return {
                    "recommendation": data.get("recommendation", "HOLD").upper(),
                    "target_price": float(data.get("target_price", 100)),
                    "price_upside": float(data.get("price_upside", 0)),
                    "conviction": data.get("conviction", "Medium"),
                    "rationale": data.get("rationale", "Based on comprehensive analysis"),
                }
        except Exception as e:
            logger.warning(f"Failed to parse final rating: {str(e)}")
        
        # Fallback
        return {
            "recommendation": "HOLD",
            "target_price": 100.0,
            "price_upside": 0.0,
            "conviction": "Medium",
            "rationale": "Awaiting additional market data",
        }
    
    def _extract_json(self, response: str) -> Optional[str]:
        """Extract JSON string from LLM response"""
        try:
            # Try to find JSON block
            if "{" in response:
                start_idx = response.find("{")
                # Find matching closing brace
                brace_count = 0
                for i in range(start_idx, len(response)):
                    if response[i] == "{":
                        brace_count += 1
                    elif response[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            return response[start_idx : i + 1]
            
            # Try array
            if "[" in response:
                start_idx = response.find("[")
                bracket_count = 0
                for i in range(start_idx, len(response)):
                    if response[i] == "[":
                        bracket_count += 1
                    elif response[i] == "]":
                        bracket_count -= 1
                        if bracket_count == 0:
                            return response[start_idx : i + 1]
        except Exception as e:
            logger.debug(f"JSON extraction error: {str(e)}")
        
        return None
    
    def _calculate_confidence_score(
        self,
        sections: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """Calculate overall confidence score"""
        confidence_factors = []
        
        # Technical signal strength
        tech = sections.get("technical_view", {})
        if "signal_strength" in tech:
            confidence_factors.append(tech["signal_strength"] / 100.0)
        
        # Forecast confidence
        forecast = context.get("forecast_data", {})
        if "confidence" in forecast:
            confidence_factors.append(forecast["confidence"] / 100.0)
        
        # Fundamental quality
        fundamental = sections.get("fundamental_snapshot", {})
        if "quality_score" in fundamental:
            confidence_factors.append(fundamental["quality_score"] / 100.0)
        
        # Bull case probability
        bull = sections.get("bull_case", {})
        if "probability" in bull:
            confidence_factors.append(bull["probability"] / 100.0)
        
        # Average confidence
        if confidence_factors:
            avg_confidence = (sum(confidence_factors) / len(confidence_factors)) * 100
            return min(100, max(0, avg_confidence))
        
        return 70.0  # Default confidence
    
    async def close(self):
        """Close HTTP client connection"""
        if self.client:
            await self.client.aclose()
    """
    Service layer for AI reasoning
    Provides high-level methods for analysis
    """
    
    def __init__(self, provider: Optional[ReasoningProvider] = None):
        """
        Initialize service
        
        Args:
            provider: Reasoning provider instance (defaults to Groq)
        """
        settings = get_settings()
        
        if provider:
            self.provider = provider
        elif settings.groq_api_key:
            self.provider = GroqReasoningProvider()
        else:
            logger.warning("No reasoning provider configured. Using mock.")
            self.provider = MockReasoningProvider()
    
    async def analyze_ticker(
        self,
        ticker: str,
        data: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Perform comprehensive analysis of ticker
        
        Args:
            ticker: Stock ticker
            data: Financial and market data
        
        Returns:
            Dictionary with various analysis types
        """
        analyses = {}
        
        for analysis_type in AnalysisType:
            try:
                result = await self.provider.analyze(analysis_type, data, ticker)
                analyses[analysis_type.value] = result
            except Exception as e:
                logger.error(f"Failed {analysis_type} analysis: {str(e)}")
                analyses[analysis_type.value] = f"Error: {str(e)}"
        
        return analyses
    
    async def generate_report(
        self,
        ticker: str,
        data: Dict[str, Any],
        include_sections: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Generate multi-section report
        
        Args:
            ticker: Stock ticker
            data: Financial data
            include_sections: Specific sections to include
        
        Returns:
            Report sections
        """
        if not include_sections:
            include_sections = [t.value for t in AnalysisType]
        
        report = {}
        
        for section in include_sections:
            try:
                analysis_type = AnalysisType(section)
                result = await self.provider.analyze(analysis_type, data, ticker)
                report[section] = result
            except Exception as e:
                logger.error(f"Failed to generate {section}: {str(e)}")
        
        return report
    
    async def explain(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get explanation or answer to a question
        
        Args:
            question: Question to answer
            context: Financial context data
        
        Returns:
            Explanation text
        """
        return await self.provider.reason(question, context)
    
    async def close(self):
        """Cleanup resources"""
        if hasattr(self.provider, 'close'):
            await self.provider.close()


def get_reasoning_provider() -> ReasoningProvider:
    """
    Factory: return the best available reasoning provider.

    Priority: deepseek → groq → mock
    Controlled by REASONING_PROVIDER env var (defaults to "deepseek").
    """
    settings = get_settings()
    preferred = (settings.reasoning_provider or "deepseek").lower()

    if preferred == "deepseek" and settings.deepseek_api_key:
        logger.info("Using DeepSeekReasoningProvider")
        return DeepSeekReasoningProvider()

    if preferred == "groq" and settings.groq_api_key:
        logger.info("Using GroqReasoningProvider")
        return GroqReasoningProvider()

    # Auto-fallback: try deepseek → groq → mock regardless of preference
    if settings.deepseek_api_key:
        logger.info("Falling back to DeepSeekReasoningProvider")
        return DeepSeekReasoningProvider()

    if settings.groq_api_key:
        logger.info("Falling back to GroqReasoningProvider")
        return GroqReasoningProvider()

    logger.warning("No LLM API key found — using MockReasoningProvider")
    return MockReasoningProvider()


class MockReasoningProvider(ReasoningProvider):
    """Mock implementation for development and testing"""
    
    async def reason(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        max_tokens: int = 1000
    ) -> str:
        """Return mock reasoning"""
        return f"Mock LLM Response:\n\n{prompt[:100]}...\n\nThis is a placeholder response from the mock LLM provider."
    
    async def analyze(
        self,
        analysis_type: AnalysisType,
        data: Dict[str, Any],
        ticker: str
    ) -> str:
        """Return mock analysis"""
        analyses = {
            AnalysisType.SENTIMENT: f"{ticker} shows positive market sentiment with strong buyer engagement.",
            AnalysisType.TECHNICAL: f"{ticker} is in an uptrend with support at $150 and resistance at $160.",
            AnalysisType.FUNDAMENTAL: f"{ticker} demonstrates solid fundamentals with improving margins.",
            AnalysisType.VALUATION: f"{ticker} is trading at a fair valuation relative to peers.",
            AnalysisType.RISK: f"{ticker} carries moderate execution risk from competitive pressures.",
            AnalysisType.SUMMARY: f"{ticker} is a strong buy with attractive risk/reward profile.",
        }
        return analyses.get(analysis_type, "Mock analysis result")
