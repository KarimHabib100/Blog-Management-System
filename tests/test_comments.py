"""Tests for comment CRUD — creation, nested replies, editing, deletion."""


def test_create_comment(client, reader_token, sample_post):
    post_id = sample_post["id"]
    res = client.post(
        f"/posts/{post_id}/comments/",
        json={"content": "Great post!"},
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["content"] == "Great post!"
    assert data["parent_id"] is None


def test_create_nested_reply(client, reader_token, sample_post):
    post_id = sample_post["id"]

    parent = client.post(
        f"/posts/{post_id}/comments/",
        json={"content": "Parent comment"},
        headers={"Authorization": f"Bearer {reader_token}"},
    ).json()

    reply = client.post(
        f"/posts/{post_id}/comments/",
        json={"content": "This is a reply", "parent_id": parent["id"]},
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert reply.status_code == 201
    assert reply.json()["parent_id"] == parent["id"]


def test_reply_to_nonexistent_comment(client, reader_token, sample_post):
    post_id = sample_post["id"]
    res = client.post(
        f"/posts/{post_id}/comments/",
        json={"content": "orphan", "parent_id": 9999},
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert res.status_code == 404


def test_comment_on_nonexistent_post(client, reader_token):
    res = client.post(
        "/posts/9999/comments/",
        json={"content": "ghost comment"},
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert res.status_code == 404


def test_get_comments_with_nested_replies(client, reader_token, sample_post):
    post_id = sample_post["id"]

    parent = client.post(
        f"/posts/{post_id}/comments/",
        json={"content": "Root comment"},
        headers={"Authorization": f"Bearer {reader_token}"},
    ).json()

    client.post(
        f"/posts/{post_id}/comments/",
        json={"content": "First reply", "parent_id": parent["id"]},
        headers={"Authorization": f"Bearer {reader_token}"},
    )

    res = client.get(f"/posts/{post_id}/comments/")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1

    root = next(c for c in data["comments"] if c["id"] == parent["id"])
    assert len(root["replies"]) == 1
    assert root["replies"][0]["content"] == "First reply"


def test_comment_requires_auth(client, sample_post):
    res = client.post(
        f"/posts/{sample_post['id']}/comments/",
        json={"content": "no auth"},
    )
    assert res.status_code == 401


def test_update_own_comment(client, reader_token, sample_post):
    post_id = sample_post["id"]
    comment = client.post(
        f"/posts/{post_id}/comments/",
        json={"content": "original"},
        headers={"Authorization": f"Bearer {reader_token}"},
    ).json()

    res = client.put(
        f"/posts/{post_id}/comments/{comment['id']}",
        json={"content": "edited"},
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert res.status_code == 200
    assert res.json()["content"] == "edited"


def test_update_other_users_comment_blocked(client, author_token, reader_token, sample_post):
    post_id = sample_post["id"]
    comment = client.post(
        f"/posts/{post_id}/comments/",
        json={"content": "reader wrote this"},
        headers={"Authorization": f"Bearer {reader_token}"},
    ).json()

    # author tries to edit reader's comment
    res = client.put(
        f"/posts/{post_id}/comments/{comment['id']}",
        json={"content": "author edited this"},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert res.status_code == 403


def test_admin_can_delete_any_comment(client, admin_token, reader_token, sample_post):
    post_id = sample_post["id"]
    comment = client.post(
        f"/posts/{post_id}/comments/",
        json={"content": "to be removed by admin"},
        headers={"Authorization": f"Bearer {reader_token}"},
    ).json()

    res = client.delete(
        f"/posts/{post_id}/comments/{comment['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 204


def test_comment_pagination(client, reader_token, sample_post):
    post_id = sample_post["id"]
    for i in range(5):
        client.post(
            f"/posts/{post_id}/comments/",
            json={"content": f"comment {i}"},
            headers={"Authorization": f"Bearer {reader_token}"},
        )

    res = client.get(f"/posts/{post_id}/comments/?page=1&per_page=3")
    data = res.json()
    assert data["total"] == 5
    assert len(data["comments"]) == 3
