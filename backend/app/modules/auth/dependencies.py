from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, UnauthenticatedException
from app.core.security import decode_access_token
from app.infrastructure.database.session import get_db
from app.models.organization import Organization
from app.models.user import OrganizationMembership, User
from app.modules.auth.service import AuthService

http_bearer = HTTPBearer(auto_error=False)


@dataclass
class OrganizationContext:
    """Encapsulates the validated tenant context for an authenticated request."""

    organization: Organization
    membership: OrganizationMembership
    user: User

    @property
    def organization_id(self) -> str:
        return self.organization.id

    @property
    def role(self) -> str:
        return self.membership.role


def get_current_user(
    auth: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Extracts the Bearer token, validates it, and returns the active User."""
    if not auth or not auth.credentials:
        raise UnauthenticatedException("Not authenticated")

    payload = decode_access_token(auth.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthenticatedException("Invalid token claims")

    return AuthService.get_user_by_id(db, user_id=user_id)


def get_organization_context(
    x_organization_id: str | None = Header(
        default=None,
        alias="X-Organization-Id",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganizationContext:
    """Derives and validates active tenant context for the current user."""
    organization, membership = AuthService.resolve_organization_membership(
        db=db,
        user_id=current_user.id,
        organization_id=x_organization_id,
    )
    return OrganizationContext(
        organization=organization,
        membership=membership,
        user=current_user,
    )


def require_role(
    allowed_roles: list[str],
) -> Callable[[OrganizationContext], OrganizationContext]:
    """Dependency factory verifying user possesses an allowed tenant role."""

    def role_verifier(
        context: OrganizationContext = Depends(get_organization_context),
    ) -> OrganizationContext:
        if context.role not in allowed_roles:
            raise ForbiddenException(
                f"Role '{context.role}' does not have permission for this action"
            )
        return context

    return role_verifier
