"""Authentication endpoints.

Flow:
- Register: POST /auth/register with {email, username, password, full_name?}
  Returns: UserResponse (no token, user must verify email first)
  
- Login: POST /auth/login with {email, password}
  Returns: Token {access_token, refresh_token, token_type: "bearer"}
  
- Verify Email: POST /auth/verify-email with {email, code}
  Returns: {message, verified: true}
"""

import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core import get_db, create_access_token, create_refresh_token, verify_password, get_password_hash
from app.models.user import User
from app.schemas.user import (
    UserCreate, UserLogin, UserResponse, Token,
    EmailVerificationRequest, PasswordResetRequest, PasswordResetConfirm, GoogleOAuthRequest
)
from app.services.email_service import (
    send_verification_email, send_password_reset_email, generate_verification_code
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new user and send verification email.
    
    Request body: {email, username, password, full_name?}
    Response: UserResponse (no token - user must verify email first)
    """
    try:
        logger.info(f"[REGISTER] Attempting registration for email: {user_data.email}, username: {user_data.username}")
        
        # Check if email already exists
        result = await db.execute(select(User).where(User.email == user_data.email))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            logger.warning(f"[REGISTER] Registration failed: Email already exists - {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if username already exists
        result = await db.execute(select(User).where(User.username == user_data.username))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            logger.warning(f"[REGISTER] Registration failed: Username already taken - {user_data.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Generate verification code
        verification_code = generate_verification_code()
        code_expires = datetime.utcnow() + timedelta(minutes=15)
        
        # Hash password (never store plain text)
        hashed_password = get_password_hash(user_data.password)
        
        # Create new user (not verified yet)
        new_user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            email_verified=False,
            email_verification_code=verification_code,
            email_verification_code_expires=code_expires,
            is_active=True,  # User can login but needs to verify email
        )
        
        db.add(new_user)
        try:
            await db.commit()
            await db.refresh(new_user)
            logger.info(f"[REGISTER] User created successfully - ID: {new_user.id}, email: {user_data.email}")
        except IntegrityError as e:
            await db.rollback()
            logger.error(f"[REGISTER] Database integrity error during registration: {e}", exc_info=True)
            # Check which constraint failed
            error_str = str(e).lower()
            if 'email' in error_str or 'unique' in error_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            elif 'username' in error_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Registration failed due to database constraint"
                )
        
        # Send verification email (don't fail registration if email fails)
        try:
            await send_verification_email(user_data.email, verification_code)
            logger.info(f"[REGISTER] Verification email sent to: {user_data.email}")
        except Exception as e:
            logger.error(f"[REGISTER] Failed to send verification email to {user_data.email}: {e}", exc_info=True)
            # Don't fail registration if email sending fails - user can request resend
        
        return new_user
        
    except HTTPException:
        # Re-raise HTTP exceptions (they're intentional)
        raise
    except Exception as e:
        logger.error(f"[REGISTER] Unexpected error during registration for {user_data.email}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again later."
        )


@router.post("/verify-email", response_model=dict)
async def verify_email(verification_data: EmailVerificationRequest, db: AsyncSession = Depends(get_db)):
    """Verify user email with 6-digit code."""
    result = await db.execute(select(User).where(User.email == verification_data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.email_verified:
        return {"message": "Email already verified", "verified": True}
    
    # Check if code is valid
    if not user.email_verification_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No verification code found. Please request a new one."
        )
    
    if user.email_verification_code != verification_data.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Check if code expired
    if user.email_verification_code_expires and user.email_verification_code_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new one."
        )
    
    # Verify email
    user.email_verified = True
    user.email_verification_code = None
    user.email_verification_code_expires = None
    await db.commit()
    
    return {"message": "Email verified successfully", "verified": True}


@router.post("/resend-verification", response_model=dict)
async def resend_verification(email: str, db: AsyncSession = Depends(get_db)):
    """Resend verification code."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.email_verified:
        return {"message": "Email already verified"}
    
    # Generate new code
    verification_code = generate_verification_code()
    code_expires = datetime.utcnow() + timedelta(minutes=15)
    
    user.email_verification_code = verification_code
    user.email_verification_code_expires = code_expires
    await db.commit()
    
    # Send email
    await send_verification_email(email, verification_code)
    
    return {"message": "Verification code sent successfully"}


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Login user and return JWT tokens.
    
    Request body: {email, password}
    Response: {access_token, refresh_token, token_type: "bearer"}
    """
    try:
        logger.info(f"[LOGIN] Login attempt for email: {user_data.email}")
        
        # Find user by email
        result = await db.execute(select(User).where(User.email == user_data.email))
        user = result.scalar_one_or_none()
        
        # Security: Don't reveal if email exists or password is wrong
        # Always return the same error message for invalid credentials
        if not user:
            logger.warning(f"[LOGIN] Login failed: User not found for email: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify password
        if not verify_password(user_data.password, user.hashed_password):
            logger.warning(f"[LOGIN] Login failed: Invalid password for email: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if user is active
        if not user.is_active:
            logger.warning(f"[LOGIN] Login failed: Inactive account for email: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Note: We allow login even if email is not verified
        # Frontend can check email_verified status and prompt for verification
        
        # Create tokens
        access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
        refresh_token = create_refresh_token(data={"sub": str(user.id), "email": user.email})
        
        logger.info(f"[LOGIN] Login successful for user ID: {user.id}, email: {user_data.email}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (they're intentional)
        raise
    except Exception as e:
        logger.error(f"[LOGIN] Unexpected error during login for {user_data.email}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again later."
        )


@router.post("/forgot-password", response_model=dict)
async def forgot_password(reset_data: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    """Request password reset code."""
    result = await db.execute(select(User).where(User.email == reset_data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        # Don't reveal if email exists for security
        return {"message": "If the email exists, a password reset code has been sent"}
    
    # Generate reset code
    reset_code = generate_verification_code()
    code_expires = datetime.utcnow() + timedelta(minutes=15)
    
    user.password_reset_code = reset_code
    user.password_reset_code_expires = code_expires
    await db.commit()
    
    # Send email
    await send_password_reset_email(reset_data.email, reset_code)
    
    return {"message": "If the email exists, a password reset code has been sent"}


@router.post("/reset-password", response_model=dict)
async def reset_password(reset_data: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    """Reset password with verification code."""
    result = await db.execute(select(User).where(User.email == reset_data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if code is valid
    if not user.password_reset_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No reset code found. Please request a new one."
        )
    
    if user.password_reset_code != reset_data.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset code"
        )
    
    # Check if code expired
    if user.password_reset_code_expires and user.password_reset_code_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset code has expired. Please request a new one."
        )
    
    # Update password
    user.hashed_password = get_password_hash(reset_data.new_password)
    user.password_reset_code = None
    user.password_reset_code_expires = None
    await db.commit()
    
    return {"message": "Password reset successfully"}


@router.get("/google/authorize", response_model=dict)
async def google_authorize():
    """Get Google OAuth authorization URL."""
    from app.core.config import settings
    
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth not configured"
        )
    
    redirect_uri = settings.google_redirect_uri or "http://localhost:3000/auth/google/callback"
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.google_client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope=openid email profile&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    
    return {"auth_url": auth_url}


@router.post("/google/callback", response_model=Token)
async def google_callback(oauth_data: GoogleOAuthRequest, db: AsyncSession = Depends(get_db)):
    """Handle Google OAuth callback."""
    from app.core.config import settings
    import httpx
    
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth not configured"
        )
    
    redirect_uri = settings.google_redirect_uri or "http://localhost:3000/auth/google/callback"
    
    # Exchange code for token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": oauth_data.code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
        )
        
        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for token"
            )
        
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        # Get user info from Google
        user_info_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if user_info_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google"
            )
        
        user_info = user_info_response.json()
        google_id = user_info.get("id")
        email = user_info.get("email")
        name = user_info.get("name", "")
        picture = user_info.get("picture")
    
    if not email or not google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user info from Google"
        )
    
    # Check if user exists by Google ID
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()
    
    if user:
        # Existing user, update info if needed
        if not user.email_verified:
            user.email_verified = True
        if picture and not user.avatar_url:
            user.avatar_url = picture
        await db.commit()
    else:
        # Check if email already exists
        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # Link Google account to existing user
            existing_user.google_id = google_id
            existing_user.oauth_provider = "google"
            if not existing_user.email_verified:
                existing_user.email_verified = True
            if picture and not existing_user.avatar_url:
                existing_user.avatar_url = picture
            await db.commit()
            user = existing_user
        else:
            # Create new user
            username = email.split("@")[0]
            # Ensure username is unique
            base_username = username
            counter = 1
            while True:
                result = await db.execute(select(User).where(User.username == username))
                if not result.scalar_one_or_none():
                    break
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User(
                email=email,
                username=username,
                full_name=name,
                hashed_password="",  # OAuth users don't need password
                google_id=google_id,
                oauth_provider="google",
                email_verified=True,
                is_active=True,
                avatar_url=picture,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
    
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token(data={"sub": str(user.id), "email": user.email})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token."""
    from app.core.security import verify_token
    
    try:
        payload = verify_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        email = payload.get("email")
        
        # Verify user still exists and is active
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new tokens
        new_access_token = create_access_token(data={"sub": user_id, "email": email})
        new_refresh_token = create_refresh_token(data={"sub": user_id, "email": email})
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
