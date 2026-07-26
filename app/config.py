from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: Literal["development", "production"] = "development"

    database_url: str
    redis_url: str
    supabase_url: str
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

    # CV quality gates for photo faces (permissive — guests can't retake event
    # photos, so we only reject faces genuinely too poor to embed/match).
    face_min_size_px: int = 60
    face_det_score_min: float = 0.6
    # Laplacian variance of the face crop; below this looks blurry.
    # Placeholder — calibrate against real photos.
    face_blur_variance_min: float = 100.0

    # CV quality gates for the onboarding selfie (stricter — the guest can
    # retake it immediately, so we ask for a clean, single-face shot).
    selfie_min_face_size_px: int = 200
    # Mean grayscale intensity (0-255) of the face crop must fall in this
    # range. Placeholders — calibrate against real selfies.
    selfie_brightness_min: float = 40.0
    selfie_brightness_max: float = 220.0

    # How long a gallery's signed web/thumb read URLs stay valid, in seconds.
    gallery_url_expires_in: int = 3600

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.supabase_url}/auth/v1/.well-known/jwks.json"


settings = Settings()
