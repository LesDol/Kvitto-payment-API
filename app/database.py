from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


def build_engine(url: str):
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    return create_engine(url, **kwargs)


engine = build_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
