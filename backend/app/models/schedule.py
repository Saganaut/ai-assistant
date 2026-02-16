"""Scheduled actions and run history models."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class ScheduledAction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    cron_expression: str  # Standard cron: "0 7 * * *" = daily at 7am
    prompt: str  # The instruction to send to the agent
    enabled: bool = Field(default=True)
    max_retries: int = Field(default=3)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScheduledRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    action_id: int = Field(foreign_key="scheduledaction.id")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    status: str = Field(default="running")  # running | success | failed
    result: str = Field(default="")
    error: Optional[str] = None
    retry_count: int = Field(default=0)
