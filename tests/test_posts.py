"""Tests for post CRUD — creation, retrieval, update, delete, and pagination."""


def test_get_posts_empty(client):
    res = client.get("/posts/")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["posts"] == []


def test_create_post_as_author(client, author_token):
    res = client.post(
        "/posts/",
        json={"title": "My First Post", "content": "Hello world!"},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "My First Post"
    assert data["author"]["username"] == "author_user"


def test_create_post_as_reader_is_forbidden(client, reader_token):
    res = client.post(
        "/posts/",
        json={"title": "Trying to post", "content": "Should not work"},
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert res.status_code == 403


def test_create_post_unauthenticated(client):
    res = client.post("/posts/", json={"title": "No auth", "content": "..."})
    assert res.status_code == 401


def test_create_post_empty_title(client, author_token):
    res = client.post(
        "/posts/",
        json={"title": "   ", "content": "valid content"},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert res.status_code == 422


def test_get_single_post(client, sample_post):
    post_id = sample_post["id"]
    res = client.get(f"/posts/{post_id}")
    assert res.status_code == 200
    assert res.json()["id"] == post_id


def test_get_nonexistent_post(client):
    res = client.get("/posts/9999")
    assert res.status_code == 404


def test_update_own_post(client, author_token, sample_post):
    post_id = sample_post["id"]
    res = client.put(
        f"/posts/{post_id}",
        json={"title": "Updated Title"},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert res.status_code == 200
    assert res.json()["title"] == "Updated Title"


def test_update_other_users_post_is_forbidden(client, reader_token, sample_post):
    post_id = sample_post["id"]
    res = client.put(
        f"/posts/{post_id}",
        json={"title": "Hacked!"},
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert res.status_code == 403


def test_admin_can_update_any_post(client, admin_token, sample_post):
    post_id = sample_post["id"]
    res = client.put(
        f"/posts/{post_id}",
        json={"content": "Admin edited this."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    assert "Admin edited" in res.json()["content"]


def test_delete_own_post(client, author_token):
    post = client.post(
        "/posts/",
        json={"title": "To be deleted", "content": "bye"},
        headers={"Authorization": f"Bearer {author_token}"},
    ).json()

    res = client.delete(
        f"/posts/{post['id']}",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert res.status_code == 204

    # make sure it's gone
    assert client.get(f"/posts/{post['id']}").status_code == 404


def test_reader_cannot_delete_post(client, reader_token, sample_post):
    res = client.delete(
        f"/posts/{sample_post['id']}",
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert res.status_code == 403


def test_admin_can_delete_any_post(client, admin_token, sample_post):
    res = client.delete(
        f"/posts/{sample_post['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 204


def test_pagination(client, author_token):
    for i in range(5):
        client.post(
            "/posts/",
            json={"title": f"Post {i}", "content": "content"},
            headers={"Authorization": f"Bearer {author_token}"},
        )

    res = client.get("/posts/?page=1&per_page=3")
    data = res.json()
    assert data["total"] == 5
    assert len(data["posts"]) == 3

    res2 = client.get("/posts/?page=2&per_page=3")
    data2 = res2.json()
    assert len(data2["posts"]) == 2
