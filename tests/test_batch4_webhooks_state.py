from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.webhook_security import current_timestamp, sign_webhook_payload


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _payment_payload(request_no: str, *, account_reference: str = "ACC-778899001122") -> dict[str, object]:
    return {
        "request_no": request_no,
        "merchant_id": "merchant_demo",
        "account_reference": account_reference,
        "amount": "128.50",
        "currency": "usd",
        "payer_name": "Webhook Demo",
        "card_number": "6222021234567890",
        "channel": "web",
    }


def _create_payment(client: TestClient, token: str, *, account_reference: str = "ACC-778899001122") -> dict[str, object]:
    response = client.post(
        "/payments",
        json=_payment_payload(f"REQ-{uuid4()}", account_reference=account_reference),
        headers=_auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


def _webhook_headers(payload: dict[str, object], *, nonce: str | None = None, timestamp: int | None = None) -> dict[str, str]:
    timestamp = timestamp or current_timestamp()
    nonce = nonce or f"nonce-{uuid4()}"
    signature = sign_webhook_payload(timestamp=timestamp, nonce=nonce, payload=payload)
    return {
        "X-Provider-Timestamp": str(timestamp),
        "X-Provider-Nonce": nonce,
        "X-Provider-Signature": signature,
    }


def test_valid_webhook_updates_state_and_replay_is_rejected() -> None:
    with TestClient(app) as client:
        operator_token = _login(client, "operator", "operator123")
        admin_token = _login(client, "admin", "admin123")
        payment = _create_payment(client, operator_token)
        assert payment["state"] == "APPROVED"

        payload = {
            "transaction_id": payment["id"],
            "event_type": "payment.status",
            "status": "SETTLED",
            "provider_reference": "provider-settle-001",
        }
        headers = _webhook_headers(payload)
        response = client.post("/webhooks/provider/payment-status", json=payload, headers=headers)
        assert response.status_code == 200
        assert response.json()["transaction_state"] == "SETTLED"

        replay_response = client.post("/webhooks/provider/payment-status", json=payload, headers=headers)
        assert replay_response.status_code == 409

        audit_response = client.get("/audit-logs", headers=_auth_header(admin_token))
        assert audit_response.status_code == 200
        audit_logs = audit_response.json()
        assert any(item["action"] == "WEBHOOK_ACCEPTED" for item in audit_logs)
        assert any(item["action"] == "WEBHOOK_REJECTED" and item["result"] == "REPLAY_DETECTED" for item in audit_logs)


def test_invalid_and_expired_webhook_requests_are_rejected() -> None:
    with TestClient(app) as client:
        operator_token = _login(client, "operator", "operator123")
        payment = _create_payment(client, operator_token)

        payload = {
            "transaction_id": payment["id"],
            "event_type": "payment.status",
            "status": "FAILED",
            "provider_reference": "provider-fail-001",
        }

        bad_headers = _webhook_headers(payload)
        bad_headers["X-Provider-Signature"] = "bad-signature"
        bad_signature_response = client.post(
            "/webhooks/provider/payment-status",
            json=payload,
            headers=bad_headers,
        )
        assert bad_signature_response.status_code == 403

        expired_headers = _webhook_headers(payload, timestamp=current_timestamp() - 1000)
        expired_response = client.post(
            "/webhooks/provider/payment-status",
            json=payload,
            headers=expired_headers,
        )
        assert expired_response.status_code == 400


def test_settle_reverse_and_rbac_state_rules() -> None:
    with TestClient(app) as client:
        operator_token = _login(client, "operator", "operator123")
        auditor_token = _login(client, "auditor", "auditor123")
        payment = _create_payment(client, operator_token)

        auditor_settle_response = client.post(
            f"/payments/{payment['id']}/settle",
            headers=_auth_header(auditor_token),
        )
        assert auditor_settle_response.status_code == 403

        settle_response = client.post(
            f"/payments/{payment['id']}/settle",
            headers=_auth_header(operator_token),
        )
        assert settle_response.status_code == 200
        assert settle_response.json()["state"] == "SETTLED"

        reverse_response = client.post(
            f"/payments/{payment['id']}/reverse",
            headers=_auth_header(operator_token),
        )
        assert reverse_response.status_code == 200
        assert reverse_response.json()["state"] == "REVERSED"

        rejected_payment = _create_payment(
            client,
            operator_token,
            account_reference="ACC-BLACKLISTED-001",
        )
        assert rejected_payment["state"] == "REJECTED"
        rejected_settle_response = client.post(
            f"/payments/{rejected_payment['id']}/settle",
            headers=_auth_header(operator_token),
        )
        assert rejected_settle_response.status_code == 409


def test_dev_signature_endpoint_generates_usable_headers() -> None:
    with TestClient(app) as client:
        operator_token = _login(client, "operator", "operator123")
        payment = _create_payment(client, operator_token)
        payload = {
            "transaction_id": payment["id"],
            "event_type": "payment.status",
            "status": "SETTLED",
            "provider_reference": "provider-dev-signature-001",
        }

        signature_response = client.post(
            "/dev/webhook-signature",
            json={"payload": payload, "nonce": f"nonce-{uuid4()}"},
        )
        assert signature_response.status_code == 200
        signature = signature_response.json()

        webhook_response = client.post(
            "/webhooks/provider/payment-status",
            json=payload,
            headers={
                "X-Provider-Timestamp": str(signature["timestamp"]),
                "X-Provider-Nonce": signature["nonce"],
                "X-Provider-Signature": signature["signature"],
            },
        )
        assert webhook_response.status_code == 200
        assert webhook_response.json()["transaction_state"] == "SETTLED"

