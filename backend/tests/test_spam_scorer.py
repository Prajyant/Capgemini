"""Spam scorer tests."""
import pytest

from app.utils.spam_scorer import check_spam_score


@pytest.mark.asyncio
async def test_clean_email_low_score():
    score = await check_spam_score(
        "Hi Sarah, noticed your team just shipped the new analytics dashboard. "
        "Curious how you're approaching attribution lately?"
    )
    assert score < 1.0


@pytest.mark.asyncio
async def test_spammy_email_high_score():
    score = await check_spam_score(
        "FREE!!! ACT NOW!!! 100% off!!! WINNER!!! BUY NOW!!! "
        "URGENT URGENT URGENT $$$$ LIMITED TIME!!!"
    )
    assert score > 3.0


@pytest.mark.asyncio
async def test_empty_body_zero_score():
    assert await check_spam_score("") == 0.0
