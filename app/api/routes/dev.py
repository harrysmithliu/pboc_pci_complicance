from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.schemas.webhook import WebhookSignatureRequest, WebhookSignatureResponse
from app.services.webhook_security import current_timestamp, generate_nonce, sign_webhook_payload

router = APIRouter()


@router.post("/webhook-signature", response_model=WebhookSignatureResponse)
def create_webhook_signature(payload: WebhookSignatureRequest) -> WebhookSignatureResponse:
    if settings.app_env != "local":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    timestamp = payload.timestamp or current_timestamp()
    nonce = payload.nonce or generate_nonce()
    body = payload.payload.model_dump(mode="json")
    signature = sign_webhook_payload(timestamp=timestamp, nonce=nonce, payload=body)
    return WebhookSignatureResponse(
        timestamp=timestamp,
        nonce=nonce,
        signature=signature,
        payload=payload.payload,
    )

