from sqlalchemy.orm import Session

from app.models.enums import MessageType


def notify(
    db: Session,
    *,
    user_id: int,
    message_type: MessageType,
    title: str,
    content: str,
    related_type: str | None = None,
    related_id: int | None = None,
) -> None:
    """M7 / FR-060：写入站内通知。

    通知失败不得回滚或阻塞预约、违约等业务结果；重试策略待确认。
    """
    raise NotImplementedError("站内通知待实现")
