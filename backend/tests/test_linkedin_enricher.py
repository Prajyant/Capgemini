import pytest
from app.enrichment.linkedin_enricher import (
    extract_linkedin_id,
    parse_tenure_months,
    extract_topics,
    fetch_linkedin_signals
)
from app.config import settings

def test_extract_linkedin_id():
    assert extract_linkedin_id("https://linkedin.com/in/sarah-chen-demo") == "sarah-chen-demo"
    assert extract_linkedin_id("https://www.linkedin.com/in/sarah-chen-demo/") == "sarah-chen-demo"
    assert extract_linkedin_id("http://linkedin.com/in/sarah-chen-demo?query=1") == "sarah-chen-demo"
    assert extract_linkedin_id("") is None
    assert extract_linkedin_id(None) is None


def test_parse_tenure_months():
    # Experience present
    exp = [
        {"company": "Google", "duration": "Jan 2022 - Present"}
    ]
    tenure = parse_tenure_months(exp)
    assert tenure > 0
    
    # Past job (no Present)
    exp_past = [
        {"company": "Google", "duration": "Jan 2020 - Dec 2021"}
    ]
    assert parse_tenure_months(exp_past) == 12
    
    # Empty list
    assert parse_tenure_months([]) == 12


def test_extract_topics():
    headline = "AI Product Manager at TechCorp"
    about = "Passionate about SaaS GTM alignment and cloud engineering."
    topics = extract_topics(headline, about)
    assert "AI" in topics
    assert "SAAS" in topics
    assert "GTM" in topics


@pytest.mark.asyncio
async def test_fetch_linkedin_signals_fallback():
    # With key unset (default), it should fallback to synthetic signals
    original_key = settings.LINKEDIN_API_KEY
    settings.LINKEDIN_API_KEY = ""
    try:
        signals = await fetch_linkedin_signals("https://linkedin.com/in/sarah-chen-demo")
        assert signals["source"] == "synthetic"
        assert signals["tenure_months"] == 18
    finally:
        settings.LINKEDIN_API_KEY = original_key
