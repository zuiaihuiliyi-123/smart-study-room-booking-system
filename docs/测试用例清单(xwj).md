# 智慧自习室预约与管理系统 · 测试用例（单元与集成回归，xwj）

- 版本：v1.2
- 日期：2026-11-26
- 依据：《智慧自习室预约与管理系统-需求规格说明书（课程结构版）》V2.2、《测试用例清单-阶段2》的用例设计与裁决口径；代码基线 `main` @ `a0c94ec`
- 性质：**测试用例设计基线**。本清单先按业务模块与规则定义用例，每条包含前置条件、步骤与预期断言；`docs/测试报告(xwj).md` 以本清单的用例组为执行对象，给出执行结果与统计。
- 范围：后端 185 条 + 前端 78 条 = **263 条**。白盒补充的 86 条不属于本清单，作为覆盖缺口补强在 §8.3 与 §9 引用。

---

## 0. 文档说明

### 0.1 目的与定位

本清单是《测试报告(xwj)》的**用例基线**：先定义要验证什么、如何验证、预期是什么，报告再按同一批用例给出执行结果。用例按业务模块组织，不依赖具体实现文件，便于：

1. 评审时从用例出发核对业务规则是否被完整覆盖；
2. 执行失败时按用例 ID 定位到验证目标与自动化实现；
3. 新增需求或缺陷修复时，先补用例、再执行、最后更新报告统计。

### 0.2 用例与报告的关系

用例先行、报告在后：本清单定义 263 条用例；报告按用例组执行，给出通过数、覆盖率、缺陷与结论。对应关系如下。

| 本清单章节 | 报告章节 | 对应内容 |
| --- | --- | --- |
| §1 公共约定 | §2 测试范围与策略 | 测试基座、数据隔离、代号与优先级 |
| §2 用例统计 | §4 执行统计 | 用例数、分组与执行入口 |
| §3 后端新增用例（11） | §3.4 新增用例执行结果 | UT-RL、UT-RS 的执行结果 |
| §4 前端新增用例（13） | §3.4 新增用例执行结果 | UT-SM、UT-AU 的执行结果 |
| §5 后端 QA 集成（37） | §4.1 后端执行分布 | TC-QA-* 的执行结果 |
| §6 后端 API/业务回归（137） | §4.1 后端执行分布 | TC-API-*、TC-REG、TC-HARD、TC-BFX、TC-BOOT、TC-CONC、TC-HLT、TC-RES、TC-FLOW、TC-GOV、UT-TIME |
| §7 前端回归（65） | §4.2 前端执行分布 | UT-BR、UT-AU-R、UT-LINK、UT-FMT、UT-MASK、UT-WD、UT-MSG |
| §8.2 风险追溯 | §5.1 缺陷统计、§5.2 风险与建议 | 历史缺陷的回归用例 |
| §8.3 模块追溯 | §5 覆盖率 | 低覆盖模块对应的用例与缺口 |
| §9 未覆盖范围 | §5.2 风险与建议 | 待补用例（不计入 263） |
| §10 执行与判定 | §8 复现命令 | 执行命令、三层断言与出口准则 |

说明：报告 §3.4 的 24 条新增用例与本清单使用相同的 ID（UT-RL-01…、UT-RS-01…、UT-SM-01…、UT-AU-01…）。其余 239 条既有回归用例的 ID 由本清单统一分配（见 §1.4）；表中“自动化实现”一列用于回归执行时的代码定位，不作为用例设计依据。

### 0.3 统计口径

| 范围 | 后端 | 前端 | 合计 | 说明 |
| --- | ---: | ---: | ---: | --- |
| 既有回归 | 174 | 65 | 239 | 报告 §0、§2.1 口径：后端含 QA 37 条；前端含 auth store 既有 6 条 |
| 本轮新增 | 11 | 13 | 24 | 报告 §3.4 逐条列出 |
| **本清单合计** | **185** | **78** | **263** | 与报告 §3.1 通过数一致 |
| 白盒补充（不在本清单） | 86 | — | 86 | 报告 §0 复核：合并后后端 271、前端 78，合计 349 |
| 仓库全量（2026-11-26 复核） | 271 | 78 | 349 | 白盒用例见 `backend/tests/whitebox/` |

> 后端 185 = QA 集成 37 + 其余既有 137 + 本轮新增 11；前端 78 = 既有 65 + 本轮新增 13。QA 套件是全量子集，不重复计数。
>
> 本清单只定义用例与预期；每条用例的通过/失败结果集中记录在《测试报告(xwj)》§3–§4。

### 0.4 复现限制与环境

1. **未提交文件**：报告 §5.2 第 7 条指出，新增的 4 个测试文件当时未提交 Git：`backend/tests/test_rate_limit_service.py`、`backend/tests/test_reservation_state.py`、`frontend/src/utils/__tests__/seatMapLayout.test.ts`、修改过的 `frontend/src/stores/__tests__/auth.test.ts`。未提交前，185 / 78 只能在本机复现；团队基线为 174 / 65。
2. **覆盖率工具版本**：报告环境为 pytest-cov 7.1.0，而 `backend/requirements.txt` 限定 `pytest-cov>=6.0,<7.0`。逐位复现覆盖率小数前需统一版本（见报告 §5.2 第 6 条）。
3. **数据库边界**：本清单 263 条均基于 SQLite（内存或文件型），不验证 MySQL 时间精度、唯一约束错误码与迁移；MySQL 并发与迁移由《测试报告-阶段4》§8.5 单独验证。
4. **未执行项**：Playwright E2E、真实 APScheduler 调度、多 worker 限流共享不在本清单执行范围（见 §9）。

---

## 1. 公共测试基座与约定

### 1.1 后端基座

| 项目 | 约定 |
| --- | --- |
| 用例框架 | pytest 8.4.2 + FastAPI `TestClient` |
| 数据库夹具 | `db`：每用例独立内存 SQLite（`sqlite://` + `StaticPool`），建表后注入 session，用例结束关闭并销毁 |
| 接口夹具 | `api_client`：覆盖 `get_db` 依赖，真实经过路由、服务层与 ORM；不启动真实 MySQL |
| 数据工厂 | `make_user`、`make_room`、`make_area`、`make_seat`、`make_reservation`；默认学生 `S0001`、默认房间开放 08:00–22:00 |
| 调度器 | `settings.scheduler_enabled = False`，避免后台任务连接真实数据库 |
| 时间控制 | 通过 `monkeypatch` 替换 `time_utils.now()`；各文件固定时刻不同（见 §1.3） |
| 通知隔离 | 多数用例把 `notification_service.notify_safe` 替换为空操作；需要验证通知次数时改为收集器 |
| 并发基座 | 文件型 SQLite + WAL + `busy_timeout=5000`，每线程独立 session；设置 `QA_DATABASE_URL` 时切换真实 MySQL 并每用例重建表 |

### 1.2 前端基座

| 项目 | 约定 |
| --- | --- |
| 用例框架 | Vitest 2.1.9 + happy-dom |
| API 隔离 | `vi.mock('@/api/...')` 替换网络层，断言调用参数与次数 |
| 存储隔离 | 每个用例前 `localStorage.clear()`、`sessionStorage.clear()`；Pinia 每用例重建 |
| 时间控制 | `vi.useFakeTimers()` + `vi.setSystemTime()`（format、bookingRules 的日期用例） |
| 覆盖范围 | `vitest.config.ts` 的 `coverage.include` 含 7 个文件；`seatMapLayout.ts` 未在 include 内，报告 §4.2 用 CLI 单独统计 |

### 1.3 代号与关键数据

| 代号 | 含义 |
| --- | --- |
| `NOW` | 各用例组的固定当前时刻：QA 边界/状态为 2026-11-24 10:00；API 流程/看板为 2026-11-02 10:00；登录锁定为 2026-11-06 10:00；限流单元为 2026-11-25 10:30:42；前端日期为 2026-11-12 |
| `D0 / D1 / D7 / D8` | 相对 `NOW` 的当天 / 次日 / 第 7 天 / 第 8 天 |
| `R1 / E1..En` | 启用中的自习室 / 其下座位；座位默认状态“可用” |
| `S1..Sn` | 正常学生，口令 `Ss123456`；管理员 `A0001`，口令 `Aa123456` |
| `key(n)` | 长度不少于 8 的幂等键，如 `qa-idem-0001` |
| `slot` | 5 分钟粒度槽位；14:00–16:00 对应 24 条 `reservation_slots` |

### 1.4 用例 ID 规则

| 前缀 | 含义 | 数量 | 自动化实现文件 |
| --- | --- | ---: | --- |
| `UT-RL-xx` | 限流服务单元 | 7 | `backend/tests/test_rate_limit_service.py`（新增） |
| `UT-RS-xx` | 预约状态条件更新单元 | 4 | `backend/tests/test_reservation_state.py`（新增） |
| `TC-QA-BND-xx` | QA 预约时间边界 | 15 | `backend/tests/qa/test_qa_boundaries.py` |
| `TC-QA-STS-xx` | QA 状态机、权限与安全 | 18 | `backend/tests/qa/test_qa_state_security.py` |
| `TC-QA-CONC-xx` | QA 并发与竞态 | 4 | `backend/tests/qa/test_qa_concurrency.py` |
| `TC-API-AUD-xx` | 审计日志接口 | 2 | `backend/tests/test_api_audit.py` |
| `TC-API-DASH-xx` | 看板违约 Top N | 2 | `backend/tests/test_api_dashboard_top.py` |
| `TC-API-FIX-xx` | 接口修复回归 | 6 | `backend/tests/test_api_fixes.py` |
| `TC-API-FLOW-xx` | HTTP 主流程 | 2 | `backend/tests/test_api_flow.py` |
| `TC-API-LOCK-xx` | 登录失败锁定 | 6 | `backend/tests/test_api_login_lock.py` |
| `TC-API-PWD-xx` | 自助改密 | 3 | `backend/tests/test_api_password.py` |
| `TC-API-P2-xx` | 第二阶段查询能力 | 6 | `backend/tests/test_api_phase2.py` |
| `TC-API-REV-xx` | 评价列表接口 | 2 | `backend/tests/test_api_reviews.py` |
| `TC-API-SKL-xx` | 接口骨架 | 5 | `backend/tests/test_api_skeleton.py` |
| `TC-REG-xx` | 学生注册 | 7 | `backend/tests/test_auth_register.py` |
| `TC-HARD-xx` | 数据层加固 | 7 | `backend/tests/test_backend_hardening.py` |
| `TC-BFX-xx` | 阻塞级修复回归 | 26 | `backend/tests/test_blocking_fixes.py` |
| `TC-BOOT-xx` | 启动脚本纯函数 | 8 | `backend/tests/test_bootstrap_db.py` |
| `TC-CONC-xx` | 并发预约 | 2 | `backend/tests/test_concurrency.py` |
| `TC-HLT-xx` | 健康检查 | 1 | `backend/tests/test_health.py` |
| `TC-RES-xx` | M1 资源管理（含参数化 2 组） | 16 | `backend/tests/test_m1_resource.py` |
| `TC-FLOW-xx` | M2/M3/M6/M7 服务流程 | 9 | `backend/tests/test_m2_m3_flow.py` |
| `TC-GOV-xx` | M5 治理 | 22 | `backend/tests/test_m5_governance.py` |
| `UT-TIME-xx` | 时间工具 | 5 | `backend/tests/test_time_utils.py` |
| `UT-SM-xx` | 座位图布局单元 | 10 | `frontend/src/utils/__tests__/seatMapLayout.test.ts`（新增） |
| `UT-AU-xx` | 认证 store 新增异常路径 | 3 | `frontend/src/stores/__tests__/auth.test.ts`（新增） |
| `UT-AU-Rx` | 认证 store 既有回归 | 6 | 同上（既有） |
| `UT-BR-xx` | 预约规则前端工具 | 24 | `frontend/src/utils/__tests__/bookingRules.test.ts` |
| `UT-LINK-xx` | 消息关联跳转 | 8 | `frontend/src/utils/__tests__/messageLinks.test.ts` |
| `UT-FMT-xx` | 日期格式化 | 7 | `frontend/src/utils/__tests__/format.test.ts` |
| `UT-MASK-xx` | 联系方式掩码 | 7 | `frontend/src/utils/__tests__/mask.test.ts` |
| `UT-WD-xx` | 投诉工作日 SLA | 7 | `frontend/src/utils/__tests__/workday.test.ts` |
| `UT-MSG-xx` | 消息 store | 6 | `frontend/src/stores/__tests__/message.test.ts` |

### 1.5 类型与优先级判据

| 字段 | 取值 | 判据 |
| --- | --- | --- |
| 类型 | 单元 / 集成 / 并发 / 安全 / 边界 / 幂等 / 状态机 / 配置 / 展示 | 按用例主要验证手段归类；状态机类用例也属于集成 |
| P0 | 数据一致性、越权、并发终态、凭据与令牌安全 | 失败会污染后续业务数据或造成安全暴露，阻断发布 |
| P1 | 核心业务规则、主流程、可回滚的安全边界 | 失败影响功能正确性，可由管理操作或修复回滚 |
| P2 | 输入校验、展示文案、配置、可维护性 | 失败不直接产生错误业务结果 |

> 优先级为本清单的**建议执行级别**，不是报告结论；报告中未出现 P0/P1/P2 缺陷，指的是已执行范围内的结果。

---

## 2. 用例统计

### 2.1 总表

| 用例组 | 执行入口 | 用例数 | 明细章节 |
| --- | --- | ---: | --- |
| 后端全量（排除白盒） | `pytest --ignore=tests/whitebox` | 185 | §3、§5、§6 |
| 其中 QA 集成 | `pytest tests/qa` | 37 | §5 |
| 前端全量 | `npm test` | 78 | §4、§7 |
| 合计 | — | **263** | — |
| 白盒（参考，不在本清单） | `pytest tests/whitebox` | 86 | §8.3、§9 |

### 2.2 后端分布（24 文件，185 条）

| 文件 | 用例数 | 层级 | 本清单 ID |
| --- | ---: | --- | --- |
| `tests/qa/test_qa_boundaries.py` | 15 | 集成 | TC-QA-BND-01…15 |
| `tests/qa/test_qa_state_security.py` | 18 | 集成 | TC-QA-STS-01…18 |
| `tests/qa/test_qa_concurrency.py` | 4 | 集成（并发） | TC-QA-CONC-01…04 |
| `tests/test_api_audit.py` | 2 | 集成 | TC-API-AUD-01…02 |
| `tests/test_api_dashboard_top.py` | 2 | 集成 | TC-API-DASH-01…02 |
| `tests/test_api_fixes.py` | 6 | 集成 | TC-API-FIX-01…06 |
| `tests/test_api_flow.py` | 2 | 集成 | TC-API-FLOW-01…02 |
| `tests/test_api_login_lock.py` | 6 | 集成 | TC-API-LOCK-01…06 |
| `tests/test_api_password.py` | 3 | 集成 | TC-API-PWD-01…03 |
| `tests/test_api_phase2.py` | 6 | 集成 | TC-API-P2-01…06 |
| `tests/test_api_reviews.py` | 2 | 集成 | TC-API-REV-01…02 |
| `tests/test_api_skeleton.py` | 5 | 集成 | TC-API-SKL-01…05 |
| `tests/test_auth_register.py` | 7 | 集成 | TC-REG-01…07 |
| `tests/test_backend_hardening.py` | 7 | 单元（含 1 条接口缓存） | TC-HARD-01…07 |
| `tests/test_blocking_fixes.py` | 26 | 集成（含服务层直调） | TC-BFX-01…26 |
| `tests/test_bootstrap_db.py` | 8 | 单元 | TC-BOOT-01…08 |
| `tests/test_concurrency.py` | 2 | 集成（并发） | TC-CONC-01…02 |
| `tests/test_health.py` | 1 | 集成 | TC-HLT-01 |
| `tests/test_m1_resource.py` | 16 | 单元（服务层） | TC-RES-01…16（04、05 为同一参数化函数的两组） |
| `tests/test_m2_m3_flow.py` | 9 | 单元（服务层） | TC-FLOW-01…09 |
| `tests/test_m5_governance.py` | 22 | 单元（服务层） | TC-GOV-01…22 |
| `tests/test_rate_limit_service.py` | 7 | 单元 | UT-RL-01…07（新增） |
| `tests/test_reservation_state.py` | 4 | 单元 | UT-RS-01…04（新增） |
| `tests/test_time_utils.py` | 5 | 单元 | UT-TIME-01…05 |

### 2.3 前端分布（8 文件，78 条）

| 文件 | 用例数 | 层级 | 本清单 ID |
| --- | ---: | --- | --- |
| `src/utils/__tests__/bookingRules.test.ts` | 24 | 单元 | UT-BR-01…24 |
| `src/utils/__tests__/seatMapLayout.test.ts` | 10 | 单元 | UT-SM-01…10（新增） |
| `src/stores/__tests__/auth.test.ts` | 9 | 单元（store） | UT-AU-01…03（新增）+ UT-AU-R1…R6（既有） |
| `src/utils/__tests__/messageLinks.test.ts` | 8 | 单元 | UT-LINK-01…08 |
| `src/utils/__tests__/format.test.ts` | 7 | 单元 | UT-FMT-01…07 |
| `src/utils/__tests__/mask.test.ts` | 7 | 单元 | UT-MASK-01…07 |
| `src/utils/__tests__/workday.test.ts` | 7 | 单元 | UT-WD-01…07 |
| `src/stores/__tests__/message.test.ts` | 6 | 单元（store） | UT-MSG-01…06 |

### 2.4 按测试层级汇总

| 层级 | 用例组 | 用例数 | 执行入口 |
| --- | --- | ---: | --- |
| 后端单元/服务层 | UT-RL、UT-RS、UT-TIME、TC-RES、TC-FLOW、TC-GOV、TC-BOOT、TC-HARD | 78 | 直接调用 service/工具函数 + 内存 SQLite |
| 后端集成 | TC-QA-*、TC-API-*、TC-REG、TC-BFX、TC-CONC、TC-HLT | 107 | FastAPI TestClient + 覆盖 `get_db`；并发用文件型 SQLite |
| 前端单元（含 store） | UT-BR、UT-SM、UT-AU、UT-AU-R、UT-LINK、UT-FMT、UT-MASK、UT-WD、UT-MSG | 78 | Vitest + happy-dom + mock API |
| **合计** | — | **263** | — |

> 层级按用例的主要执行方式归类；`test_backend_hardening.py` 含 1 条接口缓存用例、`test_blocking_fixes.py` 含服务层直调用例，按主导方式分别归入单元与集成。各层级、各文件的通过/失败结果见《测试报告(xwj)》§3。

---

## 3. 后端新增用例（11 条）

文件：`backend/tests/test_rate_limit_service.py`、`backend/tests/test_reservation_state.py`。以下 ID 与报告 §3.4 完全一致。

### 3.1 限流固定窗口（UT-RL）

#### UT-RL-01 首次命中建桶并整分钟对齐

- 类型 / 优先级：单元 / P1
- 前置：内存库无 `rate_limit_buckets` 记录；固定 `NOW=2026-11-25 10:30:42`；`scope=login`、`key=192.0.2.10`、`limit=3`、`window_seconds=60`。
- 步骤：调用 `rate_limit_service.hit(db, scope, key, limit, window_seconds, now)` 一次。
- 预期：返回 `1`；桶表仅 1 行；该行 `scope=login`、`key=192.0.2.10`、`window_start=2026-11-25 10:30:00`（向下对齐整分钟）、`hits=1`。
- 自动化实现：`test_first_hit_creates_bucket_aligned_to_minute`

#### UT-RL-02 窗口内累计且只保留一行

- 类型 / 优先级：单元 / P1
- 前置：同 UT-RL-01，库为空。
- 步骤：同一 `(scope, key, now)` 连续调用 `hit` 三次。
- 预期：三次返回依次为 `1、2、3`；桶表仍仅 1 行，`hits=3`。
- 自动化实现：`test_hits_accumulate_in_one_row_until_limit`

#### UT-RL-03 上限边界与 429 响应

- 类型 / 优先级：单元 / 安全 / P1
- 前置：同 UT-RL-01；`limit=3`；`NOW=10:30:42`（距窗口结束 18 秒）。
- 步骤：连续调用 `hit` 4 次，捕获第 4 次的异常。
- 预期：第 1–3 次放行；第 4 次抛 `BusinessError`：`code=RATE_LIMITED`、HTTP 429、消息“请求过于频繁，请稍后重试”、`details={"scope":"login","limit":3,"window_seconds":60}`、响应头 `Retry-After: 18`。
- 自动化实现：`test_hit_over_limit_raises_429_with_retry_after`

#### UT-RL-04 IP 与接口维度隔离

- 类型 / 优先级：单元 / 安全 / P1
- 前置：库为空；`limit=1`。
- 步骤：IP `192.0.2.10` 的 `login` 命中 2 次；IP `198.51.100.7` 的 `login` 命中 1 次；IP `192.0.2.10` 的 `register` 命中 1 次。
- 预期：第 2 次同 IP 同 scope 抛限流；其他 IP、其他 scope 均返回 `1`；桶表键集合恰为 `(login,192.0.2.10)`、`(login,198.51.100.7)`、`(register,192.0.2.10)`。
- 自动化实现：`test_limit_counts_are_isolated_by_ip_and_scope`

#### UT-RL-05 跨窗口重新计数

- 类型 / 优先级：单元 / 边界 / P2
- 前置：`NOW=10:30:42`，先连续命中 3 次。
- 步骤：将 `now` 推进到 `10:31:01` 再命中 1 次。
- 预期：新窗口返回 `1`；桶表 `window_start` 集合为 `{10:30:00, 10:31:00}`，旧窗口记录保留用于排查。
- 自动化实现：`test_counter_resets_in_next_window`

#### UT-RL-06 自定义 30 秒窗口对齐

- 类型 / 优先级：单元 / 边界 / P2
- 前置：库为空；`window_seconds=30`；`NOW=10:30:42`。
- 步骤：调用 `hit` 一次。
- 预期：返回 `1`；`window_start=10:30:30`（按窗口长度向下对齐）。
- 自动化实现：`test_custom_window_seconds_aligns_start`

#### UT-RL-07 过期窗口清理

- 类型 / 优先级：单元 / P2
- 前置：预置两条桶：`(login, 192.0.2.10)` 的窗口开始于 `NOW−2 天`、`hits=9`；`(login, 198.51.100.99)` 的窗口开始于 `NOW−1 小时`、`hits=4`。
- 步骤：调用 `hit` 一次触发清理。
- 预期：2 天前的桶被删除；1 小时前的桶保留；本次新桶 `(192.0.2.10, 10:30:00)` 存在。
- 自动化实现：`test_expired_windows_are_cleaned_up`

### 3.2 预约状态条件更新（UT-RS）

被测函数：`app/services/reservation_state.py::transition_if_status(db, reservation_id, expected_status, **values)`。

#### UT-RS-01 状态匹配时原子写入

- 类型 / 优先级：单元 / 状态机 / P0
- 前置：预约状态“待使用”；目标值：状态“已取消”、`cancel_time=2026-11-25 10:00`、原因“临时有事”。
- 步骤：以 `expected_status=待使用` 调用条件更新。
- 预期：返回 `True`；刷新后 `status=已取消`、`cancel_time` 与 `cancel_reason` 一并写入。
- 自动化实现：`test_transition_applies_values_when_status_matches`

#### UT-RS-02 状态不匹配不写入

- 类型 / 优先级：单元 / 状态机 / P0
- 前置：预约状态“已完成”。
- 步骤：以 `expected_status=待使用` 尝试转为“已取消”，原因传“不应写入”。
- 预期：返回 `False`；状态仍“已完成”；`cancel_reason` 仍为空，未被覆盖。
- 自动化实现：`test_transition_returns_false_and_keeps_row_on_status_mismatch`

#### UT-RS-03 重复流转仅首次成功

- 类型 / 优先级：单元 / 幂等 / P0
- 前置：预约“待使用”。
- 步骤：连续两次执行“待使用 → 已取消”，原因分别为“第一次”“第二次”。
- 预期：返回 `True`、`False`；最终 `cancel_reason=第一次`，第二次不生效。
- 自动化实现：`test_second_transition_is_rejected`

#### UT-RS-04 不提交事务、可回滚

- 类型 / 优先级：单元 / 事务 / P0
- 前置：预约“待使用”。
- 步骤：执行条件更新；在当前事务内查询状态；执行 `rollback` 后再次查询。
- 预期：事务内可见“已取消”；回滚后恢复“待使用”且原因为空；证明函数不自行提交，事务边界由调用方控制。
- 自动化实现：`test_transition_does_not_commit_transaction`

---

## 4. 前端新增用例（13 条）

### 4.1 座位图布局（UT-SM）

文件：`frontend/src/utils/__tests__/seatMapLayout.test.ts`，被测函数 `buildSeatMapLayout(groups, areas?)`。以下 ID 与报告 §3.4 一致。

#### UT-SM-01 空输入返回默认布局

- 类型 / 优先级：单元 / P2
- 前置：无座位组，或传入一个 `cells=[]` 的空组。
- 步骤：调用 `buildSeatMapLayout([])` 与 `buildSeatMapLayout([空组])`。
- 预期：前者严格等于 `{width:760, height:580, zones:[], tables:[], chairs:[], hasWindow:false}`；后者 `chairs=[]`。
- 自动化实现：`没有可用座位时返回空布局与默认画布尺寸`

#### UT-SM-02 座位与椅子一一对应

- 类型 / 优先级：单元 / P1
- 前置：中央开放区 7 个座位。
- 步骤：构建布局，提取椅子上的座位 id 与桌子 id。
- 预期：椅子座位 id 排序后等于输入座位 id 列表；无重复；桌子 id 唯一。
- 自动化实现：`每个座位恰好生成一把椅子，桌子 id 唯一`

#### UT-SM-03 相同输入可复现

- 类型 / 优先级：单元 / P2
- 前置：窗边静区 6 个靠窗座位。
- 步骤：用同一输入连续构建两次。
- 预期：两次结果深度相等（坐标、桌号、分区完全一致）。
- 自动化实现：`相同输入重复构建结果完全一致（布局可复现）`

#### UT-SM-04 筛选不重排布局（回归）

- 类型 / 优先级：单元 / P1
- 前置：中央开放区 6 个座位；一组全部 `matched=true`，另一组 `matched` 交替为 true/false。
- 步骤：分别构建，比较几何信息（画布、分区、桌子、椅子坐标/尺寸/朝向、`hasWindow`）。
- 预期：几何信息完全一致；`matched` 只影响标记，不改变任何坐标。
- 自动化实现：`筛选标记不参与布局：命中与否不改变分区、桌子与椅子位置`

#### UT-SM-05 中央区 2 人桌拆分

- 类型 / 优先级：单元 / P1
- 前置：中央开放区 5 个座位。
- 步骤：构建布局，统计每张桌的椅子数。
- 预期：分区 `kind=central`；桌子 3 张；每桌椅子数不超过 2。
- 自动化实现：`中央开放区按 2 人一桌拆分，5 个座位得到 3 张桌`

#### UT-SM-06 桌号取座位号前缀

- 类型 / 优先级：单元 / P2
- 前置：中央开放区两个座位 `B-01`、`B-02`。
- 步骤：构建布局，读取桌子 `label`。
- 预期：桌号列表为 `["B1"]`。
- 自动化实现：`桌子编号取座位号前缀（B-01 → B1）`

#### UT-SM-07 分区名称推断与标签

- 类型 / 优先级：单元 / P1
- 前置：分区“窗边静区”（座位 `area_id=1`、`near_window=true`）与“电源长桌”（`area_id=2`、`has_power=true`）；传入 `Area[]`。
- 步骤：构建布局，读取分区类型与桌签。
- 预期：分区类型依次为 `window`、`power`；`hasWindow=true`；1 区每张桌 `tags` 含“窗”；2 区每张桌 `tags` 含“电”。
- 自动化实现：`按分区名称识别窗边/电源区，并补充对应标签`

#### UT-SM-08 属性推断与 hasWindow

- 类型 / 优先级：单元 / P1
- 前置：分区名为“A 区”，3 个座位中仅 1 个 `near_window=true`。
- 步骤：构建布局。
- 预期：分区类型推断为 `central`；只要任一靠窗座位存在，`hasWindow=true`。
- 自动化实现：`名称无线索时按座位属性推断；任一靠窗座位即标记 hasWindow`

#### UT-SM-09 窗边区 4 人桌拆分

- 类型 / 优先级：单元 / P1
- 前置：窗边静区 6 个靠窗座位。
- 步骤：构建布局。
- 预期：桌子 2 张；椅子 6 把（4+2 分配）。
- 自动化实现：`窗边区按 4 人一桌拆分`

#### UT-SM-10 桌椅不越出分区

- 类型 / 优先级：单元 / P1
- 前置：四分区：窗边 8 座、电源 4 座、静音 5 座、中央 7 座，均传 `Area[]`。
- 步骤：对每张桌、每把椅，检查其 `x/y/w/h` 是否落在所属分区边界内。
- 预期：全部桌椅满足 `table.x ≥ zone.x`、`table.x+table.w ≤ zone.x+zone.w`（y 方向同理），容差 0.001；即四分区均无溢出。
- 自动化实现：`常规分区布局中桌椅都落在各自分区内`

### 4.2 认证 store 新增异常路径（UT-AU）

文件：`frontend/src/stores/__tests__/auth.test.ts`。以下 3 条为报告 §3.4 的新增用例；同文件既有 6 条见 §7.2。

#### UT-AU-01 登录失败不落盘凭据

- 类型 / 优先级：单元 / 安全 / P1
- 前置：mock `authApi.login` 为 reject（“登录失败”）；两种 storage 为空。
- 步骤：调用 `store.login({student_no:'student', password:'wrong'}, true)`。
- 预期：Promise 抛出“登录失败”；`isLoggedIn=false`、`user=null`；`localStorage` 与 `sessionStorage` 均无 `ssr_token`。
- 自动化实现：`登录接口失败时不写入任何凭据`

#### UT-AU-02 登出接口失败仍本地登出

- 类型 / 优先级：单元 / 容错 / P1
- 前置：已登录（localStorage 中 token 为 `token-x`）；mock `authApi.logout` reject（“网络错误”）。
- 步骤：调用 `store.logout()`。
- 预期：Promise 正常 resolve（不抛错）；logout 以原 token 调用；`isLoggedIn=false`、`user=null`；两种 storage 中的 token/user 清空。
- 自动化实现：`登出接口失败时本地仍完成登出`

#### UT-AU-03 改密失败保留原令牌

- 类型 / 优先级：单元 / 安全 / P1
- 前置：localStorage 中 `ssr_token=keep-token`；mock `changePassword` reject（“旧密码错误”）。
- 步骤：调用 `store.changePassword({old_password:'bad', new_password:'newpass123'})`。
- 预期：Promise 抛出“旧密码错误”；`store.token` 仍为 `keep-token`；localStorage 中令牌未被清除，当前会话不被踢下线。
- 自动化实现：`修改密码失败时保留原令牌，不把当前用户踢下线`

---

## 5. 后端 QA 集成用例（37 条）

文件：`backend/tests/qa/`。固定 `NOW=2026-11-24 10:00`（`D0=11-24`、`D1=11-25`、`D7=12-01`、`D8=12-02`），通知统一置空。以下断言均为测试代码中的实际断言。

### 5.1 预约时间边界与规则（15 条，`test_qa_boundaries.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-QA-BND-01 | `test_cross_day_interval_rejected` | S1 对 E1 提交 D0 23:30–次日 01:00（`end_time=01:00`） | 422；`code=C6_BR-020`；`/reservations/me` 的 `total=0` | P1 |
| TC-QA-BND-02 | `test_zero_and_reversed_duration_rejected` | D1 14:00–14:00；D1 15:00–14:00 | 均 422；本人预约总数为 0 | P1 |
| TC-QA-BND-03 | `test_start_and_end_must_align_to_five_minutes` | D1 14:02–16:00；14:00–15:58；对照 14:05–15:55 | 前两条 422；14:05–15:55 返回 200 | P1 |
| TC-QA-BND-04 | `test_max_duration_four_hours` | D1 10:00–14:00（4h）；14:05–18:10（4h5m） | 4h 返回 200；4h5m 返回 422 | P1 |
| TC-QA-BND-05 | `test_advance_window_d7_allowed_d8_rejected` | D7 14:00–15:00；D8 14:00–15:00；D0 09:00–10:00（已过） | D7 200；D8 422；过去时段 422 | P1 |
| TC-QA-BND-06 | `test_start_must_be_strictly_after_now` | D0 10:00–11:00（等于 NOW）；10:05–11:05 | 10:00 起 422；10:05 起 200 | P1 |
| TC-QA-BND-07 | `test_room_open_hours_boundaries` | D1 07:55–08:05；08:00–09:00；21:55–22:00；21:55–22:05 | 07:55 起 409 `C2`；两个贴边时段 200；22:05 结束 409 `C2` | P1 |
| TC-QA-BND-08 | `test_half_open_adjacent_intervals_allowed` | S1 先占 E1 的 D1 14:00–16:00；S2 再约 15:00–17:00；16:00–17:00 | 首条 200；重叠 409 `C3_BR-006`；相邻 16:00 起 200 | P1 |
| TC-QA-BND-09 | `test_same_user_overlap_rejected_but_adjacent_allowed` | S1 同日先占 E1 14:00–16:00，再约 E2 15:00–17:00；16:00–17:00 | 重叠 409 `C4_BR-005`；相邻 200 | P1 |
| TC-QA-BND-10 | `test_daily_limit_two_and_cancel_releases_quota` | D1 依次约 3 个不重叠时段；取消第 1 条后再约第 3 条时段 | 前两条 200；第 3 条 422 `C6_BR-004`；取消后重约 200 | P1 |
| TC-QA-BND-11 | `test_seat_and_room_resource_states_block_booking` | 维修中座位、停用座位、停用自习室下的座位各约一次 | 维修中 409 `C1_BR-017`；停用座位 409；停用房间内座位 409 | P1 |
| TC-QA-BND-12 | `test_restricted_and_disabled_accounts` | 停用账户登录；受限账户预约 | 登录 403；预约 403 | P1 |
| TC-QA-BND-13 | `test_idempotent_replay_and_key_reuse` | 同座位同时段同 key 提交 2 次；同 key 换时段；7 位短 key | 前两次返回同一 id；换时段 409 `IDEMPOTENCY_KEY_REUSED`；短 key 422；本人预约总数 1 | P1 |
| TC-QA-BND-14 | `test_available_seats_excludes_occupied_and_releases_after_cancel` | S1 占 E1 的 D1 14:00–16:00；S2 查可用座位；取消后再查 | 占用时结果不含 E1；取消后结果含 E1 | P1 |
| TC-QA-BND-15 | `test_registration_ignores_role_field` | 注册体额外携带 `role=自习室管理员` | 201；`/auth/me` 返回角色仍为“学生用户”（不提升权限） | P0 |

### 5.2 状态机、权限与安全（18 条，`test_qa_state_security.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-QA-STS-01 | `test_cancel_deadline_is_strict` | D1 14:00 预约；NOW=13:29 取消一条，13:30 取消另一条 | 13:29 返回 200；13:30 返回 422 `ST-029` | P1 |
| TC-QA-STS-02 | `test_checkin_window_left_and_right_edges` | 三条 D1 14:00–16:00 预约；分别在 13:44、13:45、14:14、14:15 签到 | 13:44 与 14:15 均 422 `ST-027`；13:45 与 14:14 均 200 | P1 |
| TC-QA-STS-03 | `test_checkout_completes_and_releases_slots` | 预约“使用中”，预置 1 条槽位；NOW=15:00 签退 | 200；状态“已完成”；`check_out_time=15:00`；该预约槽位数为 0 | P1 |
| TC-QA-STS-04 | `test_auto_violation_boundary_and_idempotency` | 预约 14:00–16:00；14:14、14:15、14:16 分别执行自动违约；预置槽位 | 14:14 返回 None 且状态不变；14:15 生成记录；14:16 返回同一记录 id；累计违约 1；记录 1 条；槽位 0 条 | P1 |
| TC-QA-STS-05 | `test_manual_violation_requires_in_use_and_reason` | 管理员对“使用中”预约先提交空原因，再提交“长时间占座” | 空原因 422；正常登记 200，`operator_id` 非空；状态“已违约”；累计 +1 | P1 |
| TC-QA-STS-06 | `test_third_violation_restricts_account` | 学生已有 2 次违约与 2 条历史记录；管理员登记第 3 次 | 200；`violation_count=3`；账户“受限”；存在未解除的自动黑名单记录 | P1 |
| TC-QA-STS-07 | `test_auto_restriction_expiry_resets_violation_count` | 受限学生累计 3；自动限制 `expire_at=NOW−1min`；执行 `release_expired` | 返回 1；账户恢复“正常”；`violation_count=0`（裁决 D1） | P1 |
| TC-QA-STS-08 | `test_student_cross_user_and_vertical_permissions` | S2 取消 S1 预约；S2 访问用户列表、审计、看板、黑名单 | 跨用户取消 403；四个管理接口均 403 | P0 |
| TC-QA-STS-09 | `test_admin_cannot_book_and_contacts_are_masked` | 管理员预约座位；管理员查询用户列表（学生联系方式为明文手机号） | 预约 403；列表 200，联系方式脱敏且含 `****`，不等于原手机号 | P0 |
| TC-QA-STS-10 | `test_password_change_invalidates_old_token` | 学生改密（旧 Ss123456 → 新 Ss654321）；用旧令牌与新令牌访问 `/auth/me` | 改密 200；旧令牌 401；新令牌 200 | P0 |
| TC-QA-STS-11 | `test_tampered_token_rejected` | 取合法 JWT，篡改末 2 位后访问 `/auth/me` | 401 | P0 |
| TC-QA-STS-12 | `test_logout_must_invalidate_token` | 登录后调用 `/auth/logout`，再用原令牌访问 `/auth/me` | 登出 200；原令牌立即 401 | P0 |
| TC-QA-STS-13 | `test_login_rate_limit` | 同一客户端连续 11 次正确登录；再请求一次读取响应头 | 第 11 次 429；响应含 `Retry-After` | P0 |
| TC-QA-STS-14 | `test_student_message_isolation` | S2 有一条未读消息；S1 调用该消息的已读接口 | 403 或 404；S2 消息 `is_read` 仍为 false | P0 |
| TC-QA-STS-15 | `test_complaint_state_machine_and_owner_confirm` | 学生投诉座位；管理员直接置“已处理”；再依次“处理中”“已处理”；S2 确认；S1 确认 | 创建 201；直接置已处理 409；两步处理均 200；非本人确认 403；本人确认 200 且状态“已关闭” | P1 |
| TC-QA-STS-16 | `test_available_seats_rejects_out_of_window_date` | 固定 NOW 后查询 D8 的可用座位 | 422（裁决 D2 只接受今日至 D+7） | P1 |
| TC-QA-STS-17 | `test_available_seats_rejects_misaligned_time` | 查询 D1 14:02–15:00 的可用座位 | 422（起止须 5 分钟对齐） | P1 |
| TC-QA-STS-18 | `test_docs_disabled_in_production` | `app_env=production` 创建应用；再切 `development` 创建应用 | 生产：`docs_url`、`openapi_url`、`redoc_url` 均为 None；开发：`docs_url=/docs` | P2 |

### 5.3 并发与竞态（4 条，`test_qa_concurrency.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-QA-CONC-01 | `test_same_idempotency_key_concurrently_sends_one_success_message` | 5 线程同用户、同座位、同 14:00–16:00、同幂等键；在幂等查询处用 Barrier 强制交错；收集“预约成功”消息 | 预约表仅 1 条；成功返回的 id 集合大小为 1；“预约成功”消息恰好 1 条 | P0 |
| TC-QA-CONC-02 | `test_checkin_vs_force_cancel_race` | 预约“待使用”、10:00–12:00、NOW 在签到窗口内；签到线程与管理员强制取消线程并发；第一次读取处强制交错 | 不出现矛盾终态：不得“使用中 + cancel_time”，也不得“已取消 + check_in_time” | P0 |
| TC-QA-CONC-03 | `test_close_room_vs_new_reservation_race` | 关闭窗口 D1 14:00–16:00 与同窗口新预约并发；在 `_affected` 读取清单后强制交错；SQLite 与 MySQL 两个分支 | 关闭生效后窗口内有效预约数必须为 0；关闭要么成功，要么返回 409 `CONFLICT_LIST_CHANGED`；MySQL 分支额外要求关闭成功后新预约被 `ROOM_CLOSED` 拒绝 | P0 |
| TC-QA-CONC-04 | `test_concurrent_manual_blacklist_only_one_active` | 两个管理员并发对同一学生加入手动限制；在有效限制查询处用 Barrier 强制交错 | 库中 `released_at IS NULL` 的记录恰好 1 条 | P0 |

---

## 6. 后端 API 与业务回归用例（137 条）

以下为既有回归用例的设计明细。每条用例有独立 ID；“自动化实现”列仅用于执行时定位代码，用例的验证目标与预期不依赖具体实现。

### 6.1 审计日志接口（2 条，`test_api_audit.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-API-AUD-01 | `test_audit_logs_filters_and_pagination` | 预置 4 条审计（房间修改、座位批量、越权、登录失败）；管理员登录后再查全量、按动作、按操作人、按目标、按日期、分页 | 全量 `total=5` 且首条为本次 `LOGIN_SUCCESS`；按动作 `ROOM_UPDATE` 1 条；按操作人 3 条；按目标 `SEAT` 1 条；日期区间 2 条；分页 1 条但 total=5 | P2 |
| TC-API-AUD-02 | `test_audit_logs_require_admin` | 学生登录后查询 `/audit-logs` | 403 | P1 |

### 6.2 看板违约 Top N（2 条，`test_api_dashboard_top.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-API-DASH-01 | `test_violation_top_aggregates_users_and_limits` | 甲 3 条（11-01/02/03）、乙 2 条（11-02/03）、丙 1 条（11-30 区间外）；查询 11-01–11-05、limit=2；再查 11-02 单日；最后 limit=0 | 首次 `total_records=5`，items 依次为甲（3）、乙（2），姓名与学号正确；单日 `total_records=2` 且各 1；limit=0 返回 422 | P1 |
| TC-API-DASH-02 | `test_violation_top_requires_admin` | 学生查询违约 Top N | 403 | P1 |

### 6.3 接口修复回归（6 条，`test_api_fixes.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-API-FIX-01 | `test_admin_cannot_create_reservation_or_complaint` | 管理员提交预约与投诉 | 均 403 | P0 |
| TC-API-FIX-02 | `test_complaint_owner_confirms_close_over_http` | 学生投诉自习室；管理员依次“处理中”“已处理”；管理员直接改“已关闭”；学生确认 | 创建 201；两步处理 200；管理员关闭 409；学生确认 200 且状态“已关闭” | P1 |
| TC-API-FIX-03 | `test_auth_me_exposes_restrict_until_for_auto_restriction` | 学生违约次数达到阈值，调用 `restrict_if_threshold` 创建自动限制；查询 `/auth/me` | 200；`account_status=受限`；`restrict_until` 非空 | P1 |
| TC-API-FIX-04 | `test_room_close_rejects_area_from_another_room` | 对房间 A 提交关闭，`area_id` 属于房间 B | 404，不创建关闭记录 | P1 |
| TC-API-FIX-05 | `test_login_is_audited_and_queryable_by_admin` | 学生与管理员各登录一次；管理员查询 `LOGIN_SUCCESS`；学生再查审计 | 管理员查询 `total≥2` 且含学生操作人；学生查询 403 | P1 |
| TC-API-FIX-06 | `test_messages_unread_count_endpoint` | 给学生写入 1 条系统通知；查询未读数 | 200；响应严格等于 `{"count":1}` | P2 |

### 6.4 HTTP 主流程（2 条，`test_api_flow.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-API-FLOW-01 | `test_student_reservation_flow_over_http` | 学生创建 D1 14:00–16:00 预约；查我的预约、可用座位、看板、消息 | 创建 200；我的预约 `total=1`；该时段可用座位为空列表；学生访问看板 403；消息 `total=0`（测试中通知关闭） | P1 |
| TC-API-FLOW-02 | `test_admin_filters_and_resource_endpoints` | 管理员按房间与学号筛预约；查详情、座位占用、冲突、批量改维修、关闭预览、看板、30 分钟时段占用 | 预约筛选 `total=1`；详情 id 正确；占用 `occupied=true`；冲突含该预约；批量更新为“维修中”；预览含该预约；看板 `seat_total=0`；时段统计 7 行 | P1 |

### 6.5 登录失败锁定（6 条，`test_api_login_lock.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-API-LOCK-01 | `test_login_locks_after_threshold_and_blocks_correct_password` | 固定 NOW=2026-11-06 10:00；同一 IP 连续 5 次错误口令；第 6 次用正确口令 | 前 4 次 401；第 5 次 429 `ACCOUNT_LOCKED`；正确口令仍 429；计数行 `failed_count=5`、`locked_until=NOW+15min`；写 `LOGIN_LOCKED` 审计且原因含学号 | P1 |
| TC-API-LOCK-02 | `test_successful_login_resets_failure_counter` | 4 次失败后成功登录；再失败 1 次 | 成功 200；失败计数行清零；后续失败仍 401（不立即锁定） | P1 |
| TC-API-LOCK-03 | `test_lock_expires_and_allows_login_again` | 5 次失败触发锁定；时间推进 16 分钟后用正确口令登录 | 200；计数行清除 | P1 |
| TC-API-LOCK-04 | `test_unknown_student_no_is_locked_too` | 对不存在学号连续 5 次错误口令 | 第 5 次 429；库中存在该学号的锁定记录（避免用“是否锁定”枚举账号） | P1 |
| TC-API-LOCK-05 | `test_lockout_is_isolated_by_client_ip` | 攻击 IP 连续 5 次失败锁定；受害者从 `203.0.113.9` 用正确口令登录 | 攻击 IP 被 429；受害者 200；成功后该学号所有来源的失败计数清空（Q4-02 A） | P1 |
| TC-API-LOCK-06 | `test_cleanup_removes_only_expired_login_attempts` | 预置 31 天前与 1 天前的两条计数；执行清理 | 返回 1；仅保留 1 天前的记录（Q4-02 E，保留期 30 天） | P2 |

### 6.6 自助改密（3 条，`test_api_password.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-API-PWD-01 | `test_change_password_rotates_token_and_invalidates_old` | 登录持有旧令牌；旧密码改新密码；旧/新令牌访问；旧/新密码登录 | 改密 200 且返回新令牌；`token_version=1`；旧密码哈希失效、新密码可验证；旧令牌 401；新令牌 200；旧密码登录 401、新密码 200；写 `PASSWORD_CHANGED` 审计且目标为用户 | P0 |
| TC-API-PWD-02 | `test_change_password_rejects_wrong_old_and_same` | 旧密码错误；新旧密码相同 | 分别 400 `INVALID_OLD_PASSWORD`、400 `PASSWORD_UNCHANGED`；原密码仍有效；`token_version=0` | P1 |
| TC-API-PWD-03 | `test_change_password_validates_lengths` | 新密码 5 位；旧密码 5 位；新密码 8 个空格 | 均 422 | P2 |

### 6.7 第二阶段查询能力（6 条，`test_api_phase2.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-API-P2-01 | `test_messages_type_filter_and_pagination` | 学生 3 条消息（1 预约通知、2 违约通知）；查全部、按“违约通知”、page_size=1 | 全部 `total=3`；筛选 `total=2` 且类型一致；分页 1 条但筛选后 total=2 | P2 |
| TC-API-P2-02 | `test_messages_isolated_between_users` | 甲、乙各 1 条消息；甲查询 | `total=1` 且内容为甲的消息 | P0 |
| TC-API-P2-03 | `test_complaints_filter_by_submitter_and_keyword` | 甲 2 条、乙 1 条投诉；按 user_id、关键词“噪音”、组合条件查询 | 按提交人 2 条；关键词 1 条且内容含“噪音”；组合 1 条 | P2 |
| TC-API-P2-04 | `test_my_reservations_status_counts_grouped_and_filtered` | 甲 4 条不同状态、乙 1 条；查状态计数、日期区间、房间过滤 | 计数为待使用 1、使用中 0、已完成 1、已取消 1、已违约 1，total=4；日期筛选 total=1；房间筛选 total=1 且已违约 1；他人记录不计入 | P1 |
| TC-API-P2-05 | `test_disabled_account_returns_403_not_401` | 用正常签发的令牌访问，随后账户改“停用” | 403（不是 401），消息含“停用” | P1 |
| TC-API-P2-06 | `test_normal_account_can_read_me` | 正常账户查询 `/auth/me`（对照） | 200；学号正确 | P2 |

### 6.8 评价列表接口（2 条，`test_api_reviews.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-API-REV-01 | `test_admin_review_list_filters_by_score_and_date` | 预置 2 条评价（11-01 评分 5；11-05 评分 3）；查全量、分页、score=5、日期 11-04–11-05、score=6 | 全量 total=2 且按时间倒序为 [3,5]；分页 1 条 total=2；score=5 得 1 条；日期区间得评分 3；score=6 返回 422 | P2 |
| TC-API-REV-02 | `test_student_cannot_list_all_reviews` | 学生查询评价列表 | 403 | P1 |

### 6.9 接口骨架（5 条，`test_api_skeleton.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-API-SKL-01 | `test_openapi_contains_all_modules` | 读取 `/openapi.json` | paths 含登录、房间、预约、看板、消息五个入口 | P2 |
| TC-API-SKL-02 | `test_implemented_room_endpoint_requires_login` | 未登录访问 `/rooms` | 401（不允许匿名枚举） | P1 |
| TC-API-SKL-03 | `test_dashboard_overview_returns_zero_on_empty_db` | 空库直接调用 `get_overview` | 座位总数、使用中、今日预约、今日违约、受限账户均为 0（非 501） | P2 |
| TC-API-SKL-04 | `test_protected_endpoint_requires_login` | 未登录访问 `/reservations/me` | 401 | P1 |
| TC-API-SKL-05 | `test_login_payload_is_validated` | 登录提交空对象 | 422 | P2 |

### 6.10 学生注册（7 条，`test_auth_register.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-REG-01 | `test_register_creates_student_and_returns_usable_token` | 注册李四、学号 S20260001、口令 passw0rd123、联系方式手机号；用返回令牌查 `/auth/me` | 201 且返回令牌；用户角色“学生用户”、状态正常、违约 0、联系方式保留；口令以哈希存储且可验证；`/auth/me` 学号与角色正确；写 `REGISTER_SUCCESS` 审计 | P1 |
| TC-REG-02 | `test_register_rejects_duplicate_student_no` | 同一学号注册两次 | 第二次 409 `STUDENT_NO_TAKEN`；库中仅 1 个用户 | P1 |
| TC-REG-03 | `test_register_trims_identity_fields_and_blank_contact` | 学号前后带空格；联系方式为 3 个空格 | 201；学号已去空格；联系方式落库为 None | P2 |
| TC-REG-04 | `test_register_rejects_invalid_payload` | 口令 5 位、口令 8 空格、学号 S1、学号含中文、姓名 1 字 | 均 422 `VALIDATION_ERROR`；不创建用户 | P2 |
| TC-REG-05 | `test_register_can_be_closed` | 关闭 `registration_enabled` 后注册 | 403 `REGISTRATION_CLOSED`；不创建用户 | P1 |
| TC-REG-06 | `test_register_whitelist_blocks_unlisted_and_allows_listed` | 白名单仅 S20260010、S20260011；分别注册 S20260012 与 S20260011 | 前者 403 `STUDENT_NO_NOT_ALLOWED` 且不落库；后者 201 且落库 | P1 |
| TC-REG-07 | `test_register_defaults_contact_to_null` | 注册体不提供联系方式 | 201；联系方式为 None | P2 |

### 6.11 数据层加固（7 条，`test_backend_hardening.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-HARD-01 | `test_integrity_error_is_mapped_to_409` | 路由主动抛 `IntegrityError("duplicate")` | 409 `DATA_CONFLICT`；响应体不含底层 `duplicate` 细节 | P1 |
| TC-HARD-02 | `test_db_retry_retries_deadlock_and_rolls_back` | 前两次抛 MySQL 1213 死锁，第 3 次成功；`attempts=3` | 返回 ok；调用 3 次；回滚 2 次 | P1 |
| TC-HARD-03 | `test_db_retry_does_not_retry_sql_syntax_error` | 抛 1064 语法错误 | 原样抛出；仅调用 1 次、回滚 1 次（不重试非死锁错误） | P1 |
| TC-HARD-04 | `test_dashboard_overview_uses_short_cache` | 替换 `get_overview` 为计数器；连续请求看板两次 | 两次响应一致；底层函数只调用 1 次（命中 10 秒缓存） | P2 |
| TC-HARD-05 | `test_time_utils_uses_naive_shanghai_time` | 调用 `time_utils.now()` | 返回 `datetime` 且 `tzinfo is None`（统一无时区口径） | P2 |
| TC-HARD-06 | `test_transaction_helper_rolls_back_on_business_error` | `with transaction(db)` 内修改姓名后抛 `BusinessError` | 异常抛出后回滚，姓名保持原值 | P1 |
| TC-HARD-07 | `test_scheduled_task_retries_and_records_execution` | 任务函数首次抛错、第二次返回 7；`retries=2` | 返回 7；调用 2 次；`task_executions` 记录状态“成功”、`attempts=2`、`message="7"` | P1 |

### 6.12 阻塞级修复回归（26 条，`test_blocking_fixes.py`）

固定 `NOW=2026-11-02 10:00`，通知置空。

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-BFX-01 | `test_mask_contact_phone_and_email` | 掩码手机号、邮箱、None、空串 | 手机号 `138****1234`；邮箱 `s******@zju.edu.cn`；空值 `—` | P1 |
| TC-BFX-02 | `test_list_users_masks_contact_for_admin` | 学生联系方式 13800001234；管理员查询用户列表 | 该学生 `contact=138****1234`；响应全文不含明文手机号 | P1 |
| TC-BFX-03 | `test_my_profile_keeps_raw_contact` | 学生查询 `/users/me` 与 `/auth/me` | 两处均返回原邮箱 `me@example.com`（本人可见原文） | P1 |
| TC-BFX-04 | `test_system_admin_rejected_from_business_endpoints` | 系统管理员登录后访问看板、用户列表 | 均 403（R-04 不进入业务管理接口） | P0 |
| TC-BFX-05 | `test_teacher_role_removed` | 检查 Role 枚举；直接写 `role=教师用户` | 枚举无“教师用户”且无 TEACHER；写库被 `ck_user_role` 拒绝（IntegrityError） | P1 |
| TC-BFX-06 | `test_business_admin_still_has_access` | 业务管理员访问看板 | 200（权限拆分不影响 R-02） | P1 |
| TC-BFX-07 | `test_trend_counts_transitions_not_created_at` | 构造“待使用”预约但未签到；查趋势；签到后再查 | 未签到时当日有效预约 0；签到后为 1（按状态流转计数，不按创建时间） | P2 |
| TC-BFX-08 | `test_trend_dedupes_same_day_checkin_and_checkout` | 同一预约当日签到又签退 | 趋势仍计 1（按预约单去重） | P2 |
| TC-BFX-09 | `test_trend_zero_day_has_no_breakpoint` | 查询 11-01 至 11-03 空数据区间 | 返回 3 个点，每点预约数与违约数均为 0（不断点） | P2 |
| TC-BFX-10 | `test_validate_security_rejects_placeholder` | JWT 密钥设为占位符 | 启动校验抛 `RuntimeError`，消息含“未配置” | P0 |
| TC-BFX-11 | `test_validate_security_rejects_short_key` | JWT 密钥设为 `short` | 抛 `RuntimeError`，消息含“长度不足” | P0 |
| TC-BFX-12 | `test_validate_security_accepts_valid_key` | JWT 密钥设为 40 个字符 | 校验通过，不抛异常 | P0 |
| TC-BFX-13 | `test_resource_read_endpoints_require_auth` | 未登录访问 `/rooms` 与 `/rooms/1/seats` | 均 401 | P1 |
| TC-BFX-14 | `test_resource_read_endpoints_accessible_after_login` | 学生登录后访问 `/rooms` | 200 且至少 1 条 | P2 |
| TC-BFX-15 | `test_login_failed_audited_for_wrong_password` | 学生错误口令登录 | 401；写 `LOGIN_FAILED` 审计且原因含学号 | P1 |
| TC-BFX-16 | `test_disable_and_restore_account` | 管理员停用学生；学生登录；管理员恢复；再登录 | 停用 200 且状态“停用”；登录 403；恢复 200 且“正常”；登录 200 | P1 |
| TC-BFX-17 | `test_disable_account_rejects_same_status` | 对“正常”账户再次设“正常” | 409 | P2 |
| TC-BFX-18 | `test_business_admin_cannot_disable_another_admin` | 业务管理员停用另一个管理员 | 403；目标仍“正常” | P0 |
| TC-BFX-19 | `test_business_admin_cannot_disable_system_admin` | 业务管理员停用系统管理员 | 403；目标仍“正常” | P0 |
| TC-BFX-20 | `test_business_admin_cannot_disable_self` | 业务管理员停用自己 | 403；自身仍“正常” | P0 |
| TC-BFX-21 | `test_account_status_rejects_restricted_value` | 通过账户状态接口直接设“受限” | 422；目标仍“正常”（受限只能由黑名单流程产生） | P1 |
| TC-BFX-22 | `test_business_admin_cannot_blacklist_admin` | 管理员把另一管理员加入黑名单 | 403；目标仍“正常” | P0 |
| TC-BFX-23 | `test_auto_violation_skips_non_student_reservation` | 管理员名下“待使用”预约；14:20 执行自动违约 | 返回 None；状态不变；违约计数 0；无违约记录 | P1 |
| TC-BFX-24 | `test_manual_violation_rejects_non_student_reservation` | 管理员对管理员名下“使用中”预约登记手动违约 | 抛错 409；状态仍“使用中”；计数 0 | P1 |
| TC-BFX-25 | `test_violation_stats_only_count_students` | 学生与管理员各 1 条违约记录；查 Top N 与看板 | Top N 仅“学生”；看板今日违约 1（不统计管理员历史数据） | P1 |
| TC-BFX-26 | `test_room_close_creates_window_without_disabling_seats` | 学生预约 11-03 14:00–16:00（窗口内）与 11-05（窗口外）；关闭 11-03 13:00–17:00、`cancel_affected=false` | `kept=1`、`notified_outside_window=0`；两条预约仍“待使用”；座位仍“可用”；生成关闭窗口记录且起止正确；窗口内预约收到 1 条通知 | P1 |

### 6.13 启动脚本纯函数（8 条，`test_bootstrap_db.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-BOOT-01 | `test_jwt_rotation_rules` | 传入空串、占位符、31 字符、32 字符、64 字符 | 前三个需轮换；32 与 64 字符不需要 | P2 |
| TC-BOOT-02 | `test_build_url_round_trips_special_characters` | 密码含 `@ : / ? # %` 等特殊字符 | 生成的 URL 可被 `make_url` 正确解析；驱动 mysql+pymysql；字符集 utf8mb4 | P2 |
| TC-BOOT-03 | `test_read_env_ignores_comments_and_strips_quotes` | .env 含注释、空行、单/双引号值、空值 | 注释被忽略；引号被剥离；空值保留为空串 | P2 |
| TC-BOOT-04 | `test_update_env_file_preserves_other_lines_and_backs_up` | .env 含注释与其他键；更新两个键 | 其他行保留；目标键更新；生成 `.env.bak` 且内容以原注释开头 | P2 |
| TC-BOOT-05 | `test_update_env_file_appends_missing_keys` | .env 只有 APP_NAME；追加 JWT_SECRET_KEY | 原键保留；缺失键追加成功 | P2 |
| TC-BOOT-06 | `test_parse_config_prefers_cli_over_env` | env 中 URL 指向 db.local:3307/prod；CLI 指定 127.0.0.1:3306/demo | 主机、端口、库名、用户取 CLI；密码沿用 env | P2 |
| TC-BOOT-07 | `test_parse_config_rejects_non_mysql_url` | DATABASE_URL 为 sqlite | 抛 `ConfigError` | P2 |
| TC-BOOT-08 | `test_provision_creates_database_and_both_hosts` | 用假连接执行库与用户创建 | 首条 SQL 创建库；两条 CREATE USER 分别为 localhost 与 127.0.0.1；用户名一致 | P2 |

### 6.14 并发预约（2 条，`test_concurrency.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-CONC-01 | `test_concurrent_same_seat_same_slot_only_one_succeeds` | 8 个学生、同一座位、D1 14:00–16:00、不同幂等键、8 线程并发 | 恰好 1 条成功、其余 7 条冲突；该座位该日有效预约 1 条；槽位 24 条 | P0 |
| TC-CONC-02 | `test_concurrent_same_user_same_slot_idempotent` | 同一用户、同一幂等键、5 线程并发 | 返回的成功预约 id 集合大小为 1（只产生 1 条预约单） | P0 |

### 6.15 健康检查（1 条，`test_health.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-HLT-01 | `test_health` | GET `/health` | 200；响应严格等于 `{"status":"ok"}` | P2 |

### 6.16 M1 资源管理（16 条，`test_m1_resource.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-RES-01 | `test_create_room_and_list_ordered` | 创建静学室、研修室；查询列表 | 按创建顺序返回两个房间 id | P2 |
| TC-RES-02 | `test_create_room_defaults_enabled` | 创建房间只给名称、位置、容量 | id 非空；`enabled=true`；开放时间默认 08:00 | P1 |
| TC-RES-03 | `test_create_room_duplicate_name_rejected` | 同名房间创建两次 | 409 `ROOM_NAME_DUPLICATED` | P1 |
| TC-RES-04 | `test_create_room_time_rules_rejected_by_schema`（参数组 1） | `open_time=22:00`、`close_time=08:00` 构造 `RoomCreate` | 抛 `ValidationError`（开放晚于关闭） | P2 |
| TC-RES-05 | `test_create_room_time_rules_rejected_by_schema`（参数组 2） | `open_time=8点`、`close_time=22:00` | 抛 `ValidationError`（非 HH:MM） | P2 |
| TC-RES-06 | `test_create_room_time_rules_defended_in_service` | 绕过 schema，服务层分别收到 22:00–08:00 与 `8点` | 分别 422 `ROOM_TIME_RANGE_INVALID`、422 `ROOM_TIME_FORMAT_INVALID` | P1 |
| TC-RES-07 | `test_create_area_duplicated_in_same_room` | 同房间创建同名分区两次 | `AREA_NAME_DUPLICATED` | P2 |
| TC-RES-08 | `test_create_area_room_not_found` | 对房间 999 创建分区 | 404 `ROOM_NOT_FOUND` | P2 |
| TC-RES-09 | `test_create_seat_default_available` | 创建带插座座位 | 状态“可用”；`has_power=true`（座位只存资源状态） | P1 |
| TC-RES-10 | `test_create_seat_number_must_be_unique_in_room` | 同房间同座位号创建两次 | `SEAT_NO_DUPLICATED` | P1 |
| TC-RES-11 | `test_create_seat_area_must_belong_to_room` | 在房间 A 建座位但引用房间 B 的分区 | `AREA_NOT_IN_ROOM` | P1 |
| TC-RES-12 | `test_seat_status_change_blocked_by_future_reservation` | 单座位接口改“维修中”，该座位有未来“待使用”预约 | 409 `SEAT_STATUS_CONFLICT`；座位仍“可用”（安全阀，引导走批量+预览） | P1 |
| TC-RES-13 | `test_seat_status_change_writes_audit` | 管理员改座位为维修中，原因“灯管损坏” | 状态变更；写 1 条 SEAT 审计，含操作人、前后值与原因 | P1 |
| TC-RES-14 | `test_seat_status_change_to_same_status_is_noop` | 对“可用”座位再设“可用” | 不写审计（审计数 0） | P2 |
| TC-RES-15 | `test_seat_status_can_be_restored_to_available` | 停用座位改为可用，原因“恢复开放” | 状态“可用” | P2 |
| TC-RES-16 | `test_seat_status_ignores_finished_reservations` | 该座位只有已完成的过去预约；改“维修中” | 允许变更，状态“维修中”（已完成不构成冲突） | P1 |

### 6.17 M2/M3/M6/M7 服务流程（9 条，`test_m2_m3_flow.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-FLOW-01 | `test_create_reservation_is_idempotent_and_materializes_slots` | 固定 NOW=2026-11-02 10:00；同 key 创建两次 D1 14:00–16:00 预约 | 两次返回同一 id；状态“待使用”；槽位 24 条 | P1 |
| TC-FLOW-02 | `test_create_reservation_accepts_5_minute_granularity` | 14:05–14:35（30 分钟）；14:06–14:36 | 前者成功且槽位 6 条；后者抛 422 `C6_BR-001` | P1 |
| TC-FLOW-03 | `test_available_seats_excludes_occupied_seat` | 房间内 busy 与 free 两座；busy 已被占；查询该时段可用座位 | 仅返回 free 座位 | P1 |
| TC-FLOW-04 | `test_cancel_releases_slot_and_allows_rebooking` | 创建预约后本人取消；查槽位；用新 key 重约 | 槽位 0 条；重约得到新 id（与原 id 不同） | P1 |
| TC-FLOW-05 | `test_check_in_and_check_out` | 14:00 签到；随后签退 | 签到后“使用中”且签到时间=固定时刻；签退后“已完成” | P1 |
| TC-FLOW-06 | `test_auto_violation_is_idempotent` | 14:20 连续执行自动违约两次 | 两次返回同一记录 id；违约记录 1 条；状态“已违约”；计数 1 | P1 |
| TC-FLOW-07 | `test_dashboard_and_messages` | 构造 1 条今日预约；查看板、时段占用、写 1 条通知并查消息、标记已读 | 看板 `seat_total=1`、`today_reservations=1`；时段统计 7 行且房间名正确；消息 total=1、未读 1；标记已读后未读 0 | P1 |
| TC-FLOW-08 | `test_room_close_preview_then_execute` | 预约 11-03 14:00–16:00；先预览关闭 13:00–17:00，再执行且 `cancel_affected=true` | 预览返回 1 个座位与 1 条受影响预约；执行后 `closed_seats=1`、`cancelled=1`；座位仍“可用”；生成关闭窗口；预约“已取消”；至少 1 条审计 | P1 |
| TC-FLOW-09 | `test_seat_occupancy_conflicts_and_batch` | 明日 14:00–16:00 预约；查 15:00–16:00 占用、14:30–15:30 冲突；批量改维修 | 占用 `occupied=true` 且预约 id 正确；冲突含该预约；批量后状态“维修中”且返回冲突清单 | P1 |

### 6.18 M5 用户与治理（22 条，`test_m5_governance.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| TC-GOV-01 | `test_update_my_profile_changes_contact_only` | 学生更新联系方式 | 联系方式更新；姓名与角色不变 | P2 |
| TC-GOV-02 | `test_list_users_pagination` | 3 个用户；第 1 页 2 条、第 2 页 2 条 | total=3；两页条数 2 与 1；首条第 1 个学号 | P2 |
| TC-GOV-03 | `test_review_requires_completed_reservation` | 对“待使用”预约提交评价 | 409 `REVIEW_NOT_ALLOWED` | P1 |
| TC-GOV-04 | `test_review_rejects_other_users_reservation` | 他人评价已完成预约 | 403 `REVIEW_NOT_OWNER` | P0 |
| TC-GOV-05 | `test_review_can_only_be_submitted_once` | 同一预约评价两次 | 第二次 `REVIEW_ALREADY_EXISTS` | P1 |
| TC-GOV-06 | `test_review_success` | 本人评价已完成预约，评分 5 | 创建成功；分页总数 1 | P1 |
| TC-GOV-07 | `test_complaint_target_must_exist` | 投诉不存在的座位 999 | 404 `COMPLAINT_TARGET_NOT_FOUND` | P2 |
| TC-GOV-08 | `test_complaint_state_machine_full_flow` | 创建投诉；尝试待处理→已处理；处理中→已处理；管理员关闭；他人确认；本人确认；终态再变更 | 创建“待处理”；跳步 409；两步处理成功且记录处理人/时间；管理员关闭 409；他人确认 `COMPLAINT_NOT_OWNER`；本人确认“已关闭”；终态再处理/再确认均 409；COMPLAINT 审计 3 条 | P1 |
| TC-GOV-09 | `test_complaint_rejects_blank_content_and_handle_note` | 投诉内容为空格；处理说明为空格 | 分别 422 `COMPLAINT_CONTENT_REQUIRED`、422 `COMPLAINT_NOTE_REQUIRED`；投诉仍“待处理” | P2 |
| TC-GOV-10 | `test_complaint_can_be_rejected` | 管理员将投诉置“已驳回”并填说明 | 状态“已驳回” | P1 |
| TC-GOV-11 | `test_close_stale_complaints` | 已处理投诉的处理时间推到关闭期限之前；执行自动关闭 | 关闭 1 条；状态“已关闭” | P1 |
| TC-GOV-12 | `test_close_stale_keeps_recently_resolved` | 刚处理完成的投诉；执行自动关闭 | 关闭 0 条 | P1 |
| TC-GOV-13 | `test_manual_blacklist_restricts_then_release_restores` | 管理员手动加入黑名单（3 天后到期）；再解除 | 记录模式“手动”；学生“受限”；解除后 `released_at` 与原因写入；学生“正常” | P1 |
| TC-GOV-14 | `test_blacklist_rejects_duplicate_active_entry` | 同一学生已有生效限制，再次加入 | 409 `BLACKLIST_ALREADY_ACTIVE` | P1 |
| TC-GOV-15 | `test_blacklist_expire_must_be_future` | 手动限制到期时间为昨天 | 422 `BLACKLIST_EXPIRE_INVALID` | P2 |
| TC-GOV-16 | `test_blacklist_release_twice_rejected` | 已解除的记录再次解除 | `BLACKLIST_ALREADY_RELEASED` | P2 |
| TC-GOV-17 | `test_threshold_auto_restriction_is_idempotent` | 违约次数达到阈值；调用两次 `restrict_if_threshold` | 首次返回“自动”限制且学生受限；第二次返回 None（不重复创建） | P1 |
| TC-GOV-18 | `test_threshold_not_reached_no_restriction` | 违约次数为阈值−1 | 返回 None；学生仍“正常” | P1 |
| TC-GOV-19 | `test_release_expired_skips_manual_entries` | 手动限制到期后推进时间执行 `release_expired` | 返回 0；记录未解除；学生仍“受限”（BR-010） | P1 |
| TC-GOV-20 | `test_expired_manual_entry_remains_active_until_released` | 手动限制过期后：执行释放、重复加入、自动限制；最后由管理员解除 | 释放 0；记录仍生效；重复加入 409；自动限制返回 None；管理员解除后恢复“正常”（ST-042） | P1 |
| TC-GOV-21 | `test_user_read_exposes_auto_restrict_until` | 自动限制与手动限制各 1 人；读取用户视图 | 自动限制 `restrict_until` 等于到期时间；手动限制 `restrict_until` 为 None 且状态“受限” | P1 |
| TC-GOV-22 | `test_release_expired_releases_auto_entries` | 自动限制到期后推进时间执行 | 释放 1 条；`released_at` 写入；学生“正常” | P1 |

### 6.19 时间工具（5 条，`test_time_utils.py`）

| ID | 自动化实现 | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| UT-TIME-01 | `test_adjacent_intervals_do_not_overlap` | 14:00–16:00 与 16:00–18:00 | 不重叠（左闭右开） | P2 |
| UT-TIME-02 | `test_partial_overlap_is_detected` | 14:00–16:00 与 15:00–17:00 | 判定重叠 | P2 |
| UT-TIME-03 | `test_granularity_alignment` | 14:00、14:05、14:30 对 5 分钟；14:01 对 5 分钟；14:15 对 30 分钟 | 前三个对齐；后两个不对齐 | P2 |
| UT-TIME-04 | `test_checkin_window` | 开始 2026-10-29 14:00，前后各 15 分钟 | 窗口 13:45–14:15 | P2 |
| UT-TIME-05 | `test_cancel_deadline` | 开始 14:00、提前 30 分钟；判断 13:29、13:30、13:31 | 仅 13:29 可取消；13:30 与 13:31 不可（边界为严格小于） | P2 |

---

## 7. 前端回归用例（65 条）

### 7.1 预约规则工具（24 条，`bookingRules.test.ts`）

| ID | 自动化实现（用例标题） | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| UT-BR-01 | `parseTimeToMinutes 接受合法时间，非法值返回 null` | 输入 00:00、08:05、` 8:05 `、24:00、08:60、空串、null | 前三个得 0、485、485；后四个为 null | P1 |
| UT-BR-02 | `minutesToTimeText 取整并夹在 0–24:00` | 输入 485、−1、1470、485.6 | 08:05、00:00、24:00、08:06 | P2 |
| UT-BR-03 | `shortTime / timeRangeText 统一裁剪秒` | 18:30:00、null、08:00:00–10:00:00 | 18:30、空串、08:00–10:00 | P2 |
| UT-BR-04 | `slotMinutes 与 durationText` | 08:00–10:30；10:00–08:00；150/120/45/0 分钟 | 150；−120；2 小时 30 分钟、2 小时、45 分钟、— | P2 |
| UT-BR-05 | `overlapsSlot 使用左闭右开口径` | 480–600 与 540–660、600–720、480–600 | true、false、false、true | P1 |
| UT-BR-06 | `timeOptions 按粒度生成闭区间候选` | 08:00–09:00、粒度 5 | 13 个候选；首 08:00；末 09:00 | P2 |
| UT-BR-07 | `ceilToStep 向上对齐` | 481 对 5；480 对 5；1 默认粒度 | 485、480、5 | P2 |
| UT-BR-08 | `bookingDateOptions 从今天起共 8 天，并带今天/明天前缀` | 固定 2026-11-12 10:00 | 8 个选项；首值 2026-11-12 且含“今天”；次项含“明天”；第三项 `11-14 周六` | P1 |
| UT-BR-09 | `todayIso / todayText / dayOffsetFromToday` | 固定 2026-11-12；偏移 11-13、11-12、11-11 | 2026-11-12；2026-11-12 周四；1、0、−1 | P2 |
| UT-BR-10 | `签到窗口为开始前 15 分钟至开始后 15 分钟` | 日期 2026-11-12、开始 10:00 | 开 09:45、关 10:15；范围文本 09:45–10:15；跨度 30 分钟 | P1 |
| UT-BR-11 | `countdownText 输出 mm:ss / HH:mm:ss / 00:00` | 65 秒、3665 秒、0、NaN | 01:05、01:01:05、00:00、00:00 | P2 |
| UT-BR-12 | `seatCellState 优先资源状态，其次临时关闭与占用` | 维修中、停用、临时关闭、可用且可约、被占、无可用数据 | fix、off、closed、free、taken、unknown（按优先级） | P1 |
| UT-BR-13 | `seatAriaLabel 同时交代资源状态与时段状态` | A-01、状态 free | “座位 A-01，资源状态可用，时段可约” | P2 |
| UT-BR-14 | `mySlotUsage 统计当日有效预约并找重叠项` | 4 条记录（含已取消、次日、重叠）；查询 11-12 10:00–12:00 | 当日有效计数 2；冲突 id=2；`userBlockReason` 返回 C4 | P1 |
| UT-BR-15 | `userBlockReason 在无冲突且达到每日上限时返回 C6` | 当日已有 2 条不重叠有效预约；查询 10:00–12:00 | 无冲突；计数 2；返回 C6 | P1 |
| UT-BR-16 | `isEffectiveReservation 只认待使用与使用中` | 五种状态 | 待使用/使用中 true；已完成/已取消/已违约 false | P1 |
| UT-BR-17 | `occupancyText 区分资源状态、临时关闭与占用` | 维修中、null 可用集合、可用、已占、临时关闭 | 含“暂无法判断”、含“可约”、含“已被预约”、“该时段临时关闭” | P2 |
| UT-BR-18 | `全部满足时六项都通过` | 标准上下文（座位可用、房间启用、可约、无冲突、账户正常、未超限） | 判定项依次 C1–C6，全部 pass | P1 |
| UT-BR-19 | `资源不可用 / 已关闭 / 已被占 / 本人冲突 / 账户受限分别对应 C1–C5` | 分别构造维修座位、停用房间、空可用集合、重叠预约 #9、受限账户 | C1/C2/C3/C4/C5 分别 fail；C1 场景 C3 为 unknown；C4 详情含 #9；C5 详情含“预计” | P1 |
| UT-BR-20 | `C6 覆盖已开始、超提前天数、超时长与每日上限` | 当前 10:30 预约 10:00 起；偏移 8 天；时长超 4 小时；当日达 2 条 | 四种场景 C6 均 fail；已开始提示含“已开始” | P1 |
| UT-BR-21 | `座位冲突归为 C3，且使用固定可读文案` | 409 `SEAT_CONFLICT` | kind=conflict；judgement=C3；消息“该时段已被预约，请重新选择” | P1 |
| UT-BR-22 | `账户受限保留预计解除时间` | 403 `ACCOUNT_RESTRICTED` + `restrict_until` | kind=restricted；C5；保留时间；文案格式 2026-11-20 10:00 | P1 |
| UT-BR-23 | `已开始时段归为 expired，并清理服务端提示里的需求编号` | 409 `TIME_STARTED`，消息含 ST-029 与“有效预约” | kind=expired；消息不含 ST-029 与“有效预约” | P2 |
| UT-BR-24 | `未知错误归为 rule 并保留 HTTP 状态` | 500 + `{detail:'服务异常'}` | kind=rule；code=HTTP_500；消息“服务异常” | P2 |

### 7.2 认证 store 既有回归（6 条，`auth.test.ts`）

| ID | 自动化实现（用例标题） | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| UT-AU-R1 | `勾选记住我时 token/user 写入 localStorage` | mock 登录成功（token-1）与 `/me`；`login(..., true)` | `isLoggedIn=true`；user 正确；localStorage 有 token 与用户；sessionStorage 无 token | P1 |
| UT-AU-R2 | `不记住我时 token/user 写入 sessionStorage` | 登录成功（token-2），不传记住我 | sessionStorage 有 token-2；localStorage 无 token | P1 |
| UT-AU-R3 | `初始化时从本地存储恢复登录态` | 预置 localStorage 的 token 与用户 | `isLoggedIn=true`；学号正确；`isAdmin`、`isSystemAdmin` 均 false | P2 |
| UT-AU-R4 | `登出时清空两种存储与内存状态` | 登录后（token-3）登出 | 登出接口以 token-3 调用；状态清空；两种存储的 token/user 均清除 | P1 |
| UT-AU-R5 | `改密后用新 token 覆盖原存储位置，保持当前设备登录` | localStorage 有 old-token；改密返回 new-token | token=new-token；localStorage=new-token；sessionStorage 无 token | P1 |
| UT-AU-R6 | `管理员与系统管理员分别由 role 判定` | 分别以“自习室管理员”“系统管理员”角色构造 store | 前者 isAdmin=true、isSystemAdmin=false；后者相反 | P2 |

### 7.3 消息关联跳转（8 条，`messageLinks.test.ts`）

| ID | 自动化实现（用例标题） | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| UT-LINK-01 | `已知关联类型映射到学生端列表页` | 预约单、违约记录、黑名单 | 路由分别为 `/student/reservations`、`/student/violations`；违约记录标签“我的违约” | P2 |
| UT-LINK-02 | `未知或空类型不跳转` | null、未知类型 | `relatedTarget` 均 null；label 分别为“查看详情”“仅通知” | P2 |
| UT-LINK-03 | `有 id 时带编号，没有 id 时只显示类型` | 预约单 #12；无 id；类型与 id 都为空 | `预约单 #12`；`预约单`；空串 | P2 |
| UT-LINK-04 | `预约单等带 focus 参数，高亮目标记录` | 预约单 #12；投诉 #3 | `/student/reservations?focus=12`；`/student/complaints?focus=3` | P2 |
| UT-LINK-05 | `黑名单没有学生端记录页，只跳违约页不带 focus` | 黑名单 #9 | `/student/violations`（无 focus） | P2 |
| UT-LINK-06 | `无关联对象或未知类型返回 null` | 类型/id 都为空；未知类型带 id | 均 null | P2 |
| UT-LINK-07 | `接受正整数与字符串数组首项` | `'12'`、`['7','8']` | 12、7 | P2 |
| UT-LINK-08 | `非法值返回 null` | undefined、空串、'0'、'-3'、'abc' | 均 null | P2 |

### 7.4 日期格式化（7 条，`format.test.ts`）

| ID | 自动化实现（用例标题） | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| UT-FMT-01 | `格式化 SQLite 本地时间与 ISO 时间` | `2026-11-12 10:05:00`、`2026-11-12T10:05:00` | 均输出 `2026-11-12 10:05` | P2 |
| UT-FMT-02 | `空值与非法值返回占位符` | null、空串、`not-a-date` | 均 `-` | P2 |
| UT-FMT-03 | `支持 Date 与时间戳` | Date 与毫秒时间戳（2026-11-12 09:30） | 均输出 `2026-11-12 09:30` | P2 |
| UT-FMT-04 | `formatDate / formatTimeSecond / formatMonthDayTime / formatMonthDay` | `2026-11-12 10:05:09` | `2026-11-12`、`10:05:09`、`11-12 10:05`、`11-12` | P2 |
| UT-FMT-05 | `formatApiDateTime 输出后端约定格式，非法值返回空串` | 上述时间；null | `2026-11-12T10:05:09`；空串 | P2 |
| UT-FMT-06 | `recentRange 包含今天并向前取 N-1 天` | 固定 2026-11-12；N=7 与 N=1 | `['2026-11-06','2026-11-12']`；同一天起止 | P2 |
| UT-FMT-07 | `isAfterToday / isBeforeToday 按自然日边界判断` | 固定 11-12 10:00；判断 11-13 00:00、11-12 23:59、11-11 23:59、11-12 00:00 | true/false/true/false | P2 |

### 7.5 联系方式掩码（7 条，`mask.test.ts`）

| ID | 自动化实现（用例标题） | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| UT-MASK-01 | `保留前 3 位与后 4 位` | `13800001234`、`138 0000 1234` | 均 `138****1234` | P1 |
| UT-MASK-02 | `位数不足时退回通用掩码` | `123456`、`42` | `12***56`、`**` | P2 |
| UT-MASK-03 | `空值返回占位符` | 空串、null | 均 `—` | P2 |
| UT-MASK-04 | `保留首字母与完整域名` | `student@zju.edu.cn`、`ab@x.cn` | `s******@zju.edu.cn`、`a***@x.cn` | P1 |
| UT-MASK-05 | `非邮箱结构退回通用掩码` | `wechat:abc`、undefined | `we***bc`、`—` | P2 |
| UT-MASK-06 | `按手机号或邮箱自动选择掩码` | 手机号、邮箱、其他联系方式、null | 手机/邮箱按对应规则；其他 `ot***ct`；null `—` | P1 |
| UT-MASK-07 | `识别联系方式形态` | 手机号、邮箱、空串 | 手机号、邮箱、未填写 | P2 |

### 7.6 投诉工作日 SLA（7 条，`workday.test.ts`）

| ID | 自动化实现（用例标题） | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| UT-WD-01 | `从创建时刻次日起算 3 个工作日，跳过周末` | 创建 2026-11-12 09:00（周四） | 截止 2026-11-17 23:59（周五、周一、周二） | P1 |
| UT-WD-02 | `创建时刻非法时返回 null` | null、空串、`not-a-date` | 均 null | P2 |
| UT-WD-03 | `不把起始日计入，只数完整工作日` | 11-12 00:00 至 11-17 23:59 | 等于 `COMPLAINT_SLA_WORKDAYS`（3） | P1 |
| UT-WD-04 | `倒序或同一天返回 0` | 同日；11-18 到 11-12 | 均 0 | P2 |
| UT-WD-05 | `未超时时给出剩余工作日与截止文案` | 创建 11-12 09:00；当前 11-13 10:00 | 未逾期；迟到 0；截止文案 `2026-11-17 23:59`；剩余工作日 >0；说明含“3 个工作日” | P1 |
| UT-WD-06 | `超时时按自然日给出迟到量` | 创建 11-12 09:00；当前 11-18 10:00 | 已逾期；迟到 1 个自然日；剩余工作日 0 | P1 |
| UT-WD-07 | `创建时间缺失时不给时限结论` | 创建时间为 null | 截止为 null；文案 `—`；未逾期 | P2 |

### 7.7 消息 store（6 条，`message.test.ts`）

| ID | 自动化实现（用例标题） | 前置与步骤（关键数据） | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- |
| UT-MSG-01 | `load 同时刷新列表、总数与未读数` | 列表 2 条（1 条已读）；未读数 1 | items=2、total=2、unread=1、hasUnread=true、loading=false；列表请求参数为 page=1、page_size=10、type=undefined | P2 |
| UT-MSG-02 | `loadDigest 只保留最近未读，并同步未读数` | 5 条消息，其中 1 条已读；未读数 4 | digest 保留未读的 1、3、4；unread=4 | P2 |
| UT-MSG-03 | `先本地生效，失败时回滚` | 标记已读接口先 reject 后成功 | 失败后目标仍未读、未读数 1；再成功后已读、未读数 0 | P1 |
| UT-MSG-04 | `已读消息重复标记不会发请求` | 消息本身已读 | 不调用标记已读接口 | P2 |
| UT-MSG-05 | `换账号后清空上一个账号的列表与未读数` | 先加载用户 1 的列表；切换为用户 2 后只刷新未读数 | items=[]、total=0；未读数取新账号的 1 | P1 |
| UT-MSG-06 | `reset 清空所有状态` | 加载后调用 reset | items、digest、total、unread 均清空；page=1；type=all | P2 |

---

## 8. 追溯矩阵

### 8.1 报告章节 → 用例组

| 用例组 | 报告章节（执行结果） | 数量 |
| --- | --- | ---: |
| UT-RL-01…07、UT-RS-01…04 | §3.4 新增用例执行结果 | 11 |
| UT-SM-01…10、UT-AU-01…03 | §3.4 新增用例执行结果 | 13 |
| TC-QA-BND、TC-QA-STS、TC-QA-CONC | §4.1 QA 集成 | 37 |
| TC-API-*、TC-REG、TC-HARD、TC-BFX、TC-BOOT、TC-CONC、TC-HLT、TC-RES、TC-FLOW、TC-GOV、UT-TIME | §4.1 其余后端 | 137 |
| UT-BR、UT-AU-R、UT-LINK、UT-FMT、UT-MASK、UT-WD、UT-MSG | §4.2 前端 | 65 |

### 8.2 历史风险与缺陷的回归映射

| 编号 | 风险/缺陷 | 回归用例 |
| --- | --- | --- |
| Q3-01 | 签到与强制取消并发产生矛盾终态 | TC-QA-CONC-02；UT-RS-01…04（条件更新语义） |
| Q3-02 | 关闭自习室与新预约竞态 | TC-QA-CONC-03；TC-FLOW-08；TC-BFX-26 |
| Q3-03 | 幂等重放重复发送成功消息 | TC-QA-CONC-01；TC-QA-BND-13 |
| Q3-04 | 并发加入黑名单产生重复有效限制 | TC-QA-CONC-04；TC-GOV-14 |
| Q3-05 | 自动限制解除后违约计数未清零 | TC-QA-STS-07；TC-GOV-22 |
| Q3-06 | 登出后旧令牌仍有效 | TC-QA-STS-12；UT-AU-02（前端登出容错） |
| Q3-07 | 登录接口无 IP 级限流 | TC-QA-STS-13；UT-RL-01…07 |
| Q3-08 | available-seats 不校验日期窗口 | TC-QA-STS-16 |
| Q3-09 | available-seats 不校验 5 分钟对齐 | TC-QA-STS-17 |
| Q4-01 | 生产环境未关闭接口文档 | TC-QA-STS-18 |
| Q4-02(A) | 登录锁定按 IP 隔离 | TC-API-LOCK-05 |
| Q4-02(E) | 登录失败计数保留 30 天并清理 | TC-API-LOCK-06 |
| BR-018 | 权限拆分（系统管理员不进入业务接口） | TC-BFX-04；TC-QA-STS-08；TC-BFX-18…20、22 |
| NFR-006 | 联系方式服务端脱敏 | TC-BFX-01…03；UT-MASK-01…07 |
| FR-051 | 趋势按状态流转计数、去重、零值不断点 | TC-BFX-07…09 |
| BR-010 / ST-042 | 手动限制不自动解除、不可被再次绕过 | TC-GOV-19、TC-GOV-20 |
| ST-063 | 管理员不能直接关闭投诉 | TC-API-FIX-02；TC-GOV-08 |
| B1 / B5 / A2 | 改密令牌轮换、登录锁定、注册开关与白名单 | TC-API-PWD-01…03；TC-API-LOCK-01…04；TC-REG-05、TC-REG-06 |

### 8.3 报告 §4.1 低覆盖模块 → 用例与缺口

| 模块 | 报告覆盖率 | 本清单覆盖用例 | 仍缺口 |
| --- | ---: | --- | --- |
| `app/services/reservation_state.py` | 100% | UT-RS-01…04；TC-QA-CONC-02 | 无 |
| `app/services/rate_limit_service.py` | 93% | UT-RL-01…07；TC-QA-STS-13 | 唯一约束冲突后的自增回退（69–70 行）：SQLite 顺序测试难触发，白盒 `test_whitebox_rate_limit.py` 补强；真实 MySQL 多 worker 压测未执行 |
| `app/services/auth_service.py` | 93% | TC-API-LOCK-01…06；TC-API-PWD-01…03；TC-REG-01…07；TC-QA-STS-13 | 注册白名单、令牌版本等少数异常分支；白盒补强 |
| `app/services/availability_service.py` | 87% | TC-QA-BND-14；TC-QA-STS-16、17；TC-FLOW-03 | 分区关闭作用范围、可约座位查询的参数边界；白盒补强 |
| `app/services/blacklist_service.py` | 82% | TC-GOV-13…22；TC-QA-STS-06、07；TC-QA-CONC-04 | 列表三态筛选、解除与计数清零的异常分支；白盒补强 |
| `app/services/reservation_command_service.py` | 80% | TC-QA-CONC-01；TC-FLOW-01、04；TC-QA-BND-13 | 唯一约束冲突后的 C4/ST-035 分类（仅竞态窗口可达）；白盒补强 |
| `app/services/room_service.py` | 58% | TC-FLOW-08；TC-BFX-26；TC-API-FIX-04；TC-QA-CONC-03；TC-RES-01…08 | 管理端创建/修改/删除/分区与关闭记录解除的低频分支；白盒补强至 96% |
| `app/tasks/auto_end_reservation.py` | 27% | 无直接用例 | 到点自动结束的任务函数与调度注册；白盒 11 条补强 |
| `app/tasks/auto_violation.py` | 36% | TC-QA-STS-04（服务函数，非任务入口） | 任务候选筛选、单条失败隔离；白盒补强 |
| `app/tasks/login_attempt_cleanup.py` | 56% | TC-API-LOCK-06（清理函数） | 调度触发；白盒补强 |
| `app/tasks/scheduler.py` | 58% | TC-HARD-07（任务包装器） | 调度注册与失败记录；白盒补强 |

---

## 9. 未覆盖范围与后续用例建议

以下内容**不在 263 条范围内，也未执行**，仅作为报告 §5.2 的落地建议；编号为新拟，待实现后再登记为正式用例。

| 建议 ID | 目标 | 前置与步骤 | 预期 | 对应报告条目 |
| --- | --- | --- | --- | --- |
| TC-CONC-MYSQL-01 | 限流桶并发插入回退 | 真实 MySQL + 多 worker，两个请求同时首次建桶 | 仅 1 行；计数不丢失；不 500 | §5.2 第 2 条 |
| TC-TASK-01 | 自动结束任务 | 冻结时间到结束点，直接调用任务函数 | 到点预约“已完成”；不产生违约；槽位释放 | §5.2 第 3 条 |
| TC-TASK-02 | 自动违约任务 | 冻结时间过签到截止，直接调用 | 仅生成 1 条违约；重复执行幂等 | §5.2 第 3 条 |
| TC-TASK-03 | 调度注册与失败记录 | 启动 APScheduler，注入一次失败 | 任务记录“失败”并按策略重试；注册项齐全 | §5.2 第 3 条 |
| TC-E2E-01 | 座位图悬停信息卡 | 浏览器打开选座页，悬停座位 | 卡片展示座位号、资源状态、时段状态 | §5.2 第 4 条 |
| TC-E2E-02 | 座位图缩略导航 | 座位较多时拖动缩略图 | 主视图同步滚动，定位准确 | §5.2 第 4 条 |
| TC-E2E-03 | Ctrl+滚轮缩放 | 按住 Ctrl 滚轮 | 缩放比例变化，桌椅不重叠、不溢出 | §5.2 第 4 条 |
| TC-DB-01 | MySQL 迁移与时间精度 | 空库执行 `alembic upgrade head`；写入边界时间 | 迁移成功；时间字段精度与业务一致 | §5.2 第 5 条 |
| TC-COV-01 | 覆盖率配置 | 把 `seatMapLayout.ts` 加入 `coverage.include` 后运行 | 常规覆盖率报表包含该文件 | §5.2 第 8 条 |
| TC-HYG-01 | 仓库卫生 | 清理被跟踪的 `frontend/.tmp` 与 `frontend/dist` | 工作区无构建产物；CI 不受影响 | §5.2 第 6 条 |

---

## 10. 执行与判定口径

### 10.1 复现命令（摘自报告 §7）

```bash
# 后端：本报告范围（185 条，排除白盒）
cd backend
.venv/Scripts/python.exe -m pytest --ignore=tests/whitebox

# 后端：仅 QA 集成套件（37 条）
.venv/Scripts/python.exe -m pytest tests/qa

# 后端：覆盖率（语句 + 分支）
.venv/Scripts/python.exe -m pytest --ignore=tests/whitebox \
  --cov=app --cov-branch --cov-report=term-missing

# 后端：当前全量（271 条，含白盒 86 条）
.venv/Scripts/python.exe -m pytest

# 前端：单元测试 + 覆盖率 + 类型检查
cd ../frontend
npm test
npm run test:coverage
npm run type-check

# 前端：规范检查（新增/修改文件）
npx eslint src/utils/__tests__/seatMapLayout.test.ts src/stores/__tests__/auth.test.ts
npx prettier --check src/utils/__tests__/seatMapLayout.test.ts src/stores/__tests__/auth.test.ts
```

### 10.2 判定口径

1. **通过**：用例对应的自动化实现无失败、无错误；集成用例同时满足“HTTP 状态码 → 响应 code/关键字段 → 数据库终态”三层断言。
2. **出口准则**：全量自动化通过率 100%；无 P0/P1 缺陷；前端类型检查与 ESLint 通过。覆盖率仅观察，不设强制阈值。
3. **失败记录**：命令、请求/响应、数据库终态、日志片段、复现次数；并发用例至少重复 3 次。
4. **环境记录**：Python 与 pytest-cov 版本、Node 与 Vitest 版本、数据库类型（SQLite/MySQL）必须写入执行记录，避免覆盖率小数与结果不可比。
5. **豁免规则**：不得用 `xfail` 静默跳过已知缺陷；如需保留失败证据，使用显式标记并在报告中列出。

---

## 11. 维护与修订

### 11.1 维护约定

1. 新增用例必须登记到本清单，沿用现有前缀与连续编号；不得复用已删除用例的 ID。
2. 自动化实现重命名时同步更新“自动化实现”列；断言变化时同步更新“预期结果”。
3. 报告统计变化（用例数、通过数、覆盖率）时，同步更新 §2 与报告 §3、§4，保持两处数字一致。
4. 新增“待补”用例实现后，从 §9 移入正文并分配正式 ID，同时在报告 §3.1 与 §3.4 登记。

### 11.2 修订记录

| 日期 | 版本 | 修订内容 |
| --- | --- | --- |
| 2026-11-26 | v1.0 | 初稿：建立 263 条用例（后端 185、前端 78），补齐 24 条新增用例的前置/步骤/断言，建立风险与模块追溯矩阵。 |
| 2026-11-26 | v1.1 | 调整为“用例先行”口径：本清单作为测试报告的用例基线，报告按用例组汇总执行结果；统一“自动化实现”列，弱化实现细节对用例设计的绑定。 |
| 2026-11-26 | v1.2 | 按 2026-11-26 14:38–14:41 的实际执行复核：新增 §2.2/§2.3 层级列与 §2.4 单元/集成汇总（后端单元 78、后端集成 107、前端单元 78）；用例定义与数量未变。 |
