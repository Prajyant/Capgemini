"""
Lightweight spam score heuristic. Returns 0.0-10.0 (lower is better).

Real impl could call SpamAssassin or Mail-Tester. This is a fast local heuristic
sufficient for catching obvious red flags before send.
"""
import re

SPAMMY_PHRASES = [
    "free", "buy now", "act now", "click here", "guaranteed",
    "limited time", "100% off", "winner", "congratulations",
    "make money fast", "no obligation", "risk-free", "urgent",
    "exclusive deal", "special promotion",
]


async def check_spam_score(body: str, subject: str = "") -> float:
    """Return spam score 0-10. Below 3 is generally safe."""
    if not body:
        return 0.0

    score = 0.0
    text = f"{subject} {body}".lower()

    # Spammy phrases
    for phrase in SPAMMY_PHRASES:
        if phrase in text:
            score += 0.5

    # ALL CAPS words (>20% of words in caps)
    words = body.split()
    if words:
        caps_count = sum(1 for w in words if w.isupper() and len(w) > 2)
        if caps_count / len(words) > 0.2:
            score += 1.5

    # Excessive exclamation marks
    excl_count = body.count("!")
    if excl_count > 3:
        score += min(excl_count * 0.3, 2.0)

    # Multiple dollar signs
    if body.count("$") > 2:
        score += 1.0

    # Excessive punctuation
    if re.search(r"[!?]{3,}", body):
        score += 1.5

    # Too many links
    link_count = len(re.findall(r"https?://", body))
    if link_count > 3:
        score += 1.0

    return round(min(score, 10.0), 2)
