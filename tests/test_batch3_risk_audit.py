from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _payment_payload(
    request_no: str,
    *,
    amount: str = "128.50",
    account_reference: str = "ACC-778899001122",
    merchant_id: str = "merchant_demo",
    channel: str = "web",
) -> dict[str, object]:
    return {
        "request_no": request_no,
        "merchant_id": merchant_id,
        "account_reference": account_reference,
        "amount": amount,
        "currency": "usd",
        "payer_name": "Risk Demo",
        "card_number": "6222021234567890",
        "channel": channel,
    }


def test_payment_creation_generates_risk_result_and_audit_logs() -> None:
    request_no = f"REQ-{uuid4()}"

    with TestClient(app) as client:
        operator_token = _login(client, "operator", "operator123")
        admin_token = _login(client, "admin", "admin123")

        create_response = client.post(
            "/payments",
            json=_payment_payload(request_no),
            headers=_auth_header(operator_token),
        )
        assert create_response.status_code == 201
        payment = create_response.json()
        assert payment["state"] == "APPROVED"

        risk_response = client.get(
            f"/payments/{payment['id']}/risk",
            headers=_auth_header(operator_token),
        )
        assert risk_response.status_code == 200
        risk = risk_response.json()
        assert risk["transaction_id"] == payment["id"]
        assert risk["decision"] == "APPROVE"
        assert risk["triggered_rules"] == []
        assert risk["details_json"]["account_reference_masked"].endswith("1122")
        assert "ACC-778899001122" not in str(risk)
        assert "6222021234567890" not in str(risk)

        audit_response = client.get("/audit-logs", headers=_auth_header(admin_token))
        assert audit_response.status_code == 200
        audit_logs = audit_response.json()
        matching = [
            item
            for item in audit_logs
            if item["trace_id"] == payment["trace_id"]
            and item["action"] in {"PAYMENT_CREATE", "RISK_DECISION"}
        ]
        assert {item["action"] for item in matching} == {"PAYMENT_CREATE", "RISK_DECISION"}
        assert "6222021234567890" not in str(matching)
        assert "ACC-778899001122" not in str(matching)


def test_risk_rules_can_review_and_reject_transactions() -> None:
    with TestClient(app) as client:
        operator_token = _login(client, "operator", "operator123")

        high_amount_response = client.post(
            "/payments",
            json=_payment_payload(f"REQ-{uuid4()}", amount="15000.00"),
            headers=_auth_header(operator_token),
        )
        assert high_amount_response.status_code == 201
        high_amount_payment = high_amount_response.json()
        assert high_amount_payment["state"] == "PENDING_RISK"

        high_amount_risk = client.get(
            f"/payments/{high_amount_payment['id']}/risk",
            headers=_auth_header(operator_token),
        ).json()
        assert high_amount_risk["decision"] == "REVIEW"
        assert "AMOUNT_ABOVE_THRESHOLD" in high_amount_risk["triggered_rules"]

        blacklisted_response = client.post(
            "/payments",
            json=_payment_payload(
                f"REQ-{uuid4()}",
                account_reference="ACC-BLACKLISTED-001",
            ),
            headers=_auth_header(operator_token),
        )
        assert blacklisted_response.status_code == 201
        blacklisted_payment = blacklisted_response.json()
        assert blacklisted_payment["state"] == "REJECTED"

        blacklisted_risk = client.get(
            f"/payments/{blacklisted_payment['id']}/risk",
            headers=_auth_header(operator_token),
        ).json()
        assert blacklisted_risk["decision"] == "REJECT"
        assert "BLACKLISTED_ACCOUNT" in blacklisted_risk["triggered_rules"]


def test_audit_logs_are_restricted_to_admin_and_auditor() -> None:
    with TestClient(app) as client:
        operator_token = _login(client, "operator", "operator123")
        auditor_token = _login(client, "auditor", "auditor123")

        operator_response = client.get("/audit-logs", headers=_auth_header(operator_token))
        assert operator_response.status_code == 403

        auditor_response = client.get("/audit-logs", headers=_auth_header(auditor_token))
        assert auditor_response.status_code == 200

