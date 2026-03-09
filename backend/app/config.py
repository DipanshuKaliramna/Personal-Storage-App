from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "StorageApp"
    env: str = "dev"
    debug: bool = True

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/storageapp"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 60 * 24

    storage_backend: str = "local"  # local | s3
    local_upload_dir: str = "uploads"
    public_base_url: str = "http://127.0.0.1:8000"

    s3_bucket: str = "storageapp-media"
    s3_region: str = "us-east-1"
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None

    free_quota_gb: int = 15
    premium_quota_gb: int = 25

    share_token_ttl_hours: int = 24 * 7


settings = Settings()
