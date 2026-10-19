from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Tariff(Base):
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    price_kopecks: Mapped[int] = mapped_column(Integer, nullable=False)


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount_kopecks >= 0", name="ck_payment_amount_nonnegative"),
        CheckConstraint("status IN ('pending', 'succeeded', 'failed', 'refunded')", name="ck_payment_status"),
        CheckConstraint("method IN ('card', 'sbp', 'installment')", name="ck_payment_method"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tariff_id: Mapped[int] = mapped_column(ForeignKey("tariffs.id", ondelete="RESTRICT"), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    installment_months: Mapped[int | None] = mapped_column(Integer)
    promo_code: Mapped[str | None] = mapped_column(String(50))
    amount_kopecks: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    idempotency_key: Mapped[str | None] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    tariff: Mapped[Tariff] = relationship()
    schedule: Mapped[list["Installment"]] = relationship(
        back_populates="payment", cascade="all, delete-orphan", order_by="Installment.number"
    )


class Installment(Base):
    __tablename__ = "installments"
    __table_args__ = (
        UniqueConstraint("payment_id", "number", name="uq_installment_payment_number"),
        CheckConstraint("amount_kopecks >= 0", name="ck_installment_amount_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_kopecks: Mapped[int] = mapped_column(Integer, nullable=False)
    payment: Mapped[Payment] = relationship(back_populates="schedule")
