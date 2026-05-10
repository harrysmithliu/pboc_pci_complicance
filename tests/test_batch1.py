from app.main import app


def test_health_check_returns_ok() -> None:
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_seeded_admin_can_login_and_read_me() -> None:
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        login_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]
        me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert me_response.status_code == 200
    assert me_response.json()["username"] == "admin"
    assert me_response.json()["role"] == "admin"
