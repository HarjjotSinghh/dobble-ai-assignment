"""
Authentication routes - JWT-based login and registration.

Supports role-based access control for patients and doctors.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.database import get_db
from app.config import get_settings
from app.models.models import User, Doctor, Patient, UserRole
from app.schemas.schemas import UserRegister, UserLogin, TokenResponse, UserResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def create_token(user_id: int, role: str) -> str:
    """Create a JWT token."""
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to extract and validate the current user from JWT token."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(
        select(User)
        .options(joinedload(User.doctor_profile), joinedload(User.patient_profile))
        .where(User.id == user_id)
    )
    user = result.unique().scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/register", response_model=TokenResponse)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user (patient or doctor)."""
    # Check existing email
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    user = User(
        email=data.email,
        password_hash=pwd_context.hash(data.password),
        name=data.name,
        role=UserRole(data.role),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create profile based on role
    if data.role == "doctor":
        doctor = Doctor(
            user_id=user.id,
            specialization=data.specialization or "General Physician",
            phone=data.phone,
        )
        db.add(doctor)
    else:
        patient = Patient(user_id=user.id, phone=data.phone)
        db.add(patient)

    await db.commit()

    token = create_token(user.id, user.role.value)
    return TokenResponse(
        access_token=token,
        user=UserResponse(id=user.id, email=user.email, name=user.name, role=user.role.value),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login with email and password."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user.id, user.role.value)
    return TokenResponse(
        access_token=token,
        user=UserResponse(id=user.id, email=user.email, name=user.name, role=user.role.value),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Get current user info."""
    return UserResponse(id=user.id, email=user.email, name=user.name, role=user.role.value)
