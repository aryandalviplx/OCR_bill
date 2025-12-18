"""Document classification agent for BILL vs SUPPORTING_DOC classification."""

import logging
from typing import Any
from models.document_schema import DocumentType, DocumentStatus

logger = logging.getLogger(__name__)


class ClassificationAgent:
    """Agent responsible for classifying documents as BILL or SUPPORTING_DOC."""

    def _classify_document(self, document: Any) -> DocumentType:
        """
        Classify a document as BILL or SUPPORTING_DOC.

        TODO: Implement actual ML-based classification model

        Args:
            document: Document object with OCR results

        Returns:
            DocumentType classification
        """
        # Placeholder classification logic
        # In production, use ML model trained on bill vs supporting doc features

        if document.status != DocumentStatus.COMPLETED:
            return DocumentType.UNKNOWN

        ocr_result = document.ocr_result
        if not ocr_result:
            return DocumentType.UNKNOWN

        # Simple heuristic: check for bill-like structures
        has_items = "items" in ocr_result and len(ocr_result.get("items", [])) > 0
        has_total = "total_amount" in ocr_result
        has_vendor = "vendor_name" in ocr_result and ocr_result.get("vendor_name")

        # Classify as BILL if it has structured bill data
        if has_items and has_total:
            return DocumentType.BILL

        # Default to supporting document if OCR completed but not bill-like
        return DocumentType.SUPPORTING_DOC

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Classify all documents in the claim.

        Args:
            state: State containing claim_documents with OCR results

        Returns:
            Updated state with classified documents
        """
        documents = state.get("claim_documents", [])
        if not documents:
            logger.warning("No documents to classify")
            return state

        logger.info(f"Classifying {len(documents)} documents")

        bill_count = 0
        supporting_doc_count = 0

        for document in documents:
            doc_type = self._classify_document(document)
            document.document_type = doc_type

            if doc_type == DocumentType.BILL:
                bill_count += 1
            elif doc_type == DocumentType.SUPPORTING_DOC:
                supporting_doc_count += 1

            logger.debug(
                f"Classified {document.metadata.file_name} as {doc_type.value}"
            )

        logger.info(
            f"Classification complete: {bill_count} BILLs, {supporting_doc_count} SUPPORTING_DOCs"
        )

        state["claim_documents"] = documents
        return state

