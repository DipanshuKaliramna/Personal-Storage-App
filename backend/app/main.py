from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .config import settings
from .db import engine
from .routes import auth_routes, media_routes, album_routes, share_routes


app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    if settings.storage_backend == "local":
        Path(settings.local_upload_dir).mkdir(parents=True, exist_ok=True)


@app.get("/")
def root():
    return {"status": "ok", "app": settings.app_name}


@app.get("/healthz")
def healthcheck():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc
    return {"status": "ok"}


app.include_router(auth_routes.router)
app.include_router(media_routes.router)
app.include_router(album_routes.router)
app.include_router(share_routes.router)
