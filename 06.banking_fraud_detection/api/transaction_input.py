"""Validate incoming transactions against the stored representation."""

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, FiniteFloat, StringConstraints, field_validator

from transaction_context import normalize_timestamp


DatabaseText = Annotated[str, StringConstraints(pattern=r"^[^\x00]*$")]
Identifier = Annotated[DatabaseText, Field(min_length=1, max_length=64)]


class TransactionIn(BaseModel):
    transaction_id: Identifier | None = None
    user_id: Identifier
    amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2, allow_inf_nan=False)
    currency: DatabaseText = Field(default="USD", min_length=1, max_length=3)
    merchant: Annotated[DatabaseText, Field(max_length=255)] | None = None
    merchant_category: Annotated[DatabaseText, Field(max_length=50)] | None = None
    location: Annotated[DatabaseText, Field(max_length=255)] | None = None
    latitude: FiniteFloat | None = Field(default=None, ge=-90, le=90)
    longitude: FiniteFloat | None = Field(default=None, ge=-180, le=180)
    device_id: Annotated[DatabaseText, Field(max_length=64)] | None = None
    ip_address: Annotated[DatabaseText, Field(max_length=45)] | None = None
    transaction_type: DatabaseText = Field(default="purchase", max_length=50)
    payment_method: DatabaseText = Field(default="card", max_length=50)
    timestamp: str | None = None

    @field_validator("transaction_id", "user_id")
    @classmethod
    def validate_identifier(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("identifier must not be blank")
        return value

    @field_validator("latitude", "longitude", mode="before")
    @classmethod
    def validate_coordinate(cls, value):
        if isinstance(value, bool):
            raise ValueError("coordinate must be numeric")
        return value

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, value):
        return normalize_timestamp(value).isoformat() if value is not None else None
