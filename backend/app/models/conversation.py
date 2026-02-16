"""Conversation and message models for chat history persistence."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class Conversation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(default="New Conversation")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    messages: list["ChatMessage"] = Relationship(back_populates="conversation")


class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversation.id")
    role: str  # "user" | "assistant" | "system" | "scheduled"
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    conversation: Optional[Conversation] = Relationship(back_populates="messages")
