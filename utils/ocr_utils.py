"""OCR utilities using Google Document AI."""

import logging
import re
from typing import Any, Optional
from datetime import datetime

from google.cloud import documentai_v1 as documentai
from google.api_core.client_options import ClientOptions

from config.settings import settings

logger = logging.getLogger(__name__)


def _get_document_ai_client() -> documentai.DocumentProcessorServiceClient:
    """Get Document AI client with proper endpoint."""
    location = settings.DOCUMENT_AI_LOCATION or "us"
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    return documentai.DocumentProcessorServiceClient(client_options=opts)


def _get_processor_name() -> str:
    """Build the full processor resource name."""
    project_id = settings.DOCUMENT_AI_PROJECT_ID
    location = settings.DOCUMENT_AI_LOCATION or "us"
    processor_id = settings.DOCUMENT_AI_PROCESSOR_ID

    if not project_id or not processor_id:
        raise ValueError(
            "DOCUMENT_AI_PROJECT_ID and DOCUMENT_AI_PROCESSOR_ID must be set. "
            "Create a processor in Google Cloud Console: "
            "https://console.cloud.google.com/ai/document-ai/processors"
        )

    return f"projects/{project_id}/locations/{location}/processors/{processor_id}"


def _get_mime_type(file_name: str) -> str:
    """Determine MIME type from file extension."""
    ext = file_name.lower().split(".")[-1] if "." in file_name else ""
    mime_types = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "tiff": "image/tiff",
        "tif": "image/tiff",
        "bmp": "image/bmp",
        "gif": "image/gif",
        "webp": "image/webp",
    }
    return mime_types.get(ext, "application/octet-stream")


# Maximum file size for synchronous Document AI processing (20MB)
MAX_SYNC_SIZE_BYTES = 20 * 1024 * 1024


def process_document_with_ai(
    content: bytes,
    mime_type: str = "application/pdf",
) -> documentai.Document:
    """
    Process a document using Google Document AI.

    Args:
        content: Document content as bytes
        mime_type: MIME type of the document

    Returns:
        Document AI Document object with extracted data

    Raises:
        ValueError: If document exceeds size limit
        RuntimeError: If Document AI processing fails
    """
    # Size guard: synchronous processing has a 20MB limit
    if len(content) > MAX_SYNC_SIZE_BYTES:
        raise ValueError(
            f"Document too large for synchronous Document AI processing. "
            f"Size: {len(content) / (1024*1024):.1f}MB, Max: 20MB. "
            f"Use batch processing for larger documents."
        )

    client = _get_document_ai_client()
    processor_name = _get_processor_name()

    raw_document = documentai.RawDocument(content=content, mime_type=mime_type)

    request = documentai.ProcessRequest(
        name=processor_name,
        raw_document=raw_document,
    )

    logger.info(f"Processing document with Document AI ({len(content)} bytes, {mime_type})")

    try:
        result = client.process_document(request=request)
    except Exception as e:
        logger.error("Document AI failed", exc_info=True)
        raise RuntimeError(f"Document AI processing failed: {e}")

    logger.info(f"Document AI processing complete. Extracted {len(result.document.text)} chars")

    # Note: For Invoice/Receipt processors, use result.document.entities
    # to extract structured fields like vendor_name, total_amount, line_items, etc.
    # Example: for entity in result.document.entities:
    #              print(f"{entity.type_}: {entity.mention_text}")

    return result.document


def extract_text_from_image(image_bytes: bytes, file_name: str = "image.png") -> str:
    """
    Extract text from an image using Google Document AI.

    Args:
        image_bytes: Image file content as bytes
        file_name: Original file name (for MIME type detection)

    Returns:
        Extracted text string
    """
    mime_type = _get_mime_type(file_name)
    document = process_document_with_ai(image_bytes, mime_type)
    return document.text


def extract_text_from_pdf(pdf_bytes: bytes) -> list[str]:
    """
    Extract text from PDF pages using Google Document AI.

    Args:
        pdf_bytes: PDF file content as bytes

    Returns:
        List of text strings, one per page
    """
    document = process_document_with_ai(pdf_bytes, "application/pdf")

    # Extract text per page
    page_texts = []
    for page in document.pages:
        page_text = _extract_page_text(document, page)
        page_texts.append(page_text)

    if not page_texts:
        # Fallback: return full text if page extraction fails
        page_texts = [document.text]

    logger.info(f"Extracted text from {len(page_texts)} PDF pages")
    return page_texts


def _extract_page_text(document: documentai.Document, page: documentai.Document.Page) -> str:
    """Extract text content for a specific page."""
    text = document.text
    page_text_parts = []

    # Extract text from paragraphs
    for paragraph in page.paragraphs:
        para_text = _get_text_from_layout(text, paragraph.layout)
        if para_text:
            page_text_parts.append(para_text)

    # If no paragraphs, try lines
    if not page_text_parts:
        for line in page.lines:
            line_text = _get_text_from_layout(text, line.layout)
            if line_text:
                page_text_parts.append(line_text)

    # If still no text, try tokens
    if not page_text_parts:
        for token in page.tokens:
            token_text = _get_text_from_layout(text, token.layout)
            if token_text:
                page_text_parts.append(token_text)

    return "\n".join(page_text_parts)


def _get_text_from_layout(full_text: str, layout: documentai.Document.Page.Layout) -> str:
    """Extract text segment from document based on layout anchors."""
    if not layout.text_anchor or not layout.text_anchor.text_segments:
        return ""

    text_parts = []
    for segment in layout.text_anchor.text_segments:
        start_idx = int(segment.start_index) if segment.start_index else 0
        end_idx = int(segment.end_index) if segment.end_index else len(full_text)
        text_parts.append(full_text[start_idx:end_idx])

    return "".join(text_parts).strip()


def extract_entities_from_document(document: documentai.Document) -> dict[str, Any]:
    """
    Extract structured data from Document AI entities (Invoice/Receipt Processor).

    Use this when using specialized Invoice or Receipt processors instead of OCR processor.
    These processors return pre-extracted entities like vendor_name, total_amount, line_items.

    Args:
        document: Document AI Document object

    Returns:
        Dictionary of extracted entities
    """
    entities_data: dict[str, Any] = {
        "vendor_name": "",
        "invoice_number": "",
        "bill_date": "",
        "total_amount": "0.00",
        "subtotal": "0.00",
        "tax_total": "0.00",
        "currency": "USD",
        "items": [],
        "raw_text": document.text[:1000] if document.text else "",
    }

    if not document.entities:
        logger.warning("No entities found in document. Use OCR processor with regex extraction instead.")
        return entities_data

    for entity in document.entities:
        entity_type = entity.type_.lower().replace("_", " ").replace("-", " ")
        value = entity.mention_text or ""

        # Map common entity types
        if "supplier" in entity_type or "vendor" in entity_type:
            entities_data["vendor_name"] = value
        elif "invoice" in entity_type and "number" in entity_type:
            entities_data["invoice_number"] = value
        elif "date" in entity_type and "invoice" in entity_type:
            entities_data["bill_date"] = value
        elif entity_type in ("total amount", "total", "amount due", "grand total"):
            entities_data["total_amount"] = _normalize_amount(value)
        elif "subtotal" in entity_type:
            entities_data["subtotal"] = _normalize_amount(value)
        elif "tax" in entity_type:
            entities_data["tax_total"] = _normalize_amount(value)
        elif "currency" in entity_type:
            entities_data["currency"] = value.upper()[:3]
        elif "line item" in entity_type or entity_type == "line_item":
            # Handle line items from nested properties
            item = _extract_line_item_entity(entity, len(entities_data["items"]) + 1)
            if item:
                entities_data["items"].append(item)

    logger.info(f"Extracted {len(entities_data['items'])} items from document entities")
    return entities_data


def _normalize_amount(value: str) -> str:
    """Normalize amount string to decimal format."""
    # Remove currency symbols and whitespace
    cleaned = re.sub(r"[^\d.,]", "", value)
    # Handle European format (1.234,56) vs US format (1,234.56)
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # Assume comma is decimal separator if only one comma
        if cleaned.count(",") == 1 and len(cleaned.split(",")[1]) <= 2:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    return cleaned or "0.00"


def _extract_line_item_entity(entity: documentai.Document.Entity, line_number: int) -> Optional[dict[str, Any]]:
    """Extract line item from Document AI entity."""
    item: dict[str, Any] = {
        "item_id": f"ITEM-{line_number:03d}",
        "description": "",
        "quantity": "1",
        "unit_price": "0.00",
        "total_price": "0.00",
        "line_number": line_number,
    }

    # Check properties for nested fields
    for prop in entity.properties:
        prop_type = prop.type_.lower()
        prop_value = prop.mention_text or ""

        if "description" in prop_type or "product" in prop_type:
            item["description"] = prop_value
        elif "quantity" in prop_type or "qty" in prop_type:
            item["quantity"] = _normalize_amount(prop_value) or "1"
        elif "unit" in prop_type and "price" in prop_type:
            item["unit_price"] = _normalize_amount(prop_value)
        elif "amount" in prop_type or "total" in prop_type:
            item["total_price"] = _normalize_amount(prop_value)

    # Use entity mention text as description if not found in properties
    if not item["description"] and entity.mention_text:
        item["description"] = entity.mention_text[:100]

    return item if item["description"] else None


def extract_structured_bill_data(ocr_text: str | list[str]) -> dict[str, Any]:
    """
    Extract structured bill data from OCR text using regex patterns.

    Note: For better accuracy, use Document AI's Invoice/Receipt processors
    and call extract_entities_from_document() instead.

    Args:
        ocr_text: Extracted text from OCR (string or list of strings for multi-page)

    Returns:
        Structured bill data dictionary
    """
    if isinstance(ocr_text, list):
        full_text = "\n".join(ocr_text)
    else:
        full_text = ocr_text

    logger.info("Extracting structured bill data from OCR text")

    # Extract fields using patterns
    vendor_name = _extract_vendor_name(full_text)
    invoice_number = _extract_invoice_number(full_text)
    bill_date = _extract_date(full_text)
    items = _extract_line_items(full_text)
    totals = _extract_totals(full_text)

    result = {
        "vendor_name": vendor_name,
        "bill_date": bill_date,
        "invoice_number": invoice_number,
        "items": items,
        "subtotal": totals.get("subtotal", "0.00"),
        "tax_total": totals.get("tax", "0.00"),
        "total_amount": totals.get("total", "0.00"),
        "currency": totals.get("currency", "USD"),
        "raw_text": full_text[:1000],
    }

    logger.info(f"Extracted: vendor={vendor_name}, invoice={invoice_number}, items={len(items)}")
    return result


def _extract_vendor_name(text: str) -> str:
    """Extract vendor/company name from text."""
    lines = text.strip().split("\n")

    # First non-empty line is often the company name
    for line in lines[:5]:
        line = line.strip()
        if line and len(line) > 2 and not re.match(r"^[\d\s\-/]+$", line):
            # Skip lines that are just numbers/dates
            if not re.match(r"^(invoice|bill|receipt|date|total|qty)", line.lower()):
                return line[:100]

    return "Unknown Vendor"


def _extract_invoice_number(text: str) -> str:
    """Extract invoice/bill number from text."""
    patterns = [
        r"(?:invoice|inv|bill|receipt)[\s#:]*([A-Z0-9\-]+)",
        r"(?:number|no|#)[\s:]*([A-Z0-9\-]+)",
        r"(?:ref|reference)[\s:]*([A-Z0-9\-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"


def _extract_date(text: str) -> str:
    """Extract date from text."""
    # Common date patterns
    patterns = [
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",  # MM/DD/YYYY or DD-MM-YYYY
        r"(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})",  # YYYY-MM-DD
        r"([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})",  # January 15, 2024
        r"(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})",  # 15 January 2024
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()

    return datetime.now().isoformat()


def _extract_line_items(text: str) -> list[dict[str, Any]]:
    """Extract line items from bill text."""
    items = []

    # Pattern to match line items: description, quantity, price
    # This is a simplified pattern - adjust based on actual bill formats
    patterns = [
        # Description followed by quantity and price
        r"([A-Za-z][A-Za-z\s]{2,50})\s+(\d+(?:\.\d+)?)\s+\$?([\d,]+\.?\d*)",
        # Item with price only
        r"([A-Za-z][A-Za-z\s]{5,50})\s+\$?([\d,]+\.\d{2})",
    ]

    lines = text.split("\n")
    item_count = 0

    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue

        # Try patterns
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, line)
            if match:
                item_count += 1
                groups = match.groups()

                if i == 0 and len(groups) >= 3:
                    # Pattern with quantity
                    description = groups[0].strip()
                    quantity = groups[1]
                    price = groups[2].replace(",", "")
                else:
                    # Pattern without quantity
                    description = groups[0].strip()
                    quantity = "1"
                    price = groups[1].replace(",", "") if len(groups) > 1 else "0.00"

                items.append({
                    "item_id": f"ITEM-{item_count:03d}",
                    "description": description,
                    "quantity": quantity,
                    "unit_price": price,
                    "total_price": str(float(quantity) * float(price)) if price else "0.00",
                    "line_number": item_count,
                })
                break

        # Limit items
        if item_count >= 50:
            break

    # If no items found, create a placeholder
    if not items:
        items.append({
            "item_id": "ITEM-001",
            "description": "Service/Product",
            "quantity": "1",
            "unit_price": "0.00",
            "total_price": "0.00",
            "line_number": 1,
        })

    return items


def _extract_totals(text: str) -> dict[str, str]:
    """Extract total amounts from text."""
    totals: dict[str, str] = {"currency": "USD"}

    # Total patterns
    total_patterns = [
        (r"(?:total|grand\s*total|amount\s*due)[\s:]*\$?([\d,]+\.?\d*)", "total"),
        (r"(?:subtotal|sub\s*total)[\s:]*\$?([\d,]+\.?\d*)", "subtotal"),
        (r"(?:tax|vat|gst)[\s:]*\$?([\d,]+\.?\d*)", "tax"),
    ]

    for pattern, key in total_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).replace(",", "")
            totals[key] = value

    # If no total found, try to find largest dollar amount
    if "total" not in totals:
        amounts = re.findall(r"\$?([\d,]+\.\d{2})", text)
        if amounts:
            max_amount = max(float(a.replace(",", "")) for a in amounts)
            totals["total"] = f"{max_amount:.2f}"

    # Currency detection
    if "$" in text:
        totals["currency"] = "USD"
    elif "€" in text:
        totals["currency"] = "EUR"
    elif "£" in text:
        totals["currency"] = "GBP"

    return totals


def validate_bill_structure(bill_data: dict[str, Any]) -> tuple[bool, str]:
    """
    Validate that extracted bill data has required fields.

    Args:
        bill_data: Extracted bill data dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ["items", "total_amount"]
    for field in required_fields:
        if field not in bill_data:
            return False, f"Missing required field: {field}"

    if not isinstance(bill_data.get("items"), list):
        return False, "Items must be a list"

    if len(bill_data["items"]) == 0:
        return False, "Bill must have at least one item"

    return True, "Valid"
