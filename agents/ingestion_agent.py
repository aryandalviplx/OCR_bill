"""Document ingestion agent for loading claim documents from GCS links."""

import logging
import mimetypes
from typing import Any
from models.document_schema import Document, DocumentMetadata, DocumentStatus, DocumentType
from utils.gcs_utils import parse_gcs_link, is_gcs_link
from datetime import datetime

logger = logging.getLogger(__name__)


class IngestionAgent:
    """Agent responsible for loading claim documents from GCS links."""

    def __init__(self) -> None:
        """Initialize ingestion agent."""
        # No GCS client needed - we work with links directly for faster processing
        pass

    def _infer_content_type(self, file_name: str) -> str:
       
        content_type, _ = mimetypes.guess_type(file_name)
        return content_type or "application/octet-stream"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
      
        claim_id = state.get("claim_id")
        if not claim_id:
            raise ValueError("claim_id is required in state")

        gcs_links = state.get("gcs_links", [])
        if not gcs_links:
            raise ValueError("gcs_links is required in state. Provide a list of GCS links (gs:// or https://)")

        logger.info(f"Ingesting {len(gcs_links)} documents for claim: {claim_id}")

        documents = []
        for idx, gcs_link in enumerate(gcs_links):
            try:
                if not is_gcs_link(gcs_link):
                    logger.warning(f"Invalid GCS link format: {gcs_link}, skipping")
                    continue

                # Parse GCS link to get bucket and blob path (no API call)
                bucket_name, blob_path = parse_gcs_link(gcs_link)
                
                # Extract document name from blob path
                document_name = blob_path.split("/")[-1]
                
                # Generate document ID
                document_id = f"{claim_id}_doc_{idx+1}_{document_name}"

                # Infer content type from file extension (no API call)
                content_type = self._infer_content_type(document_name)

                # Create metadata without expensive GCS API calls
                # File size and upload time are not needed for OCR processing
                metadata = DocumentMetadata(
                    document_id=document_id,
                    claim_id=claim_id,
                    gcs_path=gcs_link,  # Store the full GCS link
                    file_name=document_name,
                    file_size_bytes=0,  # Will be set during OCR if needed
                    content_type=content_type,
                    uploaded_at=datetime.now(),  # Approximate, not critical for OCR
                )

                document = Document(
                    metadata=metadata,
                    document_type=DocumentType.UNKNOWN,
                    status=DocumentStatus.PENDING,
                )

                documents.append(document)
                logger.debug(f"Loaded document: {document_name} from {gcs_link}")

            except Exception as e:
                logger.error(f"Error loading document from {gcs_link}: {e}", exc_info=True)
                continue

        logger.info(f"Ingested {len(documents)} documents for claim {claim_id} (optimized - no GCS metadata calls)")
        state["claim_documents"] = documents
        return state

