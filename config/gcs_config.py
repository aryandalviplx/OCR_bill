"""GCS configuration constants and settings."""

import os
from functools import lru_cache
from typing import Final

from dotenv import load_dotenv
from pydantic import Field

try:
    from pydantic_settings import BaseSettings
except ImportError:  # fallback for pydantic v1 environments
    from pydantic import BaseSettings

load_dotenv()

# GCS Path Constants
CLAIMS_PREFIX: Final[str] = "claims"
DOCUMENTS_PREFIX: Final[str] = "documents"
OUTPUT_PREFIX: Final[str] = "output"
AUDIT_PREFIX: Final[str] = "audit"

# File naming conventions
FINAL_BILL_FILENAME: Final[str] = "final_bill.json"
BILL_ITEM_LIST_FILENAME: Final[str] = "bill_item_list.json"
SUPPORTING_DOC_MAP_FILENAME: Final[str] = "supporting_doc_map.json"
AUDIT_LOGS_FILENAME: Final[str] = "audit_logs.json"

# Supported document formats
SUPPORTED_IMAGE_FORMATS: Final[list[str]] = [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]
SUPPORTED_PDF_FORMATS: Final[list[str]] = [".pdf"]

# Maximum file size (100MB)
MAX_FILE_SIZE_BYTES: Final[int] = 100 * 1024 * 1024


class GCSConfig(BaseSettings):
    """GCS configuration settings."""

    gcs_base_folder: str = Field(default="claims_document", env="GCS_BASE_FOLDER")
    claims_prefix: str = Field(default="claims", env="CLAIMS_PREFIX")
    documents_prefix: str = Field(default="documents", env="DOCUMENTS_PREFIX")
    output_prefix: str = Field(default="output", env="OUTPUT_PREFIX")
    audit_prefix: str = Field(default="audit", env="AUDIT_PREFIX")
    max_file_size_bytes: int = Field(default=100 * 1024 * 1024, env="MAX_FILE_SIZE_BYTES")

    class Config:
        case_sensitive = False
        env_file = os.getenv("ENV_FILE", ".env")


@lru_cache(maxsize=1)
def get_gcs_config() -> GCSConfig:
    """Get cached GCS configuration instance."""
    return GCSConfig()

