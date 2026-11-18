from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import (
    ForbiddenException,
    InvalidRequestException,
    UnauthenticatedException,
)
from app.core.security import verify_password
from app.models.organization import Organization
from app.models.user import OrganizationMembership, User


class AuthService:
    """Authentication and organization membership business logic."""

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User:
        """Authenticate a user by email and plaintext password.

        Returns the user if valid and active, otherwise raises
        UnauthenticatedException.
        """
        normalized_email = email.strip().lower()
        stmt = select(User).where(User.email == normalized_email)
        user = db.scalars(stmt).first()

        if user is None:
            raise UnauthenticatedException("Invalid email or password")

        if not verify_password(password, user.password_hash):
            raise UnauthenticatedException("Invalid email or password")

        if user.status != "active":
            raise UnauthenticatedException("User account is inactive")

        return user

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> User:
        """Fetch an active user by their UUID primary key."""
        stmt = select(User).where(User.id == user_id)
        user = db.scalars(stmt).first()

        if user is None or user.status != "active":
            raise UnauthenticatedException("User account not found or inactive")

        return user

    @staticmethod
    def get_user_memberships(
        db: Session,
        user_id: str,
    ) -> list[OrganizationMembership]:
        """Fetch all active organization memberships with their organizations."""
        stmt = (
            select(OrganizationMembership)
            .options(joinedload(OrganizationMembership.organization))
            .join(Organization)
            .where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.status == "active",
                Organization.status == "active",
            )
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def resolve_organization_membership(
        db: Session,
        user_id: str,
        organization_id: str | None = None,
    ) -> tuple[Organization, OrganizationMembership]:
        """Resolve and validate active organization context for a user."""
        if organization_id is None:
            active_memberships = AuthService.get_user_memberships(db, user_id)
            if not active_memberships:
                raise ForbiddenException(
                    "User does not have access to any active organization"
                )
            if len(active_memberships) > 1:
                raise InvalidRequestException(
                    "X-Organization-Id header is required because user belongs "
                    "to multiple organizations"
                )
            membership = active_memberships[0]
            return membership.organization, membership

        stmt = (
            select(OrganizationMembership)
            .options(joinedload(OrganizationMembership.organization))
            .join(Organization)
            .where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == organization_id,
            )
        )
        membership = db.scalars(stmt).first()

        if membership is None or membership.status != "active":
            raise ForbiddenException("User does not have access to this organization")

        organization = membership.organization
        if organization is None or organization.status != "active":
            raise ForbiddenException("Organization is inactive or not found")

        return organization, membership
