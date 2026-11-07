from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ConsentRecord, User, UserPreference
from ..security import create_token, current_user, hash_password, verify_password
from ..seed.seed import CONSENT_VERSION
from ..services.audit import audit

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone_number: str | None = None
    occupation: str | None = None
    industry: str | None = None
    age_group: str | None = None
    city: str | None = None
    consent_data_processing: bool
    consent_ai_analysis: bool = False


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def user_out(u: User) -> dict:
    return {
        "user_id": str(u.user_id), "full_name": u.full_name, "email": u.email, "phone_number": u.phone_number,
        "occupation": u.occupation, "industry": u.industry, "age_group": u.age_group, "city": u.city,
        "user_role": u.user_role, "registration_date": u.registration_date.isoformat(), "is_synthetic": u.is_synthetic,
    }


@router.post("/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if not body.consent_data_processing:
        raise HTTPException(400, "Informed consent to process your wellness data is required to create an account.")
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists.")
    u = User(
        full_name=body.full_name.strip(), email=email, password_hash=hash_password(body.password),
        phone_number=body.phone_number, occupation=body.occupation, industry=body.industry,
        age_group=body.age_group, city=body.city, user_role="individual",
    )
    db.add(u)
    db.flush()
    db.add(UserPreference(user_id=u.user_id))
    db.add(ConsentRecord(user_id=u.user_id, consent_type="data_processing", consent_version=CONSENT_VERSION, granted_status=True))
    db.add(ConsentRecord(user_id=u.user_id, consent_type="ai_analysis", consent_version=CONSENT_VERSION, granted_status=body.consent_ai_analysis))
    audit(db, u.user_id, "register", u.user_id)
    db.commit()
    return {"access_token": create_token(u), "token_type": "bearer", "user": user_out(u)}


# Very small in-memory brute-force limiter (per email). Use a shared store in production.
_failures: dict[str, list[datetime]] = {}


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    now = datetime.now(timezone.utc)
    recent = [t for t in _failures.get(email, []) if now - t < timedelta(minutes=15)]
    if len(recent) >= 10:
        raise HTTPException(429, "Too many failed attempts. Please try again later.")
    u = db.scalar(select(User).where(User.email == email))
    if u is None or not verify_password(body.password, u.password_hash) or u.account_status != "active":
        _failures[email] = recent + [now]
        raise HTTPException(401, "Incorrect email or password.")
    _failures.pop(email, None)
    audit(db, u.user_id, "login", u.user_id)
    db.commit()
    return {"access_token": create_token(u), "token_type": "bearer", "user": user_out(u)}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_out(user)
