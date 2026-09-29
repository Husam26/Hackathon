"""WebSocket delivery endpoint for interactive alert analysis."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.http.dependencies import websocket_services
from backend.schemas import Alert


router = APIRouter()


@router.websocket("/ws/analyze")
async def analyze_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            alert = Alert.model_validate(await websocket.receive_json())
            await websocket.send_json(
                {"event": "status", "message": "Recalling incident memory"}
            )
            result = await websocket_services(websocket).orchestrator.analyze(alert)
            await websocket.send_json(
                {"event": "analysis", "data": result.model_dump(mode="json")}
            )
    except WebSocketDisconnect:
        return
