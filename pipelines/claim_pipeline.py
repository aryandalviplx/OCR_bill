"""Main claim processing pipeline."""

import logging
from typing import Any
from agents.root_agent import RootAgent

logger = logging.getLogger(__name__)


class ClaimPipeline:
    """Main pipeline for processing claims."""

    def __init__(self) -> None:
        """Initialize pipeline."""
        self.root_agent = RootAgent()

    def process_claim(self, claim_id: str, gcs_links: list[str]) -> dict[str, Any]:
        
        logger.info(f"Starting claim processing pipeline for claim: {claim_id}")

        # Initialize state
        state: dict[str, Any] = {
            "claim_id": claim_id,
            "gcs_links": gcs_links,
        }

        try:
            # Run pipeline through root agent
            state = self.root_agent.run(state)

            # Finalize audit log
            if "audit_log" in state:
                state["audit_log"].completed_at = state["audit_log"].events[-1].timestamp if state["audit_log"].events else None

            # Prepare outputs as JSON-serializable dictionaries
            outputs = self._prepare_outputs(state)

            logger.info(f"Claim processing completed successfully for claim: {claim_id}")

            return {
                "claim_id": claim_id,
                "status": "SUCCESS",
                "outputs": outputs,
                "final_bill_id": (
                    state.get("final_bill").metadata.bill_id
                    if state.get("final_bill") and hasattr(state.get("final_bill"), "metadata")
                    else None
                ),
            }

        except Exception as e:
            logger.error(f"Claim processing failed for claim {claim_id}: {e}", exc_info=True)
            return {
                "claim_id": claim_id,
                "status": "FAILED",
                "error": str(e),
            }

    def _prepare_outputs(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Prepare all outputs as JSON-serializable dictionaries.

        Args:
            state: State containing all outputs

        Returns:
            Dictionary of output data (JSON-serializable)
        """
        from models.bill_schema import FinalBill, BillItemList, SupportingDocMapping
        from models.audit_schema import AuditLog

        outputs: dict[str, Any] = {}

        try:
            # Prepare final_bill
            if "final_bill" in state:
                final_bill = state["final_bill"]
                if isinstance(final_bill, FinalBill):
                    outputs["final_bill"] = final_bill.model_dump(mode="json")
                else:
                    outputs["final_bill"] = final_bill

            # Prepare bill_item_list
            if "bill_item_list" in state:
                bill_item_list = state["bill_item_list"]
                if isinstance(bill_item_list, BillItemList):
                    outputs["bill_item_list"] = bill_item_list.model_dump(mode="json")
                else:
                    outputs["bill_item_list"] = bill_item_list

            # Prepare supporting_doc_map
            if "supporting_doc_map" in state:
                supporting_doc_map = state["supporting_doc_map"]
                if isinstance(supporting_doc_map, SupportingDocMapping):
                    outputs["supporting_doc_map"] = supporting_doc_map.model_dump(mode="json")
                else:
                    outputs["supporting_doc_map"] = supporting_doc_map

            # Prepare audit_logs
            if "audit_log" in state:
                audit_log = state["audit_log"]
                if isinstance(audit_log, AuditLog):
                    outputs["audit_logs"] = audit_log.model_dump(mode="json")
                else:
                    outputs["audit_logs"] = audit_log

            logger.info(f"Prepared {len(outputs)} output dictionaries")
            return outputs

        except Exception as e:
            logger.error(f"Error preparing outputs: {e}", exc_info=True)
            raise
