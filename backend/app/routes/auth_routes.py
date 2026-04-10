import random
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from .. import models, schemas
from ..auth import hash_password, verify_password, create_access_token
from ..email import send_verification_email, smtp_is_configured

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _generate_verification_code() -> str:
    return f"{random.randint(0, 999999):06d}"


def _deliver_verification_code(email: str, code: str) -> tuple[bool, str | None, str | None]:
    if smtp_is_configured():
        try:
            sent = send_verification_email(email, code)
            if sent:
                return True, None, None
        except Exception as exc:
            logger.exception("Verification email delivery failed for %s", email)
            if settings.env != "dev":
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not send verification email",
                )
            return False, code, str(exc)

    if settings.env == "dev":
        return False, code, "SMTP is not configured"
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Email delivery is not configured",
    )


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
        email_sent, dev_code, email_error = _deliver_verification_code(user.email, verification_code)
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
        email_error=email_error,
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
    try:
        email_sent, dev_code, email_error = _deliver_verification_code(user.email, verification_code)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    return schemas.ResendVerificationOut(
        detail="A fresh verification code has been sent.",
        email_sent=email_sent,
        dev_verification_code=dev_code,
        email_error=email_error,
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


if settings.oauth_enabled:
    @router.get("/oauth/{provider}/login")
    def oauth_login(provider: str):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"OAuth provider '{provider}' is not implemented yet",
        )


    @router.get("/oauth/{provider}/callback")
    def oauth_callback(provider: str):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"OAuth provider '{provider}' is not implemented yet",
        )
