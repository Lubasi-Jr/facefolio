from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    redis_url: str
    supabase_url: str
    supabase_jwt_secret: str
    supabase_service_key: str
    storage_bucket: str


settings = Settings()
