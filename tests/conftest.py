import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db

TEST_DB_URL = "sqlite:///./test_blog.db"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Reusable token fixtures ────────────────────────────────────────────────────

@pytest.fixture
def admin_token(client):
    client.post("/auth/register", json={
        "username": "admin_user",
        "email": "admin@test.com",
        "password": "adminpass",
        "role": "admin",
    })
    res = client.post("/auth/login", data={"username": "admin_user", "password": "adminpass"})
    return res.json()["access_token"]


@pytest.fixture
def author_token(client):
    client.post("/auth/register", json={
        "username": "author_user",
        "email": "author@test.com",
        "password": "authorpass",
        "role": "author",
    })
    res = client.post("/auth/login", data={"username": "author_user", "password": "authorpass"})
    return res.json()["access_token"]


@pytest.fixture
def reader_token(client):
    client.post("/auth/register", json={
        "username": "reader_user",
        "email": "reader@test.com",
        "password": "readerpass",
        "role": "reader",
    })
    res = client.post("/auth/login", data={"username": "reader_user", "password": "readerpass"})
    return res.json()["access_token"]


@pytest.fixture
def sample_post(client, author_token):
    """Create a post and return its data."""
    res = client.post(
        "/posts/",
        json={"title": "Test Post", "content": "Some content here."},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    return res.json()
