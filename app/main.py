import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.config import settings
from app.database import create_tables
import app.models  # registers all ORM models before create_tables()
from app.routers import auth, users, posts, comments
from app.monitoring.metrics import record_request, record_error, get_metrics


# ── Logging setup ─────────────────────────────────────────────────────────────

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
    level="INFO",
    colorize=True,
)
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    level="DEBUG",
)


# ── App lifecycle ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name}")
    create_tables()
    logger.info("Database tables ready")
    yield
    logger.info("Shutting down")


# ── App instance ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    description="RESTful API for a blog platform with posts, comments, and role-based access.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging + metrics middleware ───────────────────────────────────────

@app.middleware("http")
async def log_and_track(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000

    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} "
        f"({duration_ms:.1f}ms)"
    )

    record_request(request.method, request.url.path, response.status_code, duration_ms)

    if response.status_code >= 400:
        record_error(request.method, request.url.path, response.status_code, "")

    return response


# ── Routers ────────────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)
app.include_router(comments.router)


# ── Static files (frontend) ────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="frontend"), name="static")


# ── Utility routes ─────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"], include_in_schema=False)
def root():
    return {"status": "running", "docs": "/docs", "app": settings.app_name}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "app": settings.app_name}


@app.get("/api/metrics", tags=["Monitoring"])
def get_app_metrics():
    """Returns request counts, response times, error rate, and recent errors."""
    return get_metrics()


@app.get("/dashboard", response_class=HTMLResponse, tags=["Monitoring"], include_in_schema=False)
def monitoring_dashboard():
    with open("frontend/dashboard.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/app", response_class=HTMLResponse, include_in_schema=False)
def blog_app():
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return f.read()
