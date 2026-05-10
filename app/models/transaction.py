from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_no: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    merchant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    account_reference_masked: Mapped[str] = mapped_column(String(128), nullable=False)
    payment_identifier_masked: Mapped[str] = mapped_column(String(128), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    payer_name: Mapped[str] = mapped_column(String(128), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    state: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    trace_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

