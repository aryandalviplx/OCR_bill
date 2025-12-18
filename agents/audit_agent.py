"""Audit agent for traceability and audit logging."""

import logging
from typing import Any
import uuid
from datetime import datetime
from models.audit_schema import AuditLog, AuditEvent, AuditEventType

logger = logging.getLogger(__name__)


class AuditAgent:
    """Agent responsible for audit logging and traceability."""

    def create_audit_log(self, claim_id: str) -> AuditLog:
        """
        Create a new audit log for a claim.

        Args:
            claim_id: Claim identifier

        Returns:
            AuditLog object
        """
        return AuditLog(claim_id=claim_id)

    def log_event(
        self,
        audit_log: AuditLog,
        agent_name: str,
        event_type: str,
        message: str,
        metadata: dict[str, Any] | None = None,
        status: str = "SUCCESS",
        error_details: dict[str, Any] | None = None,
    ) -> None:
        """
        Log an audit event.

        Args:
            audit_log: AuditLog to add event to
            agent_name: Name of the agent logging the event
            event_type: Type of event
            message: Event message
            metadata: Optional event metadata
            status: Event status (default: SUCCESS)
            error_details: Optional error details
        """
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            claim_id=audit_log.claim_id,
            event_type=AuditEventType[event_type] if hasattr(AuditEventType, event_type) else AuditEventType.PIPELINE_COMPLETE,
            timestamp=datetime.now(),
            agent_name=agent_name,
            message=message,
            metadata=metadata or {},
            status=status,
            error_details=error_details,
        )

        audit_log.add_event(event)
        logger.info(f"Audit event: {event_type} - {message}")

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Finalize audit log and prepare for storage.

        Args:
            state: State containing audit_log

        Returns:
            Updated state with finalized audit_log
        """
        audit_log = state.get("audit_log")
        if audit_log:
            audit_log.completed_at = datetime.now()
            logger.info(f"Audit log finalized with {audit_log.total_events} events")

        return state
