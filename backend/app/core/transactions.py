"""Service 层事务边界。

约定：
- 查询方法只读，不 commit、不 rollback；
- 命令方法自己拥有且只拥有一个事务，使用 ``transaction(db)`` 包住全部写操作；
- 事务提交后再发送站内通知（通知失败不能回滚业务）；
- API 层不 commit，避免一个请求出现多个事务边界。
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session


@contextmanager
def transaction(db: Session) -> Iterator[Session]:
    """提交一次 Service 命令事务；异常时回滚并原样抛出。"""
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
