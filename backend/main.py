"""
Agent Lighthouse - Multi-Agent Observability Backend

A framework-agnostic visual debugger for multi-agent AI systems.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from services.redis_service import RedisService
from services.connection_manager import ConnectionManager
from routers import traces_router, agents_router, state_router, websocket_router

logger = logging.getLogger(__name__)
settings = get_settings()
if settings.require_auth and settings.api_key == "change-me-in-production":
    logger.warning("Using default LIGHTHOUSE_API_KEY value; set a strong key before production deployment.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - connect/disconnect Redis"""
    redis_service = RedisService(
        redis_url=settings.redis_url,
        trace_ttl_hours=settings.trace_ttl_hours,
    )
    connection_manager = ConnectionManager()
    app.state.redis_service = redis_service
    app.state.connection_manager = connection_manager
    app.state.settings = settings

    # Startup
    await redis_service.connect()
    logger.info("Connected to Redis")
    yield

    # Shutdown
    await redis_service.disconnect()
    logger.info("Disconnected from Redis")


# Create FastAPI app
app = FastAPI(
    title="Agent Lighthouse",
    description="Multi-Agent Observability Dashboard - A visual debugger for agentic AI systems",
    version="0.1.0",
    lifespan=lifespan
)

# CORS configuration
allow_credentials = settings.cors_allow_credentials and "*" not in settings.allowed_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(traces_router)
app.include_router(agents_router)
app.include_router(state_router)
app.include_router(websocket_router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "name": "Agent Lighthouse",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    redis_service = app.state.redis_service
    connection_manager = app.state.connection_manager
    redis_connected = redis_service.redis is not None
    return {
        "status": "healthy" if redis_connected else "degraded",
        "redis": "connected" if redis_connected else "disconnected",
        "websocket_connections": len(connection_manager.active_connections)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
