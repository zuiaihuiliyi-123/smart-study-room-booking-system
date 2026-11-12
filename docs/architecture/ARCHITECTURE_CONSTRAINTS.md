# 智慧自习室预约与管理系统 · 软件架构约束文档

> **文档性质**：本文件是本仓库的架构治理依据，用于约束后续人类开发者与 AI 编程助手的架构行为。
> 它不重新定义业务规则；业务规则以需求规格说明书与 `AGENTS.md` 第 5 节为准。
> 本文只回答一个问题：**在现有系统上继续开发时，哪些架构边界不能破、为什么、怎么检查。**

| 项目 | 内容 |
|---|---|
| 文档编号 | ARC-SSR-001 |
| 文档版本 | V1.0 |
| 文档状态 | 已生效（架构约束基线） |
| 编制日期 | 2026-11-12 |
| 适用仓库 | 智慧自习室预约与管理系统 |
| 适用代码基线 | `main` 分支，提交 `0550401` 及其后工作区 |
| 需求基线 | `docs/智慧自习室预约与管理系统-需求规格说明书（课程结构版）.md` |
| 协作基线 | 仓库根目录 `AGENTS.md` |
| 维护责任 | 项目架构负责人；任何 P0 级变更须经小组复核 |
| 文档位置 | `docs/architecture/ARCHITECTURE_CONSTRAINTS.md` |

---

## 0. 阅读说明

### 0.1 状态标记

本文对每条约束标注“当前实现状态”，严格区分事实与目标：

| 标记 | 含义 |
|---|---|
| ✅ 已实现 | 当前代码已经按该约束实现，并有明确代码位置可核对 |
| ◐ 部分实现 | 主路径已实现，但存在例外、盲区或未覆盖的关联路径 |
| ○ 目标 | 当前代码**尚未实现**，属于后续应逐步建设的要求，不得表述为已完成 |
| ？ 待确认 | 依赖产品、部署或环境决策，当前无法从代码与文档确认 |

### 0.2 约束等级

| 等级 | 含义 | 违反后果 |
|---|---|---|
| **P0** | 强制性约束。涉及业务正确性、数据一致性、安全边界、接口兼容、迁移链稳定 | 必须停止修改，先解决架构冲突；不得以“赶进度”为由绕过 |
| **P1** | 重要架构约束。原则上必须遵守 | 确需突破时，必须在开发报告中说明原因、影响范围、替代方案与验证结果 |
| **P2** | 建议性约束。允许按实际情况调整 | 不得因 P2 建议阻碍合理功能开发；调整无需逐项审批，但应保持整体一致 |

### 0.3 冲突处理优先级

发生冲突时，按以下顺序裁决：

1. 需求规格说明书中的已定稿业务规则；
2. `AGENTS.md` 第 2.1 节 A 级硬约束；
3. 本文 P0 约束；
4. `AGENTS.md` B 级工程约定与本文 P1 约束；
5. 本文 P2 约束与一般代码风格偏好。

若需求与本文冲突，**不得静默按本文执行**，应说明冲突点、影响范围与可选方案，交由用户或架构负责人裁决。

### 0.4 本文不做什么

- 不修改任何业务代码、数据库结构、接口或前端页面。
- 不把“建议的目标架构”写成“已经实现的事实”。
- 不把当前代码中的临时实现、历史包袱或已知缺陷包装成合理约束。
- 不规定每一行代码怎么写；只划定边界与验收方式。

---

## 1. 文档基本信息与适用范围

### 1.1 目的

1. **保持架构一致性**：新增功能、修复缺陷、重构局部代码时，不随意改变已确定的架构边界。
2. **明确模块边界**：规定前后端各模块的职责、数据归属、调用方向与禁止的跨层访问。
3. **保证数据安全与一致性**：固化事务、并发、状态流转、权限校验与异常处理的落点。
4. **控制技术复杂度**：避免重复造轮子、过度设计、无评估地引入新依赖或替换技术栈。
5. **规范 AI 协作**：让后续 AI 能判断“哪些必须遵守、哪些可以自主决定、哪些必须先问”。
6. **支持合理演进**：允许在影响分析、兼容性验证与决策记录之后调整架构。

### 1.2 适用范围

**纳入范围：**

- `backend/`：FastAPI 应用、SQLAlchemy 模型、Pydantic Schema、业务 Service、定时任务、Alembic 迁移、Pytest。
- `frontend/`：Vue 3 SPA、路由、Pinia、API 封装、Composable、页面与组件、MSW Mock。
- 前后端接口契约、数据库结构、权限边界、部署与运行方式。
- 与本系统直接相关的开发文档、测试与构建脚本。

**不纳入范围：**

- 课程作业的文档排版、答辩材料、成员分工。
- 已明确排除的功能（违约申诉、记录导出、门禁、支付、候补、代预约等）。
- 第三方软件（MySQL、Node.js、Windows 服务）自身的安装与运维细节。

### 1.3 依据文件

| 文件 | 用途 |
|---|---|
| `docs/智慧自习室预约与管理系统-需求规格说明书（课程结构版）.md` | 业务规则、状态机、权限矩阵、统计口径的最终依据 |
| `AGENTS.md` | AI 协作规范、A 级硬约束、开发流程与交付要求 |
| `backend/README.md` | 后端启动、目录结构、分层约定（部分内容已过时，见 §18） |
| `frontend/docs/前端实现说明.md` | 前端路由、接口、状态字典与 Mock 差异（部分内容已过时，见 §18） |
| `docs/数据库表结构说明.md` | 数据库表、字段、索引与约束（快照版本，见 §18） |
| `docs/系统使用说明.md` | 本地启动、演示账号、运行方式 |
| `frontend/src/types/index.ts` | 前端接口与实体的 TypeScript 契约 |
| `backend/app/models/enums.py` | 后端角色、状态、类型的枚举真值 |

### 1.4 与 `AGENTS.md` 的关系

`AGENTS.md` 是**协作规范**，规定“AI 应该怎样工作、哪些业务约束不能破”；本文是**架构治理细则**，规定“代码结构、依赖方向、数据与接口边界应该怎样落地”。

- 两者不重复：本文不复制 `AGENTS.md` 的业务参数表，只引用其数值来源与代码落点。
- 两者不替代：违反 `AGENTS.md` A 级约束的改动，即使符合本文，也不允许。
- 两者需同步：若架构调整导致 `AGENTS.md` 中的目录、启动方式、已知状态失效，必须同步更新 `AGENTS.md` 与相关文档。

### 1.5 生效与维护

- 本文自 2026-11-12 起生效。
- 任何 P0 约束的新增、删除或降级，须通过 §17 的架构变更流程，并留下 ADR。
- 每轮涉及架构的改动完成后，开发者应检查 §14 的约束索引是否仍与代码一致。
- 本文不追求一次性完美；发现“文档与代码不符”时，应记录在 §18，而不是悄悄改文档迁就代码。

---

## 2. 项目架构现状概述

### 2.1 系统形态（已核对代码）

本系统是**前后端分离的 Web 单体应用**：

- 前端：Vue 3 单页应用（SPA），由 Vite 构建，浏览器内运行；开发期可将 `/api` 代理到后端，也可用 MSW 在浏览器内拦截请求做独立演示。
- 后端：FastAPI 单体服务，同步 SQLAlchemy Session 访问 MySQL；所有业务模块在同一进程内。
- 数据库：MySQL 8.4 LTS 为目标版本（本地实际版本以环境为准），InnoDB、`utf8mb4`。
- 定时任务：APScheduler `BackgroundScheduler` 与 API 同进程运行。
- 通信：浏览器与后端之间仅通过 HTTP/JSON，前缀 `/api/v1`；前后端不共享数据库，不共享进程内对象。
- 缓存、消息队列、对象存储、短信/邮件/微信、支付、门禁：**当前均未使用**。

### 2.2 技术栈事实

| 层 | 技术 | 代码位置 | 说明 |
|---|---|---|---|
| 前端框架 | Vue 3 `<script setup>` + TypeScript | `frontend/src/` | 不使用 Vuex、不引入其他 UI 框架 |
| 构建 | Vite 6 | `frontend/vite.config.ts` | 开发代理 `/api` → `127.0.0.1:8000` |
| UI | Element Plus 2 | `frontend/src/main.ts` | 中文 locale；主题变量在 `assets/styles/index.scss` |
| 状态 | Pinia 2 | `frontend/src/stores/` | 仅 `auth`、`message` 两个全局 store |
| 路由 | Vue Router 4 | `frontend/src/router/index.ts` | `meta.roles` + 全局前置守卫 |
| 图表 | ECharts 5 | `frontend/src/components/BaseChart.vue`、`utils/chartTheme.ts` | 看板三张图 |
| HTTP | Axios | `frontend/src/api/request.ts` | 统一注入 Bearer、统一错误提示、401 跳登录 |
| Mock | MSW 2 | `frontend/src/mocks/`、`src/main.ts` | 仅 `DEV && VITE_USE_MOCK=true` 时加载 |
| 后端框架 | FastAPI | `backend/app/main.py` | lifespan 内做安全校验与调度器启停 |
| 数据校验 | Pydantic 2 | `backend/app/schemas/` | 请求/响应模型 |
| ORM | SQLAlchemy 2（同步） | `backend/app/models/`、`core/database.py` | `SessionLocal`，每请求一个 Session |
| 迁移 | Alembic | `backend/alembic/versions/` | 单 head 迁移链（历史含一次合并） |
| 数据库 | MySQL + PyMySQL | `backend/app/core/config.py` | `DATABASE_URL` 可由 `.env` 覆盖 |
| 认证 | JWT（HS256）+ pwdlib/Argon2 | `backend/app/core/security.py` | Bearer Token；`token_version` 使旧令牌失效 |
| 调度 | APScheduler 3 | `backend/app/tasks/scheduler.py` | 时区 `Asia/Shanghai` |
| 测试 | Pytest + FastAPI TestClient + SQLite 内存库 | `backend/tests/` | `conftest.py` 覆盖 `get_db`，不依赖本机 MySQL |

### 2.3 代码组织与规模（静态统计）

**后端：**

- 入口：`backend/app/main.py`。
- 路由：`backend/app/api/v1/`，13 个模块，统一挂到 `app/api/router.py`，前缀 `/api/v1`。
- 业务：`backend/app/services/`，15 个 Service 文件；没有 Repository 层。
- 模型：14 张业务表（`users`、`rooms`、`areas`、`seats`、`reservations`、`reservation_slots`、`violation_records`、`reviews`、`complaints`、`blacklist_entries`、`audit_logs`、`station_messages`、`login_attempts`、`room_closures`）。
- 任务：`backend/app/tasks/`，4 个后台任务 + 1 个调度器。
- 工具：`backend/app/utils/`，时间、脱敏、分页。
- 测试：17 个测试文件，静态统计 119 个 `test_` 函数。

**前端：**

- 页面：学生端 7 个、管理端 11 个，另有登录、注册、404。路由定义见 `frontend/src/router/index.ts`。
- API 模块：12 个（`src/api/*.ts`），统一经 `request.ts` 的 `http` 对象。
- 全局 store：2 个（`auth.ts`、`message.ts`）。
- 页面编排 Composable：19 个（`src/utils/use*.ts`）。
- 组件：约 45 个（`src/components/`），含通用组件与业务组件。
- Mock：13 个 handler 模块，路径与 `src/api/*.ts` 对应。

### 2.4 质量基线（本轮实际执行情况）

| 检查项 | 结果 | 说明 |
|---|---|---|
| `cd frontend && npm run type-check` | **通过**（无 error） | 2026-11-12 实际执行，`vue-tsc --noEmit` |
| `cd frontend && npm run build` | **未执行** | 本轮以架构调研与文档为主；`frontend/dist` 当前被 Git 跟踪，构建会写入工作区，故不在本轮制造额外变更 |
| `pytest backend/tests/` | **未执行** | 当前执行环境无法运行 Python；仅做静态统计，不代表测试通过 |
| `alembic heads` | **未执行** | 按迁移文件 `down_revision` 静态核对：当前唯一 head 为 `f4b2d8c6a1e0`；历史中存在一次合并迁移 `b860458bfa51`（合并 `a7d3e5f8b1c2` 与 `d4e7b1c9f2a3`），合并后为单 head 链 |
| `git status` | **存在未提交变更** | 工作区有大量 `frontend/dist/` 的修改与删除，本轮未处理 |

> **真实性声明**：上表中“通过”仅指类型检查；测试、构建、迁移均未在本轮执行。不得把本文的静态核对表述为运行验证。

### 2.5 已确认的架构事实（Facts）

以下事实均从代码核对得出，后续改动若不成立，必须走架构变更流程：

| 编号 | 事实 | 代码依据 |
|---|---|---|
| F-01 | 后端没有 Repository 层；路由直接调用 Service，Service 直接使用 SQLAlchemy Session | `backend/app/api/v1/*.py`、`backend/app/services/*.py` |
| F-02 | Service 负责业务规则并负责 `db.commit()`；路由不提交事务 | `reservation_service.py`、`room_service.py` 等 |
| F-03 | 每个 HTTP 请求一个 `Session`，由 `get_db()` 关闭 | `backend/app/core/database.py` |
| F-04 | 后台任务使用独立 `SessionLocal()`，不共享请求 Session | `backend/app/tasks/auto_violation.py`、`auto_end_reservation.py` |
| F-05 | 预约占用以 `reservation_slots` 的 `(seat_id, slot_start)` 与 `(user_id, slot_start)` 唯一约束做持久层兜底 | `backend/app/models/reservation_slot.py`、`reservation_service.py` |
| F-06 | 座位表只保存“可用 / 维修中 / 停用”，不保存“已预约 / 使用中” | `backend/app/models/seat.py`、`enums.py` |
| F-07 | 有效预约固定为“待使用 / 使用中”；取消、完成、违约不占用时段 | `availability_service.py`、`reservation_service.py` |
| F-08 | 幂等键唯一约束为 `(user_id, idempotency_key)` | `backend/app/models/reservation.py` |
| F-09 | JWT 角色校验在 `core/dependencies.py` 中统一实现；R-04 系统管理员无业务管理权限 | `dependencies.py`、`frontend/src/router/index.ts` |
| F-10 | 管理端联系方式由后端脱敏；本人资料不脱敏 | `backend/app/utils/masking.py`、`api/v1/users.py` |
| F-11 | 场地关闭先调用只读 `close-preview`，再以 `expected_reservation_ids` 指纹确认执行 | `room_service.py`、`schemas/room.py`、`frontend/src/utils/useRoomClose.ts` |
| F-12 | 自动违约、自动结束、黑名单到期、投诉超时关闭由 APScheduler 周期执行 | `backend/app/tasks/scheduler.py` |
| F-13 | 站内通知在业务提交后以独立 Session 写入，失败只记日志 | `notification_service.notify_safe` |
| F-14 | 前端只有开发期 Mock；生产构建会移除 MSW 与 `mockServiceWorker.js` | `frontend/src/main.ts`、`vite.config.ts` |
| F-15 | 看板前端每 10 秒刷新；时间口径以服务端为准 | `frontend/src/utils/useDashboard.ts`、`backend/app/utils/time_utils.py` |

### 2.6 明确没有采用的技术（不要凭想象补全）

- 没有 Redis / Memcached 等缓存。
- 没有 RabbitMQ / Kafka / Celery 等消息队列或异步任务框架。
- 没有 WebSocket / SSE；消息未读数由轮询获取。
- 没有对象存储与文件上传接口。
- 没有微服务、服务注册、API 网关、容器编排。
- 没有多租户；`room_id` 是业务范围，不是租户隔离。
- 没有前端单元测试框架（Vitest/Jest）与 E2E 框架（Playwright/Cypress）接入。

> 后续若需要上述能力，属于架构演进，必须走 §17 的 ADR 流程；不得在普通功能任务中顺手引入。

---

## 3. 总体架构设计与架构视图

### 3.1 架构模式

**前后端分离 + 模块化单体后端 + 同步 REST + 进程内定时任务 + 单一关系型数据库。**

选择该模式的现实原因：

- 课程项目规模有限，单体后端在开发、调试、演示和部署上成本最低。
- 预约冲突、签到、违约等业务需要强事务一致性，单库单进程最容易保证。
- 当前没有高并发、异步解耦、跨团队独立部署的硬需求，引入分布式组件会显著增加复杂度而无实际收益。

### 3.2 逻辑架构图

```text
┌──────────────────────────────────────────────────────────────────┐
│ Browser                                                          │
│  Vue 3 SPA                                                       │
│  views/*.vue                                                     │
│    → utils/use*.ts（页面状态与流程编排）                          │
│    → api/*.ts（接口声明）                                        │
│    → api/request.ts（Axios 实例、Bearer、错误提示、401 跳转）      │
│  Pinia: stores/auth.ts, stores/message.ts                        │
│  Router: meta.roles + beforeEach（仅 UX 守卫）                    │
│  MSW: src/mocks/**（仅 DEV + VITE_USE_MOCK=true）                 │
└───────────────────────────┬──────────────────────────────────────┘
                            │ HTTP/JSON  /api/v1
                            │ dev: Vite proxy 5173 → 8000
┌───────────────────────────▼──────────────────────────────────────┐
│ FastAPI 单进程                                                    │
│  main.py                                                         │
│    → CORS 中间件                                                 │
│    → 统一异常处理器（BusinessError / HTTPException / 422）         │
│    → api/v1/*.py（参数绑定、鉴权依赖、response_model）             │
│         → core/dependencies.py（JWT 解析、角色校验）               │
│         → services/*.py（业务规则、事务、commit）                  │
│              → models/*.py（SQLAlchemy ORM）                      │
│              → schemas/*.py（Pydantic I/O）                       │
│              → utils/*（时间、脱敏、分页）                         │
│    → SQLAlchemy Session（同步）                                   │
│                                                                  │
│  APScheduler BackgroundScheduler（同进程，Asia/Shanghai）          │
│    → tasks/*.py → services/*.py → 独立 SessionLocal()             │
└───────────────────────────┬──────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│ MySQL 8.4（InnoDB, utf8mb4）                                      │
│  users / rooms / areas / seats / reservations / reservation_slots  │
│  violation_records / reviews / complaints / blacklist_entries      │
│  audit_logs / station_messages / login_attempts / room_closures    │
└──────────────────────────────────────────────────────────────────┘

无 Redis / MQ / 对象存储 / 外部短信邮件服务 / WebSocket
```

### 3.3 三条关键链路

#### 链路 A：学生创建预约

```text
SeatBookingView.vue
 → useSeatBooking.ts（本地预判、幂等键生成、提交状态）
 → api/reservation.ts: createReservation
 → api/request.ts（注入 Bearer）
 → POST /api/v1/reservations
 → require_booking_user（仅学生 R-01）
 → reservation_service.create_reservation
     → 幂等键查询
     → SELECT ... FOR UPDATE 锁定 seat / user
     → availability_service.check_reservation_rules（C1～C6）
     → INSERT reservations
     → INSERT reservation_slots（每 5 分钟一行）
     → COMMIT
 → notification_service.notify_safe（独立 Session，提交后写入）
 → 返回 ReservationRead
```

关键点：**座位资源状态全程不变**；占用由预约单与槽位表达；并发最终由槽位唯一约束兜底。

#### 链路 B：管理员临时关闭场地

```text
RoomManageView.vue
 → useRoomClose.ts
 → GET /rooms/{id}/close-preview（只读，展示受影响座位与预约）
 → 管理员二次确认
 → POST /rooms/{id}/close
     body: 时间窗、area_id、reason、cancel_affected、expected_reservation_ids
 → require_admin
 → room_service.close_room
     → 重新计算受影响清单
     → 比对 expected_reservation_ids（不一致返回 409，要求重新预览）
     → INSERT room_closures
     → 可选：批量取消受影响预约并释放槽位
     → 写审计日志
     → COMMIT
 → 逐条 notify_safe
```

关键点：**确认前不得自动取消**；关闭用时间窗表达，不改写座位资源状态。

#### 链路 C：自动违约扫描

```text
APScheduler 每 1 分钟
 → tasks/auto_violation.scan_auto_violations
     → 查询“待使用且日期 <= 今天”的预约 id
     → 每条预约独立 SessionLocal()
     → violation_service.apply_auto_violation
         → 校验 now >= 开始时间 + 15 分钟
         → 校验状态仍为“待使用”
         → 查询/写入 ViolationRecord（唯一约束 reservation_id + type）
         → 预约状态 → 已违约
         → 释放 reservation_slots
         → blacklist_service.restrict_if_threshold（同一事务）
         → 写审计
         → COMMIT
     → notify_safe
     → 单条失败 rollback + logger.exception，不影响其他预约
```

关键点：**幂等**（同一预约同一类型只产生一条记录）、**逐条事务**、**失败隔离**。

### 3.4 依赖方向

**后端允许的依赖方向：**

```text
api/v1  →  core/dependencies, schemas, services, models（仅类型标注）
services →  core, models, schemas, utils, 其他 services
tasks    →  services, core.database, models（只读查询）
core     →  config / database / security / exceptions
models   →  core.database
schemas  →  pydantic
utils    →  标准库或纯工具依赖
```

**禁止的依赖方向：**

- `models` 导入 `services`、`api`、`schemas`。
- `schemas` 导入 `services`、`api`、`models` 的 ORM 查询逻辑。
- `utils` 导入 `services`、`api`。
- `api/v1` 直接执行 SQLAlchemy 查询/写入并承载业务规则（路由应薄）。
- `tasks` 复制业务规则，而不是调用 `services`。

**前端允许的依赖方向：**

```text
views        → composables, components, stores, types, utils
composables  → api, stores, types, utils
components   → types, utils, 必要的展示型 composable
api          → request, types
request      → axios, element-plus（仅 ElMessage）
stores       → api, types
```

**当前存在的例外（已知，不扩大）：**

- `components/admin/AreaManageDrawer.vue`、`components/admin/BlacklistAddDialog.vue` 直接调用 `@/api/*`；`components/account/PasswordChangeDialog.vue` 直接使用 `@/stores/auth`。这些是“自包含对话框”的局部实现，不属于禁止项，但**不得扩散为组件层普遍直接取数**。

### 3.5 运行与部署形态

- 开发：`start.bat` 启动 MySQL、后端 `uvicorn app.main:app --reload`、前端 `vite`；前端 `/api` 代理到 `127.0.0.1:8000`。
- 测试：Pytest 使用 SQLite 内存库，覆盖 `get_db`；`settings.scheduler_enabled = False`，不启动调度器。
- 生产：当前没有容器、CI/CD、反向代理与 HTTPS 配置；属于**待建设**，见 §18。
- 调度器与 API 同进程：**只能以单 worker 运行**；多 worker 会启动多个调度器实例，导致重复任务。若未来需要多 worker，必须把调度器拆为独立进程或加分布式锁。

### 3.6 关键架构决策摘要

| 决策 | 选择 | 理由 | 影响 |
|---|---|---|---|
| ADR-S-001 | 单体后端，不拆微服务 | 课程规模、强事务、低运维成本 | 模块边界靠代码纪律而非网络边界 |
| ADR-S-002 | 同步 SQLAlchemy，不引入 async ORM | 现有代码、测试与调度器均同步；避免混用 | 请求内不得执行长时间阻塞外部调用 |
| ADR-S-003 | 用 `reservation_slots` 物化时段占用 | 数据库唯一约束比“先查后写”可靠 | 预约创建/终止必须同步维护槽位 |
| ADR-S-004 | JWT Bearer + 角色依赖，不用 Session/Cookie | 前后端分离、演示简单 | 前端负责携带令牌；服务端每次校验 |
| ADR-S-005 | 场地关闭用时间窗 `room_closures`，不改座位状态 | 窗口结束自动恢复，避免座位状态被污染 | 可预约性需同时查预约与关闭记录 |
| ADR-S-006 | 进程内 APScheduler，不引入 Celery | 无 MQ，任务简单、频率低 | 必须单实例运行；任务必须幂等 |
| ADR-S-007 | MSW 仅开发期，生产不打包 | 避免 Mock 污染真实环境 | Mock 不能作为业务验收依据 |

---

## 4. 模块职责与依赖边界

### 4.1 后端模块职责

| 模块 | 职责 | 不应承担 |
|---|---|---|
| `app/main.py` | 应用装配、CORS、异常处理注册、路由挂载、启动期安全校验、调度器启停 | 业务规则、数据库查询 |
| `app/core/config.py` | 环境配置、业务参数、启动期安全校验 | 业务状态判断 |
| `app/core/database.py` | Engine、Session 工厂、`get_db` | 业务查询 |
| `app/core/security.py` | 密码哈希、JWT 签发/解析 | 角色授权、用户查询 |
| `app/core/dependencies.py` | 当前用户解析、角色校验、越权审计 | 具体业务规则 |
| `app/core/exceptions.py` | `BusinessError` 与统一异常响应 | 业务流程控制 |
| `app/models/` | 表结构、约束、索引、枚举落库 | 业务查询、事务提交 |
| `app/schemas/` | 请求/响应结构与字段校验 | 数据库访问 |
| `app/api/v1/` | 路由、参数绑定、鉴权依赖、`response_model` | 业务规则、事务提交、复杂查询 |
| `app/services/` | 业务规则、状态流转、事务边界、跨服务协作 | HTTP 细节、直接构造响应 |
| `app/tasks/` | 周期扫描、逐条调用 Service、失败隔离 | 复制业务规则、长事务 |
| `app/utils/` | 纯函数工具（时间、脱敏、分页） | 依赖数据库/业务状态 |

### 4.2 前端模块职责

| 模块 | 职责 | 不应承担 |
|---|---|---|
| `src/views/` | 页面结构、布局、组合子组件、调用 Composable | 直接拼 URL、直接处理 Axios 错误细节 |
| `src/utils/use*.ts` | 页面状态机、取数、筛选、提交、错误映射 | 全局认证状态、跨页面共享缓存 |
| `src/api/*.ts` | 每个业务模块的接口声明与参数类型 | 业务规则、UI 提示、状态管理 |
| `src/api/request.ts` | Axios 实例、baseURL、Bearer、401 处理、统一错误提示 | 具体业务判断 |
| `src/stores/` | 跨页面全局状态（认证、消息未读） | 单页面临时状态、组件局部状态 |
| `src/router/` | 路由表、懒加载、角色 meta、登录守卫 | 真正的授权（授权在服务端） |
| `src/components/` | 可复用展示与交互组件 | 全局数据编排（自包含对话框例外） |
| `src/types/` | 前后端契约的 TS 类型 | 运行时逻辑 |
| `src/mocks/` | 开发期接口模拟、与真实契约对齐 | 生产运行、业务验收依据 |
| `src/assets/styles/` | 设计 token、Element Plus 覆盖、全局样式 | 页面私有布局逻辑 |

### 4.3 业务规则归属（唯一责任模块）

| 业务规则 | 后端唯一归属 | 前端镜像（仅 UX） | 不得出现的位置 |
|---|---|---|---|
| 预约粒度、提前天数、最长时长、每日次数 | `core/config.py` + `availability_service.py` | `utils/bookingRules.ts` | 路由、组件、数据库 CHECK 之外的第二套参数 |
| 座位/自习室可预约性（C1/C2/C2b） | `availability_service.py` | `useSeatBooking.ts` | 前端独立裁定“可约”并直接提交 |
| 座位/用户时段冲突（C3/C4） | `availability_service.py` + `reservation_slots` 唯一约束 | 座位图状态 | 仅靠前端过滤 |
| 幂等（BR-021） | `reservation_service.py` + `uq_reservation_idempotency` | `useSeatBooking.createIdempotencyKey` | 前端按钮禁用作为唯一防重 |
| 取消时限、签到窗口 | `attendance_service.py` + `time_utils.py` | `bookingRules.ts` | 客户端时间判定后直接放行 |
| 自动违约、状态互斥 | `violation_service.py` + `tasks/auto_violation.py` | 无 | 前端定时器、消息内容推断 |
| 黑名单阈值、到期解除 | `blacklist_service.py` + `tasks/blacklist_expiry.py` | 仅展示 | 前端自行计算“应解除”并改状态 |
| 投诉状态机、SLA | `complaint_service.py` + `utils/workday.ts`（展示） | `workday.ts`（仅展示超时） | 管理端直接改 `status` 字符串 |
| 场地关闭影响清单与批量处理 | `room_service.py` | `useRoomClose.ts` | 前端自行取消预约 |
| 看板统计口径 | `dashboard_service.py` | `dashboardCharts.ts`（仅展示） | 前端二次聚合改变口径 |
| 权限与数据范围 | `core/dependencies.py` + 各 Service 的 `user_id` 过滤 | 路由守卫、按钮显隐 | 仅靠前端隐藏 |
| 审计 | `audit_service.py` + 各管理 Service | 无 | 前端伪造“已审计”提示 |

### 4.4 跨模块调用规则

- 允许 Service 调用其他 Service 的**公开函数**；不得导入其他 Service 的私有函数（`_` 前缀）作为稳定契约。
- 当前存在的跨 Service 调用：
  - `attendance_service` → `reservation_service.release_slots`
  - `violation_service` → `blacklist_service.restrict_if_threshold`、`reservation_service.release_slots`、`audit_service`、`notification_service`
  - `room_service` → `reservation_service.release_slots`
  - `reservation_service` → `availability_service`、`audit_service`、`notification_service`
- 新增跨模块调用时，必须确认：调用方向是否形成环、是否会把事务边界拉长、是否会造成重复提交。
- **不得**为了“复用”让 `models` 或 `schemas` 反向依赖 Service。

### 4.5 不得跨越的边界

1. 前端不得直接连接 MySQL，也不得假设数据库结构。
2. 后端不得依赖前端计算出的业务结论（如“前端已判断可约”“前端已过滤冲突”）。
3. 路由不得绕过 Service 直接写 `reservations`、`reservation_slots`、`violation_records`、`blacklist_entries`、`audit_logs`、`station_messages`。
4. 定时任务不得绕过 Service 直接改预约状态或写违约记录。
5. 任何模块不得直接改 `users.violation_count` 或 `users.account_status` 来“顺带修正”状态；必须经 `blacklist_service` / `user_service` 的规则路径。
6. Mock 不得成为真实后端的替代实现；真实接口存在时，Mock 只模拟其契约。

---

## 5. 总体架构约束

### ARC-001 · 服务端是业务裁决的唯一权威 · P0 · ✅ 已实现

- **约束**：任何影响业务结果的判断（能否预约、能否取消、能否签到、是否违约、是否有权限、统计口径）必须由后端 Service 重新计算并裁决；前端与 Mock 的判断只能用于交互提示，不能作为放行依据。
- **原因**：前端代码、浏览器时间、请求参数都可被篡改；只靠前端校验无法保证业务正确性与安全性。
- **适用范围**：`backend/app/services/` 全部模块；`frontend/src/utils/bookingRules.ts`、`frontend/src/mocks/rules.ts`。
- **典型违反**：前端判断“时段可约”后直接调用创建接口并假定成功；后端信任 `payload.user_id`；Mock 通过后宣称业务通过。
- **检查方式**：审查每个写接口是否在 Service 内重新校验；搜索前端是否存在“校验通过即跳过服务端错误处理”的分支；用错误参数直接调用接口验证仍被拒绝。

### ARC-002 · 核心业务规则单一归属，禁止复制 · P0 · ◐ 部分实现

- **约束**：同一条核心业务规则只能有一个“权威实现”。前端镜像、Mock 规则、文档表格可以存在，但必须明确标注“非权威”，并与权威实现保持同步。
- **原因**：规则多处复制会在参数调整时产生漂移。当前 5 分钟粒度调整后，`frontend/docs/前端实现说明.md` 仍有 30 分钟表述，就是漂移的实例。
- **适用范围**：预约参数、状态流转、权限矩阵、统计口径、脱敏口径。
- **典型违反**：在页面组件里再写一套“每日最多 2 条”；在 Mock 里使用与后端不同的违约阈值；在两个 Service 中各写一份状态转换表。
- **检查方式**：对照 §4.3 的归属表；搜索 `settings.`、`BOOKING_RULES`、`RULES` 的重复定义；参数变更时用全局搜索确认所有镜像已更新。

### ARC-003 · 前后端分层与依赖方向 · P1 · ◐ 部分实现

- **约束**：遵守 §3.4 的允许方向；路由薄、Service 厚、组件展示化、Composable 编排页面。
- **原因**：依赖方向一旦反转，测试、复用与替换都会变难；当前少量组件直接取数是可接受的局部例外，但不能扩散。
- **适用范围**：新增或修改的前后端模块。
- **典型违反**：`api/v1` 里写复杂 SQL；`models` 导入 Service；页面直接 `axios.get`；组件层普遍直接调 API。
- **检查方式**：检查 import 关系；新增文件时对照 §3.4；代码评审关注“这段逻辑为什么不在 Service/Composable”。

### ARC-004 · 技术栈锁定，不引入平行体系 · P1 · ✅ 已实现

- **约束**：前端继续使用 Vue 3 + TypeScript + Vite + Element Plus + Pinia + Vue Router + ECharts + Axios + SCSS + MSW；后端继续使用 FastAPI + Pydantic 2 + SQLAlchemy 2 + Alembic + MySQL + JWT + APScheduler + Pytest。不得引入 Tailwind、Ant Design Vue、Vuex、Naive UI、React、Next.js 等替代体系。
- **原因**：双技术体系会造成构建、主题、状态与团队认知分裂；课程项目没有迁移收益。
- **适用范围**：所有新功能与重构。
- **典型违反**：为了一个页面引入 Tailwind；为了一个图表引入新的图表库；为了表单引入新的表单框架。
- **检查方式**：审查 `frontend/package.json`、`backend/requirements.txt` 的变更；新增依赖必须说明现有工具为何不够。

### ARC-005 · 新模块必须落位现有目录与分层 · P1 · ✅ 已实现

- **约束**：新增后端业务模块按 `api/v1/<module>.py` + `services/<module>_service.py` + `schemas/<module>.py` + `models/<entity>.py` 组织；新增前端页面按 `views/<role>/` + `utils/use<Module>.ts` + `api/<module>.ts` + `components/<domain>/` 组织。
- **原因**：保持可预测性，降低 AI 与人类开发者寻找代码的成本。
- **适用范围**：新增功能、拆分模块。
- **典型违反**：把业务逻辑塞进 `main.py`；在 `views/` 下新建 `services/`；把多个领域塞进一个巨型 `utils.ts`。
- **检查方式**：对照现有目录；新增文件必须能用一句话说明为什么放在该位置。

### ARC-006 · 不引入无必要的架构层 · P2 · ✅ 已实现

- **约束**：当前不引入 Repository、Unit of Work、DDD 聚合、CQRS、事件总线等额外抽象；只有在出现明确的复用/测试/替换需求时才评估。
- **原因**：现有 Service 已能清晰承载业务；为架构风格而架构会增加无意义层级。
- **适用范围**：后端。
- **典型违反**：为一个简单查询新增 Repository 接口与实现；为状态流转引入事件总线但没有第二个消费者。
- **检查方式**：新增抽象时回答“它解决了当前哪个具体问题”；无法回答则不引入。

### ARC-007 · HTTP/JSON 是前后端唯一跨端边界 · P0 · ✅ 已实现

- **约束**：前后端只通过 `/api/v1` 的 HTTP/JSON 交互；前端不读取后端数据库，后端不依赖前端本地存储；跨端字段以 `frontend/src/types/index.ts` 与 `backend/app/schemas/` 的双向对照为准。
- **原因**：共享数据库或共享进程内对象会破坏前后端分离，导致部署与权限边界失效。
- **适用范围**：所有跨端功能。
- **典型违反**：前端直连 MySQL；后端返回 ORM 对象内部字段并让前端依赖；用文件系统在前后端之间传数据。
- **检查方式**：检查 `frontend/src/api/` 是否存在非 HTTP 数据源；检查后端响应是否只包含 Schema 声明字段。

### ARC-008 · 单体单进程 + 进程内调度 · P1 · ✅ 已实现

- **约束**：当前部署形态是一个 FastAPI 进程 + 一个 APScheduler 实例。生产环境不得在未拆分调度器的情况下使用多 worker（如 `uvicorn --workers N`、Gunicorn 多 worker），否则每个进程都会启动一套定时任务。
- **原因**：APScheduler 的 `max_instances=1` 只在单进程内生效；多进程会重复扫描、重复写违约记录、重复发通知。
- **适用范围**：`backend/app/tasks/scheduler.py`、启动脚本、部署配置。
- **典型违反**：为了“提高并发”直接加 `--workers 4`；在容器里水平扩容 API 副本而不剥离调度器。
- **检查方式**：审查启动命令与部署配置；确认调度器只在唯一进程启动；若必须多 worker，先引入独立调度进程或分布式锁（走 ADR）。

### ARC-009 · 架构演进必须留下决策记录 · P2 · ○ 目标

- **约束**：涉及分层、技术栈、数据库结构、接口兼容、部署形态的变更，必须写 ADR（模板见 §17.3），并在本文 §14 更新约束状态。
- **原因**：避免“为什么改成这样”只存在于个人记忆或聊天记录中，防止后续 AI 反向重构。
- **适用范围**：所有架构级变更。
- **典型违反**：直接引入缓存但不记录一致性策略；直接改接口字段但不记录兼容方案。
- **检查方式**：查看 `docs/architecture/adr/`（当前尚未建立）；重大变更的提交说明中是否引用 ADR。

---

## 6. 前端架构约束

### ARC-010 · 所有 HTTP 请求经统一入口 · P0 · ✅ 已实现

- **约束**：页面的所有后端请求必须经 `src/api/*.ts`，最终使用 `src/api/request.ts` 导出的 `http` 对象。禁止在 `views/`、`components/` 中直接 `import axios`、直接 `fetch`、手写完整 URL 或自行拼接 baseURL。
- **原因**：统一入口集中处理 baseURL、Bearer 注入、超时、401 清理与跳转、统一错误提示；绕过它会漏掉认证或产生不一致的提示。
- **适用范围**：`frontend/src/` 全部前端代码。
- **典型违反**：页面里 `fetch('/api/v1/reservations')`；组件里 `axios.post`；手动从 localStorage 取 token 拼 header。
- **检查方式**：`grep -rn "from 'axios'\\|fetch(" frontend/src/views frontend/src/components` 应为空；新增接口必须同时新增 `api/*.ts` 函数。

### ARC-011 · 前端权限控制只是体验，不是授权 · P0 · ✅ 已实现

- **约束**：路由 `meta.roles`、菜单隐藏、按钮禁用只用于避免用户进入无权页面；真正的授权必须在后端 `core/dependencies.py` 的依赖中完成。前端不得把“守卫通过”当作“接口一定安全”。
- **原因**：用户可以手工输入 URL、修改 localStorage、直接调用接口；前端守卫无法阻止越权。
- **适用范围**：`frontend/src/router/index.ts`、`src/layouts/menu.ts`、各页面按钮显隐；`backend/app/core/dependencies.py`。
- **典型违反**：只在前端隐藏“强制取消”按钮，后端接口不校验 `require_admin`；系统管理员在 Mock 中被允许调用业务接口，而真实后端拒绝。
- **检查方式**：逐个管理端接口确认后端依赖；用学生令牌直接调用管理接口应返回 403；用系统管理员令牌调用业务接口应返回 403。

### ARC-012 · 页面编排在 Composable，全局状态在 Pinia · P1 · ◐ 部分实现

- **约束**：单页面的取数、筛选、分页、提交、错误状态放在 `src/utils/use*.ts`；Pinia 只保存跨页面共享的全局状态（当前为认证与消息未读）。不得把页面临时状态塞进全局 store，也不得让多个页面各自维护同一份全局状态。
- **原因**：页面状态与全局状态混在一起会导致切换页面后残留、账号切换后串数据。
- **适用范围**：`src/utils/use*.ts`、`src/stores/`、`src/views/`。
- **典型违反**：在 `auth` store 里放某个页面的筛选条件；每个页面各自轮询未读数并各自维护角标。
- **检查方式**：store 数量与职责是否仍然只有 `auth`、`message`；新增 store 必须说明跨页面共享的必要性；账号切换时全局状态是否清空（参考 `message.ts` 的 `ensureOwner`）。

### ARC-013 · 类型单一来源，API 模块只做传输 · P1 · ✅ 已实现

- **约束**：接口请求/响应类型集中在 `src/types/index.ts`；`src/api/*.ts` 只声明函数、参数与返回类型，不写业务规则、不弹提示、不做数据加工（必要的参数映射除外）。
- **原因**：类型分散会导致同一实体在不同页面有不同形状；API 模块混入业务会让测试与替换变难。
- **适用范围**：`src/types/`、`src/api/`。
- **典型违反**：在 `api/reservation.ts` 里判断“是否超过 30 分钟”；在页面里重新定义 `Reservation` 接口；同一字段在不同页面用不同命名。
- **检查方式**：搜索重复的 `interface Reservation`；新增接口类型必须进 `types/index.ts`；API 模块中不应出现 `ElMessage`。

### ARC-014 · 页面必须具备加载、空数据、失败三态 · P1 · ✅ 已实现

- **约束**：所有列表、详情、看板、选座页面必须具备加载中、空数据、请求失败三种状态；错误提示统一使用 `ElMessage` 或页面内联错误块；禁止使用浏览器原生 `alert` / `confirm`，需要确认时使用 `ElMessageBox`。
- **原因**：只做成功态会在网络失败或空数据时出现空白页、卡死或误导。
- **适用范围**：全部页面与数据型组件。
- **典型违反**：请求失败后 `loading` 仍为 true；空数组直接渲染空白；用 `window.confirm` 做二次确认。
- **检查方式**：逐页断网/改错接口验证三态；`grep -rn "window.alert\\|window.confirm\\|alert(\\|confirm(" frontend/src` 应为空或仅 `ElMessageBox`。

### ARC-015 · 前端规则镜像必须与后端一致 · P1 · ◐ 部分实现

- **约束**：`frontend/src/utils/bookingRules.ts` 的 `BOOKING_RULES` 与 `frontend/src/mocks/rules.ts` 的 `RULES` 是后端 `core/config.py` 的镜像，只能用于界面预判、按钮禁用与提示；其数值、时间窗口、状态集合必须与后端一致。后端参数变更时，必须同步更新这两处与相关文档。
- **原因**：镜像漂移会让用户在界面上看到“可约”但提交被拒，或反之；也会让 Mock 演示与真实行为不一致。
- **适用范围**：`bookingRules.ts`、`mocks/rules.ts`、`frontend/docs/前端实现说明.md`。
- **典型违反**：后端改为 5 分钟，前端仍按 30 分钟取整；Mock 的每日上限与后端不同；前端自行放宽签到窗口。
- **检查方式**：参数变更时全局搜索 `granularity`、`advanceDays`、`maxHours`、`dailyLimit`、`checkin`、`cancelBefore`、`violationThreshold`；对照 `config.py` 与两个 TS 文件。

### ARC-016 · 路由必须登记角色，权限矩阵保持一致 · P1 · ✅ 已实现

- **约束**：每条受保护路由必须声明 `meta.roles`；学生端只允许“学生用户”，业务管理页只允许“自习室管理员”，系统管理员只进入 `notice` 与 `profile`；新增页面必须同时登记路由与菜单，并与后端权限矩阵一致。
- **原因**：路由角色是用户体验边界，也是发现权限配置错误的早期信号。
- **适用范围**：`src/router/index.ts`、`src/layouts/menu.ts`、`src/stores/auth.ts`。
- **典型违反**：新管理页忘记加 `roles`；把系统管理员加入业务页 `roles`；菜单显示但路由未定义。
- **检查方式**：逐条对照需求权限矩阵；用三种角色登录检查可见菜单与可进入页面；后端对应接口的依赖必须匹配。

### ARC-017 · 看板 10 秒轮询规范 · P1 · ✅ 已实现

- **约束**：看板数据每 10 秒读取一次；轮询失败必须保留上一次数据并显示“数据截至时间/更新失败”，不得清空页面或用 toast 刷屏；轮询请求使用 `silent` 选项。10 秒是数据读取周期，不是违约任务执行周期。
- **原因**：频繁失败提示会干扰使用；清空旧数据会让管理员误判系统无数据。
- **适用范围**：`src/utils/useDashboard.ts`、`src/api/dashboard.ts`、`src/api/request.ts` 的 `silent`。
- **典型违反**：失败后把 `overview` 置空；每次轮询失败弹 `ElMessage.error`；把轮询间隔改成 1 秒。
- **检查方式**：断网观察看板是否保留旧值与截至时间；搜索 `silent: true` 是否覆盖看板请求；确认定时器在页面卸载时清理。

### ARC-018 · 设计 token 与视觉一致性 · P2 · ✅ 已实现

- **约束**：颜色、字号、圆角、阴影优先使用 `src/assets/styles/index.scss` 的 `--ssr-*` 变量；组件内禁止散落十六进制色值；ECharts 颜色统一从 `src/utils/chartTheme.ts` 取；状态标签统一使用 `StatusTag.vue`。
- **原因**：视觉 token 分散会导致暗色模式、主题切换与无障碍对比度失效。
- **适用范围**：`src/components/`、`src/views/`、`src/assets/styles/`。
- **典型违反**：组件里写 `#2b5f9e`；图表另用一套颜色；新状态直接 `<el-tag>` 而不走 `StatusTag`。
- **检查方式**：搜索组件中的 `#[0-9a-fA-F]{3,8}`；对照 `chartTheme.ts` 与 SCSS 变量；状态展示走统一组件。

### ARC-019 · 组件规模、可访问性与响应式 · P2 · ✅ 已实现

- **约束**：组件职责清晰优先，建议单文件不超过约 300 行；纯图标按钮必须有 `aria-label`；表格在窄屏可横向滚动；抽屉宽度不超过 92vw；表单控件必须有可关联的 label。
- **原因**：控制复杂度，保证课程演示在投影与窄屏下可用。
- **适用范围**：`src/views/`、`src/components/`。
- **典型违反**：单页面 800 行；图标按钮无名称；窄屏横向溢出。
- **检查方式**：`wc -l` 抽查；键盘 Tab 走查焦点；1440/1024/768 宽度检查。

---

## 7. 后端架构约束

### ARC-020 · 认证与鉴权统一在依赖层实现 · P0 · ✅ 已实现

- **约束**：所有需要登录的接口必须依赖 `get_current_user`；需要角色的接口必须使用 `require_admin`、`require_system_admin`、`require_student` 或 `require_booking_user`。禁止在路由函数内自行解析 `Authorization`、自行解 JWT、自行比较角色字符串。
- **原因**：分散解析会漏掉 `token_version`、停用账户、角色变更等校验；统一依赖才能保证每个接口口径一致。
- **适用范围**：`backend/app/core/dependencies.py`、`backend/app/api/v1/*.py`。
- **典型违反**：新接口直接读 `request.headers['Authorization']`；只检查“已登录”不检查角色；用 `if user.role == '管理员'` 这种硬编码而不是枚举。
- **检查方式**：搜索 `Authorization`、`jwt.decode` 是否只出现在 `dependencies.py`；逐个管理接口检查依赖；用过期令牌、改密后的旧令牌、停用账户令牌验证 401/403。

### ARC-021 · 路由薄，业务在 Service · P1 · ✅ 已实现

- **约束**：`api/v1/*.py` 只做参数绑定、依赖注入、调用 Service、声明 `response_model`；不得在路由中写状态判断、事务提交、复杂查询或多步业务编排。
- **原因**：路由承载业务会导致接口测试、复用与事务边界混乱。
- **适用范围**：`backend/app/api/v1/`。
- **典型违反**：在路由里 `db.query(...)` 后直接改状态并 `db.commit()`；在路由里判断“是否超过 30 分钟”。
- **检查方式**：搜索路由文件中的 `db.`、`commit(`、`select(`；路由函数体超过约 30 行且包含业务分支时需要拆分。

### ARC-022 · Service 拥有事务边界与原子性 · P0 · ✅ 已实现

- **约束**：一次业务操作的多表写入必须在同一个 Service 事务内完成并统一 `commit()`；失败必须 `rollback()`；不得在业务未完成时提前提交，也不得把“失败的一部分”留在库里。站内通知属于非关键路径，必须在业务提交后以独立 Session 写入。
- **原因**：预约、槽位、违约、黑名单、审计之间存在强关联；部分提交会造成数据不一致。
- **适用范围**：`backend/app/services/`、`backend/app/tasks/`。
- **典型违反**：先提交预约单再写槽位；违约记录提交后黑名单另起事务；通知失败导致整个预约回滚。
- **检查方式**：审查每个写 Service 的 `commit` 位置；构造中途异常验证回滚；确认 `notify_safe` 在 `commit` 之后调用。

### ARC-023 · Pydantic Schema 是接口契约 · P1 · ✅ 已实现

- **约束**：请求体必须使用 Pydantic 模型并声明字段约束；响应必须声明 `response_model`；不得把 ORM 对象的密码哈希、`token_version`、内部标记等字段直接暴露给前端。
- **原因**：Schema 是前后端契约的可执行文档，也是输入校验与输出裁剪的边界。
- **适用范围**：`backend/app/schemas/`、`api/v1/*.py`。
- **典型违反**：路由接收 `dict` 后 `payload['x']`；返回 `User` ORM 导致 `password_hash` 泄露；响应字段与前端类型不一致。
- **检查方式**：检查每个路由是否有 `response_model`；搜索裸 `dict` 请求体；对照 `types/index.ts` 与 Schema 字段。

### ARC-024 · 异常分层，禁止吞错 · P1 · ✅ 已实现

- **约束**：业务失败抛 `BusinessError`（带 `code`、`message`、可选 `details`）；协议层失败抛 `HTTPException`；未预期异常由统一处理器返回 500。禁止 `except Exception: pass`，后台任务捕获异常必须 `logger.exception` 并回滚。
- **原因**：吞错会把失败伪装成成功，导致用户以为操作完成而数据未变。
- **适用范围**：全部后端代码。
- **典型违反**：空 `except`；捕获后返回 `{"message": "ok"}`；定时任务单条失败导致整批中断。
- **检查方式**：搜索 `except` 块是否有日志/回滚/重新抛出；确认前端能收到非 2xx；检查任务日志。

### ARC-025 · Session 生命周期清晰，禁止跨线程共享 · P1 · ✅ 已实现

- **约束**：HTTP 请求使用 `get_db()` 注入的 Session；后台任务每条记录使用独立的 `SessionLocal()`；不得把请求 Session 传给线程、调度器或长期缓存；不得在 Session 关闭后继续使用 ORM 对象。
- **原因**：SQLAlchemy Session 非线程安全；跨线程共享会导致连接泄漏、脏读或随机错误。
- **适用范围**：`core/database.py`、`services/`、`tasks/`。
- **典型违反**：在 APScheduler 任务里复用请求 Session；把 ORM 对象存到全局变量；在 `finally` 之外提前关闭 Session。
- **检查方式**：搜索 `SessionLocal()` 的使用位置；确认任务中 `with SessionLocal() as db`；确认 `get_db` 的 `finally: db.close()`。

### ARC-026 · 定时任务必须幂等、单实例、逐条事务 · P1 · ✅ 已实现

- **约束**：每个定时任务必须满足：重复执行不产生重复业务记录；同一任务在同一进程内 `max_instances=1`、`coalesce=True`；逐条记录独立事务，单条失败不影响其他记录；任务只调用 Service，不复制规则。
- **原因**：调度器可能因重启、时钟漂移、重叠触发而重复执行；批量事务会让一条坏数据拖垮整批。
- **适用范围**：`backend/app/tasks/`、`scheduler.py`。
- **典型违反**：自动违约直接插入记录而不查重；整个扫描共用一个事务；任务里手写一套“超过 15 分钟”的判断。
- **检查方式**：检查 `scheduler.add_job` 参数；重复调用任务函数验证记录数不增加；检查 `apply_auto_violation` 的唯一约束与状态判断。

### ARC-027 · 配置集中，环境变量覆盖 · P1 · ✅ 已实现

- **约束**：业务参数、数据库连接、JWT、CORS、调度开关统一放在 `core/config.py` 的 `Settings`；通过 `backend/.env` 或环境变量覆盖；不得在 Service、路由、任务中散落魔法数字或重复读取 `os.environ`。
- **原因**：参数散落会导致改一处漏一处；环境差异应通过配置而不是改代码解决。
- **适用范围**：`core/config.py`、`backend/.env.example`、启动脚本。
- **典型违反**：在 `attendance_service.py` 写 `timedelta(minutes=15)`；在路由里读 `os.getenv`；把数据库密码写进代码。
- **检查方式**：搜索 `timedelta(minutes=`、`os.getenv`、硬编码 URL；新增参数必须进 `Settings` 并更新 `.env.example`。

### ARC-028 · 日志与审计可追踪且不含敏感信息 · P1 · ◐ 部分实现

- **约束**：重要业务操作与越权尝试写入 `audit_logs`（只追加）；运行日志使用 `logging`，包含可定位的实体 id 与操作类型；日志不得记录密码、密码哈希、JWT、完整手机号/邮箱等敏感信息。
- **原因**：审计用于追责与排障；敏感信息进日志会造成二次泄露。
- **适用范围**：`services/`、`tasks/`、`core/dependencies.py`、`audit_service.py`。
- **典型违反**：`logger.info(f"payload={payload}")` 打印密码；管理员操作不写审计；审计日志可被更新/删除。
- **检查方式**：搜索日志中的 `password`、`token`、`contact`；检查管理端写操作是否调用 `audit_service.record`；确认审计接口只读。

---

## 8. 数据架构约束

### ARC-030 · `reservation_slots` 是并发占用的最终保证 · P0 · ✅ 已实现

- **约束**：任何创建预约的路径都必须在同一事务内为区间 `[start, end)` 每 5 分钟写入一行 `reservation_slots`；任何进入终态（取消、完成、违约）的路径都必须删除对应槽位。不得只改预约状态而不释放槽位，也不得只写预约单而不写槽位。
- **原因**：`(seat_id, slot_start)` 与 `(user_id, slot_start)` 唯一约束是数据库层对 BR-005/BR-006 的最终保证；“先查后写”在并发下必然有窗口。
- **适用范围**：`reservation_service.py`、`attendance_service.py`、`violation_service.py`、`room_service.py`、`tasks/auto_end_reservation.py`。
- **典型违反**：新增“管理员代建预约”功能只插 `reservations`；取消时只改状态；自动完成时忘记 `release_slots`。
- **检查方式**：搜索所有写 `Reservation.status` 的位置，确认终态都调用 `release_slots`；搜索所有 `db.add(Reservation(...))`，确认都写槽位；并发测试验证唯一约束生效。

### ARC-031 · 幂等键唯一且同键同请求 · P0 · ✅ 已实现

- **约束**：`(user_id, idempotency_key)` 必须唯一；同一幂等键重复提交必须返回同一业务结果；同一键若对应不同座位/日期/时段，必须拒绝（`IDEMPOTENCY_KEY_REUSED`），不得静默创建第二张单。
- **原因**：网络重试、用户连点、前端重放都会产生重复请求；幂等是“重复提交不得产生多笔预约”的实现基础。
- **适用范围**：`reservation_service.py`、`models/reservation.py`、`frontend/src/utils/useSeatBooking.ts`。
- **典型违反**：每次点击重新生成幂等键；后端不校验同键 payload；用前端按钮禁用代替服务端幂等。
- **检查方式**：并发/串行重复提交同一 payload，确认只产生一条记录；同键改时段应返回 409；检查唯一约束是否存在。

### ARC-032 · 座位资源状态与预约状态严格分离 · P0 · ✅ 已实现

- **约束**：`seats.status` 只能取“可用 / 维修中 / 停用”；不得写入“已预约 / 使用中 / 已占用”。某座位某时段是否被占用，必须由预约单与槽位实时计算。
- **原因**：把预约状态写回座位会造成状态污染、释放困难、并发错误；需求已明确区分两种状态。
- **适用范围**：`models/seat.py`、`enums.py`、`seat_service.py`、`availability_service.py`、前端座位图。
- **典型违反**：预约成功后把 `seat.status` 改为“已预约”；关闭场地时把座位改为“停用”；看板把“使用中”算作座位状态。
- **检查方式**：搜索对 `seat.status` 的赋值；确认只出现在座位管理的新增/状态调整；数据库 CHECK 约束只允许三个值。

### ARC-033 · 有效预约定义与时段释放 · P0 · ✅ 已实现

- **约束**：有效预约固定为 `{待使用, 使用中}`；已取消、已完成、已违约不占用未来时段。任何可预约性判断、冲突检测、每日次数统计都必须使用该集合；统计看板的历史占用可以另外包含“已完成”，但必须在口径中说明。
- **原因**：不同模块对“有效”的定义不一致会导致座位明明已取消却仍不可约，或统计口径互相矛盾。
- **适用范围**：`availability_service.py`、`reservation_service.py`、`dashboard_service.py`、前端 `bookingRules.ts`。
- **典型违反**：冲突查询把“已完成”也算占用；每日次数把“已取消”算进去；看板把“已违约”算作历史使用。
- **检查方式**：搜索 `ACTIVE_STATUSES`、`OCCUPIED_STATUSES` 的定义；确认预约冲突只用前者；看板历史占用使用后者且有注释说明。

### ARC-034 · 状态流转必须校验来源状态 · P0 · ◐ 部分实现

- **约束**：每个状态变更必须先校验当前状态是否允许该操作，并拒绝非法来源状态；终态不得再流转。预约、投诉、黑名单/账户都必须有明确的转换表，Service 是唯一执行者。
- **原因**：非法流转会破坏审计、统计与用户预期；例如“已完成”再被强制取消会产生负向记录。
- **适用范围**：`attendance_service.py`、`reservation_service.py`、`violation_service.py`、`complaint_service.py`、`blacklist_service.py`、`user_service.py`。
- **典型违反**：不判断状态直接赋值；只判断“不是已取消”就允许；管理端批量改状态绕过转换表。
- **检查方式**：对照附录 C 的状态机；为每个转换写“非法来源”测试；检查是否有 `status =` 赋值前缺少 `if`。
- **已知缺口**：来源状态校验与并发控制未绑定，见 ARC-040 与 §18 I-08。

### ARC-035 · Alembic 迁移链纪律 · P0 · ✅ 已实现

- **约束**：数据库结构变更必须提供 Alembic 迁移；迁移链必须保持单一 head，不再新增分叉；不得修改已执行/已提交的历史迁移；不得清空数据库或删除业务数据；迁移必须考虑已有数据兼容；执行前必须核对 `alembic current` / `alembic heads`。
- **原因**：多人本地 MySQL + 迁移链是当前协作方式；改历史迁移会导致不同成员数据库状态分叉。
- **适用范围**：`backend/alembic/versions/`、`backend/app/models/`。
- **典型违反**：直接改模型不生成迁移；修改旧迁移文件；用 `drop_all/create_all` 代替迁移；迁移里无默认值地加非空列。
- **检查方式**：`alembic heads` 应只有一个 head；`alembic check` 无差异；新迁移包含 upgrade/downgrade（或明确说明不可逆）；在空库与有数据库各验证一次。历史合并点 `b860458bfa51` 已存在，不得再新增分叉；新增迁移的 `down_revision` 必须指向当前唯一 head。

### ARC-036 · 索引与查询模式匹配 · P1 · ✅ 已实现

- **约束**：新增高频筛选/排序字段时必须评估索引；预约按 `(seat_id, reserve_date)`、`(user_id, reserve_date)`、`status`，违约按 `(user_id, created_at)`，消息按 `(user_id, is_read)`，审计按 `(operator_id, created_at)` 等已有索引应被复用；不得为每个字段盲目加索引。
- **原因**：索引不足会导致列表与看板随数据增长变慢；索引过多会增加写入成本。
- **适用范围**：`models/*.py`、`services/*.py` 的查询。
- **典型违反**：新增按 `created_at` 过滤但不加索引；在 `WHERE` 里对索引列做函数运算导致失效；为低基数字段单独建索引。
- **检查方式**：对新增查询看 `EXPLAIN`；对照模型 `Index` 声明；避免 `func.date(column) == ...` 这类不可用索引的写法。

### ARC-037 · 枚举字面量同步 · P1 · ✅ 已实现

- **约束**：角色、账户状态、座位状态、预约状态、投诉状态、违约类型、黑名单来源、消息类型的中文字面量，必须同时存在于：后端 `models/enums.py`、数据库 CHECK 约束、前端 `types/index.ts`、Mock 规则/种子、相关文档。新增或修改枚举必须一次性同步全部位置，并提供迁移。
- **原因**：中文字面量直接落库，任何一处缺失都会导致写入失败或前端显示未知状态。
- **适用范围**：`enums.py`、`models/*.py` 的 `CheckConstraint`、`types/index.ts`、`mocks/`。
- **典型违反**：新增“待审核”状态只改前端；删除“教师用户”但数据库 CHECK 仍保留；Mock 使用旧枚举。
- **检查方式**：全局搜索字面量；对照 CHECK 约束；用非法值写入应被数据库拒绝。

### ARC-038 · 派生数据必须与明细一致 · P1 · ✅ 已实现

- **约束**：`users.violation_count` 必须与违约记录数一致；`users.account_status` 必须与“是否存在有效黑名单限制”一致；`reservation_slots` 必须与有效预约区间一致。派生字段只能由所属 Service 维护，不得由多个模块各自回写。
- **原因**：派生字段是查询加速与展示需要，一旦与明细不一致，会出现“次数已达阈值但未受限”或“已解除但仍受限”。
- **适用范围**：`violation_service.py`、`blacklist_service.py`、`user_service.py`、`reservation_service.py`。
- **典型违反**：手动改 `violation_count` 做演示；解除黑名单后不 `_sync_account_status`；取消预约不释放槽位。
- **检查方式**：编写一致性核对查询（计数 vs 明细）；重复执行解除/限制操作验证幂等；检查所有回写点是否集中在所属 Service。

### ARC-039 · 核心表写入必须经所属 Service · P1 · ✅ 已实现

- **约束**：`reservations`、`reservation_slots`、`violation_records`、`blacklist_entries`、`audit_logs`、`station_messages` 的写入必须经对应 Service 的公开函数；路由、任务、其他 Service 不得直接构造这些 ORM 对象并提交。
- **原因**：这些表承载业务不变量；绕过 Service 就绕过了状态校验、槽位维护、审计与通知。
- **适用范围**：`api/v1/`、`tasks/`、`services/`。
- **典型违反**：任务里直接 `db.add(ViolationRecord(...))`；路由里直接改 `BlacklistEntry.released_at`；消息直接 `db.add(StationMessage(...))` 而不走通知服务。
- **检查方式**：搜索这些模型的构造与赋值位置；允许的写入点应集中在对应 Service。

### ARC-040 · 并发状态流转必须串行化 · P0 · ○ 目标

- **约束**：对同一预约单的状态变更（签到、签退、用户取消、管理员强制取消、自动违约、自动完成、手动违约）必须串行化。实现方式可以是 `SELECT ... FOR UPDATE` 行锁、带来源状态条件的 `UPDATE ... WHERE status = 期望值`、或等价的乐观锁；必须保证“读取状态—判断—写入”之间不被另一个事务插入。
- **原因**：当前 `attendance_service.check_in`、`reservation_service.force_cancel`、`violation_service.register_manual` 等使用普通 `db.get` 读取后再赋值，未加行锁。并发下两个操作可能都通过来源状态校验，最后写入者覆盖前者，产生例如“状态为使用中但槽位已被取消操作删除”“审计记录为已取消但状态为使用中”的不一致。
- **适用范围**：所有预约状态变更路径，以及黑名单/账户状态的并发变更。
- **典型违反**：学生签到与管理员强制取消同时发生；自动违约与签到在截止时刻竞争；两个管理员同时登记手动违约。
- **检查方式**：编写并发测试（两个线程/两个 TestClient 请求）验证只有一个操作成功、另一个返回 409；检查关键更新是否使用 `with_for_update()` 或条件 `UPDATE`；检查状态变更与槽位操作是否在同一事务。
- **当前状态**：**尚未实现**。这是本文识别出的最高优先级架构风险，见 §18 I-08。

---

## 9. API 与接口约束

### ARC-041 · 统一错误响应结构 · P0 · ✅ 已实现

- **约束**：业务失败统一返回 `{ "code": string, "message": string, "details"?: object }`；HTTP 状态码表达语义（400/401/403/404/409/422/500）；不得返回 200 表示失败；不得把异常堆栈返回给前端。
- **原因**：前端需要稳定地读取 `message` 展示、按 `code` 分支处理；统一结构也便于测试断言。
- **适用范围**：`core/exceptions.py`、所有路由与 Service。
- **典型违反**：`return {"success": False}` 但状态码 200；不同接口分别返回 `detail` / `msg` / `error`；把数据库异常原文返回。
- **检查方式**：对照 `register_exception_handlers`；用非法参数、越权、冲突分别验证响应体；搜索 `JSONResponse(status_code=200` 的业务失败分支。

### ARC-042 · 契约变更必须全链路同步 · P0 · ✅ 已实现

- **约束**：修改 API 路径、方法、请求字段、响应字段、类型、分页结构或错误码时，必须同步更新：后端 Schema、前端 `api/*.ts`、`types/index.ts`、MSW handler、相关测试、文档。优先采用向后兼容的增量变更；破坏性变更必须先说明迁移方案。
- **原因**：任何一处遗漏都会造成运行时类型错误或 Mock 与真实后端不一致。
- **适用范围**：所有接口变更。
- **典型违反**：后端把 `page_size` 改成 `size` 但前端未改；新增响应字段只在后端加；删除字段但 Mock 仍返回。
- **检查方式**：接口变更清单逐项打勾；前后端联调；`npm run type-check`；Mock 与真实后端各跑一遍关键流程。

### ARC-043 · REST 命名与版本前缀 · P1 · ✅ 已实现

- **约束**：接口统一挂在 `/api/v1`；资源路径使用复数名词（`/reservations`、`/rooms`、`/violations`）；“本人”资源使用 `/me` 子路径；动作用子路径表达（`/{id}/cancel`、`/{id}/check-in`），不使用动词型顶层路径。
- **原因**：一致命名降低认知成本，便于权限与文档组织。
- **适用范围**：`api/v1/*.py`。
- **典型违反**：新增 `/getMyReservations`；把动作写成 `POST /cancelReservation`；版本前缀硬编码在 Service。
- **检查方式**：对照现有路由表（附录 D）；新增路由必须符合模式。

### ARC-044 · 分页约定与例外 · P1 · ✅ 已实现

- **约束**：列表接口统一返回 `{ items, total, page, page_size }`；`page >= 1`，`1 <= page_size <= 100`；前端不得假定一次能取全量。例外：`GET /rooms`、`GET /rooms/{id}/seats`、`GET /rooms/{id}/closures` 等有界资源列表可以返回数组，但必须确认其规模有上限。
- **原因**：分页结构统一便于前端复用；无上限列表会随数据增长拖垮页面。
- **适用范围**：`schemas/common.py`、各列表路由、前端 `PageResult`。
- **典型违反**：新增列表不分页且可能无限增长；`page_size` 允许 10000；前端用 `items.length` 当作总数。
- **检查方式**：搜索 `PageResult` 使用；检查 `Query(..., le=100)`；评估无分页列表的数据上限。

### ARC-045 · 只读接口无副作用，写操作可防重 · P1 · ✅ 已实现

- **约束**：`GET` 接口不得修改业务数据；写接口必须考虑重复提交：创建预约用幂等键，取消/签到/签退等状态操作必须对重复请求返回明确结果（幂等成功或 409），不得静默产生重复记录。
- **原因**：浏览器重试、用户连点、代理重放都会重复调用；只读接口有副作用会破坏缓存与权限审计的直觉。
- **适用范围**：所有路由。
- **典型违反**：`GET /rooms/{id}/close-preview` 里顺手创建关闭记录；重复点击“签到”产生两条记录；重复取消返回 500。
- **检查方式**：审查 GET 是否有写操作；对写接口连续调用两次验证结果；检查幂等键与状态判断。

### ARC-046 · 显式响应模型，避免多态响应 · P1 · ◐ 部分实现

- **约束**：每个接口必须声明 `response_model`；同一路径不应根据查询参数返回结构完全不同的响应。若确需多形态，应使用统一信封或拆分接口，并在前端类型中明确区分。
- **原因**：多态响应会让前端类型、Mock、测试与文档难以维护。
- **适用范围**：`api/v1/*.py`、`types/index.ts`。
- **典型违反**：`GET /dashboard/seat-usage` 在 `group_by=seat` 与 `group_by=slot` 下返回两种数组（当前实现即为此），前端用两个函数各自断言类型。
- **检查方式**：检查 `response_model`；搜索 `|` 联合响应模型；新增接口优先一资源一形态。

### ARC-047 · 时间与字段格式统一 · P1 · ✅ 已实现

- **约束**：日期使用 `YYYY-MM-DD`；时间使用 `HH:MM:SS` 或 `HH:MM`（与现有接口一致）；日期时间使用 ISO 8601（`YYYY-MM-DDTHH:mm:ss`）；字段命名使用 `snake_case`；布尔字段使用 `is_` / `has_` / `enabled` 等明确语义。
- **原因**：格式不一致会导致前端解析错误、时区误解与排序错误。
- **适用范围**：Schema、前端类型、Mock、数据库字段。
- **典型违反**：某接口返回 `2026/11/12`；时间返回带时区偏移而其他接口不带；字段用 `createTime` 与 `created_at` 混用。
- **检查方式**：对照 `types/index.ts` 与 Schema；用实际响应抽样检查；前端统一走 `utils/format.ts`。

### ARC-048 · 错误码可追溯并集中登记 · P1 · ○ 目标

- **约束**：业务错误码应可追溯到需求编号或明确的业务含义（如 `C3_BR-006`、`ST-029`），并逐步建立集中错误码目录；新增错误码必须避免与现有码冲突，前端需要分支处理时必须使用稳定码而不是匹配文案。
- **原因**：当前错误码分散在各 Service，前端主要依赖 `message`；文案调整会破坏基于文案的判断。
- **适用范围**：`core/exceptions.py`、所有 `BusinessError`、前端错误处理。
- **典型违反**：同一含义在不同接口用不同码；前端用 `message.includes('已满')` 判断；错误码拼写不一致。
- **检查方式**：全局搜索 `code="`；建立错误码表（目标）；前端分支只使用 `code`。

---

## 10. 安全与权限约束

### ARC-050 · 服务端认证强制 · P0 · ✅ 已实现

- **约束**：除 `/health`、`/auth/login`、`/auth/register` 等明确公开的接口外，所有接口必须要求 Bearer JWT；令牌缺失、过期、签名错误、`token_version` 不匹配、账户停用都必须拒绝。
- **原因**：前端隐藏页面不能阻止直接调用接口；认证必须在服务端每个请求执行。
- **适用范围**：`core/dependencies.py`、`api/v1/*.py`。
- **典型违反**：新增接口忘记加 `Depends(get_current_user)`；只校验令牌存在不校验签名；停用账户仍可访问。
- **检查方式**：枚举全部路由，确认依赖；用无令牌/过期令牌/改密后旧令牌/停用账户令牌逐一验证。

### ARC-051 · 角色边界固定 · P0 · ✅ 已实现

- **约束**：R-01 学生只能使用学生端能力；R-02 自习室管理员拥有业务管理权限；R-04 系统管理员本版**没有业务操作权限**，只能进入系统管理员提示页与个人资料。不得把系统管理员并入业务管理员，也不得恢复已取消的 R-03 教师角色。
- **原因**：权限矩阵已定稿；放宽角色会造成越权与审计混乱。
- **适用范围**：`core/dependencies.py`、`router/index.ts`、`stores/auth.ts`、`mocks/http.ts`。
- **典型违反**：`require_admin` 同时接受“自习室管理员”和“系统管理员”；前端把系统管理员导向看板；Mock 允许系统管理员调用业务接口。
- **检查方式**：三种角色逐一调用关键接口；对照权限矩阵；检查 `require_admin` 的角色集合。

### ARC-052 · 数据范围隔离 · P0 · ✅ 已实现

- **约束**：学生接口只能访问本人数据：`/me` 的查询必须以 `current_user.id` 过滤，不得接受前端传入的 `user_id` 作为本人范围；学生端不得返回其他用户的姓名、学号、联系方式；管理员接口可以按 `student_no` / `user_id` 筛选，但必须要求管理员角色。
- **原因**：越权访问与隐私泄露是 A 级约束；前端传参不可信。
- **适用范围**：`reservation_service.list_my_reservations`、`violation_service.list_my_violations`、`complaint_service.list_my_complaints`、`message_service.list_my_messages`、`user_service`。
- **典型违反**：`GET /reservations/me?user_id=2` 能看别人；学生端预约列表返回用户姓名；管理员接口漏加 `require_admin`。
- **检查方式**：用学生 A 的令牌请求 `user_id=B` 的资源应被忽略或拒绝；检查所有 `/me` 查询条件；检查响应 Schema 是否含他人 PII。

### ARC-053 · 管理端 PII 必须服务端脱敏 · P0 · ✅ 已实现

- **约束**：管理员查看用户联系方式时，后端必须脱敏（手机号保留前 3 后 4，邮箱保留首字母与域名）；前端掩码只能作为兜底，不能作为唯一手段；本人查看本人资料不脱敏。管理员不得修改姓名、学号。
- **原因**：只在前端遮挡时，明文仍会出现在 HTTP 响应、日志与调试工具中。
- **适用范围**：`utils/masking.py`、`user_service.to_user_read(mask_contact=True)`、`api/v1/users.py`。
- **典型违反**：管理端用户列表直接返回 `contact` 原值；前端 `mask.ts` 是唯一脱敏层；管理员接口提供修改姓名字段。
- **检查方式**：用管理员令牌请求 `/users`，确认响应中无完整手机号/邮箱；检查本人 `/users/me` 保持原值；检查 `UserUpdate` 是否只允许 `contact`。

### ARC-054 · 密钥与敏感信息管理 · P0 · ✅ 已实现

- **约束**：JWT 密钥、数据库密码等不得硬编码在源码中；必须通过 `backend/.env` 或环境变量提供；`.env` 不得提交；启动时 `settings.validate_security()` 必须拒绝占位符和过短密钥；密码只存 Argon2 哈希，不存明文。
- **原因**：公开的默认密钥允许任何人伪造管理员令牌；泄露的数据库密码会造成全量数据风险。
- **适用范围**：`core/config.py`、`core/security.py`、`backend/.env.example`、`start.bat`。
- **典型违反**：把真实密钥写进 `config.py` 默认值；提交 `.env`；把密码哈希返回给前端；日志打印令牌。
- **检查方式**：搜索 `jwt_secret_key`、`password`、`DATABASE_URL` 的硬编码；确认 `.gitignore` 忽略 `.env`；启动时用占位符密钥应失败。

### ARC-055 · 密码哈希与令牌失效 · P0 · ✅ 已实现

- **约束**：密码必须使用 `pwdlib` 推荐的 Argon2 哈希；修改密码必须校验旧密码、拒绝新旧相同，并递增 `token_version` 使旧令牌立即失效；登录与注册签发令牌必须携带当前 `token_version`。
- **原因**：明文/弱哈希会造成拖库风险；改密后旧令牌仍有效会导致账号无法真正踢下线。
- **适用范围**：`core/security.py`、`auth_service.py`、`dependencies.py`。
- **典型违反**：使用 MD5/SHA1 存密码；改密不递增版本；JWT 不含 `ver`；校验时忽略 `ver`。
- **检查方式**：检查 `PasswordHash.recommended()`；改密后用旧令牌请求应 401；检查 JWT payload 含 `ver`。

### ARC-056 · 登录失败锁定与注册策略 · P1 · ✅ 已实现

**约束**：登录失败在窗口内达到阈值必须临时锁定；锁定状态不得泄露“账号是否存在”；自助注册受 `registration_enabled` 与可选学号白名单控制，注册只能创建学生角色。**原因**：防止暴力破解与批量注册。**检查**：用错误密码连续登录触发 429 `ACCOUNT_LOCKED`；关闭注册开关后注册应 403；注册请求携带 `role` 应被忽略/拒绝。

### ARC-057 · 参数化查询与输入校验 · P1 · ✅ 已实现

**约束**：数据库访问必须使用 SQLAlchemy ORM 或参数化查询；禁止字符串拼接 SQL；所有外部输入必须经 Pydantic 或显式校验（分页、枚举、日期范围、文件大小等）。**原因**：防 SQL 注入与非法输入导致的 500。**检查**：搜索 `text(`、`execute(f"`；用非法枚举/负分页/超长字符串验证 422 或明确业务错误。

### ARC-058 · CORS 与生产安全配置 · P1 · ◐ 部分实现

**约束**：CORS 只允许明确来源；`allow_credentials=True` 时禁止 `allow_origins=["*"]`；生产环境必须通过环境变量配置前端域名、HTTPS、反向代理与安全响应头。**原因**：通配来源 + 凭据会造成跨站请求风险；开发默认值不应直接用于生产。**检查**：查看 `core/config.py` 的 `cors_origins`；生产部署前逐项核对；当前生产配置**尚未定义**，见 §18。

### ARC-059 · 传输安全与前端令牌存储 · P2 · ？ 待确认

**约束**：生产环境必须使用 HTTPS；当前前端将 JWT 存入 `localStorage`（记住我）或 `sessionStorage`，存在 XSS 读取风险，且没有 refresh token。若未来面向真实用户上线，应评估改为 HttpOnly Cookie + CSRF 防护，或增加短期令牌与刷新机制。**原因**：Web Storage 对 XSS 不设防；课程演示可接受，生产不可默认接受。**检查**：确认部署启用 HTTPS；安全评审记录该风险；本轮不修改认证方案。

---

## 11. 核心业务一致性约束

### ARC-060 · 预约创建校验顺序与同事务 · P0 · ✅ 已实现

- **约束**：创建预约必须按既定顺序校验：幂等 → 行锁 → C1 座位资源 / C2 自习室启用与开放时间 / C2b 临时关闭 / C5 账户资格 / C6 参数与每日次数 / C3 座位冲突 / C4 用户冲突；校验与“预约单 + 槽位”写入必须在同一事务内完成。
- **原因**：顺序影响错误提示的准确性与并发窗口；分开事务会让校验结果失效。
- **适用范围**：`reservation_service.create_reservation`、`availability_service.check_reservation_rules`。
- **典型违反**：先写预约再校验；把每日次数校验放在事务外；新增校验但忘记放进同一事务。
- **检查方式**：对照 `check_reservation_rules` 的分支顺序；构造每个条件的失败用例；并发测试验证唯一约束兜底。

### ARC-061 · 取消、签到、签退、违约的状态互斥 · P0 · ✅ 已实现

- **约束**：
  - 学生只能在开始前 30 分钟以上取消“待使用”预约；
  - 管理员只能强制取消“待使用”预约，且必须填原因；
  - 签到只允许“待使用”且在窗口内；签退只允许“使用中”；
  - 手动违约只允许“使用中”，必须填原因；自动违约只允许“待使用”且超过开始后 15 分钟；
  - 已完成、已取消、已违约不得再次操作。
- **原因**：这些操作共享同一状态字段，互斥规则是业务正确性的核心。
- **适用范围**：`reservation_service.py`、`attendance_service.py`、`violation_service.py`。
- **典型违反**：允许对“使用中”强制取消；允许对“已完成”登记违约；重复签到覆盖首次签到时间。
- **检查方式**：为每个状态 × 每个操作写矩阵测试；检查 Service 中的状态判断；并发场景见 ARC-040。

### ARC-062 · 签到窗口以服务器时间为准 · P0 · ✅ 已实现

- **约束**：签到窗口为 `[开始时间 - 15 分钟, 开始时间 + 15 分钟)`；判定必须使用服务器时间（`time_utils.now()`），不得信任客户端时间；窗口外签到必须拒绝并返回窗口时间。
- **原因**：客户端时间可修改；窗口边界是违约判定的基础。
- **适用范围**：`attendance_service.check_in`、`time_utils.checkin_window`、前端提示。
- **典型违反**：前端用本地时间判断后直接放行；后端用 `datetime.utcnow()` 导致 8 小时偏差；窗口右端点包含。
- **检查方式**：固定服务器时间测试边界（开始前 15 分、开始后 14:59、开始后 15:00）；检查时区；前端只做提示。

### ARC-063 · 违约幂等、阈值与黑名单原子性 · P0 · ✅ 已实现

- **约束**：同一预约同一违约类型只能有一条记录（`uq_violation_reservation_type`）；写入违约、更新 `violation_count`、触发阈值黑名单、写审计必须在同一事务内；重复执行任务不得重复累加；自动限制到期自动解除，手动限制只能管理员解除。
- **原因**：违约次数直接决定黑名单；重复累加会让用户被错误限制，部分提交会造成计数与记录不一致。
- **适用范围**：`violation_service._apply`、`blacklist_service.restrict_if_threshold`、`tasks/auto_violation.py`、`tasks/blacklist_expiry.py`。
- **典型违反**：违约记录与黑名单分两次提交；重复扫描重复加 1；手动限制到期被自动解除。
- **检查方式**：重复调用 `apply_auto_violation` 验证幂等；并发触发阈值验证只创建一条黑名单；检查 `commit=False` 的调用链。

### ARC-064 · 场地关闭两阶段确认与指纹校验 · P0 · ✅ 已实现

- **约束**：必须先只读查询影响清单（`GET /rooms/{id}/close-preview`），再执行关闭（`POST /rooms/{id}/close`）；执行请求必须携带 `expected_reservation_ids`，后端重新计算并比对，不一致返回 409 要求重新预览；确认前不得自动取消任何预约；`cancel_affected` 必须由管理员显式选择；关闭只写 `room_closures`，不得改写座位资源状态。
- **原因**：影响清单可能在预览与确认之间变化；跳过确认会误取消用户预约。
- **适用范围**：`room_service.preview_close`、`close_room`、`schemas/room.py`、`useRoomClose.ts`。
- **典型违反**：前端预览后直接调用关闭且不传指纹；后端不比对指纹；关闭时把座位改为“停用”；默认取消全部受影响预约。
- **检查方式**：预览后人为新增一条冲突预约，再提交旧指纹应 409；检查关闭后座位 `status` 未变；检查审计记录包含影响清单。

### ARC-065 · 座位资源状态调整不自动取消预约 · P0 · ✅ 已实现

- **约束**：管理员把座位改为维修中/停用时，系统只返回冲突预约清单并提示，不得自动取消预约；单座位接口遇冲突应拒绝并引导使用批量接口；所有状态调整必须填原因并写审计。
- **原因**：自动取消会绕过用户的知情与补偿；需求要求资源状态调整与预约处理分离。
- **适用范围**：`seat_service.update_seat_status`、`update_status_batch`、`SeatManageView.vue`。
- **典型违反**：停用座位时级联取消未来预约；批量接口静默忽略冲突；不写审计。
- **检查方式**：对有未来预约的座位改状态，确认预约仍在且返回冲突清单；检查审计日志；确认前端展示冲突。

### ARC-066 · 投诉状态机与 SLA · P1 · ✅ 已实现

**约束**：投诉只允许 `待处理 → 处理中/已驳回`、`处理中 → 已处理`、`已处理 → 已关闭`；已驳回/已关闭为终态；管理员负责受理与处理，投诉人确认关闭；3 个工作日 SLA 只用于提示，不自动升级。**原因**：状态机与责任边界已定稿。**检查**：`complaint_service._ALLOWED_TRANSITIONS`；非法转换测试；超时只标红不改状态。

### ARC-067 · 站内消息是非关键路径 · P1 · ✅ 已实现

**约束**：消息写入失败不得回滚已经成功的预约、取消、违约等业务；消息必须在业务提交后通过独立 Session 写入；消息只能本人查看，未读数按服务端统计。**原因**：消息是通知而非业务事实，不能反向影响主流程。**检查**：`notify_safe` 的独立 Session 与异常捕获；模拟消息表写入失败验证业务仍成功；`messages/me` 按 `user_id` 过滤。

### ARC-068 · 看板统计口径固定 · P0 · ✅ 已实现

- **约束**：概览五项口径固定：座位总数=可用座位数（不含维修中/停用）；当前时段使用中=查询时刻处于“使用中”的预约单数（不是座位状态）；今日预约数=当日 `[00:00,24:00)` 创建且未取消的预约单数；今日违约数=当日产生的违约记录数；受限账户数=当前状态为“受限”的用户数。柱状图=各座位已使用时段数（已完成预约覆盖的时段，按 30 分钟统计块）；折线图=按自然日的有效预约数与违约数；每 10 秒刷新并显示数据截至时间。
- **原因**：统计口径已定稿；口径漂移会让同一页面不同时间/不同实现给出不同数字。
- **适用范围**：`dashboard_service.py`、`dashboard.py`、`useDashboard.ts`、`dashboardCharts.ts`。
- **典型违反**：把“今日预约数”改成按 `reserve_date` 统计；把“使用中”算成座位状态；把轮询周期当作违约任务周期；柱状图按 5 分钟统计块。
- **检查方式**：对照需求 FR-050～FR-053 的验收用例；用固定数据核对五项数值；检查 `dashboard_block_minutes` 仍为 30；检查 `created_at` 与 `reserve_date` 的使用位置。

### ARC-069 · 四类自动任务语义 · P1 · ✅ 已实现

**约束**：自动违约=开始后 15 分钟仍未签到→违约；自动结束=使用中到结束时间→已完成（未签退不违约）；黑名单到期=仅自动限制到期解除，手动限制不自动解除；投诉超时关闭=已处理超过配置天数→已关闭。四类任务都必须幂等、可重复执行。**原因**：这些任务在没有人工操作时维持系统状态正确。**检查**：`tasks/*.py` 与 `scheduler.py`；固定时间重复执行；检查手动限制不被自动解除。

---

## 12. 性能与可扩展性约束

### ARC-070 · 列表必须分页或有明确上限 · P1 · ✅ 已实现

**约束**：可能增长的列表必须服务端分页；前端不得一次性拉取全量后在本地分页；分页上限 100；导出功能本期排除，不得通过“拉全量”变相实现导出。**原因**：数据增长后全量拉取会造成接口超时与浏览器卡顿。**检查**：检查 `page_size` 上限；搜索 `page_size=500`、`page_size=1000`；评估无分页列表的规模。

### ARC-071 · 聚合尽量下推数据库 · P1 · ◐ 部分实现

**约束**：统计、计数、Top N 应优先用 SQL `COUNT` / `GROUP BY` 完成；不得把大量明细拉到 Python/JS 再聚合。**原因**：应用层聚合会随数据量线性变慢并占用内存。**检查**：当前 `GET /dashboard/violation-top` 已下推；`get_trend` 仍会把满足条件的预约全部加载后在 Python 按日去重（见 §18 I-11），新增统计应避免复制该模式。

### ARC-072 · 查询必须带时间范围并可用索引 · P1 · ◐ 部分实现

**约束**：预约、违约、审计、消息等时间序列查询必须带明确时间范围；不得无界扫描全表；范围应与索引前缀匹配。**原因**：无界查询在演示数据量下不明显，真实数据量下会拖垮服务。**检查**：检查 Service 查询条件；`EXPLAIN` 关键列表；看板趋势接口的查询范围（当前存在无界加载，见 §18 I-11）。

### ARC-073 · 轮询与请求节流 · P1 · ✅ 已实现

**约束**：只有看板按 10 秒轮询；其他页面按操作或手动刷新；同一数据的多个消费者共用一次请求（如消息未读数）；页面卸载必须清理定时器；轮询失败使用 `silent`。**原因**：过多轮询会造成请求风暴与提示刷屏。**检查**：搜索 `setInterval`；确认清理逻辑；看板之外的页面不得新增常驻轮询。

### ARC-074 · 前端懒加载与构建产物 · P2 · ✅ 已实现

**约束**：路由页面使用动态 `import()` 懒加载；公共依赖由 Vite 统一打包；不得为了“首屏更快”把整页组件拆成大量微小 chunk。**原因**：当前页面数量与体量适合路由级拆分。**检查**：`router/index.ts` 的 `() => import`；构建后的 chunk 大小。

### ARC-075 · 缓存引入前必须评估一致性 · P2 · ○ 目标

**约束**：当前不使用缓存。未来若引入 Redis 或本地缓存，必须先明确：缓存哪些数据、失效策略、与数据库的一致性、并发更新时的穿透/雪崩处理，并记录 ADR。**原因**：预约余量、黑名单状态等强一致数据缓存后极易出现“显示可约但提交失败”。**检查**：当前无缓存依赖；新增缓存必须附设计与失效验证。

### ARC-076 · 调度任务运行约束 · P1 · ✅ 已实现

**约束**：任务频率与业务要求匹配（自动违约/自动结束 1 分钟、黑名单到期 10 分钟、投诉超时关闭 1 小时）；任务执行时间应远小于间隔；必须设置 `max_instances=1`、`coalesce=True`；测试环境必须关闭调度器。**原因**：任务重叠会重复处理；长任务会拖住后续执行。**检查**：`scheduler.py` 的参数；任务耗时日志；`conftest.py` 的 `scheduler_enabled=False`。

---

## 13. 工程质量与测试约束

### ARC-080 · 目录与模块组织稳定 · P1 · ✅ 已实现

**约束**：保持 §2.3 的目录结构；新增文件按职责放入现有目录；不得在根目录堆积临时脚本；不得创建与现有体系平行的第二套 `services` / `utils`。**原因**：目录是团队与 AI 的共同地图。**检查**：新增文件路径；根目录是否出现临时文件；`git status` 是否包含无关产物。

### ARC-081 · TypeScript 零 error，禁止绕过类型 · P1 · ✅ 已实现

**约束**：`npm run type-check` 必须零 error；禁止 `@ts-ignore`、`@ts-expect-error` 掩盖问题；尽量避免 `any`，确需使用时必须有注释说明原因；前端类型必须与后端 Schema 对齐。**原因**：类型是前后端契约的第一道检查。**检查**：本轮 type-check 已通过；搜索 `@ts-ignore`、`: any`；新增接口必须补类型。

### ARC-082 · 核心业务必须有测试与回归 · P1 · ◐ 部分实现

**约束**：预约创建/冲突/幂等/并发、取消、签到签退、自动违约、黑名单阈值、场地关闭、权限隔离、投诉状态机、看板口径必须有后端测试；修改核心业务必须跑相关测试与完整回归；前端至少执行 type-check 与 build。**原因**：这些路径一旦回归，影响面大且难以人工覆盖。**检查**：`backend/tests/` 现有 17 个文件、119 个 test 函数；本轮未执行；前端尚无自动化测试（见 §18 I-06）。

### ARC-083 · 依赖治理 · P1 · ✅ 已实现

**约束**：新增依赖前评估：现有工具能否完成、是否实质改善、部署复杂度、兼容性、维护成本；常规低风险依赖可直接加入并更新 `requirements.txt` / `package.json`；核心框架替换、数据库迁移、基础设施变化必须先说明。**原因**：依赖是长期维护成本。**检查**：审查依赖清单变更；新增依赖必须在报告中说明理由。

### ARC-084 · 生成物与构建产物管理 · P1 · ◐ 部分实现

**约束**：`node_modules/`、`dist/`、`__pycache__/`、`.pytest_cache/`、`.env` 不得提交；构建产物不应作为源码维护。**原因**：生成物会造成巨大且无意义的 diff，并让“当前运行的是哪份构建”变得不可信。**检查**：`.gitignore` 已包含 `frontend/dist/`，但仓库仍跟踪 67 个 `frontend/dist` 文件（见 §18 I-05）；本轮不删除，后续应单独清理。

### ARC-085 · 文档与代码同步 · P1 · ◐ 部分实现

**约束**：修改接口、参数、页面、迁移、启动方式时，必须同步更新相关文档；文档中的“当前版本/迁移 head/页面数量/粒度”等事实必须可核对；不得把计划写成已完成。**原因**：文档漂移会误导后续开发者与 AI。**检查**：对照 §18 的文档漂移清单；每次迁移后更新 `docs/数据库表结构说明.md`；每次参数变更搜索全部镜像。

### ARC-086 · Mock 纪律 · P1 · ✅ 已实现

**约束**：MSW 只在 `DEV && VITE_USE_MOCK=true` 时加载；生产构建不得包含 MSW 与 `mockServiceWorker.js`；Mock 的路径、请求字段、响应结构、分页结构必须与真实后端一致；Mock 通过不等于业务验证通过，不得作为验收结论。**原因**：Mock 是演示工具，不是业务实现。**检查**：`main.ts` 的条件；`vite.config.ts` 的 `dropMockServiceWorker`；`VITE_USE_MOCK` 默认 false；对照 §18 I-01/I-02 的差异。

### ARC-087 · 命名、注释与可读性 · P2 · ✅ 已实现

**约束**：文件名与函数名表达职责；业务注释说明“为什么”而不是复述“做了什么”；需求编号只用于源码注释与文档追溯，不出现在界面文案；避免死代码与未使用导入。**原因**：可读性直接影响维护与 AI 上下文质量。**检查**：代码评审；搜索界面中的 `FR-` / `BR-`；删除未使用导入。

### ARC-088 · 可访问性与响应式 · P2 · ✅ 已实现

**约束**：图表有 `role="img"` 与描述性 `aria-label`；纯图标按钮有名称；表单 label 关联；键盘焦点可见；1440/1024/768 宽度无横向溢出；抽屉不超过 92vw。**原因**：课程演示与日常使用的可用性要求。**检查**：键盘 Tab 走查；窄屏检查；对照 `frontend/docs/前端实现说明.md` 的自检表。

### ARC-089 · 修改后必须执行验证 · P1 · ✅ 已实现

**约束**：前端修改至少执行 `npm run type-check`，涉及构建配置或发布时执行 `npm run build`；后端修改执行相关 `pytest`；涉及数据库执行 `alembic current/heads/check`；未执行的检查必须在报告中标注“未执行”，不得声称通过。**原因**：保证交付结果可验证，避免“看起来完成”。**检查**：开发报告中的命令与输出；CI（待建设）应逐步固化这些命令。

---

## 14. 约束等级总表

> 统计：**P0 29 条，P1 46 条，P2 9 条，合计 84 条**。状态：✅ 66 条、◐ 13 条、○ 4 条、？ 1 条。状态表示“当前代码与约束的吻合程度”，不代表约束等级。

| ID | 约束名称 | 等级 | 状态 |
|---|---|---|---|
| ARC-001 | 服务端是业务裁决的唯一权威 | P0 | ✅ |
| ARC-002 | 核心业务规则单一归属 | P0 | ◐ |
| ARC-003 | 前后端分层与依赖方向 | P1 | ◐ |
| ARC-004 | 技术栈锁定 | P1 | ✅ |
| ARC-005 | 新模块落位现有目录 | P1 | ✅ |
| ARC-006 | 不引入无必要架构层 | P2 | ✅ |
| ARC-007 | HTTP/JSON 唯一跨端边界 | P0 | ✅ |
| ARC-008 | 单体单进程 + 进程内调度 | P1 | ✅ |
| ARC-009 | 架构演进留下 ADR | P2 | ○ |
| ARC-010 | 统一 HTTP 入口 | P0 | ✅ |
| ARC-011 | 前端权限仅 UX | P0 | ✅ |
| ARC-012 | Composable 编排 / Pinia 全局 | P1 | ◐ |
| ARC-013 | 类型单一来源 | P1 | ✅ |
| ARC-014 | 页面三态与统一反馈 | P1 | ✅ |
| ARC-015 | 前端规则镜像一致 | P1 | ◐ |
| ARC-016 | 路由角色登记 | P1 | ✅ |
| ARC-017 | 看板 10 秒轮询规范 | P1 | ✅ |
| ARC-018 | 设计 token 与视觉一致 | P2 | ✅ |
| ARC-019 | 组件规模/可访问性/响应式 | P2 | ✅ |
| ARC-020 | 认证鉴权统一依赖 | P0 | ✅ |
| ARC-021 | 路由薄，业务在 Service | P1 | ✅ |
| ARC-022 | Service 事务边界与原子性 | P0 | ✅ |
| ARC-023 | Schema 契约与响应模型 | P1 | ✅ |
| ARC-024 | 异常分层，禁止吞错 | P1 | ✅ |
| ARC-025 | Session 生命周期 | P1 | ✅ |
| ARC-026 | 定时任务幂等/单实例/逐条事务 | P1 | ✅ |
| ARC-027 | 配置集中与环境变量 | P1 | ✅ |
| ARC-028 | 日志与审计可追踪、无敏感信息 | P1 | ◐ |
| ARC-030 | `reservation_slots` 并发保证 | P0 | ✅ |
| ARC-031 | 幂等键唯一 | P0 | ✅ |
| ARC-032 | 座位状态与预约状态分离 | P0 | ✅ |
| ARC-033 | 有效预约定义与槽位释放 | P0 | ✅ |
| ARC-034 | 状态流转校验来源状态 | P0 | ◐ |
| ARC-035 | Alembic 迁移链纪律 | P0 | ✅ |
| ARC-036 | 索引与查询模式匹配 | P1 | ✅ |
| ARC-037 | 枚举字面量同步 | P1 | ✅ |
| ARC-038 | 派生数据与明细一致 | P1 | ✅ |
| ARC-039 | 核心表写入经所属 Service | P1 | ✅ |
| ARC-040 | 并发状态流转串行化 | P0 | ○ |
| ARC-041 | 统一错误结构 | P0 | ✅ |
| ARC-042 | 契约变更全链路同步 | P0 | ✅ |
| ARC-043 | REST 命名与版本前缀 | P1 | ✅ |
| ARC-044 | 分页约定与例外 | P1 | ✅ |
| ARC-045 | 只读无副作用/写操作防重 | P1 | ✅ |
| ARC-046 | 显式响应模型、避免多态响应 | P1 | ◐ |
| ARC-047 | 时间与字段格式统一 | P1 | ✅ |
| ARC-048 | 错误码集中登记 | P1 | ○ |
| ARC-050 | 服务端认证强制 | P0 | ✅ |
| ARC-051 | 角色边界固定 | P0 | ✅ |
| ARC-052 | 数据范围隔离 | P0 | ✅ |
| ARC-053 | 管理端 PII 服务端脱敏 | P0 | ✅ |
| ARC-054 | 密钥与敏感信息管理 | P0 | ✅ |
| ARC-055 | 密码哈希与令牌失效 | P0 | ✅ |
| ARC-056 | 登录锁定与注册策略 | P1 | ✅ |
| ARC-057 | 参数化查询与输入校验 | P1 | ✅ |
| ARC-058 | CORS 与生产安全配置 | P1 | ◐ |
| ARC-059 | 传输安全与令牌存储 | P2 | ？ |
| ARC-060 | 预约创建校验顺序与同事务 | P0 | ✅ |
| ARC-061 | 取消/签到/签退/违约互斥 | P0 | ✅ |
| ARC-062 | 签到窗口服务器时间 | P0 | ✅ |
| ARC-063 | 违约幂等与黑名单原子性 | P0 | ✅ |
| ARC-064 | 场地关闭两阶段与指纹 | P0 | ✅ |
| ARC-065 | 座位状态调整不自动取消 | P0 | ✅ |
| ARC-066 | 投诉状态机与 SLA | P1 | ✅ |
| ARC-067 | 站内消息非关键路径 | P1 | ✅ |
| ARC-068 | 看板统计口径固定 | P0 | ✅ |
| ARC-069 | 四类自动任务语义 | P1 | ✅ |
| ARC-070 | 列表分页或明确上限 | P1 | ✅ |
| ARC-071 | 聚合尽量下推数据库 | P1 | ◐ |
| ARC-072 | 查询带时间范围并可用索引 | P1 | ◐ |
| ARC-073 | 轮询与请求节流 | P1 | ✅ |
| ARC-074 | 前端懒加载与构建产物 | P2 | ✅ |
| ARC-075 | 缓存引入前评估一致性 | P2 | ○ |
| ARC-076 | 调度任务运行约束 | P1 | ✅ |
| ARC-080 | 目录与模块组织稳定 | P1 | ✅ |
| ARC-081 | TypeScript 零 error | P1 | ✅ |
| ARC-082 | 核心业务测试与回归 | P1 | ◐ |
| ARC-083 | 依赖治理 | P1 | ✅ |
| ARC-084 | 生成物与构建产物管理 | P1 | ◐ |
| ARC-085 | 文档与代码同步 | P1 | ◐ |
| ARC-086 | Mock 纪律 | P1 | ✅ |
| ARC-087 | 命名、注释与可读性 | P2 | ✅ |
| ARC-088 | 可访问性与响应式 | P2 | ✅ |
| ARC-089 | 修改后执行验证 | P1 | ✅ |

### 14.1 已由现有代码实现的约束（节选说明）

以下约束不是“未来目标”，而是当前代码已经落地、后续不得破坏的事实：

- **预约并发与幂等**：`reservation_slots` 唯一约束、`uq_reservation_idempotency`、行锁、C1～C6 校验（ARC-030/031/060）。
- **状态与数据分离**：座位资源状态与预约状态分离、有效预约集合、终态释放槽位（ARC-032/033）。
- **权限与隐私**：JWT + 角色依赖、`/me` 数据隔离、服务端脱敏、启动期密钥校验（ARC-020/050/051/052/053/054/055）。
- **场地关闭两阶段**：预览 + 指纹 + 可选取消（ARC-064）。
- **看板口径与轮询**：后端聚合、10 秒刷新、失败保留旧值（ARC-017/068）。
- **迁移与 Mock 纪律**：单 head Alembic、MSW 仅开发期（ARC-035/086）。

### 14.2 需要逐步实现的目标（不得表述为已完成）

- **ARC-040 并发状态流转串行化**：当前缺少行锁/条件更新，是最高优先级目标。
- **ARC-048 错误码集中登记**：当前错误码分散。
- **ARC-009 ADR 目录与流程**：当前尚未建立 `docs/architecture/adr/`。
- **ARC-075 缓存**：当前未使用，未来引入前需设计。
- **ARC-082 前端自动化测试与 CI**：当前只有后端 Pytest，无 CI 配置。
- **ARC-084 构建产物清理**：`frontend/dist` 仍被跟踪，需单独治理。

---

## 15. 允许与禁止的架构行为

### 15.1 允许的行为

1. 在不改变 P0 边界的前提下新增业务模块，并按 §4.1/§4.2 落位。
2. 调整 Service 内部实现、查询方式、算法与局部数据结构，只要对外行为与事务语义不变。
3. 在不破坏接口兼容性的前提下优化性能（分页、索引、聚合下推、前端懒加载）。
4. 对重复逻辑进行合理抽象（公共组件、公共校验、公共错误映射），但不得抽象出第二套业务规则。
5. 用更简单、更可靠的技术方案替换复杂实现（例如用条件 `UPDATE` 替代“先查后写”），并在报告中说明。
6. 补充测试、日志、错误提示、加载/空/失败状态、可访问性与响应式改进。
7. 在完成影响分析、兼容性验证与 ADR 记录后，进行必要的架构演进（如拆分调度器、引入缓存）。
8. 修复与当前任务直接相关的关联缺陷，但不得无限扩大范围。
9. 更新本文与相关文档，使约束与代码保持一致。

### 15.2 禁止的行为

1. 为实现一个功能随意引入新的技术体系（Tailwind、Ant Design Vue、Vuex、React、Celery、Redis 等），或替换已确定的核心框架。
2. 未经分析直接修改核心模块职责边界（例如让路由承载业务、让模型依赖 Service、让前端直接连数据库）。
3. 通过复制代码绕过现有公共业务逻辑（复制一套预约校验、复制一套状态机、复制一套权限判断）。
4. 绕过统一认证、授权、数据访问与审计机制（自解析 JWT、直接改核心表、跳过 `audit_service`）。
5. 在多个模块重复维护同一份核心业务规则或业务参数。
6. 未经评估修改数据库核心结构、枚举字面量、迁移链或接口契约。
7. 为短期开发方便引入长期难以维护的依赖关系（前端组件直接拼 SQL/URL、后端模块循环依赖）。
8. 在缺少验证的情况下删除、覆盖或重构已有关键功能。
9. 把 Mock、前端预判或演示数据当作业务完成或验收通过。
10. 使用 `git reset --hard`、强制推送、覆盖用户未提交代码、删除不明来源的数据文件。
11. 把密钥、密码、令牌、完整个人信息写入源码、日志、文档或提交记录。
12. 在 P0 约束冲突未解决时继续堆叠功能改动。

---

## 16. AI 编程助手执行规则

> 本节是后续 AI 接手任务时的**必读操作规范**。它不替代 `AGENTS.md`，而是把架构约束转成可执行的检查步骤。

### 16.1 开工前

1. **先读本文与 `AGENTS.md`**，再读与任务相关的代码；不要只看 README 或凭技术栈猜测架构。
2. **定位任务涉及的模块**：后端路由/Service/模型/Schema/任务/迁移；前端页面/Composable/API/类型/Mock。
3. **识别可能触及的约束**：至少检查 §14 中与任务模块相关的 P0 条目；涉及预约状态、权限、接口、迁移、统计口径时，必须逐条对照。
4. **检查工作区状态**：`git status`；不得覆盖用户未提交的修改；不得在脏工作区上做批量重构。
5. **确认运行方式**：是否需要启动后端/MySQL；是否应使用 `VITE_USE_MOCK=true` 独立演示；测试环境是否关闭调度器。

### 16.2 修改中

1. **优先复用**现有 Service、Composable、公共组件、工具函数与类型；不要新建重复实现。
2. **P0 约束必须严格遵守**；发现需求与 P0 冲突时，停止修改，说明冲突、影响与可选方案。
3. **P1 约束原则上遵守**；确需突破时，在代码注释与最终报告中说明原因、影响范围、替代方案与验证方式。
4. **P2 约束可自主决定**；但不得以“P2 允许灵活”为由破坏整体一致性。
5. **业务规则只改一处**：修改参数时同步检查 `config.py`、`bookingRules.ts`、`mocks/rules.ts`、文档与测试。
6. **接口变更全链路**：后端 Schema → 前端 `types` → `api` → MSW → 测试 → 文档，缺一不可。
7. **数据库变更**：模型 + Alembic 迁移 + 兼容性验证 + 文档；不得改历史迁移。
8. **状态变更**：先确认来源状态、目标状态、槽位释放、审计与通知；并发路径必须考虑串行化。
9. **权限变更**：后端依赖 + 前端路由/按钮 + Mock 三者同时更新；不得只改前端。
10. **不要顺手扩大范围**：与任务无关的问题记录到报告或 §18，不在本轮强行重构。

### 16.3 完成后

1. **自检约束**：逐条核对本次改动是否违反 P0；是否破坏了已实现的 P1；是否让文档与代码脱节。
2. **执行验证**：
   - 前端：`npm run type-check`；涉及构建/发布：`npm run build`。
   - 后端：相关 `pytest`；涉及核心业务：完整回归。
   - 数据库：`alembic current`、`alembic heads`、`alembic check`。
3. **区分结果**：明确写出“已编写 / 已运行 / 通过 / 未执行 / 环境不具备”，不得把未执行写成通过。
4. **更新文档**：接口、参数、迁移、页面、启动方式变化时，同步更新本文相关条目与项目文档。
5. **报告遗留**：未完成、未验证、需用户确认的事项必须列出。

### 16.4 必须停下来询问用户的情况

仅在以下情况暂停并询问，不要把所有工程决策推回用户：

1. 业务规则存在多种合理解释，且不同选择导致不同业务结果。
2. 需求与已定稿规则或本文 P0 明显冲突。
3. 需要破坏性数据库操作（删表、清库、不可逆迁移）。
4. 需要整体更换技术栈或大规模架构迁移。
5. 需要改变已有 API 兼容约定且无法平滑处理。
6. 涉及重要权限、安全或个人信息边界的变化。
7. 需要用户提供当前环境无法推断的关键资料（如生产域名、证书、真实密钥策略）。

### 16.5 AI 的技术自主权

- 架构约束负责**划定边界**，不负责规定每一行代码怎么写。
- 在不违反 P0、不破坏 P1 的前提下，AI 可以自主选择：组件拆分方式、Composable 组织、查询写法、索引策略、错误提示措辞、局部重构、测试组织。
- 不得因为“用户没逐字要求”就拒绝合理的关联修复；也不得因为“可以自主”就无限扩大改动。
- 若现有架构本身存在缺陷，不应为了遵守旧架构而维护错误设计；应提出修正方案，按 §17 走变更流程。

### 16.6 建议的交付报告结构

```text
1. 改动内容（新增/修改/删除文件，涉及模块）
2. 实现说明（方案、取舍、关键业务处理、接口/数据库影响、新依赖）
3. 约束自检（本次涉及的 ARC 条目，是否违反 P0/P1）
4. 测试结果（实际命令与输出；未执行项明确标注）
5. 手工验证（操作步骤与预期结果）
6. 遗留问题（未完成、未验证、需确认）
```

---

## 17. 架构变更与决策管理

### 17.1 何时需要走架构变更流程

以下任一情况必须走变更流程，而不是在普通任务中直接改：

- 新增或删除分层（如引入 Repository、事件总线、CQRS）。
- 替换核心框架、数据库、ORM、认证方案、调度方案。
- 修改数据库核心表结构、枚举字面量、迁移链策略。
- 修改 API 版本策略、错误结构、分页结构，或做破坏性字段变更。
- 修改权限矩阵、角色定义、数据隔离边界。
- 修改预约/违约/黑名单/投诉的核心状态机或并发策略。
- 引入缓存、消息队列、外部服务、文件存储。
- 改变部署形态（多 worker、容器、独立调度进程）。

### 17.2 变更前的影响分析清单

1. **业务影响**：哪些需求/规则/状态机受影响？是否需要产品确认？
2. **前后端影响**：哪些页面、Composable、API、类型、Mock 需要同步？
3. **数据库影响**：表结构、索引、约束、迁移、历史数据兼容、回滚方案。
4. **接口影响**：路径、方法、字段、类型、错误码、分页；是否向后兼容。
5. **权限与安全影响**：角色、数据范围、PII、密钥、审计。
6. **并发与事务影响**：锁、唯一约束、事务边界、幂等、重试。
7. **性能影响**：查询量、索引、聚合位置、轮询频率、数据增长。
8. **测试影响**：需要新增/修改哪些单元、接口、并发、回归测试。
9. **部署与运维影响**：环境变量、启动命令、调度器、备份、回滚。
10. **文档影响**：本文、`AGENTS.md`、README、数据库说明、前端说明、API 文档。

### 17.3 ADR 模板

建议在 `docs/architecture/adr/` 下按 `ADR-YYYYMMDD-短标题.md` 保存：

```markdown
# ADR-YYYYMMDD 标题

## 状态
提议 / 已接受 / 已废弃 / 被替代

## 背景
当前问题、约束、触发原因。

## 备选方案
方案 A / B / C，各自的成本、风险、兼容性。

## 决策
选择哪个方案，为什么。

## 影响
- 业务：
- 前后端：
- 数据库与迁移：
- 接口兼容：
- 安全与权限：
- 性能：
- 测试：
- 部署：

## 迁移与回滚
步骤、验证方式、失败回退。

## 验证结果
实际执行的命令与结果；未执行项。

## 相关约束
ARC-xxx、需求编号、相关文件。
```

### 17.4 文档同步矩阵

| 变更类型 | 必须同步更新 |
|---|---|
| 新增/修改接口 | 后端 Schema、前端 `types`/`api`、MSW、测试、本文 §9/附录 D、`frontend/docs/前端实现说明.md` |
| 修改业务参数 | `config.py`、`bookingRules.ts`、`mocks/rules.ts`、相关测试、本文 §11、需求对照说明 |
| 修改数据库 | 模型、Alembic 迁移、`docs/数据库表结构说明.md`、本文 §8、测试 |
| 修改权限 | `dependencies.py`、`router/index.ts`、`menu.ts`、Mock、测试、本文 §10 |
| 修改状态机 | 对应 Service、测试、本文附录 C、需求对照 |
| 修改部署方式 | `start.bat`、`backend/README.md`、`docs/系统使用说明.md`、本文 §3.5/ARC-008 |
| 修改技术栈 | `AGENTS.md` §4、本文 §2.2/ARC-004、依赖清单、ADR |

### 17.5 复核节奏

- 每个里程碑（如完成一个业务模块）复核一次本文与代码的一致性。
- 每次数据库迁移后复核 §8 与附录 D。
- 每次权限或状态机变更后复核 §10/§11 与附录 C。
- 发现文档与代码不一致时，先记录到 §18，再决定“改代码”还是“改文档”，不得静默二选一。

---

## 18. 当前架构问题与待解决事项

> 本节记录**已识别但本轮不修复**的问题。它们不是“合理架构”，而是需要后续排期处理的风险。优先级按对业务正确性、安全性、可维护性的影响排序。

### 18.1 问题清单

| 编号 | 优先级 | 问题 | 证据 | 建议 | 本轮状态 |
|---|---|---|---|---|---|
| I-01 | P1 | Mock 管理员权限与真实后端不一致：Mock 允许“系统管理员”调用业务接口，后端 `require_admin` 只允许“自习室管理员” | `frontend/src/mocks/http.ts:91-94`；`backend/app/core/dependencies.py:70-86` | 将 Mock 的 `requireAdmin` 收紧为仅“自习室管理员”，与 ARC-051 一致 | 未修复 |
| I-02 | P1 | Mock 的 401/403 响应体为 `{detail}`，真实后端统一为 `{code, message}` | `frontend/src/mocks/http.ts:40-43`；`backend/app/core/exceptions.py:38-50` | 统一 Mock 的错误体；前端可同时兼容，但契约应以真实后端为准 | 未修复 |
| I-03 | P1 | 业务参数/规则在三处重复：`config.py`、`bookingRules.ts`、`mocks/rules.ts`；5 分钟调整后文档仍有 30 分钟表述 | 三处定义；`frontend/docs/前端实现说明.md` §5.1 | 参数变更时建立检查清单；长期考虑由后端下发配置或生成共享常量 | 未修复 |
| I-04 | P1 | 文档漂移：迁移 head、页面数量、粒度、角色枚举、数据库类型与实际代码不一致 | `docs/数据库表结构说明.md` 顶部写 `f2a3b4c5d6e7`；前端说明写 30 分钟 / PostgreSQL / 教师用户；根 README 写 17 页 | 以代码为准逐项修订；每轮迁移/页面变更后同步 | 未修复 |
| I-05 | P1 | `frontend/dist/` 被 Git 跟踪 67 个文件，但 `.gitignore` 已忽略该目录；工作区存在大量 dist 修改/删除 | `git ls-files frontend/dist`；`git status` | 单独提交清理：`git rm -r --cached frontend/dist`，确认构建流程后再删除；不得在本轮混入业务改动 | 未处理 |
| I-06 | P1 | 无 CI 配置；前端无自动化测试（无 Vitest/E2E）；后端有 17 个测试文件但本轮未执行 | 仓库无 `.github/`；`frontend/package.json` 无 test 脚本 | 先补前端关键规则单测与后端回归脚本；再考虑 CI | 未处理 |
| I-07 | P1 | 时区假设隐式：应用使用 naive `datetime.now()`，调度器固定 `Asia/Shanghai`；若服务器时区不是 UTC+8，签到/违约/统计会偏移 | `backend/app/utils/time_utils.py`；`backend/app/tasks/scheduler.py:9` | 部署文档明确要求 `TZ=Asia/Shanghai`；长期考虑统一 UTC 存储与显式转换（需 ADR） | 未处理 |
| I-08 | **P0** | 并发状态流转未串行化：签到、强制取消、手动违约、自动违约/完成之间可能同时通过来源状态校验，最后写入者覆盖前者，出现“状态与槽位/审计不一致” | `attendance_service.check_in` 使用 `db.get`；`reservation_service.force_cancel` 使用 `db.get`；`violation_service.register_manual` 使用 `db.get`；均未 `with_for_update()` 或条件 `UPDATE` | 对关键状态更新使用 `SELECT ... FOR UPDATE` 或 `UPDATE ... WHERE status = 期望值`；补充并发测试；这是 ARC-040 的落地任务 | **未修复，最高优先级** |
| I-09 | P1 | `violation_service._apply` 依赖 `(reservation_id, type)` 唯一约束做幂等，但未捕获并发插入的 `IntegrityError`；极端并发下可能返回 500 | `violation_service.py:109-143`；模型唯一约束 | 捕获 `IntegrityError` 后查询并返回已有记录；或对预约行加锁 | 未处理 |
| I-10 | P1 | `create_reservation` 的重试只识别 SQLite 的 `locked/busy` 文案；MySQL 死锁（1213）与锁等待超时（1205）不会被重试 | `reservation_service.py:101-111` | 识别 MySQL 错误码并有限重试；或依赖唯一约束返回 409；需并发验证 | 未处理 |
| I-11 | P2 | 看板趋势查询把满足条件的预约全部加载到 Python 再按日去重，且查询未限制时间范围；数据增长后变慢 | `dashboard_service.get_trend`：`select(Reservation).where(check_in_time.is_not(None) | check_out_time.is_not(None))`，无日期条件 | 在 SQL 中按时间范围过滤并聚合；避免全量加载 | 未处理 |
| I-12 | P2 | `GET /dashboard/seat-usage` 根据 `group_by` 返回两种完全不同的数组，`response_model` 为联合类型，前端需要两个函数分别断言 | `dashboard.py:47-66`；`api/dashboard.ts` | 拆分为两个端点或统一信封；至少在文档中明确两种形态 | 未处理 |
| I-13 | P2 | `rooms.open_time/close_time` 使用 `VARCHAR(5)` 存 `HH:MM`，没有数据库格式 CHECK；脏数据只能靠 `_parse_room_time` 在运行时抛 500 | `models/room.py:29-30`；`availability_service._parse_room_time` | 增加格式校验/迁移为 `TIME`；至少在新写入路径做严格校验 | 未处理 |
| I-14 | P2 | 前端 JWT 存在 Web Storage，缺少 HttpOnly/CSRF/刷新机制；生产环境存在 XSS 盗令牌风险 | `frontend/src/stores/auth.ts`；`request.ts` | 课程演示可接受；上线前评估 HttpOnly Cookie + CSRF 或短期令牌方案 | 待确认 |
| I-15 | P2 | 看板占用率分母使用“全部座位数”，而 FR-052 座位总数口径为“可用座位数”；两者是否应一致未确认 | `dashboard_service.get_seat_usage_by_slot` 使用 `len(seats)`；需求 FR-052 | 由产品确认分母口径；确认后统一实现与文案 | 待确认 |
| I-16 | P2 | 管理端无站内消息页；学生端评价入口在“我的预约”弹窗，无独立页面 | `router/index.ts`；`frontend/docs/前端实现说明.md` §4.2 | 属于当前范围决策，不是缺陷；若产品要求再补 | 已知 |

### 18.2 需进一步验证的事项

以下内容无法仅凭代码与现有文档确认，**不得当作既定事实**：

1. **I-08 并发缺陷的可复现性**：需要在 MySQL（非 SQLite）下用两个并发请求验证；SQLite 的锁行为与 MySQL 不同，现有测试未必能暴露。
2. **I-10 MySQL 死锁/锁等待的实际触发条件**：需要压测或故障注入。
3. **生产部署形态**：是否使用多 worker、反向代理、HTTPS、容器；当前仓库没有配置。
4. **看板占用率分母**：`len(seats)` 还是“可用座位数”，需产品确认（I-15）。
5. **投诉内容长度上限**：需求未规定，后端 1000、学生端界面 500，需统一。
6. **管理端是否需要站内消息**：当前产品范围未包含，需确认是否纳入后续。
7. **数据库目标版本**：团队标准 MySQL 8.4 LTS，本地实际 9.6.0；生产以哪个为准需确认。
8. **时区策略**：是否长期保持 naive local + Asia/Shanghai，还是改为 UTC 存储。

### 18.3 本轮未做的验证

- 未执行 `pytest`、`npm run build`、`alembic heads/current/check`。
- 未启动 MySQL 与前后端做人工联调。
- 未做并发复现、压测、故障注入。
- 未清理 `frontend/dist` 的 Git 跟踪。
- 未修改任何业务代码。

---

## 19. 附录

### 附录 A：术语

| 术语 | 含义 |
|---|---|
| 有效预约 | 状态为“待使用”或“使用中”的预约单；占用时段 |
| 终态 | 已取消、已完成、已违约；不占用未来时段 |
| 槽位（Slot） | `reservation_slots` 中每 5 分钟一行，用于唯一约束与占用表达 |
| 资源状态 | 座位自身的“可用 / 维修中 / 停用” |
| 时段占用 | 某座位在某 `[s, e)` 是否被有效预约覆盖的派生结论 |
| C1～C6 | 预约创建的判定项：资源、房间、冲突、用户冲突、资格、参数 |
| 幂等键 | 客户端为一次预约意图生成的唯一键，用于重复提交去重 |
| 两阶段关闭 | 先预览影响清单，再带指纹确认执行 |
| 镜像 | 前端/Mock 为展示而复制的后端规则，非权威 |
| ADR | Architecture Decision Record，架构决策记录 |

### 附录 B：关键文件索引

**后端：**

| 主题 | 文件 |
|---|---|
| 应用入口 / CORS / 异常 | `backend/app/main.py` |
| 配置与业务参数 | `backend/app/core/config.py` |
| 数据库与 Session | `backend/app/core/database.py` |
| JWT / 密码 | `backend/app/core/security.py` |
| 认证与角色依赖 | `backend/app/core/dependencies.py` |
| 业务异常与统一响应 | `backend/app/core/exceptions.py` |
| 路由汇总 | `backend/app/api/router.py`、`backend/app/api/v1/` |
| 预约创建与取消 | `backend/app/services/reservation_service.py` |
| 可预约性与 C1～C6 | `backend/app/services/availability_service.py` |
| 签到签退 | `backend/app/services/attendance_service.py` |
| 违约与阈值 | `backend/app/services/violation_service.py`、`blacklist_service.py` |
| 自习室与关闭 | `backend/app/services/room_service.py` |
| 座位状态与冲突 | `backend/app/services/seat_service.py` |
| 看板统计 | `backend/app/services/dashboard_service.py` |
| 通知 | `backend/app/services/notification_service.py`、`message_service.py` |
| 调度器 | `backend/app/tasks/scheduler.py` |
| 自动任务 | `backend/app/tasks/auto_violation.py`、`auto_end_reservation.py`、`blacklist_expiry.py`、`complaint_auto_close.py` |
| 时间工具 | `backend/app/utils/time_utils.py` |
| 脱敏 | `backend/app/utils/masking.py` |
| 模型与枚举 | `backend/app/models/` |
| 迁移 | `backend/alembic/versions/` |
| 测试基座 | `backend/tests/conftest.py` |

**前端：**

| 主题 | 文件 |
|---|---|
| 入口 / Mock 开关 | `frontend/src/main.ts` |
| 路由与角色守卫 | `frontend/src/router/index.ts` |
| 认证 store | `frontend/src/stores/auth.ts` |
| 消息 store | `frontend/src/stores/message.ts` |
| Axios 封装 | `frontend/src/api/request.ts` |
| 接口声明 | `frontend/src/api/*.ts` |
| 类型契约 | `frontend/src/types/index.ts` |
| 选座状态机 | `frontend/src/utils/useSeatBooking.ts` |
| 前端规则镜像 | `frontend/src/utils/bookingRules.ts` |
| 我的预约 | `frontend/src/utils/useMyReservations.ts` |
| 看板轮询 | `frontend/src/utils/useDashboard.ts` |
| 场地关闭 | `frontend/src/utils/useRoomClose.ts` |
| 脱敏兜底 | `frontend/src/utils/mask.ts` |
| 设计 token | `frontend/src/assets/styles/index.scss` |
| 图表主题 | `frontend/src/utils/chartTheme.ts` |
| Mock 基座 | `frontend/src/mocks/http.ts`、`db.ts`、`rules.ts` |
| Mock handler | `frontend/src/mocks/handlers/` |
| 构建配置 | `frontend/vite.config.ts` |
| 环境变量 | `frontend/.env.development`、`.env.example` |

### 附录 C：状态机

#### C.1 预约单（`Reservation.status`）

```text
待使用 ──签到（窗口内）──────────────→ 使用中
  │                                      │
  │                                      ├──签退────────────→ 已完成
  │                                      ├──到结束时间自动结束→ 已完成
  │                                      └──管理员手动违约──→ 已违约
  │
  ├──学生取消（开始前 ≥30 分钟）───────→ 已取消
  ├──管理员强制取消（待使用，必填原因）→ 已取消
  └──超过开始后 15 分钟未签到（自动）──→ 已违约

终态：已取消 / 已完成 / 已违约（不得再流转）
```

#### C.2 投诉（`Complaint.status`）

```text
待处理 ──受理──→ 处理中 ──录入处理结果──→ 已处理 ──投诉人确认/超时──→ 已关闭
   │
   └──驳回──→ 已驳回（终态）

已关闭、已驳回为终态。
```

#### C.3 账户与黑名单

```text
正常 ←──限制解除/自动到期── 受限
  │                          │
  └──管理员停用──→ 停用 ←────┘（管理员停用受限账户）
                    │
                    └──管理员恢复（无有效黑名单）──→ 正常

自动限制：到期由定时任务解除；
手动限制：到期不自动解除，必须管理员显式解除。
```

### 附录 D：API 一览（按模块）

> 前缀统一为 `/api/v1`。权限列：公开 / 登录 / 学生 / 管理员 / 系统管理员。

| 模块 | 方法与路径 | 权限 | 说明 |
|---|---|---|---|
| 认证 | `POST /auth/register` | 公开（受注册策略） | 学生自助注册 |
| 认证 | `POST /auth/login` | 公开 | 登录，失败锁定 |
| 认证 | `GET /auth/me` | 登录 | 当前用户 |
| 用户 | `GET /users/me` | 登录 | 本人资料 |
| 用户 | `PATCH /users/me` | 登录 | 修改联系方式 |
| 用户 | `PATCH /users/me/password` | 登录 | 改密，旧令牌失效 |
| 用户 | `GET /users` | 管理员 | 用户列表，联系方式脱敏 |
| 用户 | `PATCH /users/{id}/account-status` | 管理员 | 停用/恢复 |
| 自习室 | `GET /rooms` | 登录 | 列表（有界） |
| 自习室 | `POST /rooms` | 管理员 | 新建 |
| 自习室 | `PATCH /rooms/{id}` | 管理员 | 修改 |
| 自习室 | `DELETE /rooms/{id}` | 管理员 | 仅无预约历史 |
| 自习室 | `GET/POST /rooms/{id}/areas` | 登录/管理员 | 分区 |
| 自习室 | `GET /rooms/{id}/close-preview` | 管理员 | 关闭影响清单 |
| 自习室 | `POST /rooms/{id}/close` | 管理员 | 两阶段关闭 |
| 自习室 | `GET /rooms/{id}/closures` | 登录 | 未结束关闭记录 |
| 自习室 | `DELETE /rooms/{id}/closures/{cid}` | 管理员 | 提前解除 |
| 座位 | `GET /rooms/{room_id}/seats` | 登录 | 座位列表 |
| 座位 | `GET /seats/occupancy` | 管理员 | 资源状态与占用 |
| 座位 | `GET /seats/conflicts` | 管理员 | 调整冲突清单 |
| 座位 | `POST /seats` | 管理员 | 新增 |
| 座位 | `PATCH /seats/status` | 管理员 | 批量调整 |
| 座位 | `PATCH /seats/{id}/status` | 管理员 | 单座位调整 |
| 预约 | `POST /reservations` | 学生 | 创建，幂等 |
| 预约 | `GET /reservations/me` | 登录 | 本人预约 |
| 预约 | `GET /reservations/me/status-counts` | 登录 | 状态计数 |
| 预约 | `GET /reservations/available-seats` | 登录 | 可约座位 |
| 预约 | `GET /reservations` | 管理员 | 全部预约 |
| 预约 | `GET /reservations/{id}` | 管理员 | 详情 |
| 预约 | `POST /reservations/{id}/cancel` | 学生 | 本人取消 |
| 预约 | `POST /reservations/{id}/force-cancel` | 管理员 | 强制取消 |
| 签到 | `POST /reservations/{id}/check-in` | 学生 | 签到 |
| 签到 | `POST /reservations/{id}/check-out` | 学生 | 签退 |
| 违约 | `GET /violations/me` | 登录 | 本人违约 |
| 违约 | `GET /violations` | 管理员 | 全部违约 |
| 违约 | `POST /violations/manual` | 管理员 | 手动登记 |
| 评价 | `POST /reviews` | 学生 | 提交评价 |
| 评价 | `GET /reviews/me` | 登录 | 本人评价 |
| 评价 | `GET /reviews` | 管理员 | 全部评价（只读） |
| 投诉 | `POST /complaints` | 学生 | 提交 |
| 投诉 | `GET /complaints/me` | 登录 | 本人投诉 |
| 投诉 | `GET /complaints` | 管理员 | 全部投诉 |
| 投诉 | `PATCH /complaints/{id}` | 管理员 | 受理/处理/驳回 |
| 投诉 | `POST /complaints/{id}/confirm` | 学生 | 投诉人确认关闭 |
| 黑名单 | `GET /blacklist` | 管理员 | 记录 |
| 黑名单 | `POST /blacklist` | 管理员 | 手动加入 |
| 黑名单 | `POST /blacklist/{id}/release` | 管理员 | 解除 |
| 审计 | `GET /audit-logs` | 管理员 | 只读 |
| 看板 | `GET /dashboard/overview` | 管理员 | 五项概览 |
| 看板 | `GET /dashboard/seat-usage` | 管理员 | 座位/时段占用 |
| 看板 | `GET /dashboard/trend` | 管理员 | 趋势 |
| 看板 | `GET /dashboard/violation-top` | 管理员 | 违约 Top N |
| 消息 | `GET /messages/me` | 登录 | 本人消息 |
| 消息 | `GET /messages/unread-count` | 登录 | 未读数 |
| 消息 | `POST /messages/{id}/read` | 登录 | 标记已读 |
| 系统 | `GET /health` | 公开 | 健康检查 |

### 附录 E：约束与验证方式映射

| 验证目标 | 建议命令/操作 |
|---|---|
| 前端类型契约 | `cd frontend && npm run type-check` |
| 前端构建 | `cd frontend && npm run build`（会写 dist，注意工作区） |
| 后端核心回归 | `cd backend && pytest tests/` |
| 并发与幂等 | `backend/tests/test_concurrency.py`、`test_blocking_fixes.py`，另需 MySQL 并发复现 |
| 迁移状态 | `cd backend && alembic current && alembic heads && alembic check` |
| 权限隔离 | 三种角色令牌直接调用关键接口 |
| PII 脱敏 | 管理员请求 `/users` 检查联系方式字段 |
| Mock 契约 | `VITE_USE_MOCK=true` 与 `false` 各跑关键流程，对比响应 |
| 看板口径 | 固定数据构造 FR-052 验收用例，核对五项数值 |
| 场地关闭 | 预览后新增冲突，验证旧指纹返回 409 |
| 自动任务幂等 | 固定时间重复调用任务函数，核对记录数 |

### 附录 F：待确认事项汇总

1. 生产部署形态与是否多 worker（影响 ARC-008）。
2. 生产环境 HTTPS、域名、CORS 来源（影响 ARC-058）。
3. 看板占用率分母口径（I-15）。
4. 投诉内容长度上限（后端 1000 / 前端 500）。
5. 管理端是否需要站内消息页。
6. 数据库目标版本（8.4 LTS vs 本地 9.6）。
7. 时区长期策略（naive local + Asia/Shanghai vs UTC）。
8. 前端令牌存储是否改为 HttpOnly Cookie（ARC-059）。

---

## 文档自检声明

- 本文的架构事实来自 2026-11-12 对仓库代码的静态阅读，引用的文件路径、类名、函数名均已核对存在。
- 本文明确区分了 ✅ 已实现、◐ 部分实现、○ 目标、？ 待确认；未把计划写成已完成。
- 本轮实际执行的检查：`cd frontend && npm run type-check`（通过）。
- 本轮未执行：`pytest`、`npm run build`、`alembic` 命令、前后端联调、并发复现。
- 本轮未修改任何业务代码、数据库结构、接口或前端页面；仅新增本文件。
- 若后续代码与本文不一致，以“代码 + 需求 + `AGENTS.md`”重新核对，并按 §17 更新本文，不得静默删除约束。
