from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.rate_limit import SlidingWindowRateLimiter
from app.core.security import (
    AuthenticatedUser,
    create_access_token,
    decode_access_token,
    hash_password,
    require_roles,
    verify_password,
)
from app.main import app
from app.models import UserRole


def user(role: UserRole = UserRole.analyst) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=UUID("055cd878-67b8-5d5d-9ba8-f5ef678b002e"),
        username="security-test",
        full_name="Security Test",
        role=role,
        active=True,
    )


def test_passwords_use_argon2_and_plaintext_is_never_retained() -> None:
    encoded = hash_password("correct-horse-battery-staple")

    assert encoded.startswith("$argon2id$")
    assert "correct-horse-battery-staple" not in encoded
    assert verify_password("correct-horse-battery-staple", encoded)
    assert not verify_password("incorrect-password", encoded)


def test_access_token_has_verified_subject_role_and_expiration() -> None:
    token, expires_in = create_access_token(user())

    username, role = decode_access_token(token)
    assert username == "security-test"
    assert role is UserRole.analyst
    assert expires_in == 1800


def test_tampered_access_token_is_rejected() -> None:
    token, _ = create_access_token(user())

    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(f"{token[:-1]}x")
    assert exc_info.value.status_code == 401


def test_expired_access_token_is_rejected() -> None:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "username:security-test",
            "role": "analyst",
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now - timedelta(minutes=2),
            "exp": now - timedelta(minutes=1),
            "jti": "expired-security-test",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)
    assert exc_info.value.status_code == 401


def test_production_rejects_default_or_missing_service_secrets() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET"):
        Settings(_env_file=None, APP_ENVIRONMENT="production")


@pytest.mark.asyncio
async def test_role_dependency_rejects_analyst_from_admin_operation() -> None:
    admin_only = require_roles(UserRole.administrator)

    with pytest.raises(HTTPException) as exc_info:
        await admin_only(user())
    assert exc_info.value.status_code == 403
    assert (await admin_only(user(UserRole.administrator))).role is UserRole.administrator


def test_rate_limiter_returns_retry_after_when_window_is_full() -> None:
    limiter = SlidingWindowRateLimiter()

    assert limiter.check("client", 2)[0]
    assert limiter.check("client", 2)[0]
    allowed, retry_after = limiter.check("client", 2)
    assert not allowed
    assert retry_after >= 1


def test_sensitive_component_route_requires_bearer_token() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/intelligence/risk/score",
            json={
                "threat_confidence": 1,
                "asset_criticality": 1,
                "attack_stage": 1,
                "anomaly_level": 1,
                "observed_at": "2026-01-01T00:00:00Z",
                "as_of": "2026-01-01T00:00:00Z",
            },
        )
    assert response.status_code == 401


def test_openapi_documents_phase6_platform_surface() -> None:
    paths = app.openapi()["paths"]
    expected = {
        "/api/v1/auth/token",
        "/api/v1/auth/setup-status",
        "/api/v1/auth/setup",
        "/api/v1/auth/me",
        "/api/v1/sensors",
        "/api/v1/sensors/ingest",
        "/api/v1/platform/overview",
        "/api/v1/platform/events",
        "/api/v1/platform/alerts",
        "/api/v1/platform/incidents",
        "/api/v1/platform/analysis/run",
        "/api/v1/platform/workflows/recent",
        "/api/v1/platform/models",
        "/api/v1/platform/feedback",
        "/api/v1/platform/audit-logs",
    }
    assert expected <= set(paths)
