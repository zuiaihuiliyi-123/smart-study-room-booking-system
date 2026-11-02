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
    # ST-063：已处理投诉超过该天数未关闭则自动关闭（候选 7 天，BR-014 相关，待确认）
    complaint_close_days: int = 7
    # 测试环境通过环境变量关闭定时任务，避免后台任务连接真实数据库
    scheduler_enabled: bool = True

    #: JWT 密钥的安全占位符：出现在配置中即视为未替换，启动校验会拒绝。
    JWT_SECRET_PLACEHOLDER: str = "change-me-in-env"
    #: HMAC-SHA256 推荐密钥长度（RFC 7518 §3.2）。
    JWT_SECRET_MIN_BYTES: int = 32

    def validate_security(self) -> None:
        """启动期安全校验：JWT 密钥不得为公开占位符且长度需达标（§2.1 不得绕过认证）。

        缺失 ``.env`` 或密钥仍为默认占位符时，应用直接拒绝启动，
        避免任何人用该公开常量伪造任意用户（含管理员）的令牌。
        """
        key = self.jwt_secret_key or ""
        if not key or key == self.JWT_SECRET_PLACEHOLDER:
            raise RuntimeError(
                "JWT_SECRET_KEY 未配置或仍为默认占位符，拒绝启动。"
                "请在 backend/.env 中设置一个足够长的随机字符串"
                "（建议 openssl rand -hex 32）。"
            )
        if len(key.encode("utf-8")) < self.JWT_SECRET_MIN_BYTES:
            raise RuntimeError(
                f"JWT_SECRET_KEY 长度不足 {self.JWT_SECRET_MIN_BYTES} 字节，"
                "不满足 HMAC-SHA256 的安全要求（RFC 7518 §3.2）。"
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
