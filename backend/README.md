# 后端开发（FastAPI）—— 预约与违约

本目录在仓库原有骨架上实现 **预约（M2）** 与 **违约（M3）** 后端，并补齐其依赖的资源查询、黑名单与审计能力。

- 规则取值来自《智慧自习室预约与管理系统 需求规格说明书（课程结构版 V2.0）》：30 分钟粒度、左闭右开 `[s, e)`、提前 7 天、单次 4 小时、每日 2 条、签到窗口 `[s-15min, s+15min)`、取消时限 30 分钟、违约阈值 3 次、限制期 7 天。
- 接口路径与 `frontend/src/api/reservation.ts`、`frontend/src/api/violation.ts` 中的调用保持一致。
- **不改变座位资源状态**：预约、签到、签退、取消、违约全程只写预约单（§10.0 MD-02）。

---

## 1. 已实现范围

| 模块 | 能力 | 状态 |
|---|---|---|
| M1 座位资源（支撑） | 自习室/座位查询、新建自习室/区域/座位、座位资源状态调整 | 已实现 |
| M2 预约 | 创建预约（C1～C6）、可预约座位查询、本人/全部预约列表、用户取消、管理员强制取消、场地关闭批量取消 | 已实现 |
| M3 签到/违约 | 签到、签退、自动违约、管理员手动违约登记、本人/全部违约记录 | 已实现 |
| M5 黑名单（违约后果） | 阈值自动受限、管理员手动加入/解除、自动限制期满解除 | 已实现 |
| NFR-009 审计 | 关键操作与越权尝试写审计；管理员查询审计日志 | 已实现 |
| M7 通知（仅站内） | 预约成功/取消、违约、强制取消等站内消息 | 已实现 |
| M4 查询 | 预约记录、违约记录、座位资源状态（随 M2/M3 提供） | 已实现 |
| M5 投诉、评价；M6 看板 | 业务服务仍为骨架，调用返回 HTTP 501 | 未实现（本次范围外） |
| FR-024 违约申诉、FR-033 记录导出 | 需求 V2.0 已裁定排除 | 未实现 |

---

## 2. 接口清单

基础路径：`/api/v1`。Swagger UI：<http://127.0.0.1:8000/docs>

### 认证与资源

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/auth/login` | 公开 | 学号/工号 + 口令，返回 JWT |
| GET | `/auth/me` | 已登录 | 当前用户 |
| GET | `/rooms` | 已登录 | 自习室列表 |
| GET | `/rooms/{room_id}/seats` | 已登录 | 座位列表（含资源状态） |
| POST | `/rooms` | 管理员 | 新建自习室 |
| POST | `/rooms/{room_id}/areas` | 管理员 | 新建区域 |
| POST | `/seats` | 管理员 | 新增座位（默认「可用」） |
| PATCH | `/seats/{seat_id}/status` | 管理员 | 调整资源状态；BR-019 默认保留冲突预约 |

### 预约（M2）

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/reservations` | 学生 | 创建预约；请求体含 `idempotency_key` |
| GET | `/reservations/available-seats` | 已登录 | 查询时段内可预约座位（C1/C3/C4） |
| GET | `/reservations/me` | 已登录 | 本人预约记录（分页、状态筛选） |
| GET | `/reservations` | 管理员 | 全部预约记录（分页、状态筛选） |
| POST | `/reservations/{id}/cancel` | 学生 | 取消本人「待使用」预约（`< s-30min`） |
| POST | `/reservations/{id}/force-cancel` | 管理员 | 强制取消「待使用」预约，原因必填，不计违约 |
| POST | `/reservations/{id}/check-in` | 学生 | 签到 |
| POST | `/reservations/{id}/check-out` | 学生 | 签退 |

`POST /seats/{id}/status` 额外支持 `cancel_conflicts` 与 `confirm`：存在冲突的未来预约时，默认**只提示、不取消**（BR-019）；显式选择批量取消且 `confirm=true` 才执行（BR-022），不计违约、不补偿。

### 违约与黑名单（M3 / M5）

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/violations/me` | 已登录 | 本人违约记录 |
| GET | `/violations` | 管理员 | 全部违约记录 |
| POST | `/violations/manual` | 管理员 | 对「使用中」预约手动登记违约，原因必填 |
| GET | `/blacklist` | 管理员 | 黑名单记录（含历史） |
| POST | `/blacklist` | 管理员 | 手动加入黑名单（原因、期限） |
| POST | `/blacklist/{id}/release` | 管理员 | 解除黑名单，请求体 `{"reason": "..."}` |
| GET | `/audit-logs` | 管理员 | 审计日志查询（NFR-009） |

> 与前端契约的差异：`/blacklist/{id}/release` 需要 `{"reason": "..."}` 请求体（ST-043 要求填写原因）；`/audit-logs` 是本次新增的管理端查询接口，前端尚未接入。

---

## 3. 关键规则与实现位置

| 规则 | 本版取值 | 实现位置 |
|---|---|---|
| BR-001 时间粒度 | 30 分钟；未对齐直接拒绝，不自动取整（TB-13） | `services/availability_service.py` `_validate_interval` |
| BR-002 提前天数 | 今天起 7 天内；开始时间必须晚于当前时间 | 同上 |
| BR-003 单次时长 | ≤ 4 小时 | 同上 |
| BR-004 每日次数 | ≤ 2 条**有效**预约/日（待使用 + 使用中） | `availability_service.check_reservation_rules` |
| BR-005 用户时段不重叠 | 唯一约束 `(user_id, slot_start)` + C4 校验 | `models/reservation_slot.py`、`reservation_service` |
| BR-006 座位时段独占 | 唯一约束 `(seat_id, slot_start)` + C3 校验 | 同上 |
| BR-007 签到窗口 | `[s-15min, s+15min)`；13:45 可签、14:15 不可签（TB-08） | `services/attendance_service.py` |
| BR-008 违约判定 | `now >= s+15min` 仍未签到 | `tasks/auto_violation.py`、`violation_service.apply_auto_violation` |
| BR-009 受限阈值 | 累计有效违约 ≥ 3 次 | `blacklist_service.restrict_if_threshold` |
| BR-010 限制期限 | 7 天；**自动限制**期满解除，**手动限制不自动解除** | `tasks/blacklist_expiry.py` |
| BR-011 取消时限 | 提交时刻 `< s-30min` 可取消；`>= s-30min` 拒绝（ST-029），不计违约 | `reservation_service.cancel_my_reservation` |
| BR-015 手动违约原因 | 必填，记录操作者与时间 | `violation_service.register_manual` |
| BR-017 不可预约座位 | 座位「维修中/停用」或自习室停用/非开放时间一律拒绝 | `availability_service` C1/C2 |
| BR-018 权限边界 | 学生仅本人；管理员可查全部；学生不能调用管理员接口 | `core/dependencies.py`、各服务归属校验 |
| BR-019 场地关闭 | 默认保留冲突预约并提示；显式选择才批量取消，不计违约 | `seat_service.update_seat_status` |
| BR-020 区间开闭 | 左闭右开；重叠判定 `s1 < e2 且 s2 < e1` | `utils/time_utils.py`、`availability_service` |
| BR-021 幂等 | 同一用户 + 同一幂等键返回同一张预约单；违约按「预约单 + 类型」去重 | `reservation_service`、`models/violation.py` |
| BR-022 批量确认 | 批量取消须二次确认并写审计 | `seat_service.update_seat_status` |

状态转换覆盖：ST-020（签到）、ST-021/022（取消/强制取消）、ST-023（自动违约）、ST-024/025（签退/自动结束）、ST-026（手动违约）、ST-027（签到校验失败）、ST-028（创建被拒）、ST-029（超时取消）、ST-030（重复签到）、ST-031（终态操作）、ST-032（违约未填原因）、ST-034（任务幂等）、ST-041/042/043（黑名单）。

---

## 4. 并发、幂等与时间边界

### 4.1 并发（FR-014 / NFR-011）

`reservations` 表之外增加实现层辅助表 `reservation_slots`：把预约区间按 30 分钟物化为多行，并用两个唯一约束兜底：

- `uq_slot_seat_start (seat_id, slot_start)` → 同一座位同一时段至多一条有效预约；
- `uq_slot_user_start (user_id, slot_start)` → 同一用户同一时段至多一条有效预约。

创建预约时先 `SELECT ... FOR UPDATE` 锁定座位与用户行，再校验并写入；若并发写发生唯一约束冲突，回滚后重新查询冲突并返回 `C3_BR-006` / `C4_BR-005` / `ST-035`。取消、违约、签退、自动结束都会删除对应槽位，时段因此自动重新可预约（LK-03 / LK-04），**无需回写座位状态**。

该表不对前端暴露，仅用于保证持久层一致性。

### 4.2 幂等（FR-015 / BR-021）

- 预约：`uq_reservation_idempotency (user_id, idempotency_key)`。重复提交返回同一张预约单；同一键用于不同「座位 + 时段」返回 `IDEMPOTENCY_KEY_REUSED`。
- 自动违约：`uq_violation_reservation_type (reservation_id, type)` + 服务层先查后写。任务重复执行不新增记录、不重复累加次数（ST-034）。
- 手动违约：重复登记返回原记录，不重复累加。

### 4.3 时间边界（课程版 4.3 节）

| 场景 | 判定 |
|---|---|
| `[14:00,16:00)` 与 `[16:00,18:00)` | 不冲突（TB-01） |
| `[14:00,16:00)` 与 `[15:00,17:00)` | 冲突（TB-02） |
| 已取消/已违约的预约 | 不占用时段（TB-05/06） |
| 使用中但已过结束时间、任务尚未执行 | 仍占用（TB-07） |
| 签到窗口 | `[13:45, 14:15)`；13:45 可签、14:15 不可签（TB-08） |
| 取消时限 | `< 13:30` 可取消；`>= 13:30` 拒绝（TB-09） |
| 自动违约触发 | `now >= 14:15`（TB-10） |
| 跨日预约 | 拒绝（TB-11） |
| 时间粒度 | 未对齐拒绝，不取整（TB-13） |

所有判定使用**服务器本地时间**（`utils/time_utils.now()`，naive datetime），不使用客户端时间（TB-12 / NFR-010）。

---

## 5. 错误格式

```json
{
  "code": "C3_BR-006",
  "message": "该座位在所选时段已被占用",
  "details": {
    "condition": "C3",
    "rule": "BR-006",
    "params": {
      "conflicts": [{"reservation_id": 12, "start_time": "14:00:00", "end_time": "16:00:00"}]
    }
  }
}
```

| HTTP | 含义 | 示例 |
|---|---|---|
| 401 | 未登录 / 令牌失效 | `INVALID_CREDENTIALS` |
| 403 | 无权限、账户受限/停用 | `ST-047`、`ST-048` |
| 404 | 对象不存在 | `RESERVATION_NOT_FOUND` |
| 409 | 资源/状态冲突 | `C1_BR-017`、`C2`、`C3_BR-006`、`C4_BR-005`、`ST-022`、`ST-026` |
| 422 | 规则参数/时间边界不通过 | `C6_BR-001`、`C6_BR-004`、`ST-027`、`ST-029`、`BR-022` |
| 501 | 骨架模块尚未实现 | `NOT_IMPLEMENTED` |

错误响应不包含他人的姓名、学号等身份字段（NFR-006）；冲突明细只返回预约单编号与时段。

---

## 6. 启动

### 6.1 MySQL 8.4（推荐）

```bash
# 1. 建库（utf8mb4）
#    CREATE DATABASE smart_study_room CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

cd backend
python -m venv .venv
source .venv/Scripts/activate        # Git Bash；PowerShell 用 .venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env                 # 修改 DATABASE_URL / JWT_SECRET_KEY

alembic upgrade head                 # 建表（含初始迁移）
python -m scripts.seed               # 演示账户 + 自习室 + 10 个座位

uvicorn app.main:app --reload
```

### 6.2 SQLite 快速体验（无需 MySQL）

```bash
cd backend
DATABASE_URL="sqlite:///./dev.db" alembic upgrade head
DATABASE_URL="sqlite:///./dev.db" python -m scripts.seed
DATABASE_URL="sqlite:///./dev.db" SCHEDULER_ENABLED=false uvicorn app.main:app --reload
```

> PowerShell 写法：`$env:DATABASE_URL="sqlite:///./dev.db"`。

演示账户：

| 账号 | 口令 | 角色 |
|---|---|---|
| `admin` | `admin123` | 自习室管理员 |
| `student` | `student123` | 学生 |
| `student2` | `student123` | 学生 |

### 6.3 在 Swagger 中调试

1. 展开 `POST /api/v1/auth/login` → Try it out，填入：

   ```json
   {"student_no": "student", "password": "student123"}
   ```

2. 复制响应中的 `access_token`。
3. 点击页面右上角 **Authorize**，把 token 直接粘贴进去（不需要加 `Bearer ` 前缀）。
4. 之后即可调用 `/reservations`、`/violations/me` 等受保护接口；管理员接口请用 `admin / admin123` 登录后重复上述步骤。

> 认证方案为 HTTP Bearer。登录接口本身是 JSON 形式，因此没有使用 Swagger 的 OAuth2 用户名/密码弹窗。

---

## 7. 测试

```bash
cd backend
pytest                      # 65 项
pytest -q tests/test_reservations.py
```

测试使用临时 SQLite 文件库，自动建表/清理；`SCHEDULER_ENABLED=false`，时间通过 monkeypatch 冻结在 `2026-10-29 10:00`，避免真实时钟导致边界抖动。

| 文件 | 数量 | 覆盖 |
|---|---|---|
| `test_reservations.py` | 24 | 创建成功、C1～C6、TB-01/03 相邻时段、幂等、并发、取消边界、强制取消、签到/签退 |
| `test_violations.py` | 10 | 自动违约幂等、阈值受限、受限后已有预约、期满解除、自动结束、手动违约、查询权限、站内通知 |
| `test_admin_resources.py` | 9 | 自习室/座位维护、资源状态变更、BR-019 默认保留、BR-022 批量确认、审计查询 |
| `test_availability.py` | 6 | 可预约座位过滤（C1/C3/C4）、相邻时段、房间停用/非开放时间 |
| `test_blacklist.py` | 4 | 手动加入/解除、手动限制不自动解除、重复加入、权限 |
| `test_auth.py` | 6 | 登录、错误口令、停用账户、受限账户可登录、越权审计 |
| `test_health.py` | 1 | 健康检查 |
| `test_time_utils.py` | 5 | 区间重叠、粒度、签到窗口、取消时限（TB-09 严格小于） |

验收场景对应：

- **VS-01 并发预约** → `test_concurrent_requests_create_exactly_one`
- **VS-02 幂等** → `test_idempotency_returns_same_reservation`、`test_manual_violation_repeat_is_idempotent`、`test_auto_violation_is_idempotent`
- **VS-03 相邻与已取消时段** → `test_adjacent_slots_are_allowed`、`test_replay_after_cancel_returns_cancelled_reservation`
- **VS-04 定时任务重复执行** → `test_auto_violation_is_idempotent`
- **VS-06 越权** → `test_auth.py`、`test_admin_resources.py` 中的 403 + 审计断言

---

## 8. 目录

```
backend/
├── app/
│   ├── core/          # 配置、数据库、JWT、依赖、异常
│   ├── models/        # SQLAlchemy 模型（含 reservation_slots）
│   ├── schemas/       # Pydantic 请求/响应模型
│   ├── api/v1/        # REST 路由（与前端契约一致）
│   ├── services/      # 预约、违约、黑名单、可用性、审计、通知
│   ├── tasks/         # APScheduler：自动违约 / 自动结束 / 限制期满
│   └── utils/         # 时间区间与分页
├── alembic/versions/  # 初始迁移（全部表）
├── scripts/seed.py    # 演示数据
└── tests/             # 65 项 Pytest
```

## 9. 已知边界

- 投诉、评价、数据看板的服务层仍为骨架（HTTP 501），不在本次「预约与违约」范围内。
- 违约申诉（FR-024）、记录导出（FR-033）按需求 V2.0 裁定排除。
- 通知仅写站内消息，不接短信/邮件/微信（IR-003 本版不实现）。
- 违约类型沿用前端类型 `自动违约` / `手动违约`（需求文档的完整名称为「手动违约登记」）。
- 手动黑名单到期后不会自动解除，必须管理员调用解除接口并填写原因（BR-010 / ST-043）。
- 时间按服务器本地时区（UTC+8）判定，不做客户端时区换算与夏令时处理（TB-12）。
