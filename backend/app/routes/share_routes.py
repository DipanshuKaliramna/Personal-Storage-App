import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from .. import models, schemas
from ..auth import get_current_user

router = APIRouter(prefix="/share", tags=["share"])


@router.post("", response_model=schemas.ShareOut)
def create_share_link(
    payload: schemas.ShareCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not payload.media_id and not payload.album_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="media_id or album_id required")

    token = secrets.token_urlsafe(24)
    expires_at = datetime.utcnow() + timedelta(hours=settings.share_token_ttl_hours)

    link = models.ShareLink(
        owner_id=current_user.id,
        token=token,
        media_id=payload.media_id,
        album_id=payload.album_id,
        expires_at=expires_at,
    )
    db.add(link)
    db.commit()

    return schemas.ShareOut(token=token, expires_at=expires_at)


@router.get("/{token}")
def resolve_share_link(token: str, db: Session = Depends(get_db)):
    link = db.query(models.ShareLink).filter(models.ShareLink.token == token).first()
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    if link.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Link expired")

    if link.media_id:
        media = db.get(models.MediaItem, link.media_id)
        return {"type": "media", "media": media}
    if link.album_id:
        album = db.get(models.Album, link.album_id)
        return {"type": "album", "album": album}

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link invalid")
