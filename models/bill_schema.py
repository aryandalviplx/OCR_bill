"""Bill schema definitions."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from pydantic import BaseModel, Field


class BillItem(BaseModel):
    """Individual line item in a bill."""

    item_id: str
    description: str
    quantity: Decimal = Field(default=Decimal("1.0"))
    unit_price: Decimal
    total_price: Decimal
    category: Optional[str] = None
    tax_amount: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    line_number: Optional[int] = None


class BillSummary(BaseModel):
    """Summary totals for a bill."""

    subtotal: Decimal
    tax_total: Decimal = Field(default=Decimal("0.0"))
    discount_total: Decimal = Field(default=Decimal("0.0"))
    total_amount: Decimal
    currency: str = "USD"
    item_count: int = 0


class BillMetadata(BaseModel):
    """Metadata for a bill document."""

    bill_id: str
    claim_id: str
    document_id: str
    bill_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    bill_number: Optional[str] = None
    invoice_number: Optional[str] = None


class FinalBill(BaseModel):
    """Final selected bill with all details."""

    metadata: BillMetadata
    summary: BillSummary
    items: list[BillItem] = Field(default_factory=list)
    selected_reason: str
    duplicate_flags: dict[str, Any] = Field(default_factory=dict)
    extraction_timestamp: datetime = Field(default_factory=datetime.now)

    def add_item(self, item: BillItem) -> None:
        """Add an item to the bill."""
        self.items.append(item)
        self.summary.item_count = len(self.items)


class BillItemList(BaseModel):
    """List of bill items for output."""

    claim_id: str
    bill_id: str
    items: list[BillItem] = Field(default_factory=list)
    summary: BillSummary
    extracted_at: datetime = Field(default_factory=datetime.now)


class SupportingDocMapping(BaseModel):
    """Mapping of supporting documents to claim."""

    claim_id: str
    supporting_documents: list[dict[str, Any]] = Field(default_factory=list)
    document_count: int = 0

    def add_document(self, document_info: dict[str, Any]) -> None:
        """Add a supporting document mapping."""
        self.supporting_documents.append(document_info)
        self.document_count = len(self.supporting_documents)

