import logging
from urllib.parse import urlparse
from google.cloud import storage
from google.cloud.exceptions import NotFound

logger = logging.getLogger(__name__)


def parse_gcs_link(gcs_link: str) -> tuple[str, str]:
    """
    Parse a GCS link into bucket name and blob path.

    Supports formats:
    - gs://bucket-name/path/to/blob
    - https://storage.googleapis.com/bucket-name/path/to/blob
    - https://storage.cloud.google.com/bucket-name/path/to/blob

    Args:
        gcs_link: GCS link (gs:// or https:// format)

    Returns:
        Tuple of (bucket_name, blob_path)

    Raises:
        ValueError: If the link format is invalid
    """
    gcs_link = gcs_link.strip()

    # Handle gs:// format
    if gcs_link.startswith("gs://"):
        path = gcs_link[5:]  # Remove 'gs://'
        parts = path.split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid GCS link format: {gcs_link}")
        bucket_name, blob_path = parts
        return bucket_name, blob_path

    # Handle HTTPS format
    if gcs_link.startswith("https://"):
        parsed = urlparse(gcs_link)
        path_parts = parsed.path.strip("/").split("/", 1)
        if len(path_parts) < 2:
            raise ValueError(f"Invalid GCS HTTPS link format: {gcs_link}")
        bucket_name = path_parts[0]
        blob_path = path_parts[1]
        return bucket_name, blob_path

    raise ValueError(f"Unsupported GCS link format: {gcs_link}. Use gs:// or https:// format")


def extract_blob_path_from_gcs_link(gcs_link: str) -> str:
    
    _, blob_path = parse_gcs_link(gcs_link)
    return blob_path


def extract_bucket_from_gcs_link(gcs_link: str) -> str:
   
    bucket_name, _ = parse_gcs_link(gcs_link)
    return bucket_name


def is_gcs_link(link: str) -> bool:
    
    return (
        link.startswith("gs://")
        or link.startswith("https://storage.googleapis.com/")
        or link.startswith("https://storage.cloud.google.com/")
    )


def read_file_from_gcs_link(gcs_link: str) -> bytes:
    
    bucket_name, blob_path = parse_gcs_link(gcs_link)
    
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        content = blob.download_as_bytes()
        logger.debug(f"Read {len(content)} bytes from {gcs_link}")
        return content
    except NotFound:
        logger.error(f"File not found: {gcs_link}")
        raise
    except Exception as e:
        logger.error(f"Error reading file from {gcs_link}: {e}")
        raise

