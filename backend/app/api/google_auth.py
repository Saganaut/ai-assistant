"""Google OAuth token management endpoint.

Since this is a personal assistant, we use a simple flow:
1. User gets an OAuth token externally (e.g., via Google OAuth Playground)
2. User submits the token to this endpoint
3. Token is stored in memory and used for all Google API calls

In the future, this can be replaced with a full OAuth flow.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.tools.google_tools import get_google_service

router = APIRouter()


class TokenSubmit(BaseModel):
    access_token: str


@router.post("/token")
async def set_google_token(body: TokenSubmit):
    """Set the Google OAuth access token."""
    service = get_google_service()
    service.set_token(body.access_token)
    return {"status": "ok", "message": "Google token configured"}


@router.get("/status")
async def google_auth_status():
    """Check if Google is configured."""
    service = get_google_service()
    has_token = service._token is not None
    return {"configured": has_token}
