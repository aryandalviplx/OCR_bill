import hashlib
import logging
from typing import Any
import json

logger = logging.getLogger(__name__)


def compute_content_hash(content: bytes, algorithm: str = "sha256") -> str:
    #hashes raw bytes , identical files detected
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(content)
    hash_value = hash_obj.hexdigest()
    logger.debug(f"Computed {algorithm} hash: {hash_value[:16]}...")
    return hash_value


def compute_structured_hash(data: dict[str, Any], algorithm: str = "sha256") -> str:
     
    # JSON normalized before hashing 

    json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return compute_content_hash(json_str.encode("utf-8"), algorithm)


def compute_bill_fingerprint(bill_data: dict[str, Any]) -> str:
    
    # Extract key fields for fingerprinting of bills

    fingerprint_data = {
        "vendor": bill_data.get("vendor_name", "").lower().strip(),
        "invoice_number": bill_data.get("invoice_number", "").lower().strip(),
        "bill_date": bill_data.get("bill_date", ""),
        "total_amount": bill_data.get("total_amount", ""),
        "item_count": len(bill_data.get("items", [])),
        "item_totals": sorted(
            [str(item.get("total_price", "")) for item in bill_data.get("items", [])]
        ),
    }
    return compute_structured_hash(fingerprint_data)


def compute_text_hash(text: str, algorithm: str = "sha256") -> str:
    
    #hashes extracted ORC text

    return compute_content_hash(text.encode("utf-8"), algorithm)

