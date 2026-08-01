"""
Aegis Dashboard API - Main application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import websocket
from .api.v1 import audit, auth, escalations, ingest, metrics, policies
from .config import get_settings
from .database import close_db, init_db
from .redis_client import close_redis

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()
    await close_redis()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Aegis Cloud Dashboard API for policy enforcement observability",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(ingest.router, prefix="/api/v1", tags=["Ingestion"])
app.include_router(audit.router, prefix="/api/v1", tags=["Audit"])
app.include_router(policies.router, prefix="/api/v1", tags=["Policies"])
app.include_router(metrics.router, prefix="/api/v1", tags=["Metrics"])
app.include_router(escalations.router, prefix="/api/v1", tags=["Escalations"])
app.include_router(websocket.router, tags=["WebSocket"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
