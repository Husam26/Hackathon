"""Canonical incident, manual-intake, and artifact-navigation endpoints."""

from fastapi import APIRouter, HTTPException, Request, status

from backend.http.dependencies import services_from
from backend.incident_runs import IncidentAnalysisRun
from backend.integrations import (
    ArtifactLink,
    github_hotfix_link,
    incident_artifact_links,
)
from backend.manual_incident import ManualIncidentRequest, build_manual_incident
from backend.schemas import IncidentRecord


router = APIRouter(tags=["incidents"])


@router.post("/incidents", status_code=status.HTTP_201_CREATED)
async def resolve(incident: IncidentRecord, request: Request) -> dict[str, str]:
    memory_id = await services_from(request).orchestrator.resolve(incident)
    return {"incident_id": incident.id, "memory_id": memory_id}


@router.post(
    "/incidents/manual",
    response_model=IncidentRecord,
    status_code=status.HTTP_201_CREATED,
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
)
async def analyze_manual_incident(
    payload: ManualIncidentRequest, request: Request
) -> IncidentAnalysisRun:
    services = services_from(request)
    incident = build_manual_incident(payload)
    analysis = await services.orchestrator.analyze(incident.alert)
    memory_id = await services.orchestrator.resolve(incident)
    persisted = incident.model_copy(update={"retained_memory_id": memory_id})
    return IncidentAnalysisRun(source="manual", incident=persisted, analysis=analysis)


def incident_or_404(incident_id: str, request: Request) -> IncidentRecord:
    incident = services_from(request).store.get(incident_id)
    if incident is None:
        raise HTTPException(
            status_code=404, detail=f"Incident {incident_id} was not found."
        )
    return incident


@router.post("/incidents/{incident_id}/analyze", response_model=IncidentAnalysisRun)
async def analyze_historical_incident(
    incident_id: str, request: Request
) -> IncidentAnalysisRun:
    incident = incident_or_404(incident_id, request)
    analysis = await services_from(request).orchestrator.analyze(incident.alert)
    return IncidentAnalysisRun(
        source="historical", incident=incident, analysis=analysis
    )


@router.get(
    "/incidents/{incident_id}/artifacts",
    response_model=list[ArtifactLink],
    tags=["integrations"],
)
async def historical_artifacts(
    incident_id: str, request: Request
) -> list[ArtifactLink]:
    services = services_from(request)
    incident = incident_or_404(incident_id, request)
    hotfix = github_hotfix_link(incident.id, services.settings.github_repository_url)
    return [
        ArtifactLink(label=hotfix.label, url=hotfix.url, kind="github_issue"),
        *incident_artifact_links(
            incident.artifacts, services.settings.github_repository_url
        ),
    ]


@router.get("/incidents", response_model=list[IncidentRecord])
async def list_incidents(request: Request) -> list[IncidentRecord]:
    return services_from(request).store.list()
