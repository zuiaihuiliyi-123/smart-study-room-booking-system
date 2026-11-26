# 智慧自习室预约与管理系统 · 单元与集成测试报告（阶段 5 · mzj）

- 版本：v1.0
- 测试日期：2026-11-26
- 代码基线：`main` @ `7594cae`（执行前已 `git pull --ff-only`，与 `origin/main` 一致；工作区仅新增本轮测试与文档）
- 责任人：mzj
- 测试对象：认证/权限、M5（用户/投诉/评价/审计）、M6 数据看板、M7 站内消息
- 配套用例清单：`docs/测试用例清单-阶段5-mzj.md`
- 执行证据：`docs/test-reports/pytest-junit-mzj.xml`（60 条 mzj 用例）

---

## 1. 范围

### 1.1 本轮覆盖

| 模块 | 内容 |
|---|---|
| 认证 | 登录失败锁定计数与窗口、注册白名单、登出、改密、停用账户、令牌失效 |
| 权限 | 学生/管理员/系统管理员三角色矩阵、越权审计、横向越权（投诉/消息/评价） |
| M5 用户 | 服务端脱敏、本人明文、`restrict_until`、账户停用/恢复、列表筛选分页 |
| M5 投诉 | 四类对象、状态机、处理说明、超时自动关闭、确认关闭、权限与筛选 |
| M5 评价 | 仅已完成预约、一单一评（含并发唯一约束分支）、评分/内容边界、日期筛选 |
| M5 审计 | 动作完整性、操作人/动作/日期/分页筛选、响应不含凭据 |
| M6 看板 | 5 项概览口径、房间过滤、30 分钟折算、Top N、趋势去重与区间上限、10 秒缓存键 |
| M7 消息 | 未读数、标记已读幂等、类型筛选、用户隔离、通知失败不回滚业务 |
| 前端 | `useMyComplaints`、`useAuditManage` 两个 composable 的状态机 |

### 1.2 不在本轮范围

- 真实 MySQL 并发/锁行为（沿用阶段 4 的独立 MySQL 回归结论，本轮未重复）。
- Playwright 浏览器 E2E（沿用既有 5 条主流程）。
- 预约创建、签到签退、违约/黑名单、资源管理的业务用例（由其他组员负责）。
- FR-024 违约申诉、FR-033 记录导出等已排除需求。

---

## 2. 环境与基线

| 项目 | 值 |
|---|---|
| 操作系统 | Windows 11（本机开发环境） |
| Python / pytest | 3.13.7 / 8.4.2（`backend/.venv`） |
| Node.js / npm | v24.20.0 / 11.19.0 |
| 后端测试库 | SQLite 内存库（`tests/conftest.py` 的 `db` 夹具），不连接本机 MySQL |
| 前端测试 | Vitest 2.1.9 + happy-dom |
| 时间基线 | 本组用例统一 `monkeypatch time_utils.now` 冻结为 `2026-11-26 10:00` |
| 通知隔离 | 默认把 `notification_service.SessionLocal` 置为不可用，避免连接真实数据库 |

---

## 3. 测试策略

1. **单元测试**：不经过 HTTP，只调用纯函数或单个 service 函数；验证分支、边界与幂等，不依赖接口层。
2. **集成测试**：`TestClient` + 覆盖 `get_db` 的独立 SQLite 会话，验证“路由 → 鉴权 → 服务 → 数据库 → 审计/消息”的完整链路。
3. **断言三层**：HTTP 状态码 → 业务 `code`/关键字段 → 数据库终态（状态、计数、审计条数、消息条数）。
4. **不修改业务代码**：本轮只新增测试与文档；发现的实现观察项只记录，不顺手改动。
5. **AI 辅助**：AI 负责生成候选用例与代码骨架，人工逐条核对业务规则、去重、修正断言后再执行。

---

## 4. 用例统计

| 层次 | 条目 | 执行 | 通过 | 失败 |
|---|---:|---:|---:|---:|
| 后端单元 | 31 | 36 | 36 | 0 |
| 后端集成 | 24 | 24 | 24 | 0 |
| 前端单元 | 13 | 13 | 13 | 0 |
| **合计** | **68** | **73** | **73** | **0** |

| 模块 | 用例数 | P0 | P1 | P2 |
|---|---:|---:|---:|---:|
| 认证/权限 | 12 | 7 | 5 | 0 |
| M5 用户 | 7 | 2 | 4 | 1 |
| M5 投诉 | 11 | 2 | 8 | 1 |
| M5 评价 | 5 | 1 | 3 | 1 |
| M5 审计 | 2 | 1 | 1 | 0 |
| M6 看板 | 11 | 1 | 7 | 3 |
| M7 消息 | 7 | 2 | 4 | 1 |
| 前端 | 13 | 0 | 9 | 4 |

> P0 判定：越权/数据隔离/终态一致性/审计完整性；P1：已定稿业务规则与状态机；P2：筛选分页、展示口径与观察项。

---

## 5. 执行结果（2026-11-26 实际执行）

| 命令 | 结果 |
|---|---|
| `pytest tests -q`（backend） | **320 passed**，exit 0（基线 260 + 本轮 60） |
| `pytest tests/mzj -q` | **60 passed**，exit 0 |
| `pytest tests --cov=app --cov-branch` | 320 passed，**TOTAL 96%** |
| `npm run test`（frontend） | **9 个测试文件 / 78 passed**，exit 0（原 65 + 本轮 13） |
| `npm run test:coverage` | 78 passed；语句 93.79%、分支 84.66% |
| `npm run lint` | 0 error |
| `npm run type-check` | 0 error |
| `npx prettier --check`（本轮新增 2 个前端测试文件） | 通过 |
| 生成 JUnit | `docs/test-reports/pytest-junit-mzj.xml`（60 条，8.1 KB） |

> 说明：后端耗时未单独记录，不在此处编造；可通过重跑上述命令复核。

---

## 6. 覆盖率

### 6.1 后端本组模块（`pytest --cov=app --cov-branch`）

| 模块 | 补充前（《白盒测试报告》） | 本轮后 | 说明 |
|---|---:|---:|---|
| `core/dependencies.py` | 85%–89% | **88%** | 鉴权依赖的防御性分支仍有 5 行未覆盖（缺失/伪造凭据的细分路径） |
| `services/auth_service.py` | 93% | **96%** | 并发重试、窗口重置、锁定提示分钟数 |
| `services/user_service.py` | 99% | **99%** | 分页越界与关键词空值 |
| `services/complaint_service.py` | 97% | **97%** | 四类对象、超时边界、处理说明 |
| `services/review_service.py` | 92% | **97%** | 并发唯一约束分支已覆盖 |
| `services/dashboard_service.py` | 99% | **100%** | 短预约折算、空房间、Top N 并列 |
| `services/message_service.py` | 92% | **100%** | 已读幂等、类型筛选分页 |
| `services/notification_service.py` | — | **100%** | 含失败容错分支 |
| `services/rate_limit_service.py` | 100% | **100%** | 本轮未新增，复核保持 |
| **全仓 TOTAL** | 96% | **96%** | 语句 97.5%（75 / 3053 行未覆盖）；664 个分支中 52 个部分覆盖 |

### 6.2 前端

| 指标 | 本轮前 | 本轮后 |
|---|---:|---:|
| 单测文件 / 用例 | 7 / 65 | **9 / 78** |
| 语句覆盖（配置内 7 个文件） | 93.79% | 93.79% |
| 分支覆盖 | 84.66% | 84.66% |

> 新增的 `useMyComplaints.ts`、`useAuditManage.ts` 未被 `frontend/vitest.config.ts` 的 `coverage.include` 收录，因此用例数增加但覆盖率数字不变；这是口径问题，不是测试无效。

---

## 7. 缺陷与观察

### 7.1 缺陷

本轮**未发现新的 P0/P1 业务缺陷**。73 条用例全部通过，未出现“预期失败但实际通过”或需要标记 `xfail` 的项。

### 7.2 实现观察项（不构成本轮修复）

| 编号 | 观察 | 证据 | 建议 |
|---|---|---|---|
| OBS-01 | 用户/投诉关键词直接拼入 `LIKE`，`%`、`_` 未转义，`keyword="%"` 会匹配全部记录（继承阶段 4 的 S1-11） | `TC-U-USER-03`：`keyword="%"` 返回 total=2 | 由后端负责人评估是否转义 `%`/`_`；本轮按现状记录，不改业务代码 |
| OBS-02 | 前端覆盖率只统计 7 个 utils/store 文件，composable 不在口径内 | `frontend/vitest.config.ts` 的 `coverage.include` | 后续把已测 composable 加入 include，或改用 `coverage.exclude` 白名单 |
| OBS-03 | `core/dependencies.py` 仍为 88%，剩余分支集中在“无凭据/伪造令牌”的防御路径 | 覆盖率输出：50 行、5 行未覆盖 | 可补 2~3 条纯依赖层用例，不影响主流程结论 |
| OBS-04 | `notify_safe` 真实独立会话（MySQL）未在自动化中验证 | 本组统一 patch `SessionLocal` | 由阶段 5 集成环境在真实 MySQL 上补一条冒烟 |
| OBS-05 | SQLite 与 MySQL 在唯一约束、行锁、`FOR UPDATE` 语义上存在差异 | 评价并发分支、账户唯一限制依赖数据库约束 | 并发类结论仍以阶段 4 的 MySQL 回归为准 |

---

## 8. 遗留与未执行

1. 真实 MySQL 下的本组用例回归（当前全部为 SQLite 内存库）。
2. Playwright E2E 未新增投诉/审计/看板场景。
3. `core/database.get_db` 的真实会话生命周期（共享测试基座限制）。
4. 前端 composable 未纳入覆盖率统计（见 OBS-02）。
5. 审计日志保留/归档策略（BR-012）无自动化验证，属运维配置范围。

---

## 9. 分工与责任

| 成员 | 负责模块 | 新增测试文件 | 用例数 | 结果 |
|---|---|---|---:|---|
| mzj | 认证/权限 + M5 + M6 + M7 | `backend/tests/mzj/unit/*`（6 个）、`backend/tests/mzj/integration/*`（6 个）、`frontend/src/utils/__tests__/useMyComplaints.test.ts`、`useAuditManage.test.ts`、`backend/tests/mzj/conftest.py` | 68（执行 73） | 全部通过 |

新增/修改文件清单：

```text
backend/tests/mzj/conftest.py
backend/tests/mzj/unit/test_auth_rules.py
backend/tests/mzj/unit/test_user_masking.py
backend/tests/mzj/unit/test_complaint_rules.py
backend/tests/mzj/unit/test_review_rules.py
backend/tests/mzj/unit/test_dashboard_metrics.py
backend/tests/mzj/unit/test_message_notification.py
backend/tests/mzj/integration/test_auth_permission_flow.py
backend/tests/mzj/integration/test_m5_user_flow.py
backend/tests/mzj/integration/test_m5_complaint_flow.py
backend/tests/mzj/integration/test_m5_review_audit_flow.py
backend/tests/mzj/integration/test_m6_dashboard_api.py
backend/tests/mzj/integration/test_m7_message_flow.py
frontend/src/utils/__tests__/useMyComplaints.test.ts
frontend/src/utils/__tests__/useAuditManage.test.ts
docs/测试用例清单-阶段5-mzj.md
docs/测试报告-阶段5-mzj.md
docs/test-reports/pytest-junit-mzj.xml
```

---

## 10. AI 使用记录（可复核）

| 阶段 | AI 输入 | AI 输出 | 人工修正 |
|---|---|---|---|
| 用例设计 | 模块范围、需求规则（SM-04/BR-013/BR-016/NFR-006）、既有测试清单、`AGENTS.md` §10 | 约 80 条候选用例（编号/前置/步骤/预期/优先级） | 与阶段 2 的 124 条及现有 260 条去重后保留 55 条；删除 AI 编造的 `GET /complaints/{id}`（后端只有列表/处理/确认接口）；拒绝“审计导出”用例（FR-033 已排除） |
| 代码生成 | 用例表 + 目标文件路径 + 现有夹具说明 | pytest 用例骨架与前端 Vitest 骨架 | 统一改为复用 `api_client`/`db`/`make_*`；把“每条用例都登录”改为直接签发令牌，避免 10 次/分/IP 限流误报 |
| 断言校准 | 贴出 `dashboard_service`、`review_service` 源码 | 初稿按 0.17/4=0.0417 断言短预约占用率 | 读代码后改为 `round(0.17/4,4)=0.0425`，与实现口径一致 |
| 通知处理 | 说明 `notify_safe` 使用独立 `SessionLocal` | 初稿直接调用，尝试连接 MySQL | 改为 autouse 夹具置空会话，并提供 `captured_notifications` 写回测试库；仅保留 1 条“通知失败不回滚业务”的真实容错用例 |
| 结果整理 | 实际命令输出 | 报告初稿 | 只保留真实执行数字；未执行的 MySQL/E2E 明确写入“未执行” |

> AI 只用于“生成候选 + 起草骨架”，业务规则取舍、断言值与最终执行结果均由人工核对。

---

## 11. 复现步骤

```powershell
# 0. 同步代码（本轮执行时 main = 7594cae）
git pull --ff-only origin main

# 1. 后端本组
cd backend
.\.venv\Scripts\python.exe -m pytest tests\mzj -q

# 2. 后端全量 + 覆盖率
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m pytest tests --cov=app --cov-branch --cov-report=term

# 3. JUnit 证据
.\.venv\Scripts\python.exe -m pytest tests\mzj -q --junitxml=..\docs\test-reports\pytest-junit-mzj.xml

# 4. 前端
cd ..\frontend
npm run test
npm run lint
npm run type-check
```

---

## 12. 结论

1. 本轮为 mzj 负责的认证/权限 + M5 + M6 + M7 补充了 **55 条后端用例（执行 60 次）与 13 条前端用例**，全部通过；后端全量由 **260 → 320**，前端由 **65 → 78**。
2. 关键业务口径均有可执行断言：权限三角色矩阵与越权审计、投诉状态机与超时关闭、评价并发一单一评、看板 5 项口径/30 分钟折算/趋势去重/10 秒缓存、消息已读幂等与通知失败隔离。
3. 后端整体覆盖率保持 **96%**；本组模块中看板、消息、通知、限流达到 **100%**，评价由 92% 提升到 97%，认证由 93% 提升到 96%。
4. 未发现新的 P0/P1 缺陷；发现 5 项实现/口径观察项，已登记并明确不在本轮修改业务代码。
5. 建议：将 `backend/tests/mzj` 纳入 PR 必跑；前端把已测 composable 加入覆盖率口径；真实 MySQL 环境下补跑一次本组集成用例。
