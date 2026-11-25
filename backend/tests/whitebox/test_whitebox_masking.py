"""白盒测试：PII 脱敏的所有分支。"""

from app.utils import masking


def test_mask_generic_boundaries() -> None:
    assert masking._mask_generic("") == ""
    assert masking._mask_generic("a") == "*"
    assert masking._mask_generic("ab") == "**"
    assert masking._mask_generic("abc") == "a***c"
    assert masking._mask_generic("abcde") == "a***e"
    assert masking._mask_generic("abcdef") == "ab***ef"


def test_mask_phone_variants() -> None:
    assert masking.mask_phone(None) == "—"
    assert masking.mask_phone("   ") == "—"
    assert masking.mask_phone("13800001234") == "138****1234"
    assert masking.mask_phone("138-0000-1234") == "138****1234"
    assert masking.mask_phone("138 0000 1234") == "138****1234"
    # 长度不足 7 位的数字串走通用掩码
    assert masking.mask_phone("12345") == "1***5"
    # 含字母的联系方式走通用掩码
    assert masking.mask_phone("abc123") == "ab***23"


def test_mask_email_variants() -> None:
    assert masking.mask_email(None) == "—"
    assert masking.mask_email("   ") == "—"
    assert masking.mask_email("student@zju.edu.cn") == "s******@zju.edu.cn"
    # 本地部分只有 1 位时仍至少 3 个星号
    assert masking.mask_email("a@x.com") == "a***@x.com"
    # 缺少合法 @ 前缀时退回通用掩码
    assert masking.mask_email("@x.com") == "@x***om"
    assert masking.mask_email("not-an-email") == "no***il"


def test_mask_contact_dispatch() -> None:
    assert masking.mask_contact("") == "—"
    assert masking.mask_contact("student@zju.edu.cn") == "s******@zju.edu.cn"
    assert masking.mask_contact("13800001234") == "138****1234"
    assert masking.mask_contact("138 0000 1234") == "138****1234"
    assert masking.mask_contact("WeChat:abc") == "We***bc"


def test_contact_kind_label() -> None:
    assert masking.contact_kind_label(None) == "未填写"
    assert masking.contact_kind_label(" ") == "未填写"
    assert masking.contact_kind_label("a@b.com") == "邮箱"
    assert masking.contact_kind_label("13800001234") == "手机号"
