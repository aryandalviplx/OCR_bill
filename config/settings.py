import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application configuration settings."""

    # GCS Configuration
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "")
    GCS_PROJECT_ID: str = os.getenv("GCS_PROJECT_ID", "")
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS"
    )

    # Document AI Configuration (required for OCR)
    DOCUMENT_AI_PROJECT_ID: str = os.getenv("DOCUMENT_AI_PROJECT_ID", "")
    DOCUMENT_AI_PROCESSOR_ID: str = os.getenv("DOCUMENT_AI_PROCESSOR_ID", "")
    DOCUMENT_AI_LOCATION: str = os.getenv("DOCUMENT_AI_LOCATION", "us")

    # OCR Configuration
    OCR_MAX_PAGES: int = int(os.getenv("OCR_MAX_PAGES", "100"))

    # Duplicate Detection Configuration
    DUPLICATE_HASH_ALGORITHM: str = os.getenv(
        "DUPLICATE_HASH_ALGORITHM", "sha256"
    )

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")

    # Agent Configuration
    AGENT_MAX_RETRIES: int = int(os.getenv("AGENT_MAX_RETRIES", "3"))
    AGENT_TIMEOUT_SECONDS: int = int(
        os.getenv("AGENT_TIMEOUT_SECONDS", "300")
    )

    @classmethod
    def validate(cls) -> None:
        """Validate that required settings are present."""
        # No required settings - GCS links are provided directly
        pass


# Global settings instance
settings = Settings()
