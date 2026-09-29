"""Request-scoped accessors for application-owned services."""

from fastapi import Request, WebSocket

from backend.services import Services


def services_from(request: Request) -> Services:
    return request.app.state.services


def websocket_services(websocket: WebSocket) -> Services:
    return websocket.app.state.services
