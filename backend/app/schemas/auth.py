"""
Authentication Schemas
======================

Schemas for signup, login, and manager invitations
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from pydantic import constr, EmailStr


class SignupRequest(BaseModel):
    """
    Owner signup request.
    
    When owner signs up:
    - Email: login email
    - Password: min 8 chars (will be hashed with bcrypt)
    - Business name: their supermarket name
    - Country: defaults to Rwanda(admin can change)
    
    System will:
    1. Create Business record
    2. Create User record (role=owner)
    3. Auto-create DEFAULT location
    4. Return JWT token in httpOnly cookie
    """
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=255, description="Minimum 8 characters")
    business_name: str = Field(..., min_length=1, max_length=255)
    country: str = Field(default="Rwanda")
    phone: Optional[str] = Field(None, max_length=20, description="Business phone number")
    locations: Optional[List[dict]] = Field(
        None,
        description="Optional list of branch locations to create on signup. Each item may include name, city, manager_name, manager_email, phone, and location_code."
    )


class LoginRequest(BaseModel):
    """
    User login (Owner or Manager).
    
    Simple email + password.
    System validates and returns JWT in httpOnly cookie.
    """
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """
    User info sent to frontend (NO PASSWORD!).
    
    Frontend knows:
    - User ID
    - Email
    - Role (owner/manager)
    - Which business they belong to
    - Which locations they can access
    - is_active status
    """
    id: int
    email: str
    business_id: Optional[int] = None
    role: str  # "owner" or "manager"
    assigned_location_ids: Optional[List[int]] = None  # None = owner (all locations)
    is_platform_admin: bool = False
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """
    Response after successful login/signup.
    
    (Actual token goes in httpOnly cookie, not in response body)
    """
    message: str  # "Login successful" or "Signup successful"
    user: UserResponse


class InviteManagerRequest(BaseModel):
    """
    Owner invites manager to a location.
    
    POST /locations/{location_id}/invite-manager
    {email: "manager@example.com"}
    
    System:
    1. Creates InviteToken with expiration (7 days)
    2. Emails manager: "You're invited! Click: domain/invite?token=abc123"
    3. Manager clicks → /invite-signup with token
    4. Manager sets password → User account created
    """
    email: EmailStr


class AcceptInviteRequest(BaseModel):
    """
    Manager accepts invite and creates their account.
    
    POST /auth/accept-invite?token=abc123
    {password, name}
    
    System:
    1. Validates token (not expired, not used)
    2. Creates User account
    3. Marks InviteToken as is_used=True
    4. Returns JWT in httpOnly cookie
    """
    password: str = Field(..., min_length=8, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
