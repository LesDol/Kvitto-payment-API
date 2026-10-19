from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class TariffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    price_kopecks: int


class PaymentCreate(BaseModel):
    tariff_id: int = Field(gt=0)
    email: EmailStr
    method: Literal["card", "sbp", "installment"]
    installment_months: Literal[3, 6, 12] | None = None
    promo_code: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def validate_installments(self):
        if self.method == "installment" and self.installment_months is None:
            raise ValueError("installment_months is required for installment payments")
        if self.method != "installment" and self.installment_months is not None:
            raise ValueError("installment_months is only valid for installment payments")
        return self


class InstallmentOut(BaseModel):
    number: int
    amount_kopecks: int


class PaymentOut(BaseModel):
    id: int
    tariff_id: int
    email: str
    method: str
    installment_months: int | None
    promo_code: str | None
    amount_kopecks: int
    status: str
    created_at: str
    schedule: list[InstallmentOut]


class BankWebhook(BaseModel):
    payment_id: int = Field(gt=0)
    status: Literal["succeeded", "failed", "refunded"]
