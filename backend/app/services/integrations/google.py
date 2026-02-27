"""Google API integration - Calendar, Drive, Gmail.

Uses Google API client with service account or OAuth credentials.
The credentials path is configured via ASSISTANT_GOOGLE_CREDENTIALS_PATH.
"""

import logging
from pathlib import Path
from typing import Any

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from app.core.config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.modify",
]


class GoogleService:
    """Manages Google API access using OAuth credentials from a JSON file."""

    def __init__(self):
        self._credentials_path = settings.google_credentials_path
        self._credentials: Credentials | None = None

    def _load_credentials(self) -> Credentials | None:
        """Load OAuth credentials from the configured JSON file."""
        if not self._credentials_path:
            return None

        creds_file = Path(self._credentials_path)
        if not creds_file.exists():
            logger.warning(f"Google credentials file not found: {creds_file}")
            return None

        try:
            creds = Credentials.from_authorized_user_file(str(creds_file), SCOPES)
            return creds
        except Exception as e:
            logger.error(f"Failed to load Google credentials: {e}")
            return None

    def _get_credentials(self) -> Credentials:
        """Get valid credentials, refreshing if needed."""
        if self._credentials is None:
            self._credentials = self._load_credentials()

        if self._credentials is None:
            raise ValueError(
                "Google credentials not configured. "
                "Set ASSISTANT_GOOGLE_CREDENTIALS_PATH to your OAuth credentials JSON file."
            )

        if self._credentials.expired and self._credentials.refresh_token:
            self._credentials.refresh(Request())
            # Save refreshed token back to file
            self._save_credentials()

        return self._credentials

    def _save_credentials(self) -> None:
        """Save current credentials back to the JSON file (preserves refresh token)."""
        if not self._credentials_path or not self._credentials:
            return
        try:
            creds_file = Path(self._credentials_path)
            creds_file.write_text(self._credentials.to_json())
        except Exception as e:
            logger.error(f"Failed to save refreshed credentials: {e}")

    async def _get_headers(self) -> dict[str, str]:
        """Get authorization headers with a valid access token."""
        creds = self._get_credentials()
        return {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json",
        }

    @property
    def is_configured(self) -> bool:
        """Check if Google credentials are available."""
        if not self._credentials_path:
            return False
        return Path(self._credentials_path).exists()


class GoogleCalendarService:
    """Google Calendar API wrapper."""

    BASE_URL = "https://www.googleapis.com/calendar/v3"

    def __init__(self, google: GoogleService):
        self._google = google

    async def list_events(
        self,
        time_min: str | None = None,
        time_max: str | None = None,
        max_results: int = 10,
        calendar_id: str = "primary",
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max

        headers = await self._google._get_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/calendars/{calendar_id}/events",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("items", [])

    async def create_event(
        self,
        summary: str,
        start: str,
        end: str,
        description: str = "",
        location: str = "",
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        body = {
            "summary": summary,
            "start": {"dateTime": start},
            "end": {"dateTime": end},
        }
        if description:
            body["description"] = description
        if location:
            body["location"] = location

        headers = await self._google._get_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/calendars/{calendar_id}/events",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            return resp.json()

    async def update_event(
        self,
        event_id: str,
        updates: dict[str, Any],
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        headers = await self._google._get_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{self.BASE_URL}/calendars/{calendar_id}/events/{event_id}",
                headers=headers,
                json=updates,
            )
            resp.raise_for_status()
            return resp.json()

    async def delete_event(self, event_id: str, calendar_id: str = "primary") -> None:
        headers = await self._google._get_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{self.BASE_URL}/calendars/{calendar_id}/events/{event_id}",
                headers=headers,
            )
            resp.raise_for_status()


class GoogleDriveService:
    """Google Drive API wrapper."""

    BASE_URL = "https://www.googleapis.com/drive/v3"
    UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3"

    def __init__(self, google: GoogleService):
        self._google = google

    async def list_files(
        self,
        query: str = "",
        max_results: int = 20,
        folder_id: str | None = None,
    ) -> list[dict[str, Any]]:
        q_parts = []
        if query:
            q_parts.append(f"name contains '{query}'")
        if folder_id:
            q_parts.append(f"'{folder_id}' in parents")
        q_parts.append("trashed = false")

        params: dict[str, Any] = {
            "pageSize": max_results,
            "fields": "files(id,name,mimeType,size,modifiedTime,webViewLink)",
            "q": " and ".join(q_parts),
        }

        headers = await self._google._get_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/files",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            return resp.json().get("files", [])

    async def download_file(self, file_id: str) -> bytes:
        headers = await self._google._get_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/files/{file_id}",
                headers=headers,
                params={"alt": "media"},
            )
            resp.raise_for_status()
            return resp.content

    async def upload_file(
        self, name: str, content: bytes, mime_type: str, folder_id: str | None = None
    ) -> dict[str, Any]:
        """Upload a file using multipart upload (metadata + content in one request)."""
        import json as _json

        metadata: dict[str, Any] = {"name": name}
        if folder_id:
            metadata["parents"] = [folder_id]

        boundary = "----AssistantUploadBoundary"
        metadata_json = _json.dumps(metadata)
        body = (
            f"--{boundary}\r\n"
            f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{metadata_json}\r\n"
            f"--{boundary}\r\n"
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode() + content + f"\r\n--{boundary}--".encode()

        headers = await self._google._get_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.UPLOAD_URL}/files",
                headers={
                    "Authorization": headers["Authorization"],
                    "Content-Type": f"multipart/related; boundary={boundary}",
                },
                params={"uploadType": "multipart"},
                content=body,
            )
            resp.raise_for_status()
            return resp.json()

    async def update_file(
        self, file_id: str, content: bytes, mime_type: str
    ) -> dict[str, Any]:
        """Update an existing file's content."""
        headers = await self._google._get_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{self.UPLOAD_URL}/files/{file_id}",
                headers={
                    "Authorization": headers["Authorization"],
                    "Content-Type": mime_type,
                },
                params={"uploadType": "media"},
                content=content,
            )
            resp.raise_for_status()
            return resp.json()

    async def create_folder(
        self, name: str, parent_id: str | None = None
    ) -> dict[str, Any]:
        """Create a folder on Drive, returns file metadata."""
        metadata: dict[str, Any] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            metadata["parents"] = [parent_id]

        headers = await self._google._get_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/files",
                headers=headers,
                json=metadata,
            )
            resp.raise_for_status()
            return resp.json()

    async def find_or_create_folder(
        self, name: str, parent_id: str | None = None
    ) -> dict[str, Any]:
        """Find an existing folder by name within parent, or create it."""
        q_parts = [
            f"name = '{name}'",
            "mimeType = 'application/vnd.google-apps.folder'",
            "trashed = false",
        ]
        if parent_id:
            q_parts.append(f"'{parent_id}' in parents")

        headers = await self._google._get_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/files",
                headers=headers,
                params={
                    "q": " and ".join(q_parts),
                    "fields": "files(id,name)",
                    "pageSize": 1,
                },
            )
            resp.raise_for_status()
            files = resp.json().get("files", [])

        if files:
            return files[0]
        return await self.create_folder(name, parent_id)

    async def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        return await self.list_files(query=query, max_results=max_results)


class GoogleGmailService:
    """Google Gmail API wrapper."""

    BASE_URL = "https://gmail.googleapis.com/gmail/v1"

    def __init__(self, google: GoogleService):
        self._google = google

    async def list_messages(
        self, query: str = "", max_results: int = 10
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"maxResults": max_results}
        if query:
            params["q"] = query

        headers = await self._google._get_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/users/me/messages",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            messages = resp.json().get("messages", [])

            # Fetch details for each message
            detailed = []
            for msg in messages[:max_results]:
                detail = await self._get_message(client, headers, msg["id"])
                detailed.append(detail)
            return detailed

    async def _get_message(
        self, client: httpx.AsyncClient, headers: dict, msg_id: str
    ) -> dict[str, Any]:
        resp = await client.get(
            f"{self.BASE_URL}/users/me/messages/{msg_id}",
            headers=headers,
            params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]},
        )
        resp.raise_for_status()
        data = resp.json()

        # Extract headers
        result: dict[str, Any] = {"id": msg_id, "snippet": data.get("snippet", "")}
        for header in data.get("payload", {}).get("headers", []):
            result[header["name"].lower()] = header["value"]
        return result

    async def read_message(self, msg_id: str) -> dict[str, Any]:
        headers = await self._google._get_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/users/me/messages/{msg_id}",
                headers=headers,
                params={"format": "full"},
            )
            resp.raise_for_status()
            return resp.json()

    async def send_message(self, to: str, subject: str, body: str) -> dict[str, Any]:
        import base64
        from email.mime.text import MIMEText

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        headers = await self._google._get_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/users/me/messages/send",
                headers=headers,
                json={"raw": raw},
            )
            resp.raise_for_status()
            return resp.json()

    async def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        return await self.list_messages(query=query, max_results=max_results)
