"""mzj 测试组公共夹具：认证权限 + M5（用户/投诉/评价/审计）+ M6 看板 + M7 消息。

只在本目录生效，不修改共享 `tests/conftest.py`，避免与其他组员的测试文件冲突。
"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.core.cache import clear_dashboard_cache
from app.core.security import create_access_token, hash_password
from app.models.blacklist import BlacklistEntry
from app.models.complaint import Complaint
from app.models.enums import (
    BlacklistMode,
    ComplaintStatus,
    ComplaintTargetType,
    MessageType,
    Role,
    ViolationType,
)
from app.models.login_attempt import LoginAttempt
from app.models.message import StationMessage
from app.models.review import Review
from app.models.user import User
from app.models.violation import ViolationRecord
from app.services import notification_service
from app.utils import time_utils

#: 本组统一时间基线：所有与“今日/窗口/到期”相关的用例都冻结在该时刻。
FIXED_NOW = datetime(2026, 11, 26, 10, 0)


@pytest.fixture(autouse=True)
def _clean_dashboard_cache():
    """看板缓存是进程级单例，跨用例必须清理，避免“单跑绿、全量红”。"""
    clear_dashboard_cache()
    yield
    clear_dashboard_cache()


@pytest.fixture(autouse=True)
def _isolate_notifications(monkeypatch):
    """站内通知默认走独立 SessionLocal（真实 MySQL）。

    测试中把该会话改成不可用：既避免连接外部数据库，也顺带验证
    `notify_safe` 的“通知失败不影响业务结果”容错路径。
    需要断言通知落库的用例请显式使用 `captured_notifications`。
    """

    class _UnavailableSession:
        def __enter__(self) -> None:
            raise RuntimeError("notification session is disabled in tests")

        def __exit__(self, *exc_info: object) -> bool:
            return False

    monkeypatch.setattr(notification_service, "SessionLocal", _UnavailableSession)


@pytest.fixture()
def freeze_now(monkeypatch):
    """把业务时间冻结到 FIXED_NOW，返回该时刻。"""
    monkeypatch.setattr(time_utils, "now", lambda: FIXED_NOW)
    return FIXED_NOW


@pytest.fixture()
def auth_headers():
    """直接签发令牌，避免每个用例都登录而触发 10 次/分/IP 的限流。"""

    def _headers(user: User) -> dict[str, str]:
        token = create_access_token(str(user.id), user.role, user.token_version or 0)
        return {"Authorization": f"Bearer {token}"}

    return _headers


@pytest.fixture()
def login(api_client):
    """真实登录并返回鉴权头；单用例内登录次数需控制在限流阈值以内。"""

    def _login(student_no: str, password: str = "Ss123456") -> dict[str, str]:
        response = api_client.post(
            "/api/v1/auth/login",
            json={"student_no": student_no, "password": password},
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _login


@pytest.fixture()
def make_student(db: Session, make_user):
    """带可用口令的学生工厂（与 make_user 的默认 'hash' 不同，可真实登录）。"""
    counter = {"n": 0}

    def _make(**kwargs: object) -> User:
        counter["n"] += 1
        defaults: dict[str, object] = {
            "student_no": f"S9{counter['n']:03d}",
            "name": f"学生{counter['n']}",
            "password_hash": hash_password("Ss123456"),
        }
        defaults.update(kwargs)
        return make_user(**defaults)

    return _make


@pytest.fixture()
def make_admin(db: Session, make_user):
    counter = {"n": 0}

    def _make(**kwargs: object) -> User:
        counter["n"] += 1
        defaults: dict[str, object] = {
            "student_no": f"ADM9{counter['n']:03d}",
            "name": f"管理员{counter['n']}",
            "role": Role.ADMIN.value,
            "password_hash": hash_password("Ss123456"),
        }
        defaults.update(kwargs)
        return make_user(**defaults)

    return _make


@pytest.fixture()
def make_complaint(db: Session):
    def _make(user_id: int, **kwargs: object) -> Complaint:
        defaults: dict[str, object] = {
            "user_id": user_id,
            "target_type": ComplaintTargetType.ROOM.value,
            "target_id": 1,
            "content": "空调太冷",
            "status": ComplaintStatus.PENDING.value,
        }
        defaults.update(kwargs)
        complaint = Complaint(**defaults)  # type: ignore[arg-type]
        db.add(complaint)
        db.commit()
        db.refresh(complaint)
        return complaint

    return _make


@pytest.fixture()
def make_review(db: Session):
    def _make(user_id: int, reservation_id: int, **kwargs: object) -> Review:
        defaults: dict[str, object] = {
            "user_id": user_id,
            "reservation_id": reservation_id,
            "score": 5,
        }
        defaults.update(kwargs)
        review = Review(**defaults)  # type: ignore[arg-type]
        db.add(review)
        db.commit()
        db.refresh(review)
        return review

    return _make


@pytest.fixture()
def make_violation(db: Session):
    def _make(user_id: int, reservation_id: int, **kwargs: object) -> ViolationRecord:
        defaults: dict[str, object] = {
            "user_id": user_id,
            "reservation_id": reservation_id,
            "type": ViolationType.AUTO.value,
            "reason": "超时未签到",
        }
        defaults.update(kwargs)
        violation = ViolationRecord(**defaults)  # type: ignore[arg-type]
        db.add(violation)
        db.commit()
        db.refresh(violation)
        return violation

    return _make


@pytest.fixture()
def make_message(db: Session):
    counter = {"n": 0}

    def _make(user_id: int, **kwargs: object) -> StationMessage:
        counter["n"] += 1
        defaults: dict[str, object] = {
            "user_id": user_id,
            "type": MessageType.SYSTEM.value,
            "title": f"通知{counter['n']}",
            "content": "内容",
            "is_read": False,
        }
        defaults.update(kwargs)
        message = StationMessage(**defaults)  # type: ignore[arg-type]
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    return _make


@pytest.fixture()
def make_blacklist(db: Session):
    def _make(user_id: int, **kwargs: object) -> BlacklistEntry:
        defaults: dict[str, object] = {
            "user_id": user_id,
            "reason": "累计违约达到阈值",
            "mode": BlacklistMode.AUTO.value,
            "start_at": FIXED_NOW,
            "expire_at": None,
            "active_user_id": user_id,
        }
        defaults.update(kwargs)
        entry = BlacklistEntry(**defaults)  # type: ignore[arg-type]
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    return _make


@pytest.fixture()
def make_login_attempt(db: Session):
    def _make(student_no: str, **kwargs: object) -> LoginAttempt:
        defaults: dict[str, object] = {
            "student_no": student_no,
            "ip": "unknown",
            "failed_count": 1,
            "first_failed_at": FIXED_NOW,
            "locked_until": None,
            "updated_at": FIXED_NOW,
        }
        defaults.update(kwargs)
        attempt = LoginAttempt(**defaults)  # type: ignore[arg-type]
        db.add(attempt)
        db.commit()
        return attempt

    return _make


@pytest.fixture()
def captured_notifications(db: Session, monkeypatch):
    """把站内通知写进当前测试会话，便于断言“业务操作确实产生消息”。

    返回收集到的 notify_safe 关键字参数列表。
    """
    sent: list[dict[str, object]] = []

    def _fake(**kwargs: object) -> None:
        sent.append(kwargs)
        message = StationMessage(
            user_id=kwargs["user_id"],
            type=kwargs["message_type"].value,
            title=kwargs["title"],
            content=kwargs["content"],
            related_type=kwargs.get("related_type"),
            related_id=kwargs.get("related_id"),
        )
        db.add(message)
        db.commit()
        db.refresh(message)

    monkeypatch.setattr(notification_service, "notify_safe", _fake)
    return sent
