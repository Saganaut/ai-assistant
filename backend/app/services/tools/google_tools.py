"""Google integration tools - Calendar, Drive, Gmail."""

from typing import Any

from app.services.integrations.google import (
    GoogleCalendarService,
    GoogleDriveService,
    GoogleGmailService,
    GoogleService,
)
from app.services.tools.base import BaseTool, ToolDefinition, ToolParameter

# Shared Google service instance
_google_service = GoogleService()
_calendar = GoogleCalendarService(_google_service)
_drive = GoogleDriveService(_google_service)
_gmail = GoogleGmailService(_google_service)


def get_google_service() -> GoogleService:
    return _google_service


# --- Calendar Tools ---

class CalendarListEventsTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="google_calendar_list",
            description="List upcoming events from Google Calendar.",
            parameters=[
                ToolParameter(
                    name="time_min", type="string",
                    description="Start time in ISO 8601 format (e.g., '2026-02-16T00:00:00Z'). Defaults to now.",
                    required=False,
                ),
                ToolParameter(
                    name="time_max", type="string",
                    description="End time in ISO 8601 format. Defaults to 7 days from now.",
                    required=False,
                ),
                ToolParameter(
                    name="max_results", type="integer",
                    description="Maximum number of events to return (default 10).",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        try:
            events = await _calendar.list_events(
                time_min=kwargs.get("time_min"),
                time_max=kwargs.get("time_max"),
                max_results=kwargs.get("max_results", 10),
            )
        except Exception as e:
            return f"Error listing calendar events: {e}"

        if not events:
            return "No upcoming events found."

        lines = []
        for event in events:
            start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date", "?"))
            summary = event.get("summary", "(No title)")
            event_id = event.get("id", "")
            lines.append(f"- {start}: {summary} [id: {event_id}]")
        return "Upcoming events:\n" + "\n".join(lines)


class CalendarCreateEventTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="google_calendar_create",
            description="Create a new event on Google Calendar.",
            parameters=[
                ToolParameter(name="summary", type="string", description="Event title"),
                ToolParameter(name="start", type="string", description="Start time in ISO 8601 format"),
                ToolParameter(name="end", type="string", description="End time in ISO 8601 format"),
                ToolParameter(name="description", type="string", description="Event description", required=False),
                ToolParameter(name="location", type="string", description="Event location", required=False),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        try:
            event = await _calendar.create_event(
                summary=kwargs["summary"],
                start=kwargs["start"],
                end=kwargs["end"],
                description=kwargs.get("description", ""),
                location=kwargs.get("location", ""),
            )
            return f"Event created: {event.get('summary')} (id: {event.get('id')})"
        except Exception as e:
            return f"Error creating event: {e}"


class CalendarDeleteEventTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="google_calendar_delete",
            description="Delete an event from Google Calendar.",
            parameters=[
                ToolParameter(name="event_id", type="string", description="The event ID to delete"),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        try:
            await _calendar.delete_event(kwargs["event_id"])
            return "Event deleted successfully."
        except Exception as e:
            return f"Error deleting event: {e}"


# --- Drive Tools ---

class DriveListFilesTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="google_drive_list",
            description="List files in Google Drive.",
            parameters=[
                ToolParameter(
                    name="query", type="string",
                    description="Search query to filter files by name.",
                    required=False,
                ),
                ToolParameter(
                    name="max_results", type="integer",
                    description="Maximum number of files to return (default 20).",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        try:
            files = await _drive.list_files(
                query=kwargs.get("query", ""),
                max_results=kwargs.get("max_results", 20),
            )
        except Exception as e:
            return f"Error listing Drive files: {e}"

        if not files:
            return "No files found."

        lines = []
        for f in files:
            name = f.get("name", "?")
            mime = f.get("mimeType", "")
            link = f.get("webViewLink", "")
            fid = f.get("id", "")
            lines.append(f"- {name} ({mime}) [id: {fid}]" + (f"\n  {link}" if link else ""))
        return "Drive files:\n" + "\n".join(lines)


class DriveSearchTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="google_drive_search",
            description="Search for files in Google Drive.",
            parameters=[
                ToolParameter(name="query", type="string", description="Search query"),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        try:
            files = await _drive.search(kwargs["query"])
        except Exception as e:
            return f"Error searching Drive: {e}"

        if not files:
            return f"No files found for: {kwargs['query']}"

        lines = []
        for f in files:
            lines.append(f"- {f.get('name')} [id: {f.get('id')}]")
        return "Search results:\n" + "\n".join(lines)


# --- Gmail Tools ---

class GmailListTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="google_gmail_list",
            description="List recent emails from Gmail.",
            parameters=[
                ToolParameter(
                    name="query", type="string",
                    description="Gmail search query (e.g., 'is:unread', 'from:user@example.com'). Empty for recent messages.",
                    required=False,
                ),
                ToolParameter(
                    name="max_results", type="integer",
                    description="Maximum number of emails to return (default 10).",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        try:
            messages = await _gmail.list_messages(
                query=kwargs.get("query", ""),
                max_results=kwargs.get("max_results", 10),
            )
        except Exception as e:
            return f"Error listing emails: {e}"

        if not messages:
            return "No emails found."

        lines = []
        for msg in messages:
            subject = msg.get("subject", "(No subject)")
            sender = msg.get("from", "?")
            date = msg.get("date", "")
            snippet = msg.get("snippet", "")[:80]
            lines.append(f"- [{date}] From: {sender}\n  Subject: {subject}\n  {snippet}")
        return "Emails:\n" + "\n".join(lines)


class GmailReadTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="google_gmail_read",
            description="Read a specific email by ID.",
            parameters=[
                ToolParameter(name="message_id", type="string", description="The email message ID"),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        try:
            msg = await _gmail.read_message(kwargs["message_id"])
            # Extract text content
            snippet = msg.get("snippet", "")
            headers = {
                h["name"]: h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }
            return (
                f"From: {headers.get('From', '?')}\n"
                f"To: {headers.get('To', '?')}\n"
                f"Date: {headers.get('Date', '?')}\n"
                f"Subject: {headers.get('Subject', '?')}\n\n"
                f"{snippet}"
            )
        except Exception as e:
            return f"Error reading email: {e}"


class GmailSendTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="google_gmail_send",
            description="Send an email via Gmail.",
            parameters=[
                ToolParameter(name="to", type="string", description="Recipient email address"),
                ToolParameter(name="subject", type="string", description="Email subject"),
                ToolParameter(name="body", type="string", description="Email body text"),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        try:
            result = await _gmail.send_message(
                to=kwargs["to"],
                subject=kwargs["subject"],
                body=kwargs["body"],
            )
            return f"Email sent successfully (id: {result.get('id', '?')})"
        except Exception as e:
            return f"Error sending email: {e}"
