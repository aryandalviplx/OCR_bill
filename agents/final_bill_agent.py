"""Final bill selection agent for selecting the best bill."""

import logging
from typing import Any
from datetime import datetime
from decimal import Decimal
from models.document_schema import DocumentType, DocumentStatus
from models.bill_schema import (
    FinalBill,
    BillMetadata,
    BillSummary,
    BillItem,
    BillItemList,
    SupportingDocMapping,
)

logger = logging.getLogger(__name__)


class FinalBillAgent:
    """Agent responsible for selecting the final bill and generating outputs."""

    def _select_best_bill(self, documents: list[Any]) -> Any:
        """
        Select the best bill from non-duplicate bills.

        Selection criteria: highest item count.

        Args:
            documents: List of document objects

        Returns:
            Selected document object
        """
        # Filter to non-duplicate BILL documents
        valid_bills = [
            doc for doc in documents
            if doc.document_type == DocumentType.BILL
            and doc.status == DocumentStatus.COMPLETED
        ]

        if not valid_bills:
            raise ValueError("No valid bills found for selection")

        if len(valid_bills) == 1:
            logger.info("Only one valid bill, selecting it")
            return valid_bills[0]

        # Select based on item count
        best_bill = max(
            valid_bills,
            key=lambda doc: len(doc.ocr_result.get("items", [])) if doc.ocr_result else 0,
        )

        logger.info(
            f"Selected best bill: {best_bill.metadata.file_name} "
            f"(items: {len(best_bill.ocr_result.get('items', [])) if best_bill.ocr_result else 0})"
        )
        return best_bill

    def _convert_to_final_bill(self, document: Any, duplicate_groups: list[dict[str, Any]]) -> FinalBill:
        """
        Convert document OCR result to FinalBill model.

        Args:
            document: Selected document
            duplicate_groups: Duplicate groups information

        Returns:
            FinalBill object
        """
        ocr_result = document.ocr_result
        if not ocr_result:
            raise ValueError("Document has no OCR result")

        # Extract duplicate flags for this bill
        duplicate_flags = {}
        for group in duplicate_groups:
            if group["primary"] == document.metadata.document_id:
                duplicate_flags["has_duplicates"] = True
                duplicate_flags["duplicate_count"] = len(group["duplicates"])
                duplicate_flags["duplicates"] = group["duplicates"]

        # Build metadata
        metadata = BillMetadata(
            bill_id=f"BILL_{document.metadata.document_id}",
            claim_id=document.metadata.claim_id,
            document_id=document.metadata.document_id,
            bill_date=datetime.fromisoformat(ocr_result["bill_date"]) if ocr_result.get("bill_date") else None,
            vendor_name=ocr_result.get("vendor_name"),
            bill_number=ocr_result.get("invoice_number"),
            invoice_number=ocr_result.get("invoice_number"),
        )

        # Build summary
        summary = BillSummary(
            subtotal=Decimal(str(ocr_result.get("subtotal", "0.0"))),
            tax_total=Decimal(str(ocr_result.get("tax_total", "0.0"))),
            discount_total=Decimal(str(ocr_result.get("discount_total", "0.0"))),
            total_amount=Decimal(str(ocr_result.get("total_amount", "0.0"))),
            currency=ocr_result.get("currency", "USD"),
            item_count=len(ocr_result.get("items", [])),
        )

        # Build items
        items = []
        for idx, item_data in enumerate(ocr_result.get("items", []), 1):
            item = BillItem(
                item_id=item_data.get("item_id", f"ITEM_{idx}"),
                description=item_data.get("description", ""),
                quantity=Decimal(str(item_data.get("quantity", "1.0"))),
                unit_price=Decimal(str(item_data.get("unit_price", "0.0"))),
                total_price=Decimal(str(item_data.get("total_price", "0.0"))),
                category=item_data.get("category"),
                tax_amount=Decimal(str(item_data["tax_amount"])) if item_data.get("tax_amount") else None,
                discount_amount=Decimal(str(item_data["discount_amount"])) if item_data.get("discount_amount") else None,
                line_number=item_data.get("line_number", idx),
            )
            items.append(item)

        selected_reason = f"Selected based on highest item count ({len(items)})"

        return FinalBill(
            metadata=metadata,
            summary=summary,
            items=items,
            selected_reason=selected_reason,
            duplicate_flags=duplicate_flags,
            extraction_timestamp=datetime.now(),
        )

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Select final bill and generate output structures.

        Args:
            state: State containing documents and duplicate_groups

        Returns:
            Updated state with final_bill, bill_item_list, supporting_doc_map
        """
        documents = state.get("claim_documents", [])
        duplicate_groups = state.get("duplicate_groups", [])
        claim_id = state.get("claim_id")

        if not documents:
            raise ValueError("No documents in state")

        # Select best bill
        selected_document = self._select_best_bill(documents)
        final_bill = self._convert_to_final_bill(selected_document, duplicate_groups)

        # Generate bill item list
        bill_item_list = BillItemList(
            claim_id=claim_id,
            bill_id=final_bill.metadata.bill_id,
            items=final_bill.items,
            summary=final_bill.summary,
            extracted_at=datetime.now(),
        )

        # Generate supporting document map
        supporting_doc_map = SupportingDocMapping(claim_id=claim_id)
        for doc in documents:
            if doc.document_type == DocumentType.SUPPORTING_DOC:
                supporting_doc_map.add_document({
                    "document_id": doc.metadata.document_id,
                    "file_name": doc.metadata.file_name,
                    "gcs_path": doc.metadata.gcs_path,
                    "content_type": doc.metadata.content_type,
                    "file_size_bytes": doc.metadata.file_size_bytes,
                })

        logger.info(
            f"Final bill selected: {final_bill.metadata.bill_id}, "
            f"{len(final_bill.items)} items, "
            f"{supporting_doc_map.document_count} supporting documents"
        )

        state["final_bill"] = final_bill
        state["bill_item_list"] = bill_item_list
        state["supporting_doc_map"] = supporting_doc_map
        return state

