from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """Payload for user login."""

    email: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="User email address",
    )
    password: str = Field(..., min_length=1, description="Plaintext password")


class TokenResponse(BaseModel):
    """Response returned upon successful authentication."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token lifespan in seconds")


class OrganizationMembershipItem(BaseModel):
    """Membership information for an organization the user belongs to."""

    model_config = ConfigDict(from_attributes=True)

    organization_id: str
    organization_name: str
    organization_slug: str
    role: str
    status: str


class UserMeResponse(BaseModel):
    """Authenticated user profile with active organization memberships."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    status: str
    created_at: datetime
    memberships: list[OrganizationMembershipItem] = Field(default_factory=list)


class CurrentOrganizationResponse(BaseModel):
    """Current resolved organization context for the authenticated user."""

    model_config = ConfigDict(from_attributes=True)

    organization_id: str
    name: str
    slug: str
    role: str
    status: str
