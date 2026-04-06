import random

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from .. import models, schemas
from ..auth import hash_password, verify_password, create_access_token
from ..email import send_verification_email, smtp_is_configured

router = APIRouter(prefix="/auth", tags=["auth"])


def _generate_verification_code() -> str:
    return f"{random.randint(0, 999999):06d}"


def _deliver_verification_code(email: str, code: str) -> tuple[bool, str | None]:
    if smtp_is_configured():
        try:
            sent = send_verification_email(email, code)
            if sent:
                return True, None
        except Exception:
            if settings.env != "dev":
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not send verification email",
                )

    if settings.env == "dev":
        return False, code
    return False, None


@router.post("/register", response_model=schemas.RegisterOut)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    verification_code = _generate_verification_code()
    user = models.User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        is_verified=False,
        verification_code=verification_code,
    )
    db.add(user)
    try:
        email_sent, dev_code = _deliver_verification_code(user.email, verification_code)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    return schemas.RegisterOut(
        email=user.email,
        detail="Account created. Please verify your email before logging in.",
        email_sent=email_sent,
        dev_verification_code=dev_code,
    )


@router.post("/verify", response_model=schemas.TokenOut)
def verify_account(payload: schemas.VerifyAccount, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account already verified")
    if user.verification_code != payload.code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code")

    user.is_verified = True
    user.verification_code = None
    db.commit()

    token = create_access_token(str(user.id))
    return schemas.TokenOut(access_token=token)


@router.post("/resend-verification", response_model=schemas.ResendVerificationOut)
def resend_verification(payload: schemas.ResendVerification, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account already verified")

    verification_code = _generate_verification_code()
    user.verification_code = verification_code
    db.commit()

    email_sent, dev_code = _deliver_verification_code(user.email, verification_code)
    return schemas.ResendVerificationOut(
        detail="A fresh verification code has been sent.",
        email_sent=email_sent,
        dev_verification_code=dev_code,
    )


@router.post("/login", response_model=schemas.TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form.username).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account not verified")

    token = create_access_token(str(user.id))
    return schemas.TokenOut(access_token=token)


@router.get("/oauth/{provider}/login")
def oauth_login(provider: str):
    return {
        "message": "OAuth flow not wired yet",
        "provider": provider,
    }


@router.get("/oauth/{provider}/callback")
def oauth_callback(provider: str):
    return {
        "message": "OAuth callback not wired yet",
        "provider": provider,
    }
