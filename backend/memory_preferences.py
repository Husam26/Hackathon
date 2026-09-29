"""Operator-controlled retrieval preferences for Hindsight recall."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.schemas import Alert


class MemoryPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recency: Literal["past_30_days", "past_quarter", "all_history"] = "all_history"
    severities: list[Literal["SEV-1", "SEV-2", "SEV-3", "SEV-4"]] = Field(
        default_factory=list
    )

    @field_validator("severities")
    @classmethod
    def unique_severities(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("severities must not contain duplicates")
        return values

    def temporal_window(self, reference: datetime) -> dict[str, str] | None:
        if self.recency == "all_history":
            return None
        anchor = reference.astimezone(timezone.utc)
        delta = timedelta(days=30 if self.recency == "past_30_days" else 92)
        return {
            "start": (anchor - delta).isoformat(),
            "end": anchor.isoformat(),
        }

    def severity_tags(self) -> list[str]:
        return [f"severity:{severity.lower()}" for severity in self.severities]


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert: Alert
    memory_preferences: MemoryPreferences = Field(default_factory=MemoryPreferences)
