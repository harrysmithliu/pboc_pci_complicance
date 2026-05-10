from fastapi import HTTPException, status

from app.models.transaction import Transaction


def settle_transaction(transaction: Transaction) -> None:
    if transaction.state != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only APPROVED transactions can be settled",
        )
    transaction.state = "SETTLED"


def reverse_transaction(transaction: Transaction) -> None:
    if transaction.state != "SETTLED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only SETTLED transactions can be reversed",
        )
    transaction.state = "REVERSED"


def apply_provider_status(transaction: Transaction, provider_status: str) -> None:
    normalized_status = provider_status.upper()
    if normalized_status == "SETTLED":
        settle_transaction(transaction)
        return
    if normalized_status == "FAILED":
        if transaction.state not in {"APPROVED", "PENDING_RISK"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only APPROVED or PENDING_RISK transactions can fail",
            )
        transaction.state = "FAILED"
        return
    if normalized_status == "REVERSED":
        reverse_transaction(transaction)
        return

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported provider status",
    )

