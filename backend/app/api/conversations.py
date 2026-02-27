"""REST API for conversation history management."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.conversation import ChatMessage, Conversation

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/")
async def list_conversations(session: Session = Depends(get_session)):
    conversations = session.exec(
        select(Conversation).order_by(Conversation.updated_at.desc())  # type: ignore
    ).all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
        }
        for c in conversations
    ]


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: int, session: Session = Depends(get_session)):
    conv = session.get(Conversation, conversation_id)
    if not conv:
        logger.debug(f"Conversation {conversation_id} not found")
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = session.exec(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at)  # type: ignore
    ).all()

    return {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: int, session: Session = Depends(get_session)):
    conv = session.get(Conversation, conversation_id)
    if not conv:
        logger.debug(f"Delete: conversation {conversation_id} not found")
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Delete messages first
    messages = session.exec(
        select(ChatMessage).where(ChatMessage.conversation_id == conversation_id)
    ).all()
    for msg in messages:
        session.delete(msg)

    session.delete(conv)
    session.commit()
    logger.debug(f"Deleted conversation {conversation_id}")
    return {"status": "deleted"}
