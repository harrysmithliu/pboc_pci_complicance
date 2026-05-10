from pydantic import BaseModel, Field


class WebhookPaymentStatusRequest(BaseModel):
    transaction_id: int
    event_type: str = Field(default="payment.status", min_length=1, max_length=64)
    status: str = Field(min_length=1, max_length=32)
    provider_reference: str | None = Field(default=None, max_length=128)

    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction_id": 1,
                "event_type": "payment.status",
                "status": "SETTLED",
                "provider_reference": "provider-demo-001",
            }
        }
    }


class WebhookResponse(BaseModel):
    status: str
    transaction_id: int
    transaction_state: str


class WebhookSignatureRequest(BaseModel):
    payload: WebhookPaymentStatusRequest
    nonce: str | None = Field(default=None, max_length=128)
    timestamp: int | None = None


class WebhookSignatureResponse(BaseModel):
    timestamp: int
    nonce: str
    signature: str
    payload: WebhookPaymentStatusRequest

