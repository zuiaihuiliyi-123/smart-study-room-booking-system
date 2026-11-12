from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

_engine_options: dict[str, object] = {
    "pool_pre_ping": True,
    "pool_recycle": settings.db_pool_recycle_seconds,
}
# SQLite（测试）不接受 MySQL 连接池参数；生产 MySQL 显式配置池。
if not settings.database_url.startswith("sqlite"):
    _engine_options.update(
        {
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_timeout": settings.db_pool_timeout,
        }
    )

engine = create_engine(settings.database_url, **_engine_options)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：每个请求一个数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
