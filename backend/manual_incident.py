"""Validated manual incident intake for the operations console."""

from __future__ import annotations

from datetime import datetime, timezone
import re

from pydantic import Field

from backend.schemas import Alert, IncidentRecord, RetainPayload, StrictModel


class ManualIncidentRequest(StrictModel):
    title: str = Field(min_length=3, max_length=160)
    service: str = Field(min_length=2, max_length=80)
    severity: str = Field(pattern=r"^SEV-[1-4]$")
    occurred_at: datetime | None = None
    signals: list[str] = Field(min_length=1, max_length=12)
    root_cause: str = Field(min_length=3, max_length=500)
    mitigation: str = Field(min_length=3, max_length=500)
    mttr_minutes: int | None = Field(default=None, ge=0, le=100_000)


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "unknown"


def build_manual_incident(payload: ManualIncidentRequest) -> IncidentRecord:
    occurred_at = payload.occurred_at or datetime.now(timezone.utc)
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)
    numeric_id = occurred_at.strftime("%Y%m%d%H%M%S%f")
    service_tag = f"service:{_slug(payload.service)}"
    root_cause_tag = f"root-cause:{_slug(payload.root_cause)}"
    tags = [
        service_tag,
        root_cause_tag,
        f"severity:{payload.severity.lower()}",
        "status:resolved",
    ]
    signal_text = "; ".join(payload.signals)
    mttr_text = (
        f" MTTR: {payload.mttr_minutes} minutes."
        if payload.mttr_minutes is not None
        else ""
    )
    retain_content = (
        f"INCIDENT INC-{numeric_id} (RESOLVED). {payload.title}. "
        f"Signals: {signal_text}. ROOT CAUSE: {payload.root_cause}. "
        f"MITIGATION THAT WORKED: {payload.mitigation}.{mttr_text}"
    )
    return IncidentRecord(
        id=f"INC-{numeric_id}",
        seq=int(occurred_at.timestamp()),
        title=payload.title,
        alert=Alert(
            service=payload.service,
            fired_at=occurred_at,
            severity=payload.severity,
            signals=payload.signals,
        ),
        root_cause=payload.root_cause,
        mitigation=payload.mitigation,
        mttr_minutes=payload.mttr_minutes,
        retain=RetainPayload(
            content=retain_content,
            context="Manually documented resolved production incident.",
            timestamp=occurred_at,
            tags=tags,
        ),
    )
