from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.infrastructure.database.session import get_db
from app.models.user import User
from app.modules.auth.dependencies import (
    OrganizationContext,
    get_current_user,
    get_organization_context,
)
from app.modules.auth.schemas import (
    CurrentOrganizationResponse,
    LoginRequest,
    OrganizationMembershipItem,
    TokenResponse,
    UserMeResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(tags=["Authentication & Identity"])


@router.post("/auth/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email and password to obtain a JWT access token."""
    user = AuthService.authenticate_user(
        db=db,
        email=payload.email,
        password=payload.password,
    )
    access_token = create_access_token(subject=user.id)
    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in_seconds,
    )


@router.get("/users/me", response_model=UserMeResponse)
def get_user_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserMeResponse:
    """Return the authenticated user profile and active memberships."""
    memberships = AuthService.get_user_memberships(db=db, user_id=current_user.id)

    membership_items = [
        OrganizationMembershipItem(
            organization_id=m.organization_id,
            organization_name=m.organization.name,
            organization_slug=m.organization.slug,
            role=m.role,
            status=m.status,
        )
        for m in memberships
    ]

    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        status=current_user.status,
        created_at=current_user.created_at,
        memberships=membership_items,
    )


@router.get("/organizations/current", response_model=CurrentOrganizationResponse)
def get_current_organization(
    context: OrganizationContext = Depends(get_organization_context),
) -> CurrentOrganizationResponse:
    """Return current tenant organization details and role."""
    return CurrentOrganizationResponse(
        organization_id=context.organization.id,
        name=context.organization.name,
        slug=context.organization.slug,
        role=context.role,
        status=context.organization.status,
    )
