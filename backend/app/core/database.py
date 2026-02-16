from sqlmodel import SQLModel, create_engine, Session

from app.core.config import settings

engine = create_engine(f"sqlite:///{settings.db_path}", echo=settings.debug)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
