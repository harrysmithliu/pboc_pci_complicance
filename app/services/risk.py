from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.masking import mask_identifier
from app.models.risk_result import RiskResult
from app.models.transaction import Transaction
from app.schemas.payment import PaymentCreateRequest

HIGH_AMOUNT_THRESHOLD = Decimal("10000.00")
BLACKLISTED_ACCOUNTS = {"ACC-BLACKLISTED-001", "BLACKLISTED-ACCOUNT"}
UNSUPPORTED_MERCHANT_CHANNELS = {("merchant_blocked", "WEB"), ("merchant_demo", "WIRE")}


def evaluate_and_store_risk(
    db: Session,
    *,
    transaction: Transaction,
    payload: PaymentCreateRequest,
    source: str = "system",
) -> RiskResult:
    triggered_rules: list[str] = []
    details: dict[str, object] = {
        "amount": str(payload.amount),
        "currency": payload.currency,
        "account_reference_masked": mask_identifier(payload.account_reference),
        "merchant_id": payload.merchant_id,
        "channel": payload.channel,
    }

    if payload.amount >= HIGH_AMOUNT_THRESHOLD:
        triggered_rules.append("AMOUNT_ABOVE_THRESHOLD")

    if payload.account_reference.strip().upper() in BLACKLISTED_ACCOUNTS:
        triggered_rules.append("BLACKLISTED_ACCOUNT")

    if (payload.merchant_id, payload.channel) in UNSUPPORTED_MERCHANT_CHANNELS:
        triggered_rules.append("UNSUPPORTED_MERCHANT_CHANNEL")

    if "BLACKLISTED_ACCOUNT" in triggered_rules or "UNSUPPORTED_MERCHANT_CHANNEL" in triggered_rules:
        decision = "REJECT"
        transaction.state = "REJECTED"
    elif "AMOUNT_ABOVE_THRESHOLD" in triggered_rules:
        decision = "REVIEW"
        transaction.state = "PENDING_RISK"
    else:
        decision = "APPROVE"
        transaction.state = "APPROVED"

    details["final_state"] = transaction.state

    risk_result = RiskResult(
        transaction_id=transaction.id,
        decision=decision,
        triggered_rules=triggered_rules,
        details_json=details,
        source=source,
    )
    db.add(risk_result)
    return risk_result

