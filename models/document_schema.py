"""Document schema definitions."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Document type enumeration."""

    BILL = "BILL"
    SUPPORTING_DOC = "SUPPORTING_DOC"
    UNKNOWN = "UNKNOWN"


class DocumentStatus(str, Enum):
    """Document processing status."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"


class DocumentMetadata(BaseModel):
    """Metadata for a document."""

    document_id: str
    claim_id: str
    gcs_path: str
    file_name: str
    file_size_bytes: int
    content_type: str
    uploaded_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None


class Document(BaseModel):
    """Document model with metadata and content."""

    metadata: DocumentMetadata
    document_type: DocumentType = DocumentType.UNKNOWN
    status: DocumentStatus = DocumentStatus.PENDING
    ocr_result: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None

    class Config:
        """Pydantic config."""

        use_enum_values = True


class ClaimDocuments(BaseModel):
    """Container for all documents in a claim."""

    claim_id: str
    documents: list[Document] = Field(default_factory=list)
    total_count: int = 0

    def add_document(self, document: Document) -> None:
        """Add a document to the claim."""
        self.documents.append(document)
        self.total_count = len(self.documents)

