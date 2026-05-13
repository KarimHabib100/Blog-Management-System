# Blog Management System

A RESTful backend for a blogging platform built with **FastAPI**, **SQLAlchemy**, **Redis**, and **JWT authentication**.

## Features

- Full CRUD for posts and comments
- Role-based access control: **Admin**, **Author**, **Reader**
- JWT authentication (register → login → protected routes)
- Nested comments (replies to comments)
- Pagination for posts and comments
- Redis caching with cache-aside pattern
- Structured logging with loguru
- Monitoring dashboard at `/dashboard`
- pytest test suite
- Dockerized with docker-compose (FastAPI + PostgreSQL + Redis)
- Simple HTML/JS frontend at `/app`

---

## Team Members

| Member | Responsibility | Files |
|--------|---------------|-------|
| **Karim Habib** | Project Lead & Infrastructure | `app/main.py`, `app/config.py`, `app/database.py`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `.env.example` |
| **Mohamed Ahmed** | Authentication & Security | `app/routers/auth.py`, `app/core/security.py`, `app/core/dependencies.py`, `tests/test_auth.py` |
| **Farida Wagdy** | User Management | `app/models/user.py`, `app/routers/users.py`, `app/schemas/` (user schemas) |
| **Rana Ashraf** | Posts Feature | `app/models/post.py`, `app/routers/posts.py`, `app/schemas/` (post schemas), `tests/test_posts.py` |
| **Menna Mamdouh** | Comments & Nested Replies | `app/models/comment.py`, `app/routers/comments.py`, `app/schemas/` (comment schemas), `tests/test_comments.py` |
| **Malak Hassan** | Caching, Monitoring & Frontend | `app/cache/redis_cache.py`, `app/monitoring/metrics.py`, `frontend/index.html`, `frontend/dashboard.html`, `tests/conftest.py` |

---

## Project Structure

```
blog_management/
├── app/
│   ├── main.py          # App factory, middleware, routes
│   ├── config.py        # Settings (env vars)
│   ├── database.py      # SQLAlchemy engine & session
│   ├── models/          # ORM models: User, Post, Comment
│   ├── schemas/         # Pydantic request/response schemas
│   ├── routers/         # Route handlers: auth, users, posts, comments
│   ├── core/            # JWT security, auth dependencies
│   ├── cache/           # Redis client and helpers
│   └── monitoring/      # Metrics recording and retrieval
├── tests/               # pytest test suite
├── frontend/            # HTML/JS blog app + monitoring dashboard
├── logs/                # Log files (auto-created)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Running Locally

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up environment

```bash
cp .env.example .env
# Edit .env if needed (defaults use SQLite + localhost Redis)
```

### 3. Start the server

```bash
uvicorn app.main:app --reload
```

The API will be at `http://localhost:8000`.

- Swagger docs: `http://localhost:8000/docs`
- Blog frontend: `http://localhost:8000/app`
- Monitoring dashboard: `http://localhost:8000/dashboard`

> Redis is optional — if it's not running, caching is silently disabled.

---

## Running with Docker

```bash
docker-compose up --build
```

This starts the FastAPI app, PostgreSQL, and Redis together.

---

## Running Tests

```bash
pytest tests/ -v
```

Tests use an in-memory SQLite database and do not require Redis or a running server.

---

## API Overview

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register a new user |
| POST | `/auth/login` | Login — returns JWT token |

### Posts

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/posts/` | No | List posts (paginated) |
| GET | `/posts/{id}` | No | Get a single post |
| POST | `/posts/` | Author/Admin | Create a post |
| PUT | `/posts/{id}` | Author (own) / Admin | Update a post |
| DELETE | `/posts/{id}` | Author (own) / Admin | Delete a post |

### Comments

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/posts/{id}/comments/` | No | List comments (nested, paginated) |
| POST | `/posts/{id}/comments/` | Any user | Add a comment or reply |
| PUT | `/posts/{id}/comments/{cid}` | Owner / Admin | Edit a comment |
| DELETE | `/posts/{id}/comments/{cid}` | Owner / Admin | Delete a comment |

### Users

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/users/me` | Any user | Get own profile |
| PUT | `/users/me` | Any user | Update own profile |
| GET | `/users/` | Admin | List all users |
| PUT | `/users/{id}` | Admin | Update any user |
| DELETE | `/users/{id}` | Admin | Delete a user |

---

## Roles

| Role | Can Write Posts | Can Comment | Can Delete Others' Content |
|------|----------------|-------------|---------------------------|
| Admin | ✅ | ✅ | ✅ |
| Author | ✅ | ✅ | Own only |
| Reader | ❌ | ✅ | Own only |

---

## Caching

Redis caching uses the **cache-aside** pattern:
- Cache is checked first on GET requests
- On create/update/delete, affected cache keys are invalidated
- If Redis is unavailable, the app falls back to hitting the database directly

Cache keys:
- `posts:p{page}:n{per_page}` — paginated post lists
- `post:{id}` — individual posts
- `comments:post:{id}:p{page}:n{per_page}` — comment trees

---

## Monitoring

Visit `/dashboard` for a live monitoring dashboard showing:
- Total request count and average response time
- Error rate and total errors
- Per-endpoint request breakdown (chart + table)
- Last 10 error log entries

The dashboard auto-refreshes every 30 seconds. Metrics are stored in Redis.
