from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.transaction import Transaction


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _payment_payload(request_no: str) -> dict[str, object]:
    return {
        "request_no": request_no,
        "merchant_id": "merchant_demo",
        "account_reference": "ACC-778899001122",
        "amount": "128.50",
        "currency": "usd",
        "payer_name": "Alice Demo",
        "card_number": "6222021234567890",
        "channel": "web",
    }


def test_operator_can_create_payment_with_masking_and_idempotency() -> None:
    request_no = f"REQ-{uuid4()}"

    with TestClient(app) as client:
        token = _login(client, "operator", "operator123")

        first_response = client.post(
            "/payments",
            json=_payment_payload(request_no),
            headers=_auth_header(token),
        )
        assert first_response.status_code == 201
        first_body = first_response.json()

        assert first_body["request_no"] == request_no
        assert first_body["state"] == "APPROVED"
        assert first_body["currency"] == "USD"
        assert first_body["channel"] == "WEB"
        assert first_body["payment_identifier_masked"] == "************7890"
        assert first_body["account_reference_masked"].endswith("1122")
        assert "6222021234567890" not in str(first_body)
        assert first_body["idempotent_replay"] is False

        duplicate_response = client.post(
            "/payments",
            json=_payment_payload(request_no),
            headers=_auth_header(token),
        )
        assert duplicate_response.status_code == 201
        duplicate_body = duplicate_response.json()

        assert duplicate_body["id"] == first_body["id"]
        assert duplicate_body["idempotent_replay"] is True

        list_response = client.get("/payments", headers=_auth_header(token))
        assert list_response.status_code == 200
        matching = [item for item in list_response.json() if item["request_no"] == request_no]
        assert len(matching) == 1

    db = SessionLocal()
    try:
        stored = db.query(Transaction).filter(Transaction.request_no == request_no).one()
        assert stored.payment_identifier_masked == "************7890"
        assert stored.account_reference_masked.endswith("1122")
        assert "6222021234567890" not in str(stored.__dict__)
        assert "ACC-778899001122" not in str(stored.__dict__)
    finally:
        db.close()


def test_auditor_can_query_but_cannot_create_payment() -> None:
    request_no = f"REQ-{uuid4()}"

    with TestClient(app) as client:
        operator_token = _login(client, "operator", "operator123")
        auditor_token = _login(client, "auditor", "auditor123")

        create_response = client.post(
            "/payments",
            json=_payment_payload(request_no),
            headers=_auth_header(operator_token),
        )
        assert create_response.status_code == 201
        payment_id = create_response.json()["id"]

        denied_response = client.post(
            "/payments",
            json=_payment_payload(f"REQ-{uuid4()}"),
            headers=_auth_header(auditor_token),
        )
        assert denied_response.status_code == 403

        detail_response = client.get(
            f"/payments/{payment_id}",
            headers=_auth_header(auditor_token),
        )
        assert detail_response.status_code == 200
        assert detail_response.json()["request_no"] == request_no


def test_payment_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.post("/payments", json=_payment_payload(f"REQ-{uuid4()}"))

    assert response.status_code == 401
