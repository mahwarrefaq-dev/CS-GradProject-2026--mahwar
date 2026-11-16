"""Application settings read from environment variables or backend/.env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+psycopg://mahwar:change_me@localhost:5432/mahwar"
    jwt_secret: str = "change_me"
    jwt_expire_minutes: int = 60          # SEC-03
    test_database_url: str | None = None  # pytest integration tests (section 4.11)
    max_failed_logins: int = 5            # SEC-01
    lockout_minutes: int = 15             # SEC-01


settings = Settings()
