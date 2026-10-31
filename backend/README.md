# 后端开发骨架（FastAPI）

## 技术栈

Python 3.11+ · FastAPI · Pydantic 2 · SQLAlchemy 2 · Alembic · MySQL 8.4 · JWT · APScheduler · Pytest

## 目录结构

```
backend/
├── app/
│   ├── main.py              # 应用入口、CORS、异常处理、路由挂载
│   ├── core/                # 配置、数据库、JWT、依赖、业务异常
│   ├── models/              # SQLAlchemy 模型（DR-001～DR-008 + 审计/站内通知）
│   ├── schemas/             # Pydantic 请求/响应模型
│   ├── api/v1/              # 按 M1～M7 拆分的 REST 路由
│   ├── services/            # 业务逻辑（当前多为待实现骨架）
│   ├── tasks/               # APScheduler 定时任务
│   └── utils/               # 时间区间、分页等工具
├── alembic/                 # 数据库迁移
├── scripts/
│   ├── init_db.sql          # 本地建库/建账号（方案 A）
│   └── seed.py              # 演示账户
├── tests/                   # Pytest
├── alembic.ini
└── requirements.txt
```

## 启动

```bash
cd backend

# 1. 创建数据库和专用账号（每位开发者本机执行一次）
#    先修改 scripts/init_db.sql 里的 CHANGE_ME_APP_PASSWORD
mysql -u root -p --default-character-set=utf8mb4 < scripts/init_db.sql

# 2. 虚拟环境与依赖
python -m venv .venv
source .venv/Scripts/activate      # Git Bash；PowerShell 用 .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. 配置（.env 不提交；DATABASE_URL 使用 study_app 和自己的密码）
cp .env.example .env

# 4. 建表（初始迁移已提交，直接升级；不要再自动生成 "init"）
alembic upgrade head

# 5. 演示账户（student / student123，admin / admin123）
python -m scripts.seed

# 6. 启动
uvicorn app.main:app --reload
```

- Swagger UI：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/health>
- 系统使用说明：见 [`../docs/系统使用说明.md`](../docs/系统使用说明.md)
- 数据库表结构：见 [`../docs/数据库表结构说明.md`](../docs/数据库表结构说明.md)
- 数据库初始化与 Alembic 协作流程：见 [`../docs/数据库协作说明.md`](../docs/数据库协作说明.md)

### Alembic 迁移规则

- 迁移由固定负责人生成和审核；其他组员只执行 `alembic upgrade head`。
- 修改模型后由负责人执行 `alembic revision --autogenerate -m "..."`，审核迁移文件后与模型一起提交。
- 已经执行过的迁移不要修改；有新增变化就新建 revision。
- 每次 `git pull` 后先执行 `alembic current` 和 `alembic upgrade head`；提交前执行 `alembic check`。

## 分层约定

```
api/v1/*  →  services/*  →  models/*
                ↓
            schemas/*
```

- 路由只做参数绑定、鉴权与响应声明，不写业务规则。
- M1～M7 的业务逻辑集中在 `services/`；接口均已实现，不再返回 501（保留统一异常处理器作兜底）。
- 预约冲突、幂等、自动违约等规则见需求规格说明书 `docs/` 与各服务函数的 docstring。

## 模块对照

| 模块 | 路由 | 服务 |
|---|---|---|
| M1 座位资源 | `rooms.py`、`seats.py` | `room_service.py`、`seat_service.py` |
| M2 预约管理 | `reservations.py` | `reservation_service.py`、`availability_service.py` |
| M3 签到/违约 | `attendance.py`、`violations.py` | `attendance_service.py`、`violation_service.py` |
| M4 查询 | 各路由的 `/me` 与列表接口 | 对应 `*_service.py` |
| M5 用户/投诉 | `users.py`、`reviews.py`、`complaints.py`、`blacklist.py` | `user_service.py` 等 |
| M6 数据分析 | `dashboard.py` | `dashboard_service.py` |
| M7 站内通知 | `messages.py` | `notification_service.py`、`message_service.py` |

## 测试

```bash
pytest
```

当前仅包含健康检查与时间区间工具测试；业务测试按需求文档的场景（VS-01～VS-06）补充。
