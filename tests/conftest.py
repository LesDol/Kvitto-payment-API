import pytest
from fastapi.testclient import TestClient

from app.database import Base, build_engine, get_session
from app.main import app
from app.services import seed_tariffs
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = build_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr("app.main.engine", engine)
    monkeypatch.setattr("app.main.SessionLocal", TestingSession)
    monkeypatch.setattr("app.database.SessionLocal", TestingSession)

    def override_session():
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestingSession() as session:
        seed_tariffs(session)
    with TestClient(app) as test_client:
        yield test_client, TestingSession
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def payload(**overrides):
    data = {"tariff_id": 1, "email": "person@example.com", "method": "card"}
    data.update(overrides)
    return data
