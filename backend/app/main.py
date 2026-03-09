from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .config import settings
from .db import Base, engine
from .routes import auth_routes, media_routes, album_routes, share_routes


app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://[::1]:5173",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    if settings.env == "dev":
        Base.metadata.create_all(bind=engine)
    if settings.storage_backend == "local":
        Path(settings.local_upload_dir).mkdir(parents=True, exist_ok=True)


@app.get("/")
def root():
    return {"status": "ok", "app": settings.app_name}


app.include_router(auth_routes.router)
app.include_router(media_routes.router)
app.include_router(album_routes.router)
app.include_router(share_routes.router)

if settings.storage_backend == "local":
    Path(settings.local_upload_dir).mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.local_upload_dir), name="uploads")
