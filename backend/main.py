"""
Agent Lighthouse - Multi-Agent Observability Backend

A framework-agnostic visual debugger for multi-agent AI systems.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.redis_service import RedisService
from services.connection_manager import ConnectionManager
from routers import traces_router, agents_router, state_router, websocket_router


# Global instances
redis_service = RedisService(
    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379")
)
connection_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - connect/disconnect Redis"""
    # Startup
    await redis_service.connect()
    print("✓ Connected to Redis")
    yield
    # Shutdown
    await redis_service.disconnect()
    print("✓ Disconnected from Redis")


# Create FastAPI app
app = FastAPI(
    title="Agent Lighthouse",
    description="Multi-Agent Observability Dashboard - A visual debugger for agentic AI systems",
    version="0.1.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
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
