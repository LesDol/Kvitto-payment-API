import hashlib
import hmac
import json

from sqlalchemy import func, select

from app.models import Installment, Payment, Tariff


def payload(**overrides):
    data = {"tariff_id": 1, "email": "person@example.com", "method": "card"}
    data.update(overrides)
    return data


def signed_webhook(http, body, secret="test-webhook-secret"):
    content = json.dumps(body, separators=(",", ":")).encode()
    signature = hmac.new(secret.encode(), content, hashlib.sha256).hexdigest()
    return http.post(
        "/webhooks/bank",
        content=content,
        headers={"Content-Type": "application/json", "X-Signature": signature},
    )


def test_tariffs_and_prices(client):
    http, sessions = client
    response = http.get("/tariffs")
    assert response.status_code == 200
    assert [(row["code"], row["price_kopecks"]) for row in response.json()] == [
        ("basic", 990000), ("standard", 1990000), ("premium", 2990000)
    ]
    with sessions() as db:
        assert db.scalar(select(func.count(Tariff.id))) == 3


def test_payment_prices_and_promo(client):
    http, _ = client
    full = http.post("/payments", json=payload())
    discounted = http.post("/payments", json=payload(promo_code="kvitto10"))
    assert full.status_code == 201 and full.json()["amount_kopecks"] == 990000
    assert discounted.status_code == 201 and discounted.json()["amount_kopecks"] == 891000
    assert discounted.json()["promo_code"] == "KVITTO10"


def test_unknown_promo_and_tariff(client):
    http, _ = client
    assert http.post("/payments", json=payload(promo_code="NOPE")).status_code == 422
    assert http.post("/payments", json=payload(tariff_id=999)).status_code == 404


def test_installment_schedules(client):
    http, sessions = client
    for months in (3, 6, 12):
        response = http.post("/payments", json=payload(method="installment", installment_months=months, tariff_id=2))
        assert response.status_code == 201
        body = response.json()
        amounts = [item["amount_kopecks"] for item in body["schedule"]]
        assert len(amounts) == months
        assert sum(amounts) == body["amount_kopecks"] == 1990000
        assert amounts == [1990000 // months + (i < 1990000 % months) for i in range(months)]
        with sessions() as db:
            payment = db.get(Payment, body["id"])
            stored = list(db.scalars(select(Installment).where(Installment.payment_id == payment.id).order_by(Installment.number)))
            assert len(stored) == months and sum(i.amount_kopecks for i in stored) == payment.amount_kopecks
        assert http.get(f"/payments/{body['id']}").json()["schedule"] == body["schedule"]


def test_idempotency_returns_same_payment(client):
    http, sessions = client
    headers = {"Idempotency-Key": "request-123"}
    first = http.post("/payments", json=payload(), headers=headers)
    second = http.post("/payments", json=payload(tariff_id=2), headers=headers)
    assert first.status_code == 201 and second.status_code == 200
    assert second.json() == first.json()
    with sessions() as db:
        assert db.scalar(select(func.count(Payment.id))) == 1


def test_webhook_transitions_and_invalid_transition(client):
    http, sessions = client
    created = http.post("/payments", json=payload()).json()
    payment_id = created["id"]
    assert created["status"] == "pending"
    succeeded = signed_webhook(http, {"payment_id": payment_id, "status": "succeeded"})
    assert succeeded.status_code == 200 and succeeded.json()["status"] == "succeeded"
    refunded = signed_webhook(http, {"payment_id": payment_id, "status": "refunded"})
    assert refunded.status_code == 200 and refunded.json()["status"] == "refunded"
    invalid = signed_webhook(http, {"payment_id": payment_id, "status": "failed"})
    assert invalid.status_code == 409 and invalid.json() == {"error": "invalid_transition"}
    assert http.get(f"/payments/{payment_id}").json()["status"] == "refunded"
    with sessions() as db:
        assert db.get(Payment, payment_id).status == "refunded"


def test_missing_payments_and_webhooks(client):
    http, _ = client
    assert http.get("/payments/123456").status_code == 404
    assert signed_webhook(http, {"payment_id": 123456, "status": "succeeded"}).status_code == 404


def test_payment_validation(client):
    http, _ = client
    assert http.post("/payments", json=payload(method="cash")).status_code == 422
    assert http.post("/payments", json=payload(method="installment")).status_code == 422
    assert http.post("/payments", json=payload(method="installment", installment_months=5)).status_code == 422
    assert http.post("/payments", json=payload(method="sbp", installment_months=3)).status_code == 422


def test_failed_transition_allowed_once(client):
    http, _ = client
    created = http.post("/payments", json=payload()).json()
    failed = signed_webhook(http, {"payment_id": created["id"], "status": "failed"})
    assert failed.status_code == 200 and failed.json()["status"] == "failed"
    assert signed_webhook(http, {"payment_id": created["id"], "status": "succeeded"}).status_code == 409


def test_webhook_rejects_missing_and_invalid_signatures(client):
    http, _ = client
    body = {"payment_id": 1, "status": "succeeded"}
    missing = http.post("/webhooks/bank", json=body)
    invalid = http.post("/webhooks/bank", json=body, headers={"X-Signature": "0" * 64})
    assert missing.status_code == 401
    assert invalid.status_code == 401


def test_payment_list_filters_can_be_combined(client):
    http, _ = client
    http.post("/payments", json=payload(email="alice@example.com"))
    second = http.post("/payments", json=payload(email="alice@example.com"))
    signed_webhook(http, {"payment_id": second.json()["id"], "status": "succeeded"})
    http.post("/payments", json=payload(email="bob@example.com"))

    assert len(http.get("/payments", params={"email": "alice@example.com"}).json()) == 2
    assert len(http.get("/payments", params={"status": "pending"}).json()) == 2
    combined = http.get("/payments", params={"email": "alice@example.com", "status": "succeeded"})
    assert combined.status_code == 200
    assert len(combined.json()) == 1
    assert combined.json()[0]["email"] == "alice@example.com"
    assert combined.json()[0]["status"] == "succeeded"
