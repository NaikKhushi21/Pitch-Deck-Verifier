"""
Configuration management for Sago Pitch Verifier
"""
import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration loaded from environment variables"""
    
    # LLM Configuration
    gemini_api_key: Optional[str] = field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))
    openrouter_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY"))
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openrouter"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "google/gemini-2.0-flash-exp"))
    
    # Gmail Configuration
    gmail_address: Optional[str] = field(default_factory=lambda: os.getenv("GMAIL_ADDRESS"))
    gmail_app_password: Optional[str] = field(default_factory=lambda: os.getenv("GMAIL_APP_PASSWORD"))
    report_recipient: Optional[str] = field(default_factory=lambda: os.getenv("REPORT_RECIPIENT"))
    
    # Web Search Configuration
    tavily_api_key: Optional[str] = field(default_factory=lambda: os.getenv("TAVILY_API_KEY"))
    search_provider: str = field(default_factory=lambda: os.getenv("SEARCH_PROVIDER", "tavily"))  # tavily or duckduckgo
    
    # Investor Profile (for personalization)
    investor_name: str = field(default_factory=lambda: os.getenv("INVESTOR_NAME", "Investor"))
    investor_focus_areas: str = field(default_factory=lambda: os.getenv("INVESTOR_FOCUS_AREAS", "B2B SaaS, FinTech, AI/ML"))
    investment_stage: str = field(default_factory=lambda: os.getenv("INVESTMENT_STAGE", "Series A"))
    
    def validate(self) -> bool:
        """Validate required configuration"""
        if self.llm_provider == "openrouter" and not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY must be set in .env file when using openrouter provider")
        elif self.llm_provider == "gemini" and not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY must be set in .env file when using gemini provider")
        return True


# Global config instance
config = Config()
