import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models, schemas
from ..auth import get_current_user

router = APIRouter(prefix="/albums", tags=["albums"])


@router.post("", response_model=schemas.AlbumOut)
def create_album(
    payload: schemas.AlbumCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    album = models.Album(owner_id=current_user.id, title=payload.title)
    db.add(album)
    db.commit()
    db.refresh(album)
    return album


@router.get("", response_model=list[schemas.AlbumOut])
def list_albums(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Album)
        .filter(models.Album.owner_id == current_user.id)
        .order_by(models.Album.created_at.desc())
        .all()
    )


@router.post("/{album_id}/items")
def add_to_album(
    album_id: uuid.UUID,
    payload: schemas.AddToAlbum,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    album = db.get(models.Album, album_id)
    if not album or album.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found")

    media = db.get(models.MediaItem, payload.media_id)
    if not media or media.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    item = models.AlbumItem(album_id=album_id, media_id=payload.media_id)
    db.add(item)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already in album") from exc

    return {"added": True}
