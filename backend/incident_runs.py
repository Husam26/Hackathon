"""Contracts for analysis runs that are rendered in the operator workspace."""

from typing import Literal

from backend.schemas import AnalysisResult, IncidentRecord, StrictModel


class IncidentAnalysisRun(StrictModel):
    """One analyzable incident and its evidence-grounded response."""

    source: Literal["manual", "historical"]
    incident: IncidentRecord
    analysis: AnalysisResult
