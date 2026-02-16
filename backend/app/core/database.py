from sqlmodel import SQLModel, create_engine, Session

from app.core.config import settings

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    echo=settings.debug,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    import app.models  # noqa: F401 - ensure models are registered
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
