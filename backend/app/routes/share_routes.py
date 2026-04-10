import secrets
from datetime import timedelta
from pathlib import Path

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from .. import models, schemas
from ..auth import get_current_user
from ..time_utils import utc_now
from .media_routes import _build_s3_client

router = APIRouter(prefix="/share", tags=["share"])


def build_share_download_url(token: str) -> str:
    return f"{settings.public_base_url.rstrip('/')}/share/{token}/download"


@router.post("", response_model=schemas.ShareOut)
def create_share_link(
    payload: schemas.ShareCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if bool(payload.media_id) == bool(payload.album_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide exactly one of media_id or album_id")

    if payload.media_id:
        media = db.get(models.MediaItem, payload.media_id)
        if not media or media.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    if payload.album_id:
        album = db.get(models.Album, payload.album_id)
        if not album or album.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found")

    token = secrets.token_urlsafe(24)
    expires_at = utc_now() + timedelta(hours=settings.share_token_ttl_hours)

    link = models.ShareLink(
        owner_id=current_user.id,
        token=token,
        media_id=payload.media_id,
        album_id=payload.album_id,
        expires_at=expires_at,
    )
    db.add(link)
    db.commit()

    return schemas.ShareOut(token=build_share_download_url(token), expires_at=expires_at)


@router.get("/{token}")
def resolve_share_link(token: str, db: Session = Depends(get_db)):
    link = db.query(models.ShareLink).filter(models.ShareLink.token == token).first()
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    if link.expires_at < utc_now():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Link expired")

    if link.media_id:
        media = db.get(models.MediaItem, link.media_id)
        return {"type": "media", "media": media}
    if link.album_id:
        album = db.get(models.Album, link.album_id)
        return {"type": "album", "album": album}

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link invalid")


@router.get("/{token}/download")
def download_shared_media(token: str, db: Session = Depends(get_db)):
    link = db.query(models.ShareLink).filter(models.ShareLink.token == token).first()
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    if link.expires_at < utc_now():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Link expired")
    if not link.media_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Album share downloads are not supported")

    media = db.get(models.MediaItem, link.media_id)
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    if settings.storage_backend == "local":
        target = Path(settings.local_upload_dir) / media.s3_key
        if not target.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found")
        return FileResponse(path=target, media_type=media.content_type, filename=media.filename)

    try:
        s3 = _build_s3_client()
        presigned_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": media.s3_key},
            ExpiresIn=3600,
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="S3 not configured") from exc

    return RedirectResponse(url=presigned_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
