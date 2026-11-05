"""启动辅助脚本 bootstrap_db 的纯函数测试（不连接真实数据库）。"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import make_url

from scripts import bootstrap_db


def _args(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "host": None,
        "port": None,
        "db": None,
        "app_user": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_jwt_rotation_rules() -> None:
    assert bootstrap_db.jwt_needs_rotation("")
    assert bootstrap_db.jwt_needs_rotation("change-me-in-env")
    assert bootstrap_db.jwt_needs_rotation(
        "replace-with-a-long-random-string-at-least-32-bytes"
    )
    assert bootstrap_db.jwt_needs_rotation("x" * 31)
    assert not bootstrap_db.jwt_needs_rotation("x" * 32)
    assert not bootstrap_db.jwt_needs_rotation("a" * 64)


def test_build_url_round_trips_special_characters() -> None:
    cfg = bootstrap_db.DbConfig(
        host="127.0.0.1",
        port=3306,
        user="study_app",
        password="p@ss:word/?#%",
        database="smart_study_room",
    )
    url = make_url(bootstrap_db.build_database_url(cfg))
    assert url.drivername == "mysql+pymysql"
    assert url.username == "study_app"
    assert url.password == "p@ss:word/?#%"
    assert url.host == "127.0.0.1"
    assert url.port == 3306
    assert url.database == "smart_study_room"
    assert url.query.get("charset") == "utf8mb4"


def test_read_env_ignores_comments_and_strips_quotes(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text(
        "# comment\n\n"
        "DATABASE_URL=mysql+pymysql://u:p@h:3306/d\n"
        "QUOTED='value'\n"
        'DOUBLE="other"\n'
        "EMPTY=\n",
        encoding="utf-8",
    )
    values = bootstrap_db.read_env(env)
    assert values["DATABASE_URL"].startswith("mysql+pymysql://")
    assert values["QUOTED"] == "value"
    assert values["DOUBLE"] == "other"
    assert values["EMPTY"] == ""


def test_update_env_file_preserves_other_lines_and_backs_up(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text(
        "# keep me\nAPP_NAME=demo\nDATABASE_URL=old\nJWT_SECRET_KEY=old\n",
        encoding="utf-8",
    )
    bootstrap_db.update_env_file(
        env, {"DATABASE_URL": "new", "JWT_SECRET_KEY": "secret"}
    )
    text = env.read_text(encoding="utf-8")
    assert "# keep me" in text
    assert "APP_NAME=demo" in text
    assert "DATABASE_URL=new" in text
    assert "JWT_SECRET_KEY=secret" in text
    assert (tmp_path / ".env.bak").read_text(encoding="utf-8").startswith("# keep me")


def test_update_env_file_appends_missing_keys(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("APP_NAME=demo\n", encoding="utf-8")
    bootstrap_db.update_env_file(env, {"JWT_SECRET_KEY": "x" * 64})
    text = env.read_text(encoding="utf-8")
    assert "APP_NAME=demo" in text
    assert "JWT_SECRET_KEY=" + "x" * 64 in text


def test_parse_config_prefers_cli_over_env() -> None:
    env = {"DATABASE_URL": "mysql+pymysql://app:pw@db.local:3307/prod?charset=utf8mb4"}
    cfg = bootstrap_db.parse_config(
        env, _args(host="127.0.0.1", port=3306, db="demo", app_user="study_app")
    )
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 3306
    assert cfg.database == "demo"
    assert cfg.user == "study_app"
    assert cfg.password == "pw"


def test_parse_config_rejects_non_mysql_url() -> None:
    with pytest.raises(bootstrap_db.ConfigError):
        bootstrap_db.parse_config({"DATABASE_URL": "sqlite:///demo.db"}, _args())


class _FakeCursor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...] | None]] = []

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *_: object) -> bool:
        return False

    def execute(self, sql: str, params: tuple[object, ...] | None = None) -> None:
        self.calls.append((sql, params))


class _FakeConnection:
    def __init__(self) -> None:
        self.cursor_obj = _FakeCursor()

    def cursor(self) -> _FakeCursor:
        return self.cursor_obj


def test_provision_creates_database_and_both_hosts() -> None:
    cfg = bootstrap_db.DbConfig(
        host="127.0.0.1",
        port=3306,
        user="study_app",
        password="secret",
        database="smart_study_room",
    )
    conn = _FakeConnection()
    bootstrap_db._provision(conn, cfg)  # type: ignore[arg-type]

    calls = conn.cursor_obj.calls
    assert calls[0][0].startswith("CREATE DATABASE IF NOT EXISTS `smart_study_room`")
    create_user_calls = [call for call in calls if "CREATE USER" in call[0]]
    assert len(create_user_calls) == 2
    assert all(call[1][0] == "study_app" for call in create_user_calls)
    assert [call[1][1] for call in create_user_calls] == ["localhost", "127.0.0.1"]
