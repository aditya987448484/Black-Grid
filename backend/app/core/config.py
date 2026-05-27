"""
Application settings and configuration using Pydantic Settings
Structured for easy switching between mock and real data providers
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file
    """
    
    # ============================================================================
    # APPLICATION
    # ============================================================================
    app_name: str = "Axiom Terminal API"
    app_version: str = "0.1.0"
    app_description: str = "AI-powered financial research platform"
    debug: bool = True
    
    # ============================================================================
    # SERVER & API
    # ============================================================================
    api_v1_str: str = "/api"
    
    # CORS - Add production domains here
    backend_cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]
    
    # ============================================================================
    # DATABASE
    # ============================================================================
    database_url: str = "sqlite:///./test.db"
    sqlalchemy_echo: bool = False
    
    # ============================================================================
    # DATA PROVIDERS - Switch between mock and real
    # ============================================================================
    # Set to "mock" for development, "alpha_vantage" for real data
    market_data_provider: str = "mock"
    technical_indicator_provider: str = "mock"
    forecast_provider: str = "mock"
    
    # ============================================================================
    # EXTERNAL MARKET DATA APIS
    # ============================================================================
    # Alpha Vantage API - Stock market data
    alpha_vantage_key: Optional[str] = None
    alpha_vantage_base_url: str = "https://www.alphavantage.co"
    
    # FRED API - Federal Reserve Economic Data
    fred_api_key: Optional[str] = None
    fred_base_url: str = "https://api.stlouisfed.org"
    
    # Fin Hub API - Financial data aggregator
    fin_hub_api_key: Optional[str] = None
    fin_hub_base_url: str = "https://finnhub.io"
    
    # IEX Cloud API
    iex_cloud_key: Optional[str] = None
    iex_cloud_base_url: str = "https://cloud.iexapis.com"
    
    # Polygon.io API
    polygon_key: Optional[str] = None
    polygon_base_url: str = "https://api.polygon.io"
    
    # News API - Financial news
    news_api_key: Optional[str] = None
    news_api_base_url: str = "https://newsapi.org"
    
    # SEC EDGAR - SEC filings data
    sec_api_key: Optional[str] = None
    sec_base_url: str = "https://www.sec.gov"
    sec_user_agent: str = "Axiom Terminal (contact support@example.com)"
    
    # ============================================================================
    # AI/LLM MODELS
    # ============================================================================
    # DeepSeek API - Primary LLM for analyst report generation
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    # Reasoning provider selection: "deepseek" | "groq" | "mock"
    reasoning_provider: str = "deepseek"

    # Groq API - Fallback LLM
    groq_api_key: Optional[str] = None
    groq_base_url: str = "https://api.groq.com"
    groq_model: str = "mixtral-8x7b-32768"
    
    # ============================================================================
    # ML & FORECASTING
    # ============================================================================
    use_ml_forecasts: bool = True
    ml_model_path: Optional[str] = None
    
    # ============================================================================
    # SECURITY
    # ============================================================================
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # ============================================================================
    # CACHING
    # ============================================================================
    use_cache: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes
    
    # ============================================================================
    # LOGGING
    # ============================================================================
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False  # Allow both LOWERCASE and lowercase env vars


# Singleton instance
@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
