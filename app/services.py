from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models import Installment, Payment, Tariff
from app.schemas import PaymentCreate

TARIFFS = (("basic", "Basic", 990_000), ("standard", "Standard", 1_990_000), ("premium", "Premium", 2_990_000))
ALLOWED_TRANSITIONS = {"pending": {"succeeded", "failed"}, "succeeded": {"refunded"}, "failed": set(), "refunded": set()}


def seed_tariffs(session: Session) -> None:
    existing = set(session.scalars(select(Tariff.code)))
    for code, name, price in TARIFFS:
        if code not in existing:
            session.add(Tariff(code=code, name=name, price_kopecks=price))
    session.commit()


def make_payment(session: Session, data: PaymentCreate, idempotency_key: str | None) -> tuple[Payment, bool]:
    if idempotency_key:
        existing = session.scalar(select(Payment).options(joinedload(Payment.schedule)).where(Payment.idempotency_key == idempotency_key))
        if existing:
            return existing, False

    tariff = session.get(Tariff, data.tariff_id)
    if tariff is None:
        raise LookupError("tariff_not_found")
    if data.promo_code and data.promo_code.upper() != "KVITTO10":
        raise ValueError("unknown_promo_code")
    amount = tariff.price_kopecks
    normalized_promo = data.promo_code.upper() if data.promo_code else None
    if normalized_promo == "KVITTO10":
        amount = amount * 90 // 100

    payment = Payment(
        tariff_id=tariff.id, email=str(data.email), method=data.method,
        installment_months=data.installment_months, promo_code=normalized_promo,
        amount_kopecks=amount, status="pending", idempotency_key=idempotency_key,
    )
    if data.method == "installment":
        months = data.installment_months
        assert months is not None
        base, remainder = divmod(amount, months)
        payment.schedule = [Installment(number=i + 1, amount_kopecks=base + (1 if i < remainder else 0)) for i in range(months)]

    session.add(payment)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        if idempotency_key:
            existing = session.scalar(select(Payment).options(joinedload(Payment.schedule)).where(Payment.idempotency_key == idempotency_key))
            if existing:
                return existing, False
        raise
    session.refresh(payment)
    return payment, True


def transition_payment(payment: Payment, new_status: str) -> bool:
    if new_status not in ALLOWED_TRANSITIONS.get(payment.status, set()):
        return False
    payment.status = new_status
    return True
