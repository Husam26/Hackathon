"""Alert analysis and safe enterprise-handoff endpoints."""

from fastapi import APIRouter, Request

from backend.groq_client import RulesAnalyzer
from backend.http.dependencies import services_from
from backend.integrations import (
    AzureMonitorWebhook,
    IntegrationLink,
    RunbookVerification,
    RunbookVerificationRequest,
    TeamsExport,
    github_hotfix_link,
    teams_export,
)
from backend.memory_preferences import AnalysisRequest
from backend.schemas import Alert, AnalysisResult


router = APIRouter(tags=["analysis"])


@router.post("/analyze", response_model=AnalysisResult)
async def analyze(alert: Alert, request: Request) -> AnalysisResult:
    return await services_from(request).orchestrator.analyze(alert)


@router.post("/analyze/with-preferences", response_model=AnalysisResult)
async def analyze_with_preferences(
    payload: AnalysisRequest, request: Request
) -> AnalysisResult:
    return await services_from(request).orchestrator.analyze(
        payload.alert, payload.memory_preferences
    )


@router.post("/analyze/cold", response_model=AnalysisResult)
async def analyze_cold(alert: Alert) -> AnalysisResult:
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
