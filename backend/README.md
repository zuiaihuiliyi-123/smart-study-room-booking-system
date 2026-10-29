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
├── scripts/seed.py          # 演示账户
├── tests/                   # Pytest
├── alembic.ini
└── requirements.txt
```

## 启动

```bash
# 1. 创建数据库（utf8mb4）
#    CREATE DATABASE smart_study_room CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

cd backend

# 2. 虚拟环境与依赖
python -m venv .venv
source .venv/Scripts/activate      # Git Bash；PowerShell 用 .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. 配置
cp .env.example .env               # 按本机 MySQL 修改 DATABASE_URL

# 4. 建表
alembic revision --autogenerate -m "init"
alembic upgrade head

# 5. 演示账户（student / student123，admin / admin123）
python -m scripts.seed

# 6. 启动
uvicorn app.main:app --reload
```

- Swagger UI：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/health>

## 分层约定

```
api/v1/*  →  services/*  →  models/*
                ↓
            schemas/*
```

- 路由只做参数绑定、鉴权与响应声明，不写业务规则。
- M1～M7 的业务逻辑集中在 `services/`；尚未实现的接口抛出 `NotImplementedError`，统一返回 HTTP 501。
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
