"""HTTP and WebSocket delivery layer for Sentinel.

Routes only translate transport input/output. Product policy lives in the
orchestrator, demo controller, integration adapters, and provider ports.
"""

from __future__ import annotations

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from backend.demo import DemoStatus, DemoStepResult
from backend.groq_client import RulesAnalyzer
from backend.integrations import (
    ArtifactLink,
    AzureMonitorWebhook,
    IntegrationLink,
    RunbookVerification,
    RunbookVerificationRequest,
    TeamsExport,
    github_hotfix_link,
    incident_artifact_links,
    teams_export,
)
from backend.incident_runs import IncidentAnalysisRun
from backend.manual_incident import ManualIncidentRequest, build_manual_incident
from backend.memory_preferences import AnalysisRequest, MemoryPreferences
from backend.schemas import Alert, AnalysisResult, HealthResponse, IncidentRecord
from backend.services import Services


router = APIRouter(prefix="/api")


def services_from(request: Request) -> Services:
    """Return the application-scoped dependency graph for an HTTP request."""
    return request.app.state.services


def websocket_services(websocket: WebSocket) -> Services:
    """Return the application-scoped dependency graph for a WebSocket request."""
    return websocket.app.state.services


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health(request: Request) -> HealthResponse:
    services = services_from(request)
    return HealthResponse(
        status="ok",
        version=services.settings.app_version,
        providers={
            "memory": services.memory.name,
            "analysis": services.analyzer.name,
        },
    )


@router.post("/analyze", response_model=AnalysisResult, tags=["analysis"])
async def analyze(alert: Alert, request: Request) -> AnalysisResult:
    return await services_from(request).orchestrator.analyze(alert)


@router.post(
    "/analyze/with-preferences", response_model=AnalysisResult, tags=["analysis"]
)
async def analyze_with_preferences(
    payload: AnalysisRequest, request: Request
) -> AnalysisResult:
    return await services_from(request).orchestrator.analyze(
        payload.alert, payload.memory_preferences
    )


@router.post("/analyze/cold", response_model=AnalysisResult, tags=["analysis"])
async def analyze_cold(alert: Alert) -> AnalysisResult:
    """Run the deterministic no-memory comparison used by the operator console."""
    response = await RulesAnalyzer().analyze(alert, [], None)
    return AnalysisResult(alert=alert, response=response)


@router.post(
    "/integrations/azure-monitor", response_model=AnalysisResult, tags=["integrations"]
)
async def ingest_azure_monitor(
    payload: AzureMonitorWebhook, request: Request
) -> AnalysisResult:
    return await services_from(request).orchestrator.analyze(payload.to_alert())


@router.get(
    "/integrations/github-hotfix/{incident_id}",
    response_model=IntegrationLink,
    tags=["integrations"],
)
async def github_hotfix(incident_id: str, request: Request) -> IntegrationLink:
    return github_hotfix_link(
        incident_id, services_from(request).settings.github_repository_url
    )


@router.post(
    "/integrations/teams-export/{incident_id}",
    response_model=TeamsExport,
    tags=["integrations"],
)
async def export_teams(incident_id: str, analysis: AnalysisResult) -> TeamsExport:
    return teams_export(analysis, incident_id)


@router.post("/runbooks/verify", response_model=RunbookVerification, tags=["runbooks"])
async def verify_runbook(payload: RunbookVerificationRequest) -> RunbookVerification:
    if not payload.confirmed_by_human:
        return RunbookVerification(
            status="confirmation_required",
            message="Human confirmation is required before any external runbook handoff.",
            audit_note=f"No action executed for {payload.incident_id}.",
        )
    return RunbookVerification(
        status="approved_for_handoff",
        message="Approval recorded. Sentinel produced a handoff only; it did not execute production commands.",
        audit_note=f"Approved runbook action: {payload.action} for {payload.incident_id}.",
    )


@router.post("/incidents", status_code=status.HTTP_201_CREATED, tags=["incidents"])
async def resolve(incident: IncidentRecord, request: Request) -> dict[str, str]:
    memory_id = await services_from(request).orchestrator.resolve(incident)
    return {"incident_id": incident.id, "memory_id": memory_id}


@router.post(
    "/incidents/manual",
    response_model=IncidentRecord,
    status_code=status.HTTP_201_CREATED,
    tags=["incidents"],
)
async def create_manual_incident(
    payload: ManualIncidentRequest, request: Request
) -> IncidentRecord:
    incident = build_manual_incident(payload)
    memory_id = await services_from(request).orchestrator.resolve(incident)
    return incident.model_copy(update={"retained_memory_id": memory_id})


@router.post(
    "/incidents/manual/analyze",
    response_model=IncidentAnalysisRun,
    status_code=status.HTTP_201_CREATED,
    tags=["incidents"],
)
async def analyze_manual_incident(
    payload: ManualIncidentRequest, request: Request
) -> IncidentAnalysisRun:
    """Analyze existing memory first, then retain the newly documented incident."""
    services = services_from(request)
    incident = build_manual_incident(payload)
    analysis = await services.orchestrator.analyze(incident.alert)
    memory_id = await services.orchestrator.resolve(incident)
    persisted = incident.model_copy(update={"retained_memory_id": memory_id})
    return IncidentAnalysisRun(source="manual", incident=persisted, analysis=analysis)


@router.post(
    "/incidents/{incident_id}/analyze",
    response_model=IncidentAnalysisRun,
    tags=["incidents"],
)
async def analyze_historical_incident(
    incident_id: str, request: Request
) -> IncidentAnalysisRun:
    services = services_from(request)
    incident = services.store.get(incident_id)
    if incident is None:
        raise HTTPException(
            status_code=404, detail=f"Incident {incident_id} was not found."
        )
    analysis = await services.orchestrator.analyze(incident.alert)
    return IncidentAnalysisRun(
        source="historical", incident=incident, analysis=analysis
    )


@router.get(
    "/incidents/{incident_id}/artifacts",
    response_model=list[ArtifactLink],
    tags=["incidents", "integrations"],
)
async def historical_artifacts(
    incident_id: str, request: Request
) -> list[ArtifactLink]:
    services = services_from(request)
    incident = services.store.get(incident_id)
    if incident is None:
        raise HTTPException(
            status_code=404, detail=f"Incident {incident_id} was not found."
        )
    hotfix = github_hotfix_link(incident.id, services.settings.github_repository_url)
    return [
        ArtifactLink(label=hotfix.label, url=hotfix.url, kind="github_issue"),
        *incident_artifact_links(
            incident.artifacts, services.settings.github_repository_url
        ),
    ]


@router.get("/incidents", response_model=list[IncidentRecord], tags=["incidents"])
async def list_incidents(request: Request) -> list[IncidentRecord]:
    return services_from(request).store.list()


@router.get("/demo/status", response_model=DemoStatus, tags=["demo"])
async def demo_status(request: Request) -> DemoStatus:
    return services_from(request).demo.status()


@router.post("/demo/reset", status_code=status.HTTP_204_NO_CONTENT, tags=["demo"])
async def reset_demo(request: Request) -> None:
    await services_from(request).demo.reset()


@router.post("/demo/step", response_model=DemoStepResult, tags=["demo"])
async def step_demo(
    request: Request, preferences: MemoryPreferences | None = None
) -> DemoStepResult:
    try:
        return await services_from(request).demo.step(preferences)
    except IndexError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


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
