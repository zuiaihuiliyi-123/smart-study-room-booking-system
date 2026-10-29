"""集中导入所有 ORM 模型，确保 Alembic autogenerate 能发现全部表。"""

from app.models.audit_log import AuditLog
from app.models.blacklist import BlacklistEntry
from app.models.complaint import Complaint
from app.models.message import StationMessage
from app.models.reservation import Reservation
from app.models.review import Review
from app.models.room import Area, Room
from app.models.seat import Seat
from app.models.user import User
from app.models.violation import ViolationRecord

__all__ = [
    "Area",
    "AuditLog",
    "BlacklistEntry",
    "Complaint",
    "Reservation",
    "Review",
    "Room",
    "Seat",
    "StationMessage",
    "User",
    "ViolationRecord",
]
