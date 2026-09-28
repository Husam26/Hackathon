"""SQLite system of record for canonical incidents."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import delete
from sqlmodel import Field, Session, SQLModel, create_engine, select

from backend.schemas import IncidentRecord


class IncidentRow(SQLModel, table=True):
    id: str = Field(primary_key=True)
    seq: int = Field(index=True)
    service: str = Field(index=True)
    status: str = Field(default="resolved", index=True)
    mttr_minutes: int | None = None
    payload_json: str
    retained_memory_id: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IncidentStore:
    def __init__(self, database_url: str) -> None:
        connect_args = (
            {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        )
        self.engine = create_engine(database_url, connect_args=connect_args)

    def create(self) -> None:
        SQLModel.metadata.create_all(self.engine)

    def upsert(
        self, incident: IncidentRecord, retained_memory_id: str | None = None
    ) -> None:
        with Session(self.engine) as session:
            row = session.get(IncidentRow, incident.id) or IncidentRow(
                id=incident.id,
                seq=incident.seq,
                service=incident.alert.service,
                payload_json="{}",
            )
            row.seq = incident.seq
            row.service = incident.alert.service
            row.mttr_minutes = incident.mttr_minutes
            row.retained_memory_id = retained_memory_id or incident.retained_memory_id
            row.payload_json = incident.model_copy(
                update={"retained_memory_id": row.retained_memory_id}
            ).model_dump_json()
            row.updated_at = datetime.now(timezone.utc)
            session.add(row)
            session.commit()

    def list(self) -> list[IncidentRecord]:
        with Session(self.engine) as session:
            rows = session.exec(select(IncidentRow).order_by(IncidentRow.seq)).all()
            return [
                IncidentRecord.model_validate(json.loads(row.payload_json))
                for row in rows
            ]

    def get(self, incident_id: str) -> IncidentRecord | None:
        with Session(self.engine) as session:
            row = session.get(IncidentRow, incident_id)
            return IncidentRecord.model_validate_json(row.payload_json) if row else None

    def clear(self) -> None:
        with Session(self.engine) as session:
            session.exec(delete(IncidentRow))
            session.commit()
