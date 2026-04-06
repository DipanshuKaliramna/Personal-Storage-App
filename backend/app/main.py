from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sqlalchemy import inspect, text

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

def ensure_dev_schema():
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    with engine.begin() as connection:
        if "is_verified" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE"))
            connection.execute(text("UPDATE users SET is_verified = TRUE WHERE is_verified IS NULL"))
        if "verification_code" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN verification_code VARCHAR(6)"))


@app.on_event("startup")
def on_startup():
    if settings.env == "dev":
        Base.metadata.create_all(bind=engine)
        ensure_dev_schema()
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
