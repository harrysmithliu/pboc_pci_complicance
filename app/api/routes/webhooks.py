from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy.orm import Session
from fastapi import Depends

from app.db.session import get_db
from app.models.transaction import Transaction
from app.models.webhook_event import WebhookEvent
from app.schemas.webhook import WebhookPaymentStatusRequest, WebhookResponse
from app.services.audit import write_audit_log
from app.services.state import apply_provider_status
from app.services.webhook_security import (
    payload_hash,
    timestamp_is_fresh,
    verify_webhook_signature,
)

router = APIRouter()


def _record_webhook_event(
    db: Session,
    *,
    payload: WebhookPaymentStatusRequest,
    replay_key: str,
    signature_valid: bool,
) -> None:
    db.add(
        WebhookEvent(
            source="provider",
            event_type=payload.event_type,
            signature_valid=signature_valid,
            payload_hash=payload_hash(payload.model_dump(mode="json")),
            replay_key=replay_key,
        )
    )


@router.post("/provider/payment-status", response_model=WebhookResponse)
def receive_payment_status_webhook(
    payload: WebhookPaymentStatusRequest,
    db: Annotated[Session, Depends(get_db)],
    x_provider_timestamp: Annotated[str, Header(alias="X-Provider-Timestamp")],
    x_provider_nonce: Annotated[str, Header(alias="X-Provider-Nonce")],
    x_provider_signature: Annotated[str, Header(alias="X-Provider-Signature")],
) -> WebhookResponse:
    replay_key = f"provider:{x_provider_nonce}"
    trace_id = f"webhook-{x_provider_nonce}"
    body = payload.model_dump(mode="json")

    try:
        timestamp = int(x_provider_timestamp)
    except ValueError as exc:
        _record_webhook_event(db, payload=payload, replay_key=replay_key, signature_valid=False)
        write_audit_log(
            db,
            actor="provider",
            actor_role="external",
            action="WEBHOOK_REJECTED",
            resource_type="transaction",
            resource_id=str(payload.transaction_id),
            result="INVALID_TIMESTAMP",
            trace_id=trace_id,
            metadata={"event_type": payload.event_type},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid timestamp") from exc

    if db.query(WebhookEvent).filter(WebhookEvent.replay_key == replay_key).first() is not None:
        _record_webhook_event(db, payload=payload, replay_key=replay_key, signature_valid=False)
        write_audit_log(
            db,
            actor="provider",
            actor_role="external",
            action="WEBHOOK_REJECTED",
            resource_type="transaction",
            resource_id=str(payload.transaction_id),
            result="REPLAY_DETECTED",
            trace_id=trace_id,
            metadata={"event_type": payload.event_type},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Replay detected")

    if not timestamp_is_fresh(timestamp):
        _record_webhook_event(db, payload=payload, replay_key=replay_key, signature_valid=False)
        write_audit_log(
            db,
            actor="provider",
            actor_role="external",
            action="WEBHOOK_REJECTED",
            resource_type="transaction",
            resource_id=str(payload.transaction_id),
            result="EXPIRED_TIMESTAMP",
            trace_id=trace_id,
            metadata={"event_type": payload.event_type},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Expired timestamp")

    signature_valid = verify_webhook_signature(
        timestamp=timestamp,
        nonce=x_provider_nonce,
        payload=body,
        signature=x_provider_signature,
    )
    if not signature_valid:
        _record_webhook_event(db, payload=payload, replay_key=replay_key, signature_valid=False)
        write_audit_log(
            db,
            actor="provider",
            actor_role="external",
            action="WEBHOOK_REJECTED",
            resource_type="transaction",
            resource_id=str(payload.transaction_id),
            result="INVALID_SIGNATURE",
            trace_id=trace_id,
            metadata={"event_type": payload.event_type},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")

    transaction = db.get(Transaction, payload.transaction_id)
    if transaction is None:
        _record_webhook_event(db, payload=payload, replay_key=replay_key, signature_valid=True)
        write_audit_log(
            db,
            actor="provider",
            actor_role="external",
            action="WEBHOOK_REJECTED",
            resource_type="transaction",
            resource_id=str(payload.transaction_id),
            result="TRANSACTION_NOT_FOUND",
            trace_id=trace_id,
            metadata={"event_type": payload.event_type},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    try:
        apply_provider_status(transaction, payload.status)
    except HTTPException as exc:
        _record_webhook_event(db, payload=payload, replay_key=replay_key, signature_valid=True)
        write_audit_log(
            db,
            actor="provider",
            actor_role="external",
            action="WEBHOOK_REJECTED",
            resource_type="transaction",
            resource_id=str(transaction.id),
            result="INVALID_STATE_TRANSITION",
            trace_id=transaction.trace_id,
            metadata={"event_type": payload.event_type, "provider_status": payload.status},
        )
        db.commit()
        raise exc

    _record_webhook_event(db, payload=payload, replay_key=replay_key, signature_valid=True)
    write_audit_log(
        db,
        actor="provider",
        actor_role="external",
        action="WEBHOOK_ACCEPTED",
        resource_type="transaction",
        resource_id=str(transaction.id),
        result=transaction.state,
        trace_id=transaction.trace_id,
        metadata={
            "event_type": payload.event_type,
            "provider_status": payload.status,
            "provider_reference": payload.provider_reference,
        },
    )
    db.commit()
    db.refresh(transaction)
    return WebhookResponse(
        status="accepted",
        transaction_id=transaction.id,
        transaction_state=transaction.state,
    )

