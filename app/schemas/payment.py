from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator


class PaymentCreateRequest(BaseModel):
    request_no: str = Field(min_length=1, max_length=64)
    merchant_id: str = Field(min_length=1, max_length=64)
    account_reference: str = Field(min_length=1, max_length=128)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    payer_name: str = Field(min_length=1, max_length=128)
    card_number: str | None = Field(default=None, min_length=4, max_length=32)
    payment_identifier: str | None = Field(default=None, min_length=4, max_length=128)
    channel: str = Field(min_length=1, max_length=32)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("channel")
    @classmethod
    def normalize_channel(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def require_payment_identifier(self) -> "PaymentCreateRequest":
        if not self.card_number and not self.payment_identifier:
            raise ValueError("Either card_number or payment_identifier is required")
        return self


class PaymentResponse(BaseModel):
    id: int
    request_no: str
    merchant_id: str
    account_reference_masked: str
    payment_identifier_masked: str
    amount: Decimal
    currency: str
    payer_name: str
    channel: str
    state: str
    trace_id: str
    created_at: datetime
    updated_at: datetime
    idempotent_replay: bool = False

    model_config = {"from_attributes": True}

