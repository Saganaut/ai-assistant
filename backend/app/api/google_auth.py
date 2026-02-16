"""Google OAuth status endpoint.

Credentials are loaded automatically from the JSON file at
ASSISTANT_GOOGLE_CREDENTIALS_PATH. No manual token pasting needed.
"""

from fastapi import APIRouter

from app.services.tools.google_tools import get_google_service

router = APIRouter()


@router.get("/status")
async def google_auth_status():
    """Check if Google credentials are configured."""
    service = get_google_service()
    return {"configured": service.is_configured}
