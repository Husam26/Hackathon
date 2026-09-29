"""FastAPI application factory and lifecycle ownership."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.api import router
from backend.config import Settings, get_settings
from backend.resilience import ProviderUnavailableError
from backend.services import build_services


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create a fully-wired application without global mutable service state."""
    resolved = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        services = build_services(resolved)
        app.state.services = services
        try:
            yield
        finally:
            await services.close()

    app = FastAPI(
        title=resolved.app_name,
        version=resolved.app_version,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ProviderUnavailableError)
    async def provider_unavailable(
        request: Request, exc: ProviderUnavailableError
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    app.include_router(router)
    return app
