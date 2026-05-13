"""Tests for authentication — registration, login, token validation."""


def test_register_success(client):
    res = client.post("/auth/register", json={
        "username": "alice",
        "email": "alice@example.com",
        "password": "password123",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["username"] == "alice"
    assert data["role"] == "reader"  # default role
    assert "hashed_password" not in data


def test_register_default_role_is_reader(client):
    res = client.post("/auth/register", json={
        "username": "bob",
        "email": "bob@example.com",
        "password": "password123",
    })
    assert res.json()["role"] == "reader"


def test_register_as_author(client):
    res = client.post("/auth/register", json={
        "username": "charlie",
        "email": "charlie@example.com",
        "password": "password123",
        "role": "author",
    })
    assert res.status_code == 201
    assert res.json()["role"] == "author"


def test_register_duplicate_username(client):
    client.post("/auth/register", json={
        "username": "dave",
        "email": "dave@example.com",
        "password": "password123",
    })
    res = client.post("/auth/register", json={
        "username": "dave",
        "email": "other@example.com",
        "password": "password123",
    })
    assert res.status_code == 400


def test_register_duplicate_email(client):
    client.post("/auth/register", json={
        "username": "eve1",
        "email": "eve@example.com",
        "password": "password123",
    })
    res = client.post("/auth/register", json={
        "username": "eve2",
        "email": "eve@example.com",
        "password": "password123",
    })
    assert res.status_code == 400


def test_register_short_password(client):
    res = client.post("/auth/register", json={
        "username": "frank",
        "email": "frank@example.com",
        "password": "abc",
    })
    assert res.status_code == 422


def test_login_success(client):
    client.post("/auth/register", json={
        "username": "grace",
        "email": "grace@example.com",
        "password": "password123",
    })
    res = client.post("/auth/login", data={"username": "grace", "password": "password123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    client.post("/auth/register", json={
        "username": "harry",
        "email": "harry@example.com",
        "password": "correctpassword",
    })
    res = client.post("/auth/login", data={"username": "harry", "password": "wrongpassword"})
    assert res.status_code == 401


def test_login_unknown_user(client):
    res = client.post("/auth/login", data={"username": "nobody", "password": "pass"})
    assert res.status_code == 401


def test_protected_route_requires_token(client):
    res = client.get("/users/me")
    assert res.status_code == 401


def test_protected_route_with_valid_token(client, reader_token):
    res = client.get("/users/me", headers={"Authorization": f"Bearer {reader_token}"})
    assert res.status_code == 200
    assert res.json()["username"] == "reader_user"


def test_protected_route_with_bad_token(client):
    res = client.get("/users/me", headers={"Authorization": "Bearer this.is.fake"})
    assert res.status_code == 401


def test_admin_route_blocked_for_reader(client, reader_token):
    res = client.get("/users/", headers={"Authorization": f"Bearer {reader_token}"})
    assert res.status_code == 403


def test_admin_route_accessible_for_admin(client, admin_token):
    res = client.get("/users/", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
