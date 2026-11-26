"""M5 用户资料单元测试：服务端脱敏、受限解除时间、列表筛选与分页。"""

from datetime import timedelta

from app.models.enums import BlacklistMode
from app.services import user_service


def test_to_user_read_masks_admin_view_but_not_self(db, make_user, freeze_now):
    phone = make_user(student_no="S91001", contact="13800001234")
    email = make_user(student_no="S91002", contact="student@zju.edu.cn")
    blank = make_user(student_no="S91003", contact=None)

    assert user_service.to_user_read(db, phone, mask_contact=True).contact == "138****1234"
    assert (
        user_service.to_user_read(db, email, mask_contact=True).contact
        == "s******@zju.edu.cn"
    )
    assert user_service.to_user_read(db, blank, mask_contact=True).contact == "—"
    # 本人读取本人资料保持原值（只读接口不能把脱敏值写回库）
    assert user_service.to_user_read(db, phone, mask_contact=False).contact == "13800001234"


def test_restrict_until_only_returns_active_auto_entries(
    db, make_student, make_blacklist, freeze_now
):
    student = make_student(student_no="S91010")
    now = freeze_now

    # 手动限制没有自动解除时间：界面不能显示“预计解除”
    manual = make_blacklist(
        student.id,
        mode=BlacklistMode.MANUAL.value,
        start_at=now - timedelta(days=1),
        expire_at=now + timedelta(days=5),
    )
    assert user_service._restrict_until(db, student.id) is None

    manual.released_at = now
    manual.release_reason = "管理员人工解除"
    manual.active_user_id = None
    db.commit()

    auto = make_blacklist(
        student.id,
        mode=BlacklistMode.AUTO.value,
        start_at=now - timedelta(days=1),
        expire_at=now + timedelta(days=6),
    )
    assert user_service._restrict_until(db, student.id) == auto.expire_at

    auto.released_at = now
    auto.release_reason = "到期自动解除"
    auto.active_user_id = None
    db.commit()

    # 已过期但尚未跑解除任务的历史记录，也不能被当作“预计解除时间”
    make_blacklist(
        student.id,
        start_at=now - timedelta(days=2),
        expire_at=now - timedelta(days=1),
    )
    assert user_service._restrict_until(db, student.id) is None


def test_list_users_blank_keyword_and_like_wildcard(db, make_user):
    """记录 S1-11 观察项：keyword 直接拼进 LIKE，`%`/`_` 未转义。"""
    make_user(student_no="S91020", name="张三")
    make_user(student_no="S91021", name="李四")

    blank = user_service.list_users(db, 1, 20, keyword="   ")
    assert blank.total == 2

    wildcard = user_service.list_users(db, 1, 20, keyword="%")
    assert wildcard.total == 2


def test_list_users_page_out_of_range_keeps_total(db, make_user):
    make_user(student_no="S91030")
    make_user(student_no="S91031")

    page = user_service.list_users(db, 5, 20)

    assert page.items == []
    assert page.total == 2
    assert page.page == 5
