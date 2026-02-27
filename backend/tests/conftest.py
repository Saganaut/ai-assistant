"""Shared test fixtures for backend tests."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.database import get_session

# In-memory SQLite with StaticPool so all connections (including threads) share one DB
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def get_test_session():
    with Session(test_engine) as session:
        yield session


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create all tables before each test, drop after."""
    import app.models  # noqa: F401 - register models
    SQLModel.metadata.create_all(test_engine)
    yield
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture
def mock_agent():
    """Mock Agent that yields fake tokens."""
    async def fake_run(messages):
        for token in ["Hello", " from", " agent"]:
            yield token

    agent_instance = AsyncMock()
    agent_instance.run = fake_run
    return agent_instance


async def noop_scheduler():
    """No-op replacement for scheduler_loop."""
    return


@pytest.fixture
def client(mock_agent):
    """FastAPI TestClient with all external deps patched."""
    with (
        patch("app.core.database.engine", test_engine),
        patch("app.api.chat.engine", test_engine),
        patch("app.api.chat.Agent", return_value=mock_agent),
        patch("app.services.scheduler.scheduler.scheduler_loop", noop_scheduler),
    ):
        from app.main import app

        # Use FastAPI's dependency override for get_session
        app.dependency_overrides[get_session] = get_test_session

        with TestClient(app) as c:
            yield c

        app.dependency_overrides.clear()
