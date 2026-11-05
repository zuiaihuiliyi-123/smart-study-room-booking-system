"""一键启动辅助脚本：检查并准备 ``backend/.env`` 与 MySQL 数据库。

由根目录 ``start.bat`` 调用，也可以手动执行（工作目录为 ``backend``）::

    python -m scripts.bootstrap_db probe
    python -m scripts.bootstrap_db check
    python -m scripts.bootstrap_db ensure --root-user root

命令：

``probe``
    只做 TCP 连通性探测，用于判断是否需要启动 MySQL 服务。
``check``
    读取 ``.env``，尝试用应用账号连接数据库，并校验 JWT 密钥。
``ensure``
    在 ``check`` 的基础上自动修复：数据库/账号不存在时用 MySQL 根账号创建，
    JWT 密钥缺失或过弱时生成新的随机密钥。未提供根账号且数据库不可用时退出。

退出码：

====  ====================================================
0     可用，或已成功修复
1     意外错误
2     需要数据库初始化/修复（可带根账号重试 ``ensure``）
3     MySQL 服务不可达
5     数据库可用，但 JWT 密钥需要重新生成
====  ====================================================

安全约定：本脚本不会打印任何密码；根密码优先通过环境变量
``MYSQL_ROOT_PASSWORD`` 传入，避免出现在命令行参数和进程列表中。
所有控制台输出使用英文，避免 Windows cmd 的 OEM 代码页导致乱码。
"""

from __future__ import annotations

import argparse
import os
import re
import secrets
import socket
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import pymysql
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = BACKEND_DIR / ".env"
ENV_EXAMPLE = BACKEND_DIR / ".env.example"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 3306
DEFAULT_DATABASE = "smart_study_room"
DEFAULT_APP_USER = "study_app"
DEFAULT_APP_PASSWORD = "CHANGE_ME_APP_PASSWORD"

# 与 app/core/config.py 的启动校验保持一致
JWT_PLACEHOLDERS = {
    "",
    "change-me-in-env",
    "replace-with-a-long-random-string-at-least-32-bytes",
}
JWT_MIN_BYTES = 32

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_NEEDS_PROVISION = 2
EXIT_DB_UNREACHABLE = 3
EXIT_NEEDS_JWT = 5

_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")

_UNREACHABLE_CODES = {2003, 2005, 2006, 2013}
_ACCESS_CODES = {1044, 1045, 1049, 1524, 1698, 2059}


class ConfigError(Exception):
    """``.env`` 中的配置无法使用。"""


@dataclass
class DbConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


# ---------------------------------------------------------------------------
# .env 读写
# ---------------------------------------------------------------------------


def read_env(path: Path) -> dict[str, str]:
    """读取 KEY=VALUE 形式的 .env；支持注释、空行和简单引号。"""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def update_env_file(path: Path, updates: dict[str, str]) -> None:
    """就地更新 .env 中的指定键，保留原有注释和顺序。

    已存在的 .env 会先备份到同目录的 ``.env.bak``，避免配置丢失。
    """
    existing = path.is_file()
    if existing:
        original = path.read_text(encoding="utf-8-sig")
        lines = original.splitlines()
    elif ENV_EXAMPLE.is_file():
        original = ENV_EXAMPLE.read_text(encoding="utf-8")
        lines = original.splitlines()
    else:
        original = ""
        lines = _minimal_env_lines()

    pending = dict(updates)
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in pending:
                new_lines.append(f"{key}={pending.pop(key)}")
                continue
        new_lines.append(line)

    if pending:
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        new_lines.extend(f"{key}={value}" for key, value in pending.items())

    new_text = "\n".join(new_lines).rstrip() + "\n"
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(new_text, encoding="utf-8")
    if existing:
        path.with_name(".env.bak").write_text(original, encoding="utf-8")
    os.replace(tmp_path, path)


def _minimal_env_lines() -> list[str]:
    return [
        "APP_NAME=Smart Study Room",
        "DEBUG=true",
        "",
        f"DATABASE_URL=mysql+pymysql://{DEFAULT_APP_USER}:{DEFAULT_APP_PASSWORD}"
        f"@{DEFAULT_HOST}:{DEFAULT_PORT}/{DEFAULT_DATABASE}?charset=utf8mb4",
        "",
        "JWT_ALGORITHM=HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES=120",
        'CORS_ORIGINS=["http://127.0.0.1:5173","http://localhost:5173"]',
    ]


# ---------------------------------------------------------------------------
# 配置解析
# ---------------------------------------------------------------------------


def parse_config(env: dict[str, str], args: argparse.Namespace) -> DbConfig:
    """合并 .env 与命令行参数，得到应用数据库连接参数。"""
    raw_url = env.get("DATABASE_URL", "").strip()
    url = None
    if raw_url:
        try:
            url = make_url(raw_url)
        except ArgumentError as exc:
            raise ConfigError(f"DATABASE_URL is not a valid SQLAlchemy URL: {exc}") from exc
        if not url.drivername.startswith("mysql"):
            raise ConfigError(
                f"DATABASE_URL uses '{url.drivername}'; this launcher only supports MySQL."
            )

    host = args.host or (url.host if url else None) or os.environ.get("SSR_DB_HOST") or DEFAULT_HOST
    port = (
        args.port
        or (url.port if url else None)
        or _port_from_env()
        or DEFAULT_PORT
    )
    user = (
        args.app_user
        or (url.username if url else None)
        or os.environ.get("SSR_DB_USER")
        or DEFAULT_APP_USER
    )
    password = url.password or "" if url else ""
    database = (
        args.db
        or (url.database if url else None)
        or os.environ.get("SSR_DB_NAME")
        or DEFAULT_DATABASE
    )
    return DbConfig(
        host=str(host),
        port=int(port),
        user=str(user),
        password=str(password),
        database=str(database),
    )


def _port_from_env() -> int | None:
    raw = os.environ.get("SSR_DB_PORT")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def build_database_url(cfg: DbConfig) -> str:
    return (
        f"mysql+pymysql://{quote(cfg.user, safe='')}:{quote(cfg.password, safe='')}"
        f"@{cfg.host}:{cfg.port}/{cfg.database}?charset=utf8mb4"
    )


def jwt_needs_rotation(value: str) -> bool:
    value = (value or "").strip()
    return value in JWT_PLACEHOLDERS or len(value.encode("utf-8")) < JWT_MIN_BYTES


# ---------------------------------------------------------------------------
# 数据库操作
# ---------------------------------------------------------------------------


def connect(cfg: DbConfig, *, database: str | None) -> pymysql.connections.Connection:
    return pymysql.connect(
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
        database=database,
        charset="utf8mb4",
        connect_timeout=5,
        read_timeout=10,
        write_timeout=10,
        autocommit=True,
    )


def describe_error(exc: pymysql.err.OperationalError) -> tuple[int, str]:
    code = exc.args[0] if exc.args and isinstance(exc.args[0], int) else 0
    message = exc.args[1] if len(exc.args) > 1 else str(exc)
    return code, str(message)


def probe(cfg: DbConfig) -> int:
    try:
        with socket.create_connection((cfg.host, cfg.port), timeout=3):
            pass
    except OSError as exc:
        print(f"[error] MySQL is not reachable at {cfg.host}:{cfg.port} ({exc}).")
        return EXIT_DB_UNREACHABLE
    print(f"[ok] MySQL is reachable at {cfg.host}:{cfg.port}.")
    return EXIT_OK


def check(cfg: DbConfig, env: dict[str, str], env_path: Path) -> int:
    if not env_path.is_file():
        print(f"[info] {env_path} does not exist; database setup is required.")
        return EXIT_NEEDS_PROVISION

    try:
        with connect(cfg, database=cfg.database):
            pass
    except pymysql.err.OperationalError as exc:
        code, message = describe_error(exc)
        if code in _UNREACHABLE_CODES:
            print(f"[error] Cannot connect to MySQL at {cfg.host}:{cfg.port} ({message}).")
            return EXIT_DB_UNREACHABLE
        print(
            f"[info] Database login failed for {cfg.user}@{cfg.host}:{cfg.port}"
            f"/{cfg.database} (code {code}: {message})."
        )
        return EXIT_NEEDS_PROVISION

    print(
        f"[ok] Database connection OK: {cfg.host}:{cfg.port}/{cfg.database} "
        f"(user {cfg.user})."
    )
    if jwt_needs_rotation(env.get("JWT_SECRET_KEY", "")):
        print("[info] JWT_SECRET_KEY is missing, still a placeholder, or too short.")
        return EXIT_NEEDS_JWT
    print("[ok] JWT_SECRET_KEY looks valid.")
    return EXIT_OK


def ensure(cfg: DbConfig, env: dict[str, str], env_path: Path, args: argparse.Namespace) -> int:
    updates: dict[str, str] = {}
    db_ready = False

    try:
        with connect(cfg, database=cfg.database):
            pass
        db_ready = True
        print(
            f"[ok] Database connection OK: {cfg.host}:{cfg.port}/{cfg.database} "
            f"(user {cfg.user})."
        )
    except pymysql.err.OperationalError as exc:
        code, message = describe_error(exc)
        if code in _UNREACHABLE_CODES:
            print(f"[error] Cannot connect to MySQL at {cfg.host}:{cfg.port} ({message}).")
            return EXIT_DB_UNREACHABLE
        print(
            f"[info] Database is not ready (code {code}: {message}); "
            "trying to create it with the MySQL root account."
        )

    if not db_ready:
        root_user = args.root_user or os.environ.get("MYSQL_ROOT_USER") or "root"
        root_provided = (
            args.root_user is not None
            or args.root_password is not None
            or "MYSQL_ROOT_USER" in os.environ
            or "MYSQL_ROOT_PASSWORD" in os.environ
        )
        if not root_provided:
            print(
                "[error] The database or application account is not ready, and no MySQL "
                "root credentials were supplied.\n"
                "        Re-run with --root-user root (the launcher prompts for the "
                "password), or create the database manually with "
                "backend/scripts/init_db.sql."
            )
            return EXIT_NEEDS_PROVISION

        root_password = (
            args.root_password
            if args.root_password is not None
            else os.environ.get("MYSQL_ROOT_PASSWORD", "")
        )
        root_cfg = DbConfig(
            host=cfg.host,
            port=cfg.port,
            user=root_user,
            password=root_password,
            database="",
        )
        try:
            root_conn = connect(root_cfg, database=None)
        except pymysql.err.OperationalError as exc:
            code, message = describe_error(exc)
            if code in _UNREACHABLE_CODES:
                print(f"[error] Cannot connect to MySQL at {cfg.host}:{cfg.port} ({message}).")
                return EXIT_DB_UNREACHABLE
            print(f"[error] MySQL root login failed (code {code}: {message}).")
            return EXIT_NEEDS_PROVISION

        if not _IDENTIFIER_RE.match(cfg.database):
            print(f"[error] Unsafe database name: {cfg.database!r} (use letters, digits, _).")
            return EXIT_ERROR
        if not _IDENTIFIER_RE.match(cfg.user):
            print(f"[error] Unsafe application user name: {cfg.user!r} (use letters, digits, _).")
            return EXIT_ERROR

        if not cfg.password or cfg.password == DEFAULT_APP_PASSWORD or "CHANGE_ME" in cfg.password:
            cfg.password = secrets.token_hex(16)

        try:
            _provision(root_conn, cfg)
        finally:
            root_conn.close()

        updates["DATABASE_URL"] = build_database_url(cfg)
        print(
            f"[ok] Created database '{cfg.database}' and account '{cfg.user}' "
            "for localhost and 127.0.0.1."
        )

        try:
            with connect(cfg, database=cfg.database):
                pass
        except pymysql.err.OperationalError as exc:
            code, message = describe_error(exc)
            print(f"[error] The new application account cannot log in (code {code}: {message}).")
            return EXIT_NEEDS_PROVISION
        print("[ok] Application account verified.")

    if jwt_needs_rotation(env.get("JWT_SECRET_KEY", "")):
        updates["JWT_SECRET_KEY"] = secrets.token_hex(32)
        print("[ok] Generated a new JWT_SECRET_KEY (64 hex chars).")

    # .env 不存在、缺少连接串或仍是示例占位符时，把本次使用的真实连接串写回去。
    # 否则新生成的 .env 会保留 .env.example 里的 CHANGE_ME_APP_PASSWORD。
    if (
        not env_path.is_file()
        or "DATABASE_URL" not in env
        or "CHANGE_ME" in env.get("DATABASE_URL", "")
    ):
        updates["DATABASE_URL"] = build_database_url(cfg)

    if updates:
        update_env_file(env_path, updates)
        print(f"[ok] Wrote {env_path}.")
        if env_path.with_name(".env.bak").is_file():
            print(f"[info] Previous configuration backed up to {env_path.with_name('.env.bak')}.")
    else:
        print(f"[ok] {env_path} is already up to date.")

    print(
        f"[ok] Ready: {cfg.host}:{cfg.port}/{cfg.database} "
        f"(user {cfg.user}). Passwords are stored only in {env_path.name}."
    )
    return EXIT_OK


def _provision(conn: pymysql.connections.Connection, cfg: DbConfig) -> None:
    """创建数据库与应用账号；重复执行是安全的。"""
    db = cfg.database
    with conn.cursor() as cursor:
        # 数据库名已通过 _IDENTIFIER_RE 校验，可以安全地反引号拼接。
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        for host in ("localhost", "127.0.0.1"):
            cursor.execute(
                "CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s",
                (cfg.user, host, cfg.password),
            )
            # 账号已存在时把密码重置为当前 .env/本次生成的值，避免旧密码残留。
            cursor.execute(
                "ALTER USER %s@%s IDENTIFIED BY %s",
                (cfg.user, host, cfg.password),
            )
            cursor.execute(
                f"GRANT ALL PRIVILEGES ON `{db}`.* TO %s@%s",
                (cfg.user, host),
            )


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare backend/.env and the local MySQL database for the app."
    )
    parser.add_argument("command", choices=["probe", "check", "ensure"])
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
        help="Path to the .env file (default: backend/.env).",
    )
    parser.add_argument("--host", help="MySQL host override.")
    parser.add_argument("--port", type=int, help="MySQL port override.")
    parser.add_argument("--db", help="Database name override.")
    parser.add_argument("--app-user", help="Application MySQL user override.")
    parser.add_argument("--root-user", help="MySQL root user, used only by 'ensure'.")
    parser.add_argument(
        "--root-password",
        help="MySQL root password; prefer MYSQL_ROOT_PASSWORD to keep it out of argv.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    env_path: Path = args.env_file.expanduser().resolve()
    env = read_env(env_path)

    try:
        cfg = parse_config(env, args)
    except ConfigError as exc:
        if args.command == "check":
            print(f"[error] {exc}")
            return EXIT_NEEDS_PROVISION
        # probe / ensure：连接串损坏时退回默认值，ensure 会重新生成它。
        print(f"[warn] {exc} Falling back to default connection settings.")
        env.pop("DATABASE_URL", None)
        cfg = parse_config({}, args)
    except Exception as exc:  # noqa: BLE001 - 启动脚本需要给出可读的错误而非堆栈
        print(f"[error] Cannot parse backend configuration: {exc}")
        return EXIT_ERROR

    if args.command == "probe":
        return probe(cfg)
    if args.command == "check":
        return check(cfg, env, env_path)
    return ensure(cfg, env, env_path, args)


if __name__ == "__main__":
    sys.exit(main())
