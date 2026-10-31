"""Structured output for the vendor desk agent."""
from typing import Literal

from pydantic import BaseModel, Field


class VendorQuote(BaseModel):
    vendor: str = Field(description="Vendor name exactly as written in the document.")
    sku: str | None = Field(description="Campus Customs SKU, e.g. CC-HD-006. Null if the document has none.")
    unit_price: float | None = Field(description="Price per unit in USD. Null if the document does not state one.")
    lead_time_days: int | None = Field(description="Lead time in days. Null if not stated.")
    min_order: int | None = Field(description="Minimum order quantity in units. Null if not stated.")
    decision: Literal["recommend", "do_not_recommend"] = Field(
        description="recommend only if all four handbook section 4 checks pass.")
    reason: str = Field(description="One sentence naming the failed check, or confirming all four passed.")


class RawFields(BaseModel):
    """What the model is allowed to return in the design layer: facts only. Python makes the decision."""
    vendor: str = Field(description="Vendor name exactly as written in the document.")
    sku: str | None = Field(description="Campus Customs SKU, e.g. CC-HD-006. Null if the document has none.")
    unit_price: float | None = Field(description="Price per unit in USD from the main quote fields. Null if not stated.")
    lead_time_days: int | None = Field(description="Lead time in days from the main quote fields. Null if not stated.")
    min_order: int | None = Field(description="Minimum order quantity in units from the main quote fields. Null if not stated.")
