"""Compatibility ASGI entrypoint for Uvicorn and existing imports."""

from backend.app_factory import create_app
from backend.services import Services, build_services


app = create_app()


__all__ = ["Services", "app", "build_services", "create_app"]
