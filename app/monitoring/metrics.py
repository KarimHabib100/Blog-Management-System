import json
from datetime import datetime
from loguru import logger
from app.cache.redis_cache import get_redis

METRICS_KEY = "blog:metrics"
ERRORS_KEY = "blog:recent_errors"
MAX_ERRORS = 50


def record_request(method: str, path: str, status_code: int, duration_ms: float) -> None:
    r = get_redis()
    if not r:
        return
    try:
        r.hincrby(METRICS_KEY, "total_requests", 1)
        r.hincrbyfloat(METRICS_KEY, "total_duration_ms", duration_ms)
        if status_code >= 400:
            r.hincrby(METRICS_KEY, "total_errors", 1)
        # per-endpoint counter
        r.hincrby(METRICS_KEY, f"ep:{method}:{path}", 1)
    except Exception as e:
        logger.error(f"Metrics record error: {e}")


def record_error(method: str, path: str, status_code: int, detail: str) -> None:
    r = get_redis()
    if not r:
        return
    try:
        entry = json.dumps({
            "time": datetime.utcnow().isoformat(timespec="seconds"),
            "method": method,
            "path": path,
            "status": status_code,
            "detail": detail,
        })
        r.lpush(ERRORS_KEY, entry)
        r.ltrim(ERRORS_KEY, 0, MAX_ERRORS - 1)
    except Exception as e:
        logger.error(f"Error log record error: {e}")


def get_metrics() -> dict:
    r = get_redis()
    if not r:
        return {"available": False, "message": "Redis not connected"}

    try:
        raw = r.hgetall(METRICS_KEY)
        total_req = int(raw.get("total_requests", 0))
        total_err = int(raw.get("total_errors", 0))
        total_dur = float(raw.get("total_duration_ms", 0.0))

        avg_ms = round(total_dur / total_req, 2) if total_req else 0.0
        error_rate = round((total_err / total_req) * 100, 2) if total_req else 0.0

        endpoints = {
            k.replace("ep:", ""): int(v)
            for k, v in raw.items()
            if k.startswith("ep:")
        }

        recent_errors = [json.loads(e) for e in r.lrange(ERRORS_KEY, 0, 9)]

        return {
            "available": True,
            "total_requests": total_req,
            "total_errors": total_err,
            "error_rate_percent": error_rate,
            "avg_response_time_ms": avg_ms,
            "endpoints": endpoints,
            "recent_errors": recent_errors,
            "health": "healthy",
        }
    except Exception as e:
        logger.error(f"get_metrics error: {e}")
        return {"available": False, "message": str(e)}
