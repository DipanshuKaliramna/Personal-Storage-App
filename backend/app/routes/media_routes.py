import uuid
from datetime import datetime
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from .. import models, schemas
from ..auth import get_current_user

router = APIRouter(prefix="/media", tags=["media"])


def _get_quota_bytes(is_premium: bool) -> int:
    gb = settings.premium_quota_gb if is_premium else settings.free_quota_gb
    return gb * 1024 * 1024 * 1024


def _build_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.s3_region,
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
    )


def _object_key(user_id: uuid.UUID, media_id: uuid.UUID, filename: str) -> str:
    safe_name = Path(filename).name
    return f"users/{user_id}/{media_id}/{safe_name}"


@router.post("/upload-url")
def create_upload_url(
    payload: schemas.MediaCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    quota = _get_quota_bytes(current_user.is_premium)
    if current_user.used_bytes + payload.size_bytes > quota:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Storage quota exceeded")

    media_id = uuid.uuid4()
    s3_key = _object_key(current_user.id, media_id, payload.filename)

    media = models.MediaItem(
        id=media_id,
        owner_id=current_user.id,
        kind=payload.kind,
        filename=payload.filename,
        content_type=payload.content_type,
        size_bytes=payload.size_bytes,
        s3_key=s3_key,
        created_at=datetime.utcnow(),
    )
    current_user.used_bytes += payload.size_bytes

    db.add(media)
    db.commit()

    if settings.storage_backend == "local":
        return {
            "media_id": str(media_id),
            "s3_key": s3_key,
            "upload_url": f"{settings.public_base_url.rstrip('/')}/media/upload/{media_id}",
            "upload_method": "PUT",
        }

    try:
        s3 = _build_s3_client()
        presigned_url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.s3_bucket,
                "Key": s3_key,
                "ContentType": payload.content_type,
            },
            ExpiresIn=3600,
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="S3 not configured") from exc

    return {
        "media_id": str(media_id),
        "s3_key": s3_key,
        "upload_url": presigned_url,
        "upload_method": "PUT",
    }


@router.put("/upload/{media_id}")
async def upload_media_local(
    media_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if settings.storage_backend != "local":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Local upload endpoint is disabled")

    item = db.get(models.MediaItem, media_id)
    if not item or item.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    body = await request.body()
    if len(body) != item.size_bytes:
        current_user.used_bytes = max(0, current_user.used_bytes - item.size_bytes)
        db.delete(item)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file size mismatch")

    target = Path(settings.local_upload_dir) / item.s3_key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)

    return {"uploaded": True, "media_id": str(media_id)}


@router.get("/feed", response_model=list[schemas.MediaOut])
def list_media(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    items = (
        db.query(models.MediaItem)
        .filter(models.MediaItem.owner_id == current_user.id)
        .order_by(models.MediaItem.created_at.desc())
        .all()
    )
    return items


@router.delete("/{media_id}")
def delete_media(
    media_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    item = db.get(models.MediaItem, media_id)
    if not item or item.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    current_user.used_bytes = max(0, current_user.used_bytes - item.size_bytes)

    if settings.storage_backend == "local":
        target = Path(settings.local_upload_dir) / item.s3_key
        if target.exists():
            target.unlink()

    db.delete(item)
    db.commit()

    return {"deleted": True}
