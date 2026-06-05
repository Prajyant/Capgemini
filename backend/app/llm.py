"""
LLM provider factory.

One central place to swap which AI model the agent talks to.
Switch providers via the LLM_PROVIDER env variable: groq | gemini | anthropic | openai | ollama
"""
import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import settings

logger = logging.getLogger(__name__)


def get_llm(temperature: float = 0.3, max_tokens: int = 2000) -> BaseChatModel:
    """
    Return a configured chat model based on LLM_PROVIDER env var.

    All providers must produce JSON output reliably for the reasoning agent.
    """
    provider = (settings.LLM_PROVIDER or "anthropic").lower().strip()

    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=settings.GROQ_MODEL or "llama-3.3-70b-versatile",
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=settings.GROQ_API_KEY,
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL or "gemini-1.5-flash",
            temperature=temperature,
            max_output_tokens=max_tokens,
            google_api_key=settings.GEMINI_API_KEY,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.OPENAI_MODEL or "gpt-4o-mini",
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=settings.OPENAI_API_KEY,
        )

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.OLLAMA_MODEL or "llama3.2",
            temperature=temperature,
            num_predict=max_tokens,
            base_url=settings.OLLAMA_BASE_URL or "http://host.docker.internal:11434",
        )

    # Default: Anthropic Claude
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(
        model=settings.CLAUDE_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        api_key=settings.ANTHROPIC_API_KEY,
    )


def extract_text(response_content: Any) -> str:
    """Some providers return list-of-blocks; normalise to plain string."""
    if isinstance(response_content, str):
        return response_content
    if isinstance(response_content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in response_content
        )
    return str(response_content)
