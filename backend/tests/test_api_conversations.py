"""Tests for conversation CRUD endpoints."""

from sqlmodel import Session

from tests.conftest import test_engine
from app.models.conversation import ChatMessage, Conversation


def _seed_conversation(title="Test Chat", messages=None):
    """Insert a conversation + messages directly into the test DB."""
    with Session(test_engine) as session:
        conv = Conversation(title=title)
        session.add(conv)
        session.commit()
        session.refresh(conv)

        if messages:
            for role, content in messages:
                msg = ChatMessage(conversation_id=conv.id, role=role, content=content)
                session.add(msg)
            session.commit()

        session.refresh(conv)
        return conv.id


def test_list_conversations_empty(client):
    response = client.get("/api/conversations/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_conversations(client):
    _seed_conversation("Chat A")
    _seed_conversation("Chat B")
    response = client.get("/api/conversations/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    titles = {c["title"] for c in data}
    assert titles == {"Chat A", "Chat B"}


def test_get_conversation(client):
    cid = _seed_conversation("My Chat", [("user", "hello"), ("assistant", "hi there")])
    response = client.get(f"/api/conversations/{cid}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "My Chat"
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["content"] == "hello"
    assert data["messages"][1]["role"] == "assistant"


def test_get_conversation_not_found(client):
    response = client.get("/api/conversations/9999")
    assert response.status_code == 404


def test_delete_conversation(client):
    cid = _seed_conversation("To Delete", [("user", "bye")])
    response = client.delete(f"/api/conversations/{cid}")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

    # Verify it's gone
    response = client.get(f"/api/conversations/{cid}")
    assert response.status_code == 404


def test_delete_conversation_not_found(client):
    response = client.delete("/api/conversations/9999")
    assert response.status_code == 404
