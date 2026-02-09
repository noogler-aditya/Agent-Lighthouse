"""
Agent Lighthouse - Multi-Agent Observability Backend
"""
from __future__ import annotations

import contextvars
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routers import agents_router, auth_router, state_router, traces_router, websocket_router
from security import auth_health
from services.connection_manager import ConnectionManager
from services.redis_service import RedisService

request_id_ctx = contextvars.ContextVar("request_id", default="-")
logger = logging.getLogger("agent_lighthouse")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

settings = get_settings()


def _validate_security_defaults():
    if settings.require_auth and settings.jwt_secret_uses_default:
        if settings.is_production:
            raise RuntimeError("JWT_SECRET must be configured in production")
        logger.warning("Using default JWT_SECRET; set a strong value before production")

    if settings.require_auth and not settings.allowed_origins_list:
        raise RuntimeError("ALLOWED_ORIGINS cannot be empty when authentication is enabled")

    if settings.is_production and ("*" in settings.allowed_origins_list):
        raise RuntimeError("Wildcard ALLOWED_ORIGINS is not allowed in production")


_validate_security_defaults()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - connect/disconnect Redis and run readiness gates."""
    redis_service = RedisService(
        redis_url=settings.redis_url,
        trace_ttl_hours=settings.trace_ttl_hours,
    )
    connection_manager = ConnectionManager()

    app.state.redis_service = redis_service
    app.state.connection_manager = connection_manager
    app.state.settings = settings
    app.state.started_at = datetime.now(timezone.utc)

    await redis_service.connect()
    await redis_service.verify_persistence_policy(
        required_appendonly=settings.redis_required_appendonly,
        required_save=settings.redis_required_save,
        enforce=settings.redis_enforce_persistence_policy and settings.is_production,
    )
    logger.info("Connected to Redis")

    yield

    await redis_service.disconnect()
    logger.info("Disconnected from Redis")


app = FastAPI(
    title="Agent Lighthouse",
    description="Multi-Agent Observability Dashboard - visual debugger for agentic AI systems",
    version="0.2.0",
    lifespan=lifespan,
)

allow_credentials = settings.cors_allow_credentials and "*" not in settings.allowed_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    token = request_id_ctx.set(request_id)
    request.state.request_id = request_id

    started = perf_counter()
    try:
        response = await call_next(request)
        elapsed_ms = round((perf_counter() - started) * 1000, 2)

        principal = getattr(request.state, "principal", None)
        subject = getattr(principal, "subject", "anonymous")
        role = getattr(principal, "role", "-")
        trace_id = request.path_params.get("trace_id") if hasattr(request, "path_params") else None
        logger.info(
            "request_id=%s method=%s path=%s status=%s latency_ms=%s subject=%s role=%s trace_id=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            subject,
            role,
            trace_id or "-",
        )
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        request_id_ctx.reset(token)


app.include_router(auth_router)
app.include_router(traces_router)
app.include_router(agents_router)
app.include_router(state_router)
app.include_router(websocket_router)


@app.get("/")
async def root():
    return {
        "name": "Agent Lighthouse",
        "version": "0.2.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health/live")
async def health_live(request: Request):
    return {
        "status": "alive",
        "build_version": settings.build_version,
        "request_id": request.state.request_id,
    }


@app.get("/health/ready")
async def health_ready(request: Request, response: Response):
    redis_service = app.state.redis_service
    redis_ready = await redis_service.is_ready()
    auth_info = auth_health(settings)
    auth_ready = not settings.require_auth or not auth_info["unsafe_defaults"]

    status_value = "ready" if (redis_ready and auth_ready) else "not_ready"
    if status_value != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": status_value,
        "request_id": request.state.request_id,
        "dependencies": {
            "redis": {"ready": redis_ready, "url": settings.redis_url},
            "auth": {"ready": auth_ready, **auth_info},
        },
        "build_version": settings.build_version,
    }


@app.get("/health")
async def health_check(request: Request):
    redis_service = app.state.redis_service
    connection_manager = app.state.connection_manager
    redis_ready = await redis_service.is_ready()
    auth_info = auth_health(settings)

    return {
        "status": "healthy" if redis_ready else "degraded",
        "request_id": request.state.request_id,
        "dependencies": {
            "redis": {
                "ready": redis_ready,
                "url": settings.redis_url,
            },
            "auth": auth_info,
        },
        "websocket_connections": len(connection_manager.active_connections),
        "build_version": settings.build_version,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
