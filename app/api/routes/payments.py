from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.masking import mask_identifier
from app.db.session import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.payment import PaymentCreateRequest, PaymentResponse
from app.schemas.risk import RiskResultResponse
from app.services.audit import write_audit_log
from app.services.risk import evaluate_and_store_risk
from app.models.risk_result import RiskResult

router = APIRouter()


def _to_payment_response(transaction: Transaction, idempotent_replay: bool = False) -> PaymentResponse:
    return PaymentResponse.model_validate(transaction).model_copy(
        update={"idempotent_replay": idempotent_replay}
    )


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles("admin", "operator"))],
) -> PaymentResponse:
    existing = db.query(Transaction).filter(Transaction.request_no == payload.request_no).first()
    if existing is not None:
        return _to_payment_response(existing, idempotent_replay=True)

    payment_identifier = payload.card_number or payload.payment_identifier or ""
    transaction = Transaction(
        request_no=payload.request_no,
        merchant_id=payload.merchant_id,
        account_reference_masked=mask_identifier(payload.account_reference),
        payment_identifier_masked=mask_identifier(payment_identifier),
        amount=payload.amount,
        currency=payload.currency,
        payer_name=payload.payer_name,
        channel=payload.channel,
        state="PENDING_RISK",
        trace_id=str(uuid4()),
    )
    db.add(transaction)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(Transaction).filter(Transaction.request_no == payload.request_no).first()
        if existing is not None:
            return _to_payment_response(existing, idempotent_replay=True)
        raise

    db.refresh(transaction)
    evaluate_and_store_risk(db, transaction=transaction, payload=payload)
    write_audit_log(
        db,
        actor=current_user.username,
        actor_role=current_user.role,
        action="PAYMENT_CREATE",
        resource_type="transaction",
        resource_id=str(transaction.id),
        result="SUCCESS",
        trace_id=transaction.trace_id,
        metadata={
            "request_no": transaction.request_no,
            "amount": str(transaction.amount),
            "currency": transaction.currency,
            "payment_identifier_masked": transaction.payment_identifier_masked,
        },
    )
    write_audit_log(
        db,
        actor="system",
        actor_role="system",
        action="RISK_DECISION",
        resource_type="transaction",
        resource_id=str(transaction.id),
        result=transaction.state,
        trace_id=transaction.trace_id,
        metadata={
            "request_no": transaction.request_no,
            "state": transaction.state,
        },
    )
    db.commit()
    db.refresh(transaction)
    return _to_payment_response(transaction)


@router.get("", response_model=list[PaymentResponse])
def list_payments(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles("admin", "operator", "auditor"))],
) -> list[PaymentResponse]:
    transactions = db.query(Transaction).order_by(Transaction.created_at.desc(), Transaction.id.desc()).all()
    return [_to_payment_response(transaction) for transaction in transactions]


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles("admin", "operator", "auditor"))],
) -> PaymentResponse:
    transaction = db.get(Transaction, payment_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return _to_payment_response(transaction)


@router.get("/{payment_id}/risk", response_model=RiskResultResponse)
def get_payment_risk(
    payment_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles("admin", "operator", "auditor"))],
) -> RiskResultResponse:
    transaction = db.get(Transaction, payment_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    risk_result = (
        db.query(RiskResult)
        .filter(RiskResult.transaction_id == payment_id)
        .order_by(RiskResult.created_at.desc(), RiskResult.id.desc())
        .first()
    )
    if risk_result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk result not found")
    return RiskResultResponse.model_validate(risk_result)
