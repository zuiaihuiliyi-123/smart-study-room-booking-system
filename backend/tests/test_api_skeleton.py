"""接口骨架回归：路由是否挂载、参数校验、未实现模块的占位行为。

说明：接口测试通过 ``api_client`` 夹具把 get_db 覆盖为内存 SQLite，
因此不依赖本机 MySQL；业务规则测试见 test_m1_resource / test_m5_governance。
"""

import pytest

from app.services import dashboard_service


def test_openapi_contains_all_modules(client) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/rooms" in paths
    assert "/api/v1/reservations" in paths
    assert "/api/v1/dashboard/overview" in paths
    assert "/api/v1/messages/me" in paths


def test_implemented_room_endpoint_returns_list(api_client) -> None:
    # M1 已实现：空库应返回 [] 而不是 501
    response = api_client.get("/api/v1/rooms")

    assert response.status_code == 200
    assert response.json() == []


def test_unimplemented_service_still_raises(db) -> None:
    # 尚未实现的模块（M6 看板）在服务层仍抛 NotImplementedError，路由层映射为 501
    with pytest.raises(NotImplementedError):
        dashboard_service.get_overview(db)


def test_protected_endpoint_requires_login(api_client) -> None:
    response = api_client.get("/api/v1/reservations/me")

    assert response.status_code == 401


def test_login_payload_is_validated(client) -> None:
    response = client.post("/api/v1/auth/login", json={})

    assert response.status_code == 422
