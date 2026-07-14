from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    redis_url: str
    supabase_url: str
    supabase_jwt_secret: str
    supabase_service_key: str
    storage_bucket: str

    # CORS: comma-separated if more than one origin.
    frontend_origin: str

    # CV match thresholds (cosine similarity): above t_high auto-tags, between
    # t_low and t_high needs guest confirmation, below t_low is ignored.
    match_t_high: float
    match_t_low: float
    match_margin: float

    max_photos_per_event: int
    celery_concurrency: int


settings = Settings()
