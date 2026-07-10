"""Production-mode security regression tests."""
import re

import pytest

from companion import create_app
from companion.extensions import db


@pytest.fixture
def production_app():
    app = create_app({
        "APP_ENV": "production",
        "TESTING": True,
        "SECRET_KEY": "production-test-secret",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": True,
        "SESSION_COOKIE_SECURE": True,
        "CLIENT_COOKIE_SECURE": True,
        "TRUST_PROXY_HOPS": 1,
        "DEEPSEEK_API_KEY": "test-key",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _csrf_token(client) -> str:
    response = client.get("/", base_url="https://code.example.com")
    assert response.status_code == 200
    match = re.search(
        rb'<meta name="csrf-token" content="([^"]+)"',
        response.data,
    )
    assert match is not None
    return match.group(1).decode("utf-8")


def test_mutation_without_csrf_token_is_rejected(production_app):
    client = production_app.test_client()
    response = client.post(
        "/api/v1/conversations",
        json={},
        base_url="https://code.example.com",
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "CSRF_FAILED"


def test_csrf_token_allows_mutation(production_app):
    client = production_app.test_client()
    token = _csrf_token(client)
    response = client.post(
        "/api/v1/conversations",
        json={},
        headers={
            "X-CSRFToken": token,
            "Referer": "https://code.example.com/",
        },
        base_url="https://code.example.com",
    )

    assert response.status_code == 201
    assert response.get_json()["data"]["id"]


def test_production_security_headers_and_cookie(production_app):
    client = production_app.test_client()
    _csrf_token(client)
    response = client.get(
        "/api/v1/bootstrap",
        base_url="http://127.0.0.1",
        headers={
            "Host": "code.example.com",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "code.example.com",
            "X-Forwarded-For": "203.0.113.10",
        },
    )

    assert response.status_code == 200
    assert response.headers["Strict-Transport-Security"].startswith("max-age=")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]

    identity_cookie = next(
        value
        for value in response.headers.getlist("Set-Cookie")
        if value.startswith("companion_client_id=")
    )
    assert "Secure" in identity_cookie
    assert "HttpOnly" in identity_cookie
    assert "SameSite=Lax" in identity_cookie
