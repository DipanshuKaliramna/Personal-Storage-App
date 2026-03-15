from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
import uuid


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_premium: bool
    used_bytes: int
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MediaCreate(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    kind: str


class MediaOut(BaseModel):
    id: uuid.UUID
    kind: str
    filename: str
    content_type: str
    size_bytes: int
    s3_key: str
    created_at: datetime


class AlbumCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class AlbumOut(BaseModel):
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
