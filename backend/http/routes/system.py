"""System status and reviewer-facing architecture endpoints."""

from fastapi import APIRouter, Request

from backend.http.dependencies import services_from
from backend.schemas import HealthResponse
from backend.workflows.diagrams import WorkflowDiagrams, workflow_diagrams


router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
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


@router.get("/architecture/workflow", response_model=WorkflowDiagrams)
async def architecture_workflow() -> WorkflowDiagrams:
    """Return current Mermaid architecture artifacts for reviewers and tooling."""
    return workflow_diagrams()
