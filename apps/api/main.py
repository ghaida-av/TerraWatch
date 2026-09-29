"""TerraWatch FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.config import settings
from apps.api.routes.evidence import router as evidence_router
from apps.api.routes.health import router as health_router
from apps.api.routes.investigations import router as investigations_router
from apps.api.storage import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context for startup and shutdown events."""
    # Ensure SQLite tables exist
    init_db()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="TerraWatch Environmental Crisis Intelligence API",
        description=(
            "Autonomous multi-source environmental intelligence engine. Connects normalized "
            "environmental observations, deterministic geospatial risk math, and evidence graphs."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # Cross-Origin Resource Sharing (CORS) for Person 5 frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API Routers
    app.include_router(health_router, prefix="/api")
    app.include_router(investigations_router, prefix="/api")
    app.include_router(evidence_router, prefix="/api")

    # Convenience root health redirect / endpoint
    @app.get("/", tags=["Root"])
    def root():
        return {
            "name": "TerraWatch API",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/api/health",
        }

    return app


app = create_app()
