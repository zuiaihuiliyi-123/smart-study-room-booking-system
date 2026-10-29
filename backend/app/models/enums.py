from enum import Enum


class Role(str, Enum):
    """用户角色（需求规格说明书 R-01～R-04）。"""

    STUDENT = "学生用户"
    ADMIN = "自习室管理员"
    TEACHER = "教师用户"
    SYSTEM_ADMIN = "系统管理员"


class AccountStatus(str, Enum):
    """账户状态（SM-03）。"""

    NORMAL = "正常"
    RESTRICTED = "受限"
    DISABLED = "停用"


class SeatStatus(str, Enum):
    """座位资源状态（SM-01：只含资源状态，不含“已预约/使用中”）。"""

    AVAILABLE = "可用"
    MAINTENANCE = "维修中"
    DISABLED = "停用"


class ReservationStatus(str, Enum):
    """预约单状态（SM-02）。有效预约 = 待使用 / 使用中。"""

    PENDING = "待使用"
    IN_USE = "使用中"
    COMPLETED = "已完成"
    CANCELLED = "已取消"
    VIOLATED = "已违约"


class ViolationType(str, Enum):
    AUTO = "自动违约"
    MANUAL = "手动违约"


class ComplaintStatus(str, Enum):
    """投诉状态（SM-04）。"""

    PENDING = "待处理"
    PROCESSING = "处理中"
    RESOLVED = "已处理"
    REJECTED = "已驳回"
    CLOSED = "已关闭"


class ComplaintTargetType(str, Enum):
    SEAT = "座位"
    ROOM = "自习室"
    RESERVATION = "预约单"
    USER = "用户"


class BlacklistMode(str, Enum):
    AUTO = "自动"
    MANUAL = "手动"


class MessageType(str, Enum):
    RESERVATION = "预约通知"
    VIOLATION = "违约通知"
    COMPLAINT = "投诉反馈"
    SYSTEM = "系统通知"
