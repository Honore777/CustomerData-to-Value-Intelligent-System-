
"""
Authentication Router
======================

Handles user registration (Owner), login, JWT token management, and manager invitations.

Key concepts:
- httpOnly cookies: Token stored securely, JS cannot access
- JWT tokens: Stateless auth, no session storage needed
- Password hashing: bcrypt makes guessing impossible
- Role-based: Owner sees all locations, Manager sees assigned only
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from jose import JWTError, jwt  # For JWT tokens
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
import bcrypt
import logging
import secrets  # For random invite tokens
from uuid import uuid4
import os
from datetime import datetime, timedelta as _timedelta

from app.config import settings
from app.database import get_db
from app.models import Business, User, Location, InviteToken
from app.utils.mailer import send_email
from app.schemas import (
    SignupRequest,
    LoginRequest,
    UserResponse,
    TokenResponse,
    InviteManagerRequest,
    AcceptInviteRequest,
)

logger = logging.getLogger(__name__)

# ===== CONFIGURATION =====
ALGORITHM = "HS256"

# ===== PASSWORD HASHING =====
# Use argon2-cffi directly for new hashes and keep bcrypt verification support
# for legacy hashes that may already exist in the database.
password_hasher = PasswordHasher()


def _should_be_platform_admin(email: str) -> bool:
    return email.strip().lower() in settings.platform_admin_emails


def sync_platform_admin_flag(session: Session, user: User) -> User:
    expected_value = user.is_platform_admin or _should_be_platform_admin(user.email)

    if user.is_platform_admin != expected_value:
        user.is_platform_admin = expected_value
        session.add(user)
        session.commit()
        session.refresh(user)

    return user


def set_auth_cookie(response: JSONResponse, access_token: str) -> None:
    cookie_kwargs = {
        "key": "access_token",
        "value": access_token,
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "max_age": settings.access_token_expire_minutes * 60,
    }

    if settings.cookie_domain:
        cookie_kwargs["domain"] = settings.cookie_domain

    response.set_cookie(**cookie_kwargs)

def hash_password(password: str) -> str:
    """
    Hash a plain password using the current preferred algorithm.
    
    Example:
        plain = "mypassword123"
        hashed = hash_password(plain)
        # hashed = "$argon2id$v=19$m=65536,t=3,p=4$..." (salted, never same twice)
    """
    return password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Example:
        if verify_password("mypassword123", user.password_hash):
            # Password is correct!
    """
    if hashed_password.startswith("$argon2"):
        try:
            return password_hasher.verify(hashed_password, plain_password)
        except (VerifyMismatchError, InvalidHashError):
            return False

    if hashed_password.startswith("$2a$") or hashed_password.startswith("$2b$") or hashed_password.startswith("$2y$"):
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except ValueError:
            return False

    return False


# ===== JWT TOKEN MANAGEMENT =====
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Claims dictionary (e.g., {"sub": user_id})
        expires_delta: How long token is valid
    
    Returns:
        JWT token string like: eyJhbGciOiJIUzI1NiIs...
    
    Token structure:
        Header: {alg: HS256, typ: JWT}
        Payload: {sub: user_id, exp: expiration_time, other_data}
        Signature: HMAC(header.payload, SECRET_KEY)
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    if "sub" in to_encode and to_encode["sub"] is not None:
        to_encode["sub"] = str(to_encode["sub"])

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Dictionary with token claims (e.g., {"sub": user_id, "exp": ...})
    
    Raises:
        JWTError: If token invalid, expired, or signature doesn't match
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id_raw = payload.get("sub")
        if user_id_raw is None:
            raise JWTError("Token missing user_id claim")

        try:
            user_id = int(user_id_raw)
        except (TypeError, ValueError) as exc:
            raise JWTError("Token subject must be a numeric user id") from exc

        return {"user_id": user_id}
    except JWTError as e:
        logger.warning(f"Invalid token: {e}")
        raise


# ===== ROUTER SETUP =====
router = APIRouter(prefix="/auth", tags=["Authentication"])



# ===== DEPENDENCY INJECTION =====
# This validates cookies and returns current user for protected routes

async def get_current_user(request: Request, session: Session = Depends(get_db)) -> User:
    """
    Dependency to extract current authenticated user from httpOnly cookie.
    
    HOW IT WORKS:
    1. Browser sends request with httpOnly cookie automatically
    2. FastAPI extracts cookie from request.cookies
    3. We decode JWT from cookie
    4. We query database for user
    5. Return user object
    
    USE IN ROUTES:
    @router.get("/protected")
    async def protected_route(current_user: User = Depends(get_current_user)):
        # current_user is automatically injected!
        return {"user_id": current_user.id}
    
    Raises:
        HTTPException 401: If cookie missing or token invalid
        HTTPException 403: If user inactive
    """
    # Try to get token from httpOnly cookie
    token = request.cookies.get("access_token")
    if not token:
        logger.warning("❌ No access_token cookie found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please login."
        )
    
    # Decode JWT token
    try:
        payload = decode_token(token)
        user_id = payload.get("user_id")
    except JWTError:
        logger.warning("❌ Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please login again."
        )
    
    # Query database for user
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"❌ User not found: user_id={user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    user = sync_platform_admin_flag(session, user)
    
    # Check if user is active (admin can deactivate)
    if not user.is_active:
        logger.warning(f"❌ User inactive: user_id={user_id}, email={user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Contact admin to reactivate."
        )

    if not user.is_platform_admin and user.business_id is not None:
        business = session.query(Business).filter(Business.id == user.business_id).first()
        if business and not business.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This business account is inactive. Contact admin.",
            )
    
    logger.info(f"✅ User authenticated: user_id={user.id}, email={user.email}")
    return user


def require_platform_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin access is required.",
        )

    return current_user



# ===== ROUTE 1: SIGNUP =====
@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignupRequest, session: Session = Depends(get_db)):
    """
    Owner signup endpoint.
    
    WORKFLOW:
    1. Owner sends: email, password, business_name, country
    2. System creates Business record
    3. System creates DEFAULT location (free first location)
    4. System creates User record (role=owner)
    5. System generates JWT and sets httpOnly cookie
    6. Returns user info
    """
    logger.info(f"📝 Owner signup: email={request.email}, business={request.business_name}")
    
    # Step 1: Check if email already exists
    existing_user = session.query(User).filter(User.email == request.email).first()
    if existing_user:
        logger.warning(f"❌ Email already registered: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered. Try login instead."
        )
    
    # Step 2: Create Business record
    new_business = Business(
        name=request.business_name,
        email=request.email,
        phone=request.phone,
        country=request.country,
        currency="RWF" if request.country == "Rwanda" else "USD",
        is_active=True,
        subscription_status="trial",
        trial_started_at=date.today(),
        trial_ends_at=date.today() + timedelta(days=14),
    )
    session.add(new_business)
    session.flush()  # Get ID without committing
    
    # Step 3: Create either the provided branch locations or a single default 'Main' location
    frontend_base = os.getenv("FRONTEND_URL", "http://localhost:5173")
    provided_locations = getattr(request, "locations", None) or []
    if len(provided_locations) == 0:
        # No locations provided — create a default Main location
        default_location = Location(
            business_id=new_business.id,
            location_code="MAIN",
            name="Main",
            city=request.country,
            is_active=True
        )
        session.add(default_location)
        session.flush()
    else:
        # Create any provided branch locations and optionally send invites
        for loc in provided_locations:
            loc_code = loc.get("location_code") or None
            loc_name = loc.get("name") or loc.get("location_name") or "Branch"
            loc_city = loc.get("city")
            loc_phone = loc.get("phone")
            manager_email = loc.get("manager_email")
            manager_name = loc.get("manager_name")

            new_loc = Location(
                business_id=new_business.id,
                location_code=loc_code or f"LOC_{secrets.token_hex(4)}",
                name=loc_name,
                city=loc_city,
                phone=loc_phone,
                is_active=True
            )
            session.add(new_loc)
            session.flush()

            if manager_email:
                # Create invite token for manager to accept invite
                token = str(uuid4())
                expires_at = datetime.utcnow() + _timedelta(days=7)
                invite = InviteToken(
                    email=manager_email,
                    location_id=new_loc.id,
                    business_id=new_business.id,
                    token=token,
                    expires_at=expires_at
                )
                session.add(invite)
                session.flush()

                # Send invite email if mail configured; otherwise it's a no-op
                try:
                    invite_link = f"{frontend_base.rstrip('/')}#/invite?token={token}"
                    subject = f"You're invited to manage {new_business.name} - {new_loc.name}"
                    body = (
                        f"Hello {manager_name or ''},\n\n"
                        f"You've been invited to manage the location '{new_loc.name}' for {new_business.name}.\n"
                        f"Click the link to accept the invite and create your account:\n\n{invite_link}\n\n"
                        "This link expires in 7 days.\n\n"
                        "If you did not expect this email, ignore it."
                    )
                    send_email(subject, body, manager_email)
                except Exception as e:
                    logger.exception(f"Failed to send manager invite to {manager_email}: {e}")
    
    # Step 4: Create User record (role=owner)
    hashed_password = hash_password(request.password)
    new_user = User(
        email=request.email,
        password_hash=hashed_password,
        business_id=new_business.id,
        role="owner",
        assigned_location_ids=None,  # None = can see all
        is_platform_admin=_should_be_platform_admin(request.email),
        is_active=True
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    logger.info(f"✅ User created: user_id={new_user.id}, business_id={new_business.id}")
    
    # Step 5: Generate JWT token
    access_token = create_access_token(data={"sub": new_user.id})
    
    # Step 6: Create response with cookie
    response = JSONResponse(
        content=jsonable_encoder(TokenResponse(
            message="Signup successful! Welcome to Supermarket AI.",
            user=UserResponse.from_orm(new_user)
        )),
        status_code=status.HTTP_201_CREATED
    )
    
    # Set httpOnly cookie (browser stores, JS cannot read)
    set_auth_cookie(response, access_token)
    
    logger.info(f"✅ httpOnly cookie set, signup complete")
    return response



# ===== ROUTE 2: LOGIN =====
@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, session: Session = Depends(get_db)):
    """
    User login endpoint.

    FLOW:
    1. Receive email + password from frontend
    2. Find matching user in database
    3. Compare plain password with stored hashed password
    4. Create JWT token if credentials are valid
    5. Put JWT into httpOnly cookie
    6. Return user info to frontend
    """

    logger.info(f"Login attempt for email={request.email}")

    # Step 1: find the user by email
    user = session.query(User).filter(User.email == request.email).first()

    # Security rule:
    # do not reveal whether the email or password was wrong
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    user = sync_platform_admin_flag(session, user)

    # Step 2: verify password against bcrypt hash
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Step 3: check user status
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Contact admin."
        )

    # Optional but important:
    # if the business itself is deactivated, block login too
    business = session.query(Business).filter(Business.id == user.business_id).first()
    if business and not business.is_active and not user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This business account is inactive. Contact admin."
        )

    # Step 4: create JWT token
    access_token = create_access_token(data={"sub": user.id})

    # Step 5: create response body
    response = JSONResponse(
        content=jsonable_encoder(TokenResponse(
            message="Login successful",
            user=UserResponse.from_orm(user)
        )),
        status_code=status.HTTP_200_OK
    )

    # Step 6: set httpOnly cookie
    set_auth_cookie(response, access_token)

    logger.info(f"Login successful for user_id={user.id}")
    return response



# ===== ROUTE 3: GET CURRENT USER =====
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user info.
    
    HOW IT WORKS:
    1. Frontend calls GET /auth/me
    2. Browser auto-sends httpOnly cookie
    3. get_current_user dependency:
       - Extracts JWT from cookie
       - Decodes JWT (validates signature)
       - Gets user from database
       - Returns user object
    4. We return user info
    
    REQUIRES: Valid httpOnly cookie
    
    Use cases:
    - Frontend wants to check who is logged in
    - Frontend loads user data on page refresh
    - Verify session is still valid
    
    Returns:
        UserResponse with user details
    
    Raises:
        HTTPException 401: If not authenticated
        HTTPException 403: If user inactive
    """
    logger.info(f"📋 Get current user: user_id={current_user.id}, email={current_user.email}")
    return UserResponse.from_orm(current_user)




# ===== ROUTE 4: ACCEPT MANAGER INVITE =====
@router.post("/accept-invite", response_model=TokenResponse)
async def accept_invite(
    token: str,
    request: AcceptInviteRequest,
    session: Session = Depends(get_db)
):
    """
    Manager accepts invite and creates their account.
    
    WORKFLOW:
    1. Manager receives email with invite link: domain/invite?token=abc123xyz
    2. Manager fills form: password + name
    3. Frontend calls: POST /auth/accept-invite?token=abc123xyz {password, name}
    4. System validates token
    5. System creates User account
    6. System marks token as used
    7. System returns JWT in httpOnly cookie
    
    Args:
        token: Invite token from email (query parameter)
        request: AcceptInviteRequest with password + name
        session: Database session
    
    Returns:
        TokenResponse with user info
    
    Raises:
        HTTPException 404: If token not found
        HTTPException 410: If token already used
        HTTPException 400: If token expired
    """
    logger.info(f"👤 Manager accepting invite: token={token[:10]}...")
    
    # Step 1: Find invite token
    invite_token = session.query(InviteToken).filter(
        InviteToken.token == token
    ).first()
    
    if not invite_token:
        logger.warning(f"❌ Invalid invite token: {token}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invite token. Check your email link."
        )
    
    # Step 2: Check if already used
    if invite_token.is_used:
        logger.warning(f"❌ Invite token already used: {token}")
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This invite link has already been used."
        )
    
    # Step 3: Check if expired
    if datetime.utcnow() > invite_token.expires_at:
        logger.warning(f"❌ Invite token expired: {token}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite link has expired. Ask owner for new invite."
        )
    
    # Step 4: Check if user already exists with this email
    existing_user = session.query(User).filter(
        User.email == invite_token.email
    ).first()
    
    if existing_user:
        logger.warning(f"❌ User already exists: {invite_token.email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered."
        )
    
    # Step 5: Create User account (role=manager)
    hashed_password = hash_password(request.password)
    new_user = User(
        email=invite_token.email,
        password_hash=hashed_password,
        business_id=invite_token.business_id,
        role="manager",  # ← Manager, not owner
        assigned_location_ids=[invite_token.location_id],  # Can only see this location
        is_active=True
    )
    session.add(new_user)
    session.flush()
    
    # Step 6: Mark invite token as used
    invite_token.is_used = True
    session.commit()
    session.refresh(new_user)
    
    logger.info(f"✅ Manager created: user_id={new_user.id}, email={invite_token.email}, location_id={invite_token.location_id}")
    
    # Step 7: Generate JWT token
    access_token = create_access_token(data={"sub": new_user.id})
    
    # Step 8: Create response with cookie
    response = JSONResponse(
        content=jsonable_encoder(TokenResponse(
            message="Welcome! Your account is ready.",
            user=UserResponse.from_orm(new_user)
        )),
        status_code=status.HTTP_201_CREATED
    )
    
    # Set httpOnly cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=86400
    )
    
    logger.info(f"✅ Manager invitation accepted: user_id={new_user.id}")
    return response


@router.post('/logout')
async def logout():
    response=JSONResponse(
        content={"message":"Logout successful"},
        status_code=status.HTTP_200_OK
    )

    response.delete_cookie(
        key='access_token',
        httponly=True,
        secure=False,
        samesite='lax'
    )

    return response