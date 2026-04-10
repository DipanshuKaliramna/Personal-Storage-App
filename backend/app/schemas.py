from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
import uuid


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    is_verified: bool
    is_premium: bool
    used_bytes: int
    created_at: datetime


class RegisterOut(BaseModel):
    email: EmailStr
    verification_required: bool = True
    detail: str
    email_sent: bool = False
    dev_verification_code: str | None = None
    email_error: str | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VerifyAccount(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class ResendVerification(BaseModel):
    email: EmailStr


class ResendVerificationOut(BaseModel):
    detail: str
    email_sent: bool = False
    dev_verification_code: str | None = None
    email_error: str | None = None


class MediaCreate(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    kind: str


class MediaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    filename: str
    content_type: str
    size_bytes: int
    s3_key: str
    created_at: datetime
    file_url: str


class AlbumCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class AlbumOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime


class ShareCreate(BaseModel):
    media_id: uuid.UUID | None = None
    album_id: uuid.UUID | None = None


class ShareOut(BaseModel):
    token: str
    expires_at: datetime


class AddToAlbum(BaseModel):
    media_id: uuid.UUID
