"""
Centralized configuration for SalesAgent AI.
All environment variables loaded here. Never hardcode secrets.
"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@db:5432/salesagent"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

    # LLM provider selector: anthropic | groq | gemini | openai | ollama
    LLM_PROVIDER: str = "anthropic"

    # Groq (free tier — recommended for hackathon demo)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Google Gemini (free tier)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Ollama (local, free)
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "llama3.2"

    # SendGrid
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "outreach@example.com"
    SENDGRID_FROM_NAME: str = "SalesAgent AI"
    SENDGRID_WEBHOOK_SECRET: str = ""

    # Enrichment APIs
    NEWS_API_KEY: str = ""
    BUILTWITH_API_KEY: str = ""
    LINKEDIN_API_KEY: str = ""

    # Auth
    JWT_SECRET_KEY: str = "dev-secret-key-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # CRM
    HUBSPOT_CLIENT_ID: str = ""
    HUBSPOT_CLIENT_SECRET: str = ""
    SALESFORCE_CLIENT_ID: str = ""
    SALESFORCE_CLIENT_SECRET: str = ""

    # App
    ENVIRONMENT: str = "development"
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"

    # Feature flags
    AUTOPILOT_MODE: bool = False
    CONFIDENCE_THRESHOLD: float = 0.65

    # Compliance
    COMPANY_PHYSICAL_ADDRESS: str = "123 Demo Street, San Francisco, CA 94103"
    UNSUBSCRIBE_BASE_URL: str = "http://localhost:8000/unsubscribe"

    # IMAP Inbox Reading
    IMAP_HOST: str = ""
    IMAP_PORT: int = 993
    IMAP_USER: str = ""
    IMAP_PASSWORD: str = ""


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Clear cache so reloads pick up .env changes
get_settings.cache_clear()
settings = get_settings()
