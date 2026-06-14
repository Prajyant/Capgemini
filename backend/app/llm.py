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


import re
import json
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.messages import AIMessage

class MockChatModel(BaseChatModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        # Combine messages content to look for patterns
        prompt_text = ""
        for m in messages:
            if hasattr(m, "content"):
                prompt_text += "\n" + str(m.content)
            elif isinstance(m, dict) and "content" in m:
                prompt_text += "\n" + str(m["content"])
            else:
                prompt_text += "\n" + str(m)
                
        # 1. Reasoning Agent Prompt
        if "LEAD PROFILE" in prompt_text or "sales intelligence agent" in prompt_text:
            # Parse lead details from prompt
            name_match = re.search(r"Name:\s*([^\n]+)", prompt_text)
            name = name_match.group(1).strip() if name_match else "Lead"
            first_name = name.split()[0] if name else "Lead"

            company_match = re.search(r"Company:\s*([^\n]+)", prompt_text)
            company = company_match.group(1).strip() if company_match else "their company"

            title_match = re.search(r"Title:\s*([^\n]+)", prompt_text)
            title = title_match.group(1).strip() if title_match else "Decision Maker"

            state_match = re.search(r"CURRENT LEAD STATE:\s*([^\n]+)", prompt_text)
            state = state_match.group(1).strip().lower() if state_match else "new"
            
            # Match seeded scenarios for exact matches
            if "Priya Patel" in name:
                response_data = {
                    "signal_analysis": "Series A funding 2 days ago + active hiring of 3 SDRs. Intent score 88/100.",
                    "situation_assessment": "Peak buying window. Founder/CEO is reachable. ICP fit 84.",
                    "options_considered": [
                        "Wait for inbound — risk of competitor reaching first",
                        "Send intro email now with funding congrats hook — highest expected value",
                        "Cold call CEO — too aggressive without prior touch"
                    ],
                    "decision": "send_email",
                    "confidence": 0.94,
                    "reasoning_summary": "I chose to send an intro email immediately. DataBridge just raised a Series A (news signal, 2 days old) and is hiring 3 SDRs. This is one of the highest buying-intent windows for sales tooling. Funding congratulations is a natural hook.",
                    "next_wait_days": 3,
                    "email_personalisation_hooks": ["Series A funding", "hiring 3 SDRs"]
                }
            elif "Sarah Chen" in name:
                response_data = {
                    "signal_analysis": "Two opens within 24 hours, no clicks, no reply. Strong attention signal but no commitment.",
                    "situation_assessment": "Lead is curious but not urgent. Email channel may have peaked.",
                    "options_considered": [
                        "Send another email immediately — risk of feeling pushy",
                        "Wait 3 days then switch to LinkedIn — softer touch, matches engagement pattern",
                        "Suggest a call — too aggressive for current signal"
                    ],
                    "decision": "send_linkedin_dm",
                    "confidence": 0.82,
                    "reasoning_summary": "I chose to wait 3 days and switch to LinkedIn. Sarah opened the email twice in 24 hours but hasn't replied — high curiosity, low urgency. A softer, less intrusive channel may convert this engagement signal into a conversation.",
                    "next_wait_days": 3,
                    "email_personalisation_hooks": []
                }
            elif "Marcus Williams" in name:
                response_data = {
                    "signal_analysis": "Reply received with objection: already using Outreach. Sentiment: objection.",
                    "situation_assessment": "Lead is engaged enough to reply with their stack. Open to comparison if differentiated value is clear.",
                    "options_considered": [
                        "Close sequence — premature, they engaged",
                        "Send displacement email focused on transparency — differentiates without naming competitor",
                        "Escalate to AE — better as a follow-up after value is established"
                    ],
                    "decision": "send_email",
                    "confidence": 0.78,
                    "reasoning_summary": "I chose to send a competitor displacement email. Marcus replied that they use Outreach. I'm focusing on our reasoning transparency — explaining each decision in plain English — which Outreach does not offer.",
                    "next_wait_days": 4,
                    "email_personalisation_hooks": ["reasoning transparency", "explainable decisions"]
                }
            elif "James O'Brien" in name:
                response_data = {
                    "signal_analysis": "0 opens, 0 clicks, 0 replies after 2 emails over 7 days.",
                    "situation_assessment": "Either wrong contact, wrong timing, or email landed in spam. Cannot determine cause.",
                    "options_considered": [
                        "Send 3rd email — diminishing returns, may damage sender reputation",
                        "Suggest call — could work but no signal to support confidence",
                        "Close sequence — wastes ICP fit",
                        "Escalate to human — best given uncertainty"
                    ],
                    "decision": "escalate_to_human",
                    "confidence": 0.58,
                    "reasoning_summary": "Confidence too low (58%) to act autonomously. Zero engagement after 7 days and 2 emails sent. Original recommendation was to suggest a phone call, but signals are too weak to commit autonomously. Flagged for SDR review.",
                    "next_wait_days": 1,
                    "email_personalisation_hooks": []
                }
            elif "Ananya Sharma" in name:
                response_data = {
                    "signal_analysis": "Positive reply with meeting confirmation. Goal achieved.",
                    "situation_assessment": "Conversion. No further automated outreach needed.",
                    "options_considered": ["Continue sequence — counterproductive", "Close sequence — correct"],
                    "decision": "close_sequence",
                    "confidence": 1.0,
                    "reasoning_summary": "I chose to close the sequence. Ananya replied positively and a meeting was booked. Sequence has fulfilled its purpose — handing off to AE and removing from automation queue.",
                    "next_wait_days": 0,
                    "email_personalisation_hooks": []
                }
            else:
                # Dynamic fallback for imported leads
                if state in ("new", "enriched", "cold"):
                    response_data = {
                        "signal_analysis": f"New lead {name} identified with relevant industry presence at {company}.",
                        "situation_assessment": "Initial stage. High potential match.",
                        "options_considered": ["Send intro email", "Wait for more signals"],
                        "decision": "send_email",
                        "confidence": 0.85,
                        "reasoning_summary": f"I chose to send a personalized intro email. {first_name} is {title} at {company}, matching our ICP criteria. We will lead with an insight hook highlighting how our sales intelligence agent automates judgment.",
                        "next_wait_days": 3,
                        "email_personalisation_hooks": ["sales intelligence agent", "judgment automation"]
                    }
                elif state in ("contacted", "engaged"):
                    response_data = {
                        "signal_analysis": f"Lead {name} has been contacted but has not yet replied.",
                        "situation_assessment": "Follow-up stage. Multi-channel touchpoint recommended.",
                        "options_considered": ["Send follow-up email", "Send LinkedIn DM", "Wait"],
                        "decision": "send_linkedin_dm",
                        "confidence": 0.80,
                        "reasoning_summary": f"I chose to follow up via a LinkedIn DM. Since we've already initiated contact, a multi-channel approach is recommended. A direct message to {first_name} about their role as {title} will help secure a response.",
                        "next_wait_days": 4,
                        "email_personalisation_hooks": []
                    }
                elif state == "replied":
                    response_data = {
                        "signal_analysis": f"Received inbound reply from {name}.",
                        "situation_assessment": "Active interest or objection. High engagement.",
                        "options_considered": ["Suggest call", "Send email follow-up"],
                        "decision": "suggest_call",
                        "confidence": 0.75,
                        "reasoning_summary": f"I chose to suggest a call. {first_name} recently replied to our email, and it is a good opportunity to schedule a brief 15-minute introductory call.",
                        "next_wait_days": 2,
                        "email_personalisation_hooks": []
                    }
                else:
                    response_data = {
                        "signal_analysis": f"Lead is in state {state}.",
                        "situation_assessment": "No immediate actions required.",
                        "options_considered": ["Wait"],
                        "decision": "wait",
                        "confidence": 0.90,
                        "reasoning_summary": f"I chose to wait. Let's give {first_name} some time to digest our previous message before taking further action.",
                        "next_wait_days": 5,
                        "email_personalisation_hooks": []
                    }
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=json.dumps(response_data)))])

        # 2. Email Generation Prompt
        elif "Generate a personalised B2B sales email" in prompt_text:
            # Parse details from email prompt
            name_match = re.search(r"Name:\s*([^\n]+)", prompt_text)
            name = name_match.group(1).strip() if name_match else "there"
            first_name = name.split()[0] if name else "there"

            company_match = re.search(r"Title:[^\n]+at\s*([^\n]+)", prompt_text)
            if not company_match:
                company_match = re.search(r"Company:\s*([^\n]+)", prompt_text)
            company = company_match.group(1).strip() if company_match else "your team"

            title_match = re.search(r"Title:\s*([^\n]+)", prompt_text)
            title = title_match.group(1).split(" at ")[0].strip() if title_match else "Decision Maker"

            type_match = re.search(r"EMAIL TYPE:\s*([^\n]+)", prompt_text)
            email_type = type_match.group(1).split(" (")[0].strip().lower() if type_match else "intro"

            if email_type == "intro":
                subject = f"Quick question on your Q3 outreach, {first_name}"
                body = f"Hi {first_name},\n\nSaw {company} is scaling the revenue team. Most outreach tools automate volume, but SalesAgent AI automates judgment—explaining every decision in plain English. Given your role as {title}, I thought you'd find this interesting. Open to a quick exchange?\n\nBest,\nSalesAgent AI"
            elif email_type == "follow_up":
                subject = f"Following up on {company} sales stack"
                body = f"Hi {first_name},\n\nWanted to share a quick insight: Teams using explainable AI for outreach see a 3x higher response rate. Ditching black-box automation helps build stronger relationships. Thought this would be helpful for your team at {company}.\n\nBest,\nSalesAgent AI"
            else:  # breakup
                subject = f"Last note from me, {first_name}"
                body = f"Hi {first_name},\n\nI haven't heard back, so I'm assuming outreach optimization isn't a priority for {company} right now. I'll stop emailing. If anything changes, feel free to reach back out.\n\nBest,\nSalesAgent AI"

            response_data = {
                "subject": subject,
                "body": body,
                "personalisation_used": f"referenced role as {title} and company {company}",
                "readability_notes": "short, direct, with a clear single call to action"
            }
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=json.dumps(response_data)))])

        # 3. Reply Classification Prompt
        elif "You classify inbound sales email replies" in prompt_text:
            reply_match = re.search(r"Reply text:\s*(.*)", prompt_text, re.DOTALL)
            reply_text = reply_match.group(1).strip() if reply_match else ""
            t = reply_text.lower()
            
            if any(k in t for k in ["unsubscribe", "remove me", "stop emailing"]):
                response_data = {"sentiment": "negative", "intent": "unsubscribe", "confidence": 0.95, "summary": "Unsubscribe request"}
            elif any(k in t for k in ["out of office", "ooo", "on vacation", "out of the office"]):
                response_data = {"sentiment": "neutral", "intent": "unknown", "confidence": 0.95, "summary": "Auto-reply OOO"}
            elif any(k in t for k in ["interested", "yes", "sounds good", "let's chat", "tell me more", "book"]):
                response_data = {"sentiment": "positive", "intent": "meeting_requested", "confidence": 0.90, "summary": "Expressed interest in scheduling a meeting"}
            elif any(k in t for k in ["already use", "we use", "we have"]):
                response_data = {"sentiment": "objection", "intent": "competitor", "confidence": 0.85, "summary": "Objection: already uses competitor"}
            elif any(k in t for k in ["not now", "later", "next quarter"]):
                response_data = {"sentiment": "neutral", "intent": "not_now", "confidence": 0.80, "summary": "Deferred"}
            else:
                response_data = {"sentiment": "neutral", "intent": "needs_more_info", "confidence": 0.70, "summary": "Replied requesting more information"}
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=json.dumps(response_data)))])

        # Default fallback
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="{}"))])

    @property
    def _llm_type(self) -> str:
        return "mock"

def get_llm(temperature: float = 0.3, max_tokens: int = 2000) -> BaseChatModel:
    """
    Return a configured chat model based on LLM_PROVIDER env var.

    All providers must produce JSON output reliably for the reasoning agent.
    """
    provider = (settings.LLM_PROVIDER or "anthropic").lower().strip()

    # Fallback to mock if API keys are missing
    has_key = True
    if provider == "groq" and not settings.GROQ_API_KEY:
        has_key = False
    elif provider == "gemini" and not settings.GEMINI_API_KEY:
        has_key = False
    elif provider == "openai" and not settings.OPENAI_API_KEY:
        has_key = False
    elif provider == "anthropic" and not settings.ANTHROPIC_API_KEY:
        has_key = False

    if not has_key or provider == "mock":
        logger.warning("LLM_PROVIDER '%s' has no API key configured. Falling back to 'mock' provider.", provider)
        return MockChatModel()

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
