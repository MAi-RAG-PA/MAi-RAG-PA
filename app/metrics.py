# app/metrics.py
"""
Prometheus metrics for MAi-RAG-PA.
Tracks request volume, latency, model usage, and errors.
"""
from time import perf_counter

from fastapi import Request, Response
from prometheus_client import (CONTENT_TYPE_LATEST, Counter, Gauge, Histogram,
                               generate_latest)
from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_COUNT = Counter(
    "mai_rag_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_DURATION = Histogram(
    "mai_rag_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

MODEL_REQUEST_COUNT = Counter(
    "mai_rag_model_requests_total",
    "Total LLM model invocations",
    ["model", "endpoint"],
)

MODEL_DURATION = Histogram(
    "mai_rag_model_duration_seconds",
    "LLM inference duration in seconds",
    ["model"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

ACTIVE_CONNECTIONS = Gauge(
    "mai_rag_active_connections",
    "Number of active WebSocket connections",
)

DATABASE_SIZE_BYTES = Gauge(
    "mai_rag_database_size_bytes",
    "SQLite database file size in bytes",
)


def _normalize_endpoint(path: str) -> str:
    parts = []
    for segment in path.strip("/").split("/"):
        if not segment:
            continue
        if segment.isdigit():
            parts.append(":id")
            continue
        if len(segment) > 8 and all(c in "0123456789abcdef-" for c in segment.lower()):
            parts.append(":id")
            continue
        parts.append(segment)
    return "/" + "/".join(parts) if parts else "/"


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically track request count and duration."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/api/metrics":
            return await call_next(request)

        start_time = perf_counter()
        response = await call_next(request)
        duration = perf_counter() - start_time

        endpoint = _normalize_endpoint(request.url.path)

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status=str(response.status_code),
        ).inc()

        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(duration)

        return response
