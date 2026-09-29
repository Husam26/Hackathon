"""Safe integration adapters for enterprise incident workflows."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from urllib.parse import quote, urlencode

from pydantic import BaseModel, ConfigDict

from backend.schemas import Alert, AnalysisResult, Artifacts


class AzureMonitorWebhook(BaseModel):
    """Subset of Azure Monitor Common Alert Schema accepted by Sentinel."""

    model_config = ConfigDict(extra="allow")
    data: dict[str, Any] | None = None
    essentials: dict[str, Any] | None = None
    alertContext: dict[str, Any] | None = None

    def to_alert(self) -> Alert:
        payload = self.data or {}
        essentials = self.essentials or payload.get("essentials") or {}
        context = self.alertContext or payload.get("alertContext") or {}
        targets = essentials.get("alertTargetIDs") or []
        service = str(
            targets[0] if targets else essentials.get("alertRule", "azure-workload")
        )
        service = service.rsplit("/", 1)[-1].replace(" ", "-").lower()
        severity = str(essentials.get("severity", "Sev2")).replace("Sev", "SEV-")
        if severity not in {"SEV-1", "SEV-2", "SEV-3", "SEV-4"}:
            severity = "SEV-2"
        fired_at = (
            essentials.get("firedDateTime") or datetime.now(timezone.utc).isoformat()
        )
        signals = [str(essentials.get("alertRule", "Azure Monitor alert"))]
        if context:
            signals.append(f"Azure context: {context}")
        return Alert(
            service=service, fired_at=fired_at, severity=severity, signals=signals
        )


class IntegrationLink(BaseModel):
    label: str
    url: str
    incident_id: str


class ArtifactLink(BaseModel):
    label: str
    url: str
    kind: Literal["github_issue", "pull_request", "runbook", "issue_search"]


class TeamsExport(BaseModel):
    title: str
    markdown: str
    adaptive_card: dict[str, Any]


class RunbookVerificationRequest(BaseModel):
    incident_id: str
    action: Literal["rollback_payments", "restart_checkout"]
    confirmed_by_human: bool = False


class RunbookVerification(BaseModel):
    status: Literal["confirmation_required", "approved_for_handoff"]
    message: str
    audit_note: str


def github_hotfix_link(incident_id: str, repository_url: str) -> IntegrationLink:
    base = repository_url.rstrip("/")
    query = urlencode(
        {
            "title": f"hotfix: mitigate {incident_id}",
            "body": (
                f"Incident: {incident_id}\n\n"
                "Create a reviewed rollback or bounded-pool hotfix. "
                "No production action is executed by Sentinel."
            ),
        }
    )
    return IntegrationLink(
        label="Open GitHub hotfix issue",
        url=f"{base}/issues/new?{query}",
        incident_id=incident_id,
    )


def incident_artifact_links(
    artifacts: Artifacts, repository_url: str
) -> list[ArtifactLink]:
    """Build navigable references without assuming a Jira tenant is public."""
    base = repository_url.rstrip("/")
    links: list[ArtifactLink] = []
    if artifacts.jira:
        links.append(
            ArtifactLink(
                label=f"Search GitHub issues for {artifacts.jira}",
                url=f"{base}/issues?q={quote(artifacts.jira, safe='')}",
                kind="issue_search",
            )
        )
    if artifacts.pr:
        number = artifacts.pr.removeprefix("PR-")
        links.append(
            ArtifactLink(
                label=f"Open PR reference {artifacts.pr}",
                url=f"{base}/pull/{quote(number, safe='')}",
                kind="pull_request",
            )
        )
    if artifacts.runbook:
        links.append(
            ArtifactLink(
                label=f"Open runbook {artifacts.runbook}",
                url=f"{base}/blob/main/{quote(artifacts.runbook, safe='/')}",
                kind="runbook",
            )
        )
    return links


def teams_export(analysis: AnalysisResult, incident_id: str) -> TeamsExport:
    response = analysis.response
    evidence = ", ".join(response.cited_memory_ids) or "No historical citation"
    markdown = (
        f"**Sentinel incident brief — {incident_id}**\n\n"
        f"Service: {analysis.alert.service} ({analysis.alert.severity})\n\n"
        f"Assessment: {response.summary}\n\n"
        f"Recommended action: {response.recommended_mitigation or 'Continue triage'}\n\n"
        f"Hindsight evidence: {evidence}"
    )
    return TeamsExport(
        title=f"Sentinel brief: {incident_id}",
        markdown=markdown,
        adaptive_card={
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.5",
            "body": [
                {
                    "type": "TextBlock",
                    "weight": "Bolder",
                    "text": f"Sentinel — {incident_id}",
                },
                {"type": "TextBlock", "wrap": True, "text": markdown},
            ],
        },
    )
