from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置：可通过 backend/.env 覆盖。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "智慧自习室预约与管理系统"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False

    database_url: str = (
        "mysql+pymysql://root:password@127.0.0.1:3306/smart_study_room?charset=utf8mb4"
    )

    jwt_secret_key: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120

    cors_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]

    # ---- 业务参数（需求规格说明书 BR-001～BR-009，均待业务确认） ----
    reservation_granularity_minutes: int = 30
    advance_booking_days: int = 7
    max_reservation_hours: int = 4
    daily_reservation_limit: int = 2
    checkin_early_minutes: int = 15
    checkin_late_minutes: int = 15
    cancel_before_minutes: int = 30
    violation_threshold: int = 3
    restriction_days: int = 7
    dashboard_refresh_seconds: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
