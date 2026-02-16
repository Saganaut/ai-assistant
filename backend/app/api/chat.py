import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.core.database import engine
from app.models.conversation import ChatMessage, Conversation
from app.services.agent import Agent

router = APIRouter()


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket):
    await websocket.accept()
    agent = Agent()
    gemini_messages: list[dict] = []
    conversation_id: int | None = None

    try:
        while True:
            raw = await websocket.receive_text()

            # Check if the client is sending JSON with metadata
            try:
                data = json.loads(raw)
                user_text = data.get("content", raw)
                if "conversation_id" in data:
                    new_conv_id = data["conversation_id"]
                    if new_conv_id != conversation_id:
                        conversation_id = new_conv_id
                        gemini_messages = _load_conversation_as_gemini(conversation_id)
            except (json.JSONDecodeError, TypeError):
                user_text = raw

            # Create conversation on first message if needed
            if conversation_id is None:
                conversation_id = _create_conversation(user_text[:80])

            # Save user message
            _save_message(conversation_id, "user", user_text)
            gemini_messages.append({"role": "user", "parts": [{"text": user_text}]})

            # Run agent with tool use
            full_response = ""
            async for token in agent.run(gemini_messages):
                await websocket.send_text(token)
                full_response += token

            # Save assistant message
            _save_message(conversation_id, "assistant", full_response)
            gemini_messages.append({"role": "model", "parts": [{"text": full_response}]})

            # Update conversation timestamp
            _touch_conversation(conversation_id)

            # Send end marker with conversation_id so frontend knows
            await websocket.send_json({"type": "end", "conversation_id": conversation_id})

    except WebSocketDisconnect:
        pass


def _create_conversation(title: str) -> int:
    with Session(engine) as session:
        conv = Conversation(title=title)
        session.add(conv)
        session.commit()
        session.refresh(conv)
        return conv.id  # type: ignore


def _save_message(conversation_id: int, role: str, content: str) -> None:
    with Session(engine) as session:
        msg = ChatMessage(conversation_id=conversation_id, role=role, content=content)
        session.add(msg)
        session.commit()


def _touch_conversation(conversation_id: int) -> None:
    with Session(engine) as session:
        conv = session.get(Conversation, conversation_id)
        if conv:
            conv.updated_at = datetime.now(timezone.utc)
            session.add(conv)
            session.commit()


def _load_conversation_as_gemini(conversation_id: int) -> list[dict]:
    """Load conversation messages in Gemini format."""
    with Session(engine) as session:
        conv = session.get(Conversation, conversation_id)
        if not conv:
            return []
        messages = []
        for msg in sorted(conv.messages, key=lambda m: m.created_at):
            role = "model" if msg.role == "assistant" else "user"
            messages.append({"role": role, "parts": [{"text": msg.content}]})
        return messages
