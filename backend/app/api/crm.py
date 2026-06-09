"""CRM OAuth connection endpoints for HubSpot and Salesforce."""
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.config import settings
from app.utils.crm_oauth import hubspot_authorize_url, salesforce_authorize_url

router = APIRouter(prefix="/api/crm", tags=["crm"])
logger = logging.getLogger(__name__)

# Redis keys for storing CRM tokens
_HUBSPOT_KEY = "crm:hubspot:token"
_SALESFORCE_KEY = "crm:salesforce:token"
_SALESFORCE_INSTANCE_KEY = "crm:salesforce:instance_url"


def _get_redis():
    """Return the Redis client, or None if unavailable."""
    try:
        from app.redis_client import get_redis
        return get_redis()
    except Exception:
        return None


# ── Status ─────────────────────────────────────────────────────────────────

@router.get("/status")
async def crm_status():
    """Return connection status for all CRMs."""
    redis = _get_redis()

    hubspot_connected = False
    salesforce_connected = False

    if redis:
        try:
            hubspot_connected = bool(await redis.get(_HUBSPOT_KEY))
            salesforce_connected = bool(await redis.get(_SALESFORCE_KEY))
        except Exception as e:
            logger.warning("Redis unavailable for CRM status: %s", e)

    return {
        "hubspot": {
            "connected": hubspot_connected,
            "status": "connected" if hubspot_connected else "not connected",
        },
        "salesforce": {
            "connected": salesforce_connected,
            "status": "connected" if salesforce_connected else "not connected",
        },
    }


# ── HubSpot ─────────────────────────────────────────────────────────────────

@router.get("/hubspot/connect")
async def hubspot_connect():
    """Redirect the browser to HubSpot's OAuth consent screen."""
    if not settings.HUBSPOT_CLIENT_ID:
        raise HTTPException(400, "HUBSPOT_CLIENT_ID is not configured")
    return RedirectResponse(hubspot_authorize_url())


@router.get("/hubspot/callback")
async def hubspot_callback(
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """Handle the OAuth callback from HubSpot, exchange code for tokens."""
    if error:
        logger.error("HubSpot OAuth error: %s", error)
        return RedirectResponse(f"{settings.FRONTEND_URL}/settings?crm=hubspot&error={error}")

    if not code:
        raise HTTPException(400, "Missing authorization code")

    # Exchange code for access token
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.hubapi.com/oauth/v1/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.HUBSPOT_CLIENT_ID,
                    "client_secret": settings.HUBSPOT_CLIENT_SECRET,
                    "redirect_uri": f"{settings.BACKEND_URL}/api/crm/hubspot/callback",
                    "code": code,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            token_data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("HubSpot token exchange failed: %s", e.response.text)
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/settings?crm=hubspot&error=token_exchange_failed"
        )
    except Exception as e:
        logger.error("HubSpot token exchange error: %s", e)
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/settings?crm=hubspot&error=connection_failed"
        )

    # Persist the access token (and refresh token) in Redis
    access_token = token_data.get("access_token", "")
    redis = _get_redis()
    if redis and access_token:
        try:
            # Store with a slightly shorter TTL than the token's expires_in
            expires_in = int(token_data.get("expires_in", 1800))
            await redis.set(_HUBSPOT_KEY, access_token, ex=expires_in - 60)
            refresh_token = token_data.get("refresh_token")
            if refresh_token:
                await redis.set("crm:hubspot:refresh_token", refresh_token)
        except Exception as e:
            logger.warning("Could not persist HubSpot token to Redis: %s", e)

    logger.info("HubSpot OAuth connected successfully")
    return RedirectResponse(f"{settings.FRONTEND_URL}/settings?crm=hubspot&status=connected")


@router.delete("/hubspot/disconnect")
async def hubspot_disconnect():
    """Remove stored HubSpot tokens."""
    redis = _get_redis()
    if redis:
        try:
            await redis.delete(_HUBSPOT_KEY, "crm:hubspot:refresh_token")
        except Exception as e:
            logger.warning("Redis error on HubSpot disconnect: %s", e)
    return {"status": "disconnected", "crm": "hubspot"}


# ── Salesforce ───────────────────────────────────────────────────────────────

@router.get("/salesforce/connect")
async def salesforce_connect():
    """Redirect the browser to Salesforce's OAuth consent screen."""
    if not settings.SALESFORCE_CLIENT_ID:
        raise HTTPException(400, "SALESFORCE_CLIENT_ID is not configured")
    return RedirectResponse(salesforce_authorize_url())


@router.get("/salesforce/callback")
async def salesforce_callback(
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
):
    """Handle the OAuth callback from Salesforce, exchange code for tokens."""
    if error:
        logger.error("Salesforce OAuth error: %s — %s", error, error_description)
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/settings?crm=salesforce&error={error}"
        )

    if not code:
        raise HTTPException(400, "Missing authorization code")

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://login.salesforce.com/services/oauth2/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.SALESFORCE_CLIENT_ID,
                    "client_secret": settings.SALESFORCE_CLIENT_SECRET,
                    "redirect_uri": f"{settings.BACKEND_URL}/api/crm/salesforce/callback",
                    "code": code,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            token_data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("Salesforce token exchange failed: %s", e.response.text)
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/settings?crm=salesforce&error=token_exchange_failed"
        )
    except Exception as e:
        logger.error("Salesforce token exchange error: %s", e)
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/settings?crm=salesforce&error=connection_failed"
        )

    access_token = token_data.get("access_token", "")
    instance_url = token_data.get("instance_url", "")

    redis = _get_redis()
    if redis and access_token:
        try:
            await redis.set(_SALESFORCE_KEY, access_token)
            if instance_url:
                await redis.set(_SALESFORCE_INSTANCE_KEY, instance_url)
            refresh_token = token_data.get("refresh_token")
            if refresh_token:
                await redis.set("crm:salesforce:refresh_token", refresh_token)
        except Exception as e:
            logger.warning("Could not persist Salesforce token to Redis: %s", e)

    logger.info("Salesforce OAuth connected successfully (instance: %s)", instance_url)
    return RedirectResponse(f"{settings.FRONTEND_URL}/settings?crm=salesforce&status=connected")


@router.delete("/salesforce/disconnect")
async def salesforce_disconnect():
    """Remove stored Salesforce tokens."""
    redis = _get_redis()
    if redis:
        try:
            await redis.delete(
                _SALESFORCE_KEY,
                _SALESFORCE_INSTANCE_KEY,
                "crm:salesforce:refresh_token",
            )
        except Exception as e:
            logger.warning("Redis error on Salesforce disconnect: %s", e)
    return {"status": "disconnected", "crm": "salesforce"}
