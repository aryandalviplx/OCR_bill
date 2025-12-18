"""Audit and traceability schema definitions."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    """Types of audit events."""

    INGESTION_START = "INGESTION_START"
    INGESTION_COMPLETE = "INGESTION_COMPLETE"
    OCR_START = "OCR_START"
    OCR_COMPLETE = "OCR_COMPLETE"
    CLASSIFICATION_START = "CLASSIFICATION_START"
    CLASSIFICATION_COMPLETE = "CLASSIFICATION_COMPLETE"
    DUPLICATE_CHECK_START = "DUPLICATE_CHECK_START"
    DUPLICATE_CHECK_COMPLETE = "DUPLICATE_CHECK_COMPLETE"
    FINAL_BILL_SELECTION = "FINAL_BILL_SELECTION"
    PIPELINE_START = "PIPELINE_START"
    PIPELINE_COMPLETE = "PIPELINE_COMPLETE"
    PIPELINE_ERROR = "PIPELINE_ERROR"


class AuditEvent(BaseModel):
    """Individual audit event record."""

    event_id: str
    claim_id: str
    event_type: AuditEventType
    timestamp: datetime = Field(default_factory=datetime.now)
    agent_name: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: str = "SUCCESS"
    error_details: Optional[dict[str, Any]] = None

    class Config:
        """Pydantic config."""

        use_enum_values = True


class AuditLog(BaseModel):
    """Container for all audit events for a claim."""

    claim_id: str
    events: list[AuditEvent] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_events: int = 0

    def add_event(self, event: AuditEvent) -> None:
        """Add an audit event."""
        self.events.append(event)
        self.total_events = len(self.events)
        if not self.started_at:
            self.started_at = event.timestamp
        self.completed_at = event.timestamp

