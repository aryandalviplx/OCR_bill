import logging
from typing import Any
from models.document_schema import DocumentStatus
from utils.ocr_utils import (
    extract_text_from_image,
    extract_text_from_pdf,
    extract_structured_bill_data,
    validate_bill_structure,
)
from utils.gcs_utils import read_file_from_gcs_link
from config.gcs_config import SUPPORTED_IMAGE_FORMATS, SUPPORTED_PDF_FORMATS

logger = logging.getLogger(__name__)


class OCRAgent:
    """Agent responsible for OCR extraction (Maker role in Maker-Checker pattern)."""

    def __init__(self) -> None:
        """Initialize OCR agent."""
        pass

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
       
        documents = state.get("claim_documents", [])
        if not documents:
            logger.warning("No documents to process for OCR")
            return state

        logger.info(f"Processing OCR for {len(documents)} documents")

        for document in documents:
            try:
                document.status = DocumentStatus.PROCESSING
                logger.info(f"Processing OCR for document: {document.metadata.file_name}")

                # Load document content from GCS link
                document_bytes = read_file_from_gcs_link(document.metadata.gcs_path)

                # Determine document type and extract text
                file_name = document.metadata.file_name.lower()
                ocr_text: str | list[str]

                if any(file_name.endswith(ext) for ext in SUPPORTED_IMAGE_FORMATS):
                    ocr_text = extract_text_from_image(document_bytes, file_name)
                elif any(file_name.endswith(ext) for ext in SUPPORTED_PDF_FORMATS):
                    ocr_text = extract_text_from_pdf(document_bytes)
                else:
                    logger.warning(f"Unsupported file format: {file_name}")
                    document.status = DocumentStatus.FAILED
                    document.error_message = f"Unsupported file format: {file_name}"
                    continue

                # Extract structured bill data
                structured_data = extract_structured_bill_data(ocr_text)

                # Validate structure
                is_valid, error_msg = validate_bill_structure(structured_data)
                if not is_valid:
                    logger.warning(f"Invalid bill structure for {document.metadata.file_name}: {error_msg}")
                    document.status = DocumentStatus.FAILED
                    document.error_message = error_msg
                    continue

                # Update document with OCR results
                document.ocr_result = structured_data
                document.status = DocumentStatus.COMPLETED

                logger.info(f"OCR completed for {document.metadata.file_name}")

            except Exception as e:
                logger.error(f"OCR error for document {document.metadata.file_name}: {e}", exc_info=True)
                document.status = DocumentStatus.FAILED
                document.error_message = str(e)

        state["claim_documents"] = documents
        return state
