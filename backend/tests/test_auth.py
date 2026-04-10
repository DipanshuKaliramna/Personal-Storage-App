from app.config import settings


def test_register_returns_dev_code_when_smtp_missing_in_dev(client, monkeypatch):
    monkeypatch.setattr(settings, "env", "dev")
    monkeypatch.setattr(settings, "smtp_host", None)
    monkeypatch.setattr(settings, "smtp_username", None)
    monkeypatch.setattr(settings, "smtp_password", None)
    monkeypatch.setattr(settings, "smtp_from_email", None)

    response = client.post(
        "/auth/register",
        json={"email": "dev@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["email_sent"] is False
    assert payload["dev_verification_code"] is not None


def test_register_fails_without_email_delivery_in_prod(client, monkeypatch):
    monkeypatch.setattr(settings, "env", "prod")
    monkeypatch.setattr(settings, "smtp_host", None)
    monkeypatch.setattr(settings, "smtp_username", None)
    monkeypatch.setattr(settings, "smtp_password", None)
    monkeypatch.setattr(settings, "smtp_from_email", None)

    response = client.post(
        "/auth/register",
        json={"email": "prod@example.com", "password": "password123"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Email delivery is not configured"


def test_oauth_routes_are_hidden_by_default(client):
    response = client.get("/auth/oauth/google/login")
    assert response.status_code == 404
