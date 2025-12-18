"""Duplicate checker agent for detecting duplicate bills (Checker role)."""

import logging
from typing import Any
from models.document_schema import DocumentType, DocumentStatus
from utils.hash_utils import compute_bill_fingerprint

logger = logging.getLogger(__name__)


class DuplicateCheckerAgent:
    """Agent responsible for duplicate detection (Checker role in Maker-Checker pattern)."""

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
      
        documents = state.get("claim_documents", [])
        if not documents:
            logger.warning("No documents to check for duplicates")
            return state

        # Filter to only BILL documents
        bill_documents = [
            doc for doc in documents
            if doc.document_type == DocumentType.BILL and doc.status == DocumentStatus.COMPLETED
        ]

        if len(bill_documents) < 2:
            logger.info("Less than 2 bills found, skipping duplicate check")
            state["duplicate_groups"] = []
            return state

        logger.info(f"Checking {len(bill_documents)} bills for duplicates")

        # Compute fingerprints
        bill_data: list[dict[str, Any]] = []
        for doc in bill_documents:
            if doc.ocr_result:
                fingerprint = compute_bill_fingerprint(doc.ocr_result)
                bill_data.append({
                    "document": doc,
                    "fingerprint": fingerprint,
                    "duplicate_of": None,
                    "is_duplicate": False,
                })

        # Compare bills pairwise (hash-based duplicate detection)
        duplicate_groups: list[dict[str, Any]] = []

        for i in range(len(bill_data)):
            if bill_data[i]["is_duplicate"]:
                continue

            group = [bill_data[i]]
            for j in range(i + 1, len(bill_data)):
                if bill_data[j]["is_duplicate"]:
                    continue

                # Check fingerprint match (exact duplicates)
                if bill_data[i]["fingerprint"] == bill_data[j]["fingerprint"]:
                    bill_data[j]["is_duplicate"] = True
                    bill_data[j]["duplicate_of"] = bill_data[i]["document"].metadata.document_id
                    bill_data[j]["document"].status = DocumentStatus.DUPLICATE
                    group.append(bill_data[j])
                    logger.info(
                        f"Duplicate detected: {bill_data[j]['document'].metadata.file_name} "
                        f"duplicate of {bill_data[i]['document'].metadata.file_name}"
                    )

            if len(group) > 1:
                duplicate_groups.append({
                    "primary": group[0]["document"].metadata.document_id,
                    "duplicates": [
                        {
                            "document_id": g["document"].metadata.document_id,
                            "file_name": g["document"].metadata.file_name,
                        }
                        for g in group[1:]
                    ],
                })

        logger.info(f"Duplicate check complete: {len(duplicate_groups)} duplicate group(s) found")
        state["duplicate_groups"] = duplicate_groups
        state["claim_documents"] = documents
        return state

