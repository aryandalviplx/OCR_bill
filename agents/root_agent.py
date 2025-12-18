"""Root orchestration agent for claim processing pipeline."""

import logging
from typing import Any
from agents.ingestion_agent import IngestionAgent
from agents.ocr_agent import OCRAgent
from agents.classification_agent import ClassificationAgent
from agents.duplicate_checker_agent import DuplicateCheckerAgent
from agents.final_bill_agent import FinalBillAgent
from agents.audit_agent import AuditAgent

logger = logging.getLogger(__name__)


class RootAgent:
    """Root orchestration agent that coordinates all processing agents."""

    def __init__(self) -> None:
        """Initialize root agent with sub-agents."""
        self.ingestion_agent = IngestionAgent()
        self.ocr_agent = OCRAgent()
        self.classification_agent = ClassificationAgent()
        self.duplicate_checker_agent = DuplicateCheckerAgent()
        self.final_bill_agent = FinalBillAgent()
        self.audit_agent = AuditAgent()

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the complete claim processing pipeline.

        Args:
            state: Initial state containing claim_id

        Returns:
            Final state with all processing results
        """
        claim_id = state.get("claim_id")
        if not claim_id:
            raise ValueError("claim_id is required in state")

        logger.info(f"Starting root agent pipeline for claim: {claim_id}")

        # Initialize audit log
        state["audit_log"] = self.audit_agent.create_audit_log(claim_id)
        self.audit_agent.log_event(
            state["audit_log"], "root_agent", "PIPELINE_START", f"Pipeline started for claim {claim_id}"
        )

        try:
            # Step 1: Ingestion
            logger.info("Step 1: Document ingestion")
            state = self.ingestion_agent.run(state)
            self.audit_agent.log_event(
                state["audit_log"], "ingestion_agent", "INGESTION_COMPLETE", "Documents loaded from GCS"
            )

            # Step 2: OCR processing (Maker)
            logger.info("Step 2: OCR extraction")
            state = self.ocr_agent.run(state)
            self.audit_agent.log_event(
                state["audit_log"], "ocr_agent", "OCR_COMPLETE", "OCR extraction completed"
            )

            # Step 3: Classification
            logger.info("Step 3: Document classification")
            state = self.classification_agent.run(state)
            self.audit_agent.log_event(
                state["audit_log"], "classification_agent", "CLASSIFICATION_COMPLETE", "Documents classified"
            )

            # Step 4: Duplicate detection (Checker)
            logger.info("Step 4: Duplicate detection")
            state = self.duplicate_checker_agent.run(state)
            self.audit_agent.log_event(
                state["audit_log"], "duplicate_checker_agent", "DUPLICATE_CHECK_COMPLETE", "Duplicate check completed"
            )

            # Step 5: Final bill selection
            logger.info("Step 5: Final bill selection")
            state = self.final_bill_agent.run(state)
            self.audit_agent.log_event(
                state["audit_log"], "final_bill_agent", "FINAL_BILL_SELECTION", "Final bill selected"
            )

            # Pipeline complete
            self.audit_agent.log_event(
                state["audit_log"], "root_agent", "PIPELINE_COMPLETE", f"Pipeline completed successfully for claim {claim_id}"
            )
            logger.info(f"Pipeline completed successfully for claim: {claim_id}")

        except Exception as e:
            logger.error(f"Pipeline error for claim {claim_id}: {e}", exc_info=True)
            self.audit_agent.log_event(
                state["audit_log"], "root_agent", "PIPELINE_ERROR", f"Pipeline failed: {str(e)}", status="ERROR", error_details={"error": str(e)}
            )
            raise

        return state
