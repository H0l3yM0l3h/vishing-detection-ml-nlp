"""
penipu_client.py — PenipuMY API Client for ShieldGuard
=======================================================
Standalone module for querying Malaysia's community-driven scam database.
Provides phone number lookup, bank account lookup, search, and platform stats.

API Documentation: https://penipu.my/api/v1/docs
"""

import os
import httpx
from typing import Optional

PENIPU_API_KEY = os.environ.get("PENIPU_API_KEY", "")
PENIPU_BASE_URL = "https://penipu.my/api/v1"
PENIPU_TIMEOUT = 10.0  # seconds


def _get_headers() -> dict:
    """Return headers with API key for PenipuMY requests."""
    return {
        "X-API-Key": PENIPU_API_KEY,
        "Accept": "application/json",
    }


def is_configured() -> bool:
    """Check if PenipuMY API key is configured."""
    return bool(PENIPU_API_KEY and len(PENIPU_API_KEY) > 5)


async def lookup_phone(phone_number: str) -> dict:
    """
    Quick lookup for a phone number.
    Returns police report count, community verified reports, spam/fraud flags,
    and business info if the number belongs to a verified business.
    """
    async with httpx.AsyncClient(timeout=PENIPU_TIMEOUT) as client:
        resp = await client.get(
            f"{PENIPU_BASE_URL}/phone",
            headers=_get_headers(),
            params={"q": phone_number},
        )
        resp.raise_for_status()
        return resp.json()


async def lookup_bank(account_number: str) -> dict:
    """
    Quick lookup for a bank account number.
    Returns police report count, community verified reports, and fraud flag.
    """
    async with httpx.AsyncClient(timeout=PENIPU_TIMEOUT) as client:
        resp = await client.get(
            f"{PENIPU_BASE_URL}/bank",
            headers=_get_headers(),
            params={"q": account_number},
        )
        resp.raise_for_status()
        return resp.json()


async def search(query: str, search_type: str = "auto", limit: int = 10) -> dict:
    """
    Search the scam database by phone number, bank account, social media, or general query.
    search_type: auto | phone | bank | social | name
    """
    async with httpx.AsyncClient(timeout=PENIPU_TIMEOUT) as client:
        resp = await client.get(
            f"{PENIPU_BASE_URL}/search",
            headers=_get_headers(),
            params={"q": query, "type": search_type, "limit": limit},
        )
        resp.raise_for_status()
        return resp.json()


async def get_profile(profile_id: str) -> dict:
    """
    Get detailed information about a specific scam profile,
    including all linked reports.
    """
    async with httpx.AsyncClient(timeout=PENIPU_TIMEOUT) as client:
        resp = await client.get(
            f"{PENIPU_BASE_URL}/profile/{profile_id}",
            headers=_get_headers(),
        )
        resp.raise_for_status()
        return resp.json()


async def get_stats() -> dict:
    """
    Get platform-wide statistics including total reports, profiles,
    and losses tracked across PenipuMY.
    """
    async with httpx.AsyncClient(timeout=PENIPU_TIMEOUT) as client:
        resp = await client.get(
            f"{PENIPU_BASE_URL}/stats",
            headers=_get_headers(),
        )
        resp.raise_for_status()
        return resp.json()


async def check_available() -> bool:
    """Check if PenipuMY API is reachable and the API key is valid."""
    if not is_configured():
        return False
    try:
        await get_stats()
        return True
    except Exception:
        return False
