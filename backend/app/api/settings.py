"""Settings status endpoint — never exposes secret values, only configured bools."""
from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _provider_status() -> dict:
    """Return which LLM provider is active and whether its key is set."""
    provider = (settings.LLM_PROVIDER or "anthropic").lower()
    key_present = {
        "groq": bool(settings.GROQ_API_KEY),
        "gemini": bool(settings.GEMINI_API_KEY),
        "openai": bool(settings.OPENAI_API_KEY),
        "anthropic": bool(settings.ANTHROPIC_API_KEY),
        "ollama": True,  # local, no key needed
    }
    return {
        "provider": provider,
        "key_configured": key_present.get(provider, False),
        "available_providers": [p for p, ok in key_present.items() if ok],
    }


@router.get("/status")
async def settings_status() -> dict:
    """Snapshot of which integrations are configured. Returns no secret values."""
    llm = _provider_status()
    return {
        "llm": llm,
        "integrations": {
            "anthropic": bool(settings.ANTHROPIC_API_KEY),
            "groq": bool(settings.GROQ_API_KEY),
            "gemini": bool(settings.GEMINI_API_KEY),
            "openai": bool(settings.OPENAI_API_KEY),
            "sendgrid": bool(settings.SENDGRID_API_KEY),
            "newsapi": bool(settings.NEWS_API_KEY),
            "builtwith": bool(settings.BUILTWITH_API_KEY),
            "linkedin": bool(settings.LINKEDIN_API_KEY),
            "hubspot": bool(settings.HUBSPOT_CLIENT_ID and settings.HUBSPOT_CLIENT_SECRET),
            "salesforce": bool(
                settings.SALESFORCE_CLIENT_ID and settings.SALESFORCE_CLIENT_SECRET
            ),
        },
        "agent": {
            "autopilot_mode": settings.AUTOPILOT_MODE,
            "confidence_threshold": settings.CONFIDENCE_THRESHOLD,
        },
        "sender": {
            "from_email": settings.SENDGRID_FROM_EMAIL,
            "from_name": settings.SENDGRID_FROM_NAME,
            "physical_address": settings.COMPANY_PHYSICAL_ADDRESS,
        },
        "environment": settings.ENVIRONMENT,
    }
