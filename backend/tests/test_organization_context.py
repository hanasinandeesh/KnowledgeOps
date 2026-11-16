from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.organization import Organization
from app.models.user import OrganizationMembership, User
from app.modules.auth.dependencies import (
    OrganizationContext,
    require_role,
)


# Temporary test-only endpoint to verify role authorization dependency
@app.get("/api/v1/test-admin-only")
def admin_only_endpoint(
    context: OrganizationContext = Depends(require_role(["organization_admin"])),
) -> dict[str, str]:
    return {"message": "Welcome Admin", "role": context.role}


def test_get_current_org_with_valid_header(
    client: TestClient,
    test_user: User,
    test_org: Organization,
    test_membership: OrganizationMembership,
    auth_headers: dict[str, str],
) -> None:
    """GET /api/v1/organizations/current with matching X-Organization-Id succeeds."""
    headers = {**auth_headers, "X-Organization-Id": test_org.id}
    response = client.get("/api/v1/organizations/current", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["organization_id"] == test_org.id
    assert data["name"] == test_org.name
    assert data["role"] == "employee"


def test_get_current_org_single_membership_default(
    client: TestClient,
    test_org: Organization,
    test_membership: OrganizationMembership,
    auth_headers: dict[str, str],
) -> None:
    """When X-Organization-Id is omitted, user with single membership defaults to it."""
    response = client.get("/api/v1/organizations/current", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["organization_id"] == test_org.id
    assert data["name"] == test_org.name


def test_get_current_org_multiple_memberships_requires_header(
    client: TestClient,
    db_session: Session,
    test_user: User,
    test_org: Organization,
    test_membership: OrganizationMembership,
    auth_headers: dict[str, str],
) -> None:
    """When user belongs to multiple organizations and omits header, return 400."""
    second_org = Organization(name="Beta Corp", slug="beta-corp", status="active")
    db_session.add(second_org)
    db_session.commit()

    second_membership = OrganizationMembership(
        organization_id=second_org.id,
        user_id=test_user.id,
        role="employee",
        status="active",
    )
    db_session.add(second_membership)
    db_session.commit()

    # Omit header -> 400
    response = client.get("/api/v1/organizations/current", headers=auth_headers)
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "INVALID_REQUEST"
    assert "X-Organization-Id" in data["error"]["message"]

    # Provide explicit header -> 200 for selected org
    headers = {**auth_headers, "X-Organization-Id": second_org.id}
    response2 = client.get("/api/v1/organizations/current", headers=headers)
    assert response2.status_code == 200
    assert response2.json()["organization_id"] == second_org.id


def test_cross_tenant_access_blocked(
    client: TestClient,
    db_session: Session,
    test_membership: OrganizationMembership,
    auth_headers: dict[str, str],
) -> None:
    """Accessing an organization the user does NOT belong to returns 403 FORBIDDEN."""
    foreign_org = Organization(
        name="Foreign Corp",
        slug="foreign-corp",
        status="active",
    )
    db_session.add(foreign_org)
    db_session.commit()

    headers = {**auth_headers, "X-Organization-Id": foreign_org.id}
    response = client.get("/api/v1/organizations/current", headers=headers)
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "FORBIDDEN"
    assert "does not have access" in data["error"]["message"]


def test_inactive_membership_blocked(
    client: TestClient,
    db_session: Session,
    test_org: Organization,
    test_membership: OrganizationMembership,
    auth_headers: dict[str, str],
) -> None:
    """Inactive membership returns 403 FORBIDDEN."""
    test_membership.status = "suspended"
    db_session.commit()

    headers = {**auth_headers, "X-Organization-Id": test_org.id}
    response = client.get("/api/v1/organizations/current", headers=headers)
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "FORBIDDEN"


def test_inactive_organization_blocked(
    client: TestClient,
    db_session: Session,
    test_org: Organization,
    test_membership: OrganizationMembership,
    auth_headers: dict[str, str],
) -> None:
    """Inactive organization returns 403 FORBIDDEN."""
    test_org.status = "archived"
    db_session.commit()

    headers = {**auth_headers, "X-Organization-Id": test_org.id}
    response = client.get("/api/v1/organizations/current", headers=headers)
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "FORBIDDEN"


def test_require_role_enforcement(
    client: TestClient,
    db_session: Session,
    test_org: Organization,
    test_membership: OrganizationMembership,
    auth_headers: dict[str, str],
) -> None:
    """require_role blocks employee and allows organization_admin."""
    headers = {**auth_headers, "X-Organization-Id": test_org.id}

    # test_membership currently has role="employee" -> 403
    response = client.get("/api/v1/test-admin-only", headers=headers)
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "FORBIDDEN"
    assert "Role 'employee' does not have permission" in data["error"]["message"]

    # Upgrade to organization_admin -> 200
    test_membership.role = "organization_admin"
    db_session.commit()

    response_admin = client.get("/api/v1/test-admin-only", headers=headers)
    assert response_admin.status_code == 200
    assert response_admin.json()["role"] == "organization_admin"
