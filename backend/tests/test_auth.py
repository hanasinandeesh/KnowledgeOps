from datetime import timedelta

import jwt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.organization import Organization
from app.models.user import OrganizationMembership, User


def test_password_hash_verification() -> None:
    """Verifies that bcrypt correctly hashes and verifies passwords in constant time."""
    raw_password = "SuperSecurePassword123!"
    hashed = hash_password(raw_password)

    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False


def test_login_success(client: TestClient, test_user: User) -> None:
    """POST /api/v1/auth/login with valid credentials returns 200 and access token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "ValidPassword123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600

    # Token can be decoded
    payload = decode_access_token(data["access_token"])
    assert payload["sub"] == test_user.id
    assert payload["type"] == "access"


def test_login_incorrect_password(client: TestClient, test_user: User) -> None:
    """POST /api/v1/auth/login with incorrect password returns 401 UNAUTHENTICATED."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "WrongPassword999!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHENTICATED"
    assert "Invalid email or password" in data["error"]["message"]


def test_login_unknown_user(client: TestClient, test_user: User) -> None:
    """POST /api/v1/auth/login with unknown email returns generic 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "AnyPassword123!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHENTICATED"
    assert "Invalid email or password" in data["error"]["message"]


def test_login_inactive_user(client: TestClient, db_session: Session) -> None:
    """POST /api/v1/auth/login with inactive user account returns 401."""
    inactive_user = User(
        email="inactive@example.com",
        full_name="Inactive User",
        password_hash=hash_password("Password123!"),
        status="suspended",
    )
    db_session.add(inactive_user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "Password123!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHENTICATED"
    assert "inactive" in data["error"]["message"]


def test_login_missing_fields_validation_error(client: TestClient) -> None:
    """POST /api/v1/auth/login with missing fields returns 422 VALIDATION_ERROR."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "invalid-request"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_jwt_expired_token_rejected(client: TestClient, test_user: User) -> None:
    """An expired JWT token is rejected with 401 UNAUTHENTICATED."""
    expired_token = create_access_token(
        subject=test_user.id,
        expires_delta=timedelta(seconds=-10),
    )
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHENTICATED"
    assert "expired" in data["error"]["message"].lower()


def test_jwt_tampered_token_rejected(client: TestClient, test_user: User) -> None:
    """A token signed with a different key or modified payload is rejected."""
    # Token signed with forged key (32+ bytes to avoid key length warning)
    forged_token = jwt.encode(
        {"sub": test_user.id, "type": "access", "exp": 9999999999, "iat": 1000000000},
        "wrong-secret-key-that-is-at-least-32-chars-long",
        algorithm="HS256",
    )
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {forged_token}"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHENTICATED"


def test_unauthenticated_request_rejected(client: TestClient) -> None:
    """Accessing protected endpoints without an Authorization header returns 401."""
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHENTICATED"


def test_get_users_me_success(
    client: TestClient,
    test_user: User,
    test_org: Organization,
    test_membership: OrganizationMembership,
    auth_headers: dict[str, str],
) -> None:
    """GET /api/v1/users/me returns authenticated user details and memberships."""
    response = client.get("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email
    assert data["full_name"] == test_user.full_name
    assert len(data["memberships"]) == 1
    assert data["memberships"][0]["organization_id"] == test_org.id
    assert data["memberships"][0]["organization_name"] == test_org.name
    assert data["memberships"][0]["role"] == "employee"
