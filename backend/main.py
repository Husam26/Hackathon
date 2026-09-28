"""FastAPI entrypoint for Sentinel."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware

from backend.config import Settings, get_settings
from backend.demo import DemoController, DemoStepResult
from backend.gemini_client import FallbackAnalyzer, GeminiAnalyzer
from backend.groq_client import GroqAnalyzer, IncidentAnalyzer, RulesAnalyzer
from backend.memory_client import (
    HindsightMemoryClient,
    LocalMemoryClient,
    MemoryProvider,
)
from backend.orchestrator import SentinelOrchestrator
from backend.schemas import Alert, AnalysisResult, HealthResponse, IncidentRecord
from backend.store import IncidentStore


@dataclass
class Services:
    settings: Settings
    memory: MemoryProvider
    analyzer: IncidentAnalyzer
    store: IncidentStore
    orchestrator: SentinelOrchestrator
    demo: DemoController


def build_services(settings: Settings) -> Services:
    memory: MemoryProvider
    if settings.hindsight_api_key or settings.hindsight_base_url.startswith(
        "http://localhost"
    ):
        memory = HindsightMemoryClient(
            base_url=settings.hindsight_base_url,
            bank_id=settings.hindsight_bank_id,
            api_key=settings.hindsight_api_key,
            timeout=settings.request_timeout_seconds,
        )
    else:
        memory = LocalMemoryClient()
    groq = (
        GroqAnalyzer(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            base_url=settings.groq_base_url,
            timeout=settings.request_timeout_seconds,
        )
        if settings.groq_api_key
        else None
    )
    gemini = (
        GeminiAnalyzer(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            base_url=settings.gemini_base_url,
            timeout=settings.request_timeout_seconds,
        )
        if settings.gemini_api_key
        else None
    )
    if groq and gemini:
        analyzer: IncidentAnalyzer = FallbackAnalyzer(groq, gemini)
    elif groq:
        analyzer = groq
    elif gemini:
        analyzer = gemini
    else:
        analyzer = RulesAnalyzer()
    store = IncidentStore(settings.database_url)
    store.create()
    orchestrator = SentinelOrchestrator(
        memory, analyzer, store, settings.hindsight_mental_model_id
    )
    return Services(
        settings, memory, analyzer, store, orchestrator, DemoController(orchestrator)
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.services = build_services(resolved)
        yield
        await app.state.services.memory.close()
        await app.state.services.analyzer.close()

    app = FastAPI(
        title=resolved.app_name, version=resolved.app_version, lifespan=lifespan
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthResponse)
    async def health(request: Request) -> HealthResponse:
        services: Services = request.app.state.services
        return HealthResponse(
            status="ok",
            version=services.settings.app_version,
            providers={
                "memory": services.memory.name,
                "analysis": services.analyzer.name,
            },
        )

    @app.post("/api/analyze", response_model=AnalysisResult)
    async def analyze(alert: Alert, request: Request) -> AnalysisResult:
        return await request.app.state.services.orchestrator.analyze(alert)

    @app.post("/api/incidents", status_code=status.HTTP_201_CREATED)
    async def resolve(incident: IncidentRecord, request: Request) -> dict[str, str]:
        memory_id = await request.app.state.services.orchestrator.resolve(incident)
        return {"incident_id": incident.id, "memory_id": memory_id}

    @app.get("/api/incidents", response_model=list[IncidentRecord])
    async def list_incidents(request: Request) -> list[IncidentRecord]:
        return request.app.state.services.store.list()

    @app.post("/api/demo/reset", status_code=status.HTTP_204_NO_CONTENT)
    async def reset_demo(request: Request) -> None:
        await request.app.state.services.demo.reset()

    @app.post("/api/demo/step", response_model=DemoStepResult)
    async def step_demo(request: Request) -> DemoStepResult:
        try:
            return await request.app.state.services.demo.step()
        except IndexError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.websocket("/ws/analyze")
    async def analyze_socket(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                alert = Alert.model_validate(await websocket.receive_json())
                await websocket.send_json(
                    {"event": "status", "message": "Recalling incident memory"}
                )
                result = await websocket.app.state.services.orchestrator.analyze(alert)
                await websocket.send_json(
                    {"event": "analysis", "data": result.model_dump(mode="json")}
                )
        except WebSocketDisconnect:
            return

    return app


app = create_app()
