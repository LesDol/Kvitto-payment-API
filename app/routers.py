from fastapi import APIRouter, Depends, Header, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_session
from app.models import Payment, Tariff
from app.schemas import BankWebhook, PaymentCreate, PaymentOut, TariffOut
from app.services import make_payment, transition_payment

router = APIRouter()


def payment_response(payment: Payment) -> dict:
    return {
        "id": payment.id,
        "tariff_id": payment.tariff_id,
        "email": payment.email,
        "method": payment.method,
        "installment_months": payment.installment_months,
        "promo_code": payment.promo_code,
        "amount_kopecks": payment.amount_kopecks,
        "status": payment.status,
        "created_at": payment.created_at.isoformat(),
        "schedule": [{"number": part.number, "amount_kopecks": part.amount_kopecks} for part in payment.schedule],
    }


@router.get("/tariffs", response_model=list[TariffOut])
def list_tariffs(session: Session = Depends(get_session)):
    return list(session.scalars(select(Tariff).order_by(Tariff.id)))


@router.post("/payments", response_model=PaymentOut)
def create_payment(
    data: PaymentCreate,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=255),
    session: Session = Depends(get_session),
):
    try:
        payment, created = make_payment(session, data, idempotency_key)
    except LookupError:
        raise HTTPException(status_code=404, detail="tariff_not_found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    response.status_code = 201 if created else 200
    return payment_response(payment)


@router.get("/payments/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: int, session: Session = Depends(get_session)):
    payment = session.scalar(select(Payment).options(joinedload(Payment.schedule)).where(Payment.id == payment_id))
    if payment is None:
        raise HTTPException(status_code=404, detail="payment_not_found")
    return payment_response(payment)


@router.post("/webhooks/bank", responses={409: {"description": "Invalid status transition"}})
def bank_webhook(data: BankWebhook, session: Session = Depends(get_session)):
    payment = session.scalar(select(Payment).where(Payment.id == data.payment_id).with_for_update())
    if payment is None:
        raise HTTPException(status_code=404, detail="payment_not_found")
    if not transition_payment(payment, data.status):
        return JSONResponse(status_code=409, content={"error": "invalid_transition"})
    session.commit()
    return {"id": payment.id, "status": payment.status}
