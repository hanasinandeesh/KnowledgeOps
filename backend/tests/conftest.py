from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.infrastructure.database.session import get_db
from app.main import app
from app.models import Base
from app.models.organization import Organization
from app.models.user import OrganizationMembership, User


@pytest.fixture(scope="function", autouse=True)
def test_storage_dir(tmp_path) -> Generator[None, None, None]:
    """Isolate document storage to a temporary directory for each test."""
    original_path = settings.DOCUMENT_STORAGE_PATH
    settings.DOCUMENT_STORAGE_PATH = tmp_path / "documents"
    yield
    settings.DOCUMENT_STORAGE_PATH = original_path


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Provides a fresh, isolated in-memory SQLite database session."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        if type(dbapi_connection).__module__.startswith("sqlite3"):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()

    Base.metadata.create_all(bind=test_engine)
    testing_session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )
    session = testing_session_factory()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient with get_db overridden to use test session."""
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db_session: Session) -> User:
    """Creates and returns an active test user."""
    user = User(
        email="test.user@example.com",
        full_name="Test User",
        password_hash=hash_password("ValidPassword123!"),
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_org(db_session: Session) -> Organization:
    """Creates and returns an active test organization."""
    org = Organization(
        name="Acme Corporation",
        slug="acme-corp",
        status="active",
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture(scope="function")
def test_membership(
    db_session: Session,
    test_user: User,
    test_org: Organization,
) -> OrganizationMembership:
    """Associates test_user with test_org with employee role."""
    membership = OrganizationMembership(
        organization_id=test_org.id,
        user_id=test_user.id,
        role="employee",
        status="active",
    )
    db_session.add(membership)
    db_session.commit()
    db_session.refresh(membership)
    return membership


@pytest.fixture(scope="function")
def auth_headers(test_user: User) -> dict[str, str]:
    """Returns valid Authorization Bearer header for test_user."""
    token = create_access_token(subject=test_user.id)
    return {"Authorization": f"Bearer {token}"}
