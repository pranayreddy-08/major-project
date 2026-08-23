from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.security import AuthenticatedUser, get_current_user
from app.main import app
from app.models import UserRole


@pytest.fixture
def authenticated_client():
    async def authenticated_analyst() -> AuthenticatedUser:
        return AuthenticatedUser(
            id=UUID("055cd878-67b8-5d5d-9ba8-f5ef678b002e"),
            username="test-analyst",
            full_name="Test Analyst",
            role=UserRole.analyst,
            active=True,
        )

    app.dependency_overrides[get_current_user] = authenticated_analyst
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_current_user, None)
