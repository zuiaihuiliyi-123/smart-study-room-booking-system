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
    # 统一业务时间口径：数据库存 Asia/Shanghai 的 naive datetime（MySQL DATETIME），
    # 前端按本地时间展示；禁止混用服务器本地时区与 UTC。
    app_timezone: str = "Asia/Shanghai"

    database_url: str = (
        "mysql+pymysql://root:password@127.0.0.1:3306/smart_study_room?charset=utf8mb4"
    )
    # 连接池显式配置：避免默认池在考试周高并发下不可控。
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle_seconds: int = 3600
    # MySQL 死锁/锁等待重试（SQLite 测试库的 database is locked 也复用该策略）。
    db_retry_attempts: int = 3
    db_retry_base_delay_ms: int = 50

    jwt_secret_key: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120

    cors_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]

    # ---- 业务参数（需求规格说明书 BR-001～BR-009，均待业务确认） ----
    # 2026-11-07 业务确认：预约粒度由 30 分钟调整为 5 分钟。
    reservation_granularity_minutes: int = 5
    # 看板占用率仍按 30 分钟统计块展示，与预约粒度解耦，避免改变既有统计口径。
    dashboard_block_minutes: int = 30
    advance_booking_days: int = 7
    max_reservation_hours: int = 4
    daily_reservation_limit: int = 2
    checkin_early_minutes: int = 15
    checkin_late_minutes: int = 15
    cancel_before_minutes: int = 30
    violation_threshold: int = 3
    restriction_days: int = 7
    dashboard_refresh_seconds: int = 10
    # 看板服务端短缓存：10 秒轮询时把同一窗口内的并发查询合并，降低考试周 QPS。
    dashboard_cache_seconds: int = 10
    # APScheduler：错过触发后的宽限、任务失败重试与退避。
    scheduler_misfire_grace_seconds: int = 60
    scheduler_task_retries: int = 2
    scheduler_retry_delay_seconds: int = 5
    # ST-063：已处理投诉超过该天数未关闭则自动关闭（候选 7 天，BR-014 相关，待确认）
    complaint_close_days: int = 7
    # ---- 注册策略（A2） ----
    #: 是否开放学生自助注册；关闭后由管理员批量开户（课程演示默认开放）。
    registration_enabled: bool = True
    #: 可选学籍白名单：逗号 / 分号分隔的学号；留空表示不限制。
    registration_whitelist: str = ""
    # ---- 登录失败锁定（B5） ----
    #: 窗口内允许的连续失败次数，达到即锁定。
    login_max_failures: int = 5
    #: 失败计数窗口（分钟）；窗口外的失败重新计数。
    login_failure_window_minutes: int = 15
    #: 锁定时长（分钟）。
    login_lock_minutes: int = 15
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
