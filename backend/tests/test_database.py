from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.models import (
    Base,
    Department,
    Organization,
    OrganizationMembership,
    User,
    UserDepartment,
)


def test_tables_registered_in_metadata() -> None:
    """All 5 foundational tables must be defined in Base.metadata."""
    expected_tables = {
        "organizations",
        "departments",
        "users",
        "organization_memberships",
        "user_departments",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(actual_tables)


def test_create_and_query_organization_and_user(db_session: Session) -> None:
    """Verify creating and querying Organization and User records."""
    org = Organization(name="Acme Corp", slug="acme-corp")
    user = User(
        email="alice@acme.com",
        full_name="Alice Smith",
        password_hash="fakehash123",
    )
    db_session.add_all([org, user])
    db_session.commit()

    saved_org = db_session.scalar(
        select(Organization).where(Organization.slug == "acme-corp")
    )
    assert saved_org is not None
    assert saved_org.name == "Acme Corp"
    assert saved_org.status == "active"
    assert saved_org.id is not None
    assert saved_org.created_at is not None

    saved_user = db_session.scalar(select(User).where(User.email == "alice@acme.com"))
    assert saved_user is not None
    assert saved_user.full_name == "Alice Smith"


def test_department_unique_name_per_organization(db_session: Session) -> None:
    """Departments with the same name in the same organization must be rejected."""
    org = Organization(name="Acme Corp", slug="acme-dept-test")
    db_session.add(org)
    db_session.commit()

    dept1 = Department(organization_id=org.id, name="Engineering")
    dept2 = Department(organization_id=org.id, name="Engineering")

    db_session.add(dept1)
    db_session.commit()

    db_session.add(dept2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_foreign_key_enforcement(db_session: Session) -> None:
    """Inserting a membership with a non-existent org must raise IntegrityError."""
    user = User(
        email="bob@acme.com",
        full_name="Bob Jones",
        password_hash="fakehash456",
    )
    db_session.add(user)
    db_session.commit()

    invalid_membership = OrganizationMembership(
        organization_id="non-existent-org-id",
        user_id=user.id,
        role="employee",
    )
    db_session.add(invalid_membership)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_organization_membership_unique_constraint(db_session: Session) -> None:
    """A user cannot have duplicate memberships in the same organization."""
    org = Organization(name="Beta Corp", slug="beta-corp")
    user = User(
        email="carol@beta.com",
        full_name="Carol White",
        password_hash="fakehash789",
    )
    db_session.add_all([org, user])
    db_session.commit()

    m1 = OrganizationMembership(
        organization_id=org.id,
        user_id=user.id,
        role="employee",
    )
    m2 = OrganizationMembership(
        organization_id=org.id,
        user_id=user.id,
        role="department_manager",
    )
    db_session.add(m1)
    db_session.commit()

    db_session.add(m2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cascade_delete_organization(db_session: Session) -> None:
    """Deleting an organization must cascade delete its departments and memberships."""
    org = Organization(name="Gamma Corp", slug="gamma-corp")
    user = User(
        email="dave@gamma.com",
        full_name="Dave Miller",
        password_hash="fakehash321",
    )
    db_session.add_all([org, user])
    db_session.commit()

    dept = Department(organization_id=org.id, name="Operations")
    membership = OrganizationMembership(
        organization_id=org.id,
        user_id=user.id,
        role="employee",
    )
    db_session.add_all([dept, membership])
    db_session.flush()

    user_dept = UserDepartment(
        organization_id=org.id,
        user_id=user.id,
        department_id=dept.id,
        role="member",
    )
    db_session.add(user_dept)
    db_session.commit()

    # Delete organization
    db_session.delete(org)
    db_session.commit()

    # Verify children are deleted
    depts = db_session.scalars(
        select(Department).where(Department.organization_id == org.id)
    ).all()
    assert len(depts) == 0

    memberships = db_session.scalars(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org.id
        )
    ).all()
    assert len(memberships) == 0


def test_get_db_generator_lifecycle() -> None:
    """get_db() yields an active session and closes it cleanly upon completion."""
    gen = get_db()
    db = next(gen)
    assert isinstance(db, Session)

    with patch.object(db, "close", wraps=db.close) as mock_close:
        try:
            next(gen)
        except StopIteration:
            pass
        mock_close.assert_called_once()
