"""Tests for the WebSocket chat endpoint."""

import json

from sqlmodel import Session, select

from tests.conftest import test_engine
from app.models.conversation import ChatMessage, Conversation


def test_websocket_connect_disconnect(client):
    """Basic connection and clean disconnect."""
    with client.websocket_connect("/api/chat/ws") as ws:
        pass  # just connect and disconnect


def test_websocket_send_receive_tokens(client):
    """Send a message, receive streamed tokens and end marker."""
    with client.websocket_connect("/api/chat/ws") as ws:
        ws.send_text("hello")

        # Collect streamed tokens
        tokens = []
        while True:
            data = ws.receive_text()
            try:
                parsed = json.loads(data)
                if parsed.get("type") == "end":
                    break
            except json.JSONDecodeError:
                tokens.append(data)

        assert "".join(tokens) == "Hello from agent"


def test_websocket_end_marker_has_conversation_id(client):
    """End marker should include the conversation_id."""
    with client.websocket_connect("/api/chat/ws") as ws:
        ws.send_text("hi")

        end_data = None
        while True:
            data = ws.receive_text()
            try:
                parsed = json.loads(data)
                if parsed.get("type") == "end":
                    end_data = parsed
                    break
            except json.JSONDecodeError:
                continue

        assert end_data is not None
        assert "conversation_id" in end_data
        assert isinstance(end_data["conversation_id"], int)


def test_websocket_json_payload_with_conversation_id(client):
    """Client can send JSON with content and conversation_id."""
    with client.websocket_connect("/api/chat/ws") as ws:
        ws.send_text(json.dumps({"content": "test message"}))

        # Drain tokens until end marker
        end_data = None
        while True:
            data = ws.receive_text()
            try:
                parsed = json.loads(data)
                if parsed.get("type") == "end":
                    end_data = parsed
                    break
            except json.JSONDecodeError:
                continue

        conv_id = end_data["conversation_id"]

        # Send second message to same conversation
        ws.send_text(json.dumps({"content": "follow up", "conversation_id": conv_id}))
        end_data2 = None
        while True:
            data = ws.receive_text()
            try:
                parsed = json.loads(data)
                if parsed.get("type") == "end":
                    end_data2 = parsed
                    break
            except json.JSONDecodeError:
                continue

        assert end_data2["conversation_id"] == conv_id


def test_websocket_messages_persisted(client):
    """User and assistant messages should be saved to the database."""
    with client.websocket_connect("/api/chat/ws") as ws:
        ws.send_text("save me")

        # Drain until end
        while True:
            data = ws.receive_text()
            try:
                parsed = json.loads(data)
                if parsed.get("type") == "end":
                    conv_id = parsed["conversation_id"]
                    break
            except json.JSONDecodeError:
                continue

    # Check DB
    with Session(test_engine) as session:
        conv = session.get(Conversation, conv_id)
        assert conv is not None

        messages = session.exec(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conv_id)
            .order_by(ChatMessage.created_at)
        ).all()

        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "save me"
        assert messages[1].role == "assistant"
        assert messages[1].content == "Hello from agent"


def test_websocket_multiple_messages_same_conversation(client):
    """Multiple messages in one session reuse the same conversation."""
    with client.websocket_connect("/api/chat/ws") as ws:
        conv_ids = []
        for msg in ["first", "second", "third"]:
            ws.send_text(msg)
            while True:
                data = ws.receive_text()
                try:
                    parsed = json.loads(data)
                    if parsed.get("type") == "end":
                        conv_ids.append(parsed["conversation_id"])
                        break
                except json.JSONDecodeError:
                    continue

        # All messages should be in the same conversation
        assert len(set(conv_ids)) == 1

    # Should have 6 messages total (3 user + 3 assistant)
    with Session(test_engine) as session:
        messages = session.exec(
            select(ChatMessage).where(ChatMessage.conversation_id == conv_ids[0])
        ).all()
        assert len(messages) == 6


def test_websocket_load_existing_conversation(client):
    """Sending a conversation_id should load existing history."""
    # Create a conversation with messages via first WS session
    with client.websocket_connect("/api/chat/ws") as ws:
        ws.send_text("initial message")
        while True:
            data = ws.receive_text()
            try:
                parsed = json.loads(data)
                if parsed.get("type") == "end":
                    conv_id = parsed["conversation_id"]
                    break
            except json.JSONDecodeError:
                continue

    # Connect again referencing the same conversation
    with client.websocket_connect("/api/chat/ws") as ws:
        ws.send_text(json.dumps({"content": "continuing", "conversation_id": conv_id}))
        while True:
            data = ws.receive_text()
            try:
                parsed = json.loads(data)
                if parsed.get("type") == "end":
                    assert parsed["conversation_id"] == conv_id
                    break
            except json.JSONDecodeError:
                continue

    # Should have 4 messages total
    with Session(test_engine) as session:
        messages = session.exec(
            select(ChatMessage).where(ChatMessage.conversation_id == conv_id)
        ).all()
        assert len(messages) == 4
