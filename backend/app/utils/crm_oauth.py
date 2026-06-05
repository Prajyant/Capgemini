"""CRM OAuth stubs for HubSpot and Salesforce."""
from app.config import settings


def hubspot_authorize_url() -> str:
    """Return HubSpot OAuth authorization URL."""
    return (
        "https://app.hubspot.com/oauth/authorize"
        f"?client_id={settings.HUBSPOT_CLIENT_ID}"
        f"&redirect_uri={settings.BACKEND_URL}/api/leads/oauth/hubspot/callback"
        "&scope=crm.objects.contacts.read"
    )


def salesforce_authorize_url() -> str:
    return (
        "https://login.salesforce.com/services/oauth2/authorize"
        "?response_type=code"
        f"&client_id={settings.SALESFORCE_CLIENT_ID}"
        f"&redirect_uri={settings.BACKEND_URL}/api/leads/oauth/salesforce/callback"
    )
