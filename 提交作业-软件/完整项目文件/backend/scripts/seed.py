"""创建演示账户：python -m scripts.seed"""

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.enums import Role
from app.models.user import User

DEMO_USERS = [
    ("admin", "admin123", "演示管理员", Role.ADMIN.value),
    ("student", "student123", "演示学生", Role.STUDENT.value),
]


def main() -> None:
    with SessionLocal() as db:
        for student_no, password, name, role in DEMO_USERS:
            exists = db.scalar(select(User).where(User.student_no == student_no))
            if exists:
                continue
            db.add(
                User(
                    name=name,
                    student_no=student_no,
                    password_hash=hash_password(password),
                    role=role,
                )
            )
        db.commit()
    print("演示账户已就绪：admin / admin123，student / student123")


if __name__ == "__main__":
    main()
