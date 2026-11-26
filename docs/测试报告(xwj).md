# 智慧自习室预约与管理系统 · 单元与集成测试报告

- 报告日期：2026-11-26
- 用例基线：`docs/测试用例清单(xwj).md` v1.2，263 条（后端 185 + 前端 78）
- 代码基线：`main` @ `a0c94ec`；工作区含 4 个未提交的测试文件（见 §6.2 第 7 条）
- 执行时间：2026-11-26 14:38–14:41（本地）
- 测试环境：
  - 操作系统：Windows 10.0.26200.9974（x64）
  - 后端：Python 3.14.2、pytest 8.4.2、pytest-cov 7.1.0、SQLAlchemy 2.0.57、FastAPI 0.162.5
  - 前端：Node.js v24.21.0、npm 11.19.0、Vitest 2.1.9、happy-dom 15.11.7
- 总结论：**通过**。用例基线内 263 / 263 通过（100%）；另跑含白盒的全量后端 271 / 271 通过；TypeScript 类型检查、ESLint、Prettier 均无错误。

---

## 0. 报告信息与用例基线

| 项目 | 内容 |
| --- | --- |
| 报告性质 | 以用例清单为基线的本地执行报告，不是团队发布口径 |
| 用例基线 | `docs/测试用例清单(xwj).md` v1.2：后端 185 + 前端 78 = 263 条 |
| 用例层级 | 后端单元/服务层 78、后端集成 107、前端单元（含 store）78 |
| 代码基线 | `main` @ `a0c94ec`；应用代码与当前 `origin/main` `7594cae` 相同，后者仅新增白盒用例与文档 |
| 本报告范围 | 263 条（后端 185 + 前端 78），与用例清单 §2 完全对应 |
| 参考范围（不计入 263） | 白盒补充 86 条；含白盒的全量后端为 271 条 |
| 复现限制 | 引用的 4 个本地测试文件尚未提交；克隆仓库只能复现远端基线 174 + 65 |
| 关联文档 | 用例定义见《测试用例清单(xwj)》；历史缺陷见《测试报告-阶段4》；白盒补强见《白盒测试报告》 |

### 0.1 与用例清单的对应

| 本报告章节 | 用例清单章节 | 内容 |
| --- | --- | --- |
| §2 测试范围与层级 | §2.2、§2.3、§2.4 | 层级划分、文件分布 |
| §3.1 总体结果 | §2 用例统计 | 263 条总数与通过数 |
| §3.2 后端按文件 | §2.2、§3、§5、§6 | 185 条后端用例结果 |
| §3.3 前端按文件 | §2.3、§4、§7 | 78 条前端用例结果 |
| §3.4 新增用例结果 | §3、§4 | 24 条新增用例逐条结果 |
| §4 覆盖率 | §8.3 模块追溯 | 低覆盖模块与用例映射 |
| §5 缺陷与风险 | §8.2 风险追溯、§9 待补用例 | 历史缺陷回归与未覆盖项 |
| §7 复现命令 | §10 执行与判定 | 命令与判定口径 |

---

## 1. 测试目的、依据与出口准则

### 1.1 目的

对更新后的本地基线（`a0c94ec`）执行一轮可复现的单元与集成回归，重点验证：

1. 本轮远端引入的安全加固：登录/注册限流、登出令牌撤销、登录失败按 IP 隔离、预约状态原子流转；
2. 座位图布局改动：布局几何、筛选不重排、分区边界；
3. 此前没有直接用例覆盖的 service 层逻辑：限流固定窗口、状态条件更新、治理与资源管理分支。

### 1.2 依据

- 《智慧自习室预约与管理系统-需求规格说明书（课程结构版）》V2.2
- `docs/测试用例清单(xwj).md` v1.2（本报告的用例基线）
- `docs/测试用例清单-阶段2.md`（用例设计与裁决口径）
- `docs/测试报告-阶段4.md`（历史缺陷与修复回归）
- 仓库测试配置：`backend/pytest.ini`、`backend/tests/conftest.py`、`frontend/vitest.config.ts`

### 1.3 入口与出口准则

- 入口准则：代码可导入、测试依赖可用、无阻塞性环境问题（本次均满足）。
- 出口准则：用例基线通过率 100%；无 P0/P1 缺陷；前端类型检查与代码规范检查通过。覆盖率仅作为观察指标，项目未设置强制阈值。

---

## 2. 测试范围与层级

### 2.1 层级划分

| 层级 | 覆盖内容 | 实现方式 | 用例数 |
| --- | --- | --- | ---: |
| 后端单元/服务层 | 限流窗口、状态条件更新、时间工具、资源/预约/治理服务、启动脚本 | 直接调用 service/工具函数 + 内存 SQLite | 78 |
| 后端集成 | API 路由、参数校验、权限、状态机、并发、限流与登录锁定 | FastAPI `TestClient` + 覆盖 `get_db`；并发用文件型 SQLite | 107 |
| 前端单元（含 store） | 座位布局几何、预约规则、登录态与异常路径、消息、格式化、掩码、工作日 | Vitest + happy-dom，mock API 层 | 78 |
| 前端静态检查 | TypeScript、ESLint、Prettier | `vue-tsc --noEmit`、`eslint`、`prettier --check` | — |
| **合计** | — | — | **263** |

> 层级按用例的主要执行方式归类：`test_backend_hardening.py` 含 1 条接口缓存用例、`test_blocking_fixes.py` 含服务层直调用例，按主导方式分别归入单元与集成。QA 集成 37 条是后端集成 107 条的子集，不重复计数。

### 2.2 未执行范围

| 范围 | 原因 | 已由何处覆盖 |
| --- | --- | --- |
| 浏览器 E2E（座位悬停卡、缩略导航、Ctrl+滚轮缩放） | 需启动前后端与浏览器 | 未覆盖；建议后续补 Playwright |
| 真实 MySQL 并发、迁移、多 worker 限流共享 | 本报告使用 SQLite | 《测试报告-阶段4》§8.5 的临时 MySQL 8.0.21 验证 |
| 真实 APScheduler 调度 | 测试基座关闭调度器 | 白盒任务函数用例（另一环境） |
| 生产环境部署与反向代理 IP 还原 | 本地测试环境 | 未覆盖，属于上线前检查 |

### 2.3 测试基座与隔离

- 后端每个用例独享内存 SQLite（`sqlite://` + `StaticPool`），通过 `make_user` / `make_room` / `make_area` / `make_seat` / `make_reservation` 构造数据；时间敏感用例冻结 `time_utils.now()` 或显式传入 `now`。
- 集成用例通过 `api_client` 覆盖 `get_db`，真实经过路由、服务层与 ORM；不连接真实 MySQL，不启动调度器。
- 并发用例使用文件型 SQLite + WAL + `busy_timeout=5000`，每线程独立 session；设置 `QA_DATABASE_URL` 可切换真实 MySQL。
- 前端使用 Vitest + happy-dom，API 层通过 `vi.mock` 替换，`localStorage` / `sessionStorage` 在每个用例前后清空。

---

## 3. 用例执行结果

### 3.1 总体结果

| 范围 | 用例数 | 通过 | 失败 | 耗时 |
| --- | ---: | ---: | ---: | ---: |
| 后端单元/服务层 | 78 | 78 | 0 | 含于后端合计 |
| 后端集成 | 107 | 107 | 0 | 含于后端合计 |
| **后端合计（不含白盒）** | **185** | **185** | **0** | **28.58 s** |
| 其中：QA 集成子集 | 37 | 37 | 0 | 10.83 s |
| **前端** | **78** | **78** | **0** | **3.81 s** |
| **用例基线合计** | **263** | **263** | **0** | **—** |
| 参考：后端全量（含白盒 86） | 271 | 271 | 0 | 33.50 s |

通过率：**263 / 263 = 100%**。QA 子集为后端集成的一部分，不重复计入。

### 3.2 后端按文件（24 文件，185 条）

| 文件 | 用例数 | 层级 | 结果 |
| --- | ---: | --- | --- |
| `tests/qa/test_qa_boundaries.py` | 15 | 集成 | 15 passed |
| `tests/qa/test_qa_state_security.py` | 18 | 集成 | 18 passed |
| `tests/qa/test_qa_concurrency.py` | 4 | 集成（并发） | 4 passed |
| `tests/test_api_audit.py` | 2 | 集成 | 2 passed |
| `tests/test_api_dashboard_top.py` | 2 | 集成 | 2 passed |
| `tests/test_api_fixes.py` | 6 | 集成 | 6 passed |
| `tests/test_api_flow.py` | 2 | 集成 | 2 passed |
| `tests/test_api_login_lock.py` | 6 | 集成 | 6 passed |
| `tests/test_api_password.py` | 3 | 集成 | 3 passed |
| `tests/test_api_phase2.py` | 6 | 集成 | 6 passed |
| `tests/test_api_reviews.py` | 2 | 集成 | 2 passed |
| `tests/test_api_skeleton.py` | 5 | 集成 | 5 passed |
| `tests/test_auth_register.py` | 7 | 集成 | 7 passed |
| `tests/test_backend_hardening.py` | 7 | 单元（含 1 条接口缓存） | 7 passed |
| `tests/test_blocking_fixes.py` | 26 | 集成（含服务层直调） | 26 passed |
| `tests/test_bootstrap_db.py` | 8 | 单元 | 8 passed |
| `tests/test_concurrency.py` | 2 | 集成（并发） | 2 passed |
| `tests/test_health.py` | 1 | 集成 | 1 passed |
| `tests/test_m1_resource.py` | 16 | 单元（服务层） | 16 passed |
| `tests/test_m2_m3_flow.py` | 9 | 单元（服务层） | 9 passed |
| `tests/test_m5_governance.py` | 22 | 单元（服务层） | 22 passed |
| `tests/test_rate_limit_service.py` | 7 | 单元 | 7 passed |
| `tests/test_reservation_state.py` | 4 | 单元 | 4 passed |
| `tests/test_time_utils.py` | 5 | 单元 | 5 passed |

### 3.3 前端按文件（8 文件，78 条）

| 文件 | 用例数 | 层级 | 结果 |
| --- | ---: | --- | --- |
| `src/utils/__tests__/bookingRules.test.ts` | 24 | 单元 | 24 passed |
| `src/utils/__tests__/seatMapLayout.test.ts` | 10 | 单元 | 10 passed |
| `src/stores/__tests__/auth.test.ts` | 9 | 单元（store） | 9 passed |
| `src/utils/__tests__/messageLinks.test.ts` | 8 | 单元 | 8 passed |
| `src/utils/__tests__/format.test.ts` | 7 | 单元 | 7 passed |
| `src/utils/__tests__/mask.test.ts` | 7 | 单元 | 7 passed |
| `src/utils/__tests__/workday.test.ts` | 7 | 单元 | 7 passed |
| `src/stores/__tests__/message.test.ts` | 6 | 单元（store） | 6 passed |

### 3.4 新增用例执行结果（24 条）

用例定义见《测试用例清单(xwj)》§3、§4；下表为本次执行结果。

**后端限流服务（7 条）**

| 用例 ID | 用例名称 | 结果 |
| --- | --- | --- |
| UT-RL-01 | 首次命中建桶并整分钟对齐 | 通过 |
| UT-RL-02 | 窗口内累计且只保留一行 | 通过 |
| UT-RL-03 | 上限边界与 429 响应 | 通过 |
| UT-RL-04 | IP 与接口维度隔离 | 通过 |
| UT-RL-05 | 跨窗口重新计数 | 通过 |
| UT-RL-06 | 自定义 30 秒窗口对齐 | 通过 |
| UT-RL-07 | 过期窗口清理 | 通过 |

**后端预约状态（4 条）**

| 用例 ID | 用例名称 | 结果 |
| --- | --- | --- |
| UT-RS-01 | 状态匹配时原子写入 | 通过 |
| UT-RS-02 | 状态不匹配不写入 | 通过 |
| UT-RS-03 | 重复流转仅首次成功 | 通过 |
| UT-RS-04 | 不提交事务、可回滚 | 通过 |

**前端座位布局（10 条）**

| 用例 ID | 用例名称 | 结果 |
| --- | --- | --- |
| UT-SM-01 | 空输入返回默认布局 | 通过 |
| UT-SM-02 | 座位与椅子一一对应 | 通过 |
| UT-SM-03 | 相同输入可复现 | 通过 |
| UT-SM-04 | 筛选不重排布局（回归） | 通过 |
| UT-SM-05 | 中央区 2 人桌拆分 | 通过 |
| UT-SM-06 | 桌号取座位号前缀 | 通过 |
| UT-SM-07 | 分区名称推断与标签 | 通过 |
| UT-SM-08 | 属性推断与 hasWindow | 通过 |
| UT-SM-09 | 窗边区 4 人桌拆分 | 通过 |
| UT-SM-10 | 桌椅不越出分区 | 通过 |

**前端认证 store 异常路径（3 条）**

| 用例 ID | 用例名称 | 结果 |
| --- | --- | --- |
| UT-AU-01 | 登录失败不落盘凭据 | 通过 |
| UT-AU-02 | 登出接口失败仍本地登出 | 通过 |
| UT-AU-03 | 改密失败保留原令牌 | 通过 |

### 3.5 静态检查

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 前端类型检查 | `npm run type-check` | 0 error |
| ESLint（新增/修改文件） | `npx eslint src/utils/__tests__/seatMapLayout.test.ts src/stores/__tests__/auth.test.ts` | 0 error |
| Prettier（新增/修改文件） | `npx prettier --check ...` | 全部符合 |

> 本次执行前 `auth.test.ts` 为 CRLF 行尾，与仓库 `endOfLine: "lf"` 不一致，Prettier 报格式问题；已用 `prettier --write` 规范为 LF（无逻辑改动），复跑后 9 条用例仍全部通过，Prettier 检查通过。

---

## 4. 覆盖率

### 4.1 后端（`pytest --ignore=tests/whitebox --cov=app --cov-branch`）

整体：语句覆盖 **86.2%**（2527 / 2930，未覆盖 403 行）；分支覆盖 **81.0%**（538 / 664，未覆盖 126 个分支）；语句 + 分支综合 **82%**。

本次执行的模块覆盖（节选核心安全与业务模块）：

| 模块 | 语句覆盖率 | 未覆盖行摘要 |
| --- | ---: | --- |
| `app/services/reservation_state.py` | 100% | — |
| `app/services/rate_limit_service.py` | 94% | 69–70（唯一约束冲突后的自增回退分支） |
| `app/services/auth_service.py` | 93% | 91–93、279–285 |
| `app/services/availability_service.py` | 83% | 54–55、82–83、194、209–214、230、272、394、442、444、453、515 等 |
| `app/services/blacklist_service.py` | 76% | 63、116–156、172、181、186、274、283、341、345、354、368、384–386 等 |
| `app/services/reservation_command_service.py` | 77% | 117–118、210–226、249–254、294、296–303、331、339–342、362、375–382 等 |
| `app/services/room_service.py` | 52% | 102–160、169–229、233–235、250、269、273、308–318、333–363、475–482、489–532 等（管理端低频分支） |
| `app/services/violation_service.py` | 65% | 28、48–63、75、89–106、124、155、162–165、173–176、251、269 |
| `app/services/dashboard_service.py` | 80% | 156–181、193、197、326、338、352、371–373 |
| `app/utils/masking.py` | 61% | 19–23、29、33、39、43、59、64–66 |
| `app/tasks/auto_end_reservation.py` | 21% | 20–60 |
| `app/tasks/auto_violation.py` | 27% | 24–66 |
| `app/tasks/login_attempt_cleanup.py` | 56% | 14–17 |
| `app/tasks/scheduler.py` | 53% | 15、21–71、76 |

**低覆盖模块的业务影响与补强状态**

| 模块 | 本次语句覆盖 | 未覆盖内容的业务影响 | 白盒合并后（另一环境，仅参考） |
| --- | ---: | --- | ---: |
| `app/services/room_service.py` | 52% | 管理端创建/修改/关闭/分区低频分支；关闭流程直接影响关闭窗口内预约 | 96% |
| `app/tasks/auto_end_reservation.py` | 21% | 到点自动结束；漏测会导致槽位释放与“已完成”状态流转异常 | 91% |
| `app/tasks/auto_violation.py` | 27% | 自动违约判定；影响违约计数、黑名单触发与通知 | 91% |
| `app/tasks/scheduler.py` | 53% | 调度注册与失败记录；影响定时任务可靠性 | 100% |
| `app/services/blacklist_service.py` | 76% | 限制解除与计数清零；影响重复限制与误封 | 97% |
| `app/services/availability_service.py` | 83% | 可约座位查询边界；错误会放行无效日期/时间查询 | 99% |
| `app/services/reservation_command_service.py` | 77% | 取消/强制取消/幂等分支；影响并发终态与重复通知 | 92% |
| `app/services/violation_service.py` | 65% | 手动/自动违约门槛与幂等；影响违约计数与黑名单触发 | 96% |
| `app/utils/masking.py` | 61% | 联系方式掩码的长度与形态边界；影响脱敏展示 | 100% |

> 本报告基线下管理端与定时任务路径覆盖偏低，属于“已执行范围内未发现缺陷”，不能推定这些路径无缺陷。上述缺口已由《白盒测试报告》的 86 条用例补强（右列），但那组数字来自另一环境（pytest-cov 6.3.0、语句分母 3053），不能与本报告小数直接相减。

### 4.2 前端（`vitest run --coverage`）

配置范围内整体：语句 **93.92%**、分支 **85.06%**、函数 **93.05%**、行 **93.92%**。

| 文件 | 语句 | 分支 | 函数 | 行 |
| --- | ---: | ---: | ---: | ---: |
| `src/stores/auth.ts` | 89.02% | 96.00% | 88.88% | 89.02% |
| `src/stores/message.ts` | 78.94% | 68.18% | 85.71% | 78.94% |
| `src/utils/bookingRules.ts` | 97.24% | 82.65% | 90.32% | 97.24% |
| `src/utils/format.ts` | 100% | 83.33% | 100% | 100% |
| `src/utils/mask.ts` | 100% | 84.37% | 100% | 100% |
| `src/utils/messageLinks.ts` | 100% | 93.10% | 100% | 100% |
| `src/utils/workday.ts` | 100% | 100% | 100% | 100% |

新增布局工具单独统计（不在 `vitest.config.ts` 的 `coverage.include` 列表中，本次用 CLI 单独采集）：

| 文件 | 语句 | 分支 | 函数 | 行 |
| --- | ---: | ---: | ---: | ---: |
| `src/utils/seatMapLayout.ts` | 90.61% | 80.18% | 92.85% | 90.61% |

---

## 5. 缺陷、风险与建议

### 5.1 缺陷统计

| 级别 | 发现 | 已修复 | 遗留 |
| --- | ---: | ---: | ---: |
| P0（数据一致性 / 阻塞） | 0 | 0 | 0 |
| P1（业务规则 / 安全边界） | 0 | 0 | 0 |
| P2（校验 / 配置 / 可维护性） | 0 | 0 | 0 |
| 用例失败或错误 | 0 | — | 0 |

本报告已执行范围（185 后端 + 78 前端）内未发现产品缺陷，也未出现失败用例；这不等于未覆盖的管理端路径与定时任务不存在缺陷（见 §4.1 低覆盖模块表）。历史阶段的缺陷与修复记录见《测试报告-阶段4》。

### 5.2 风险与改进建议

1. **已执行范围内未发现阻塞性缺陷**：263 条用例全部通过；新增布局用例实测四分区均无溢出。
2. **限流并发回退分支未覆盖**：`rate_limit_service.py` 第 69–70 行处理“两个请求同时首次建桶”的唯一约束冲突回退，SQLite 顺序测试难以触发。建议在真实 MySQL + 多 worker 下补一次压测；该分支已由白盒用例覆盖，但真实 MySQL 压测仍未执行。
3. **定时任务调度未纳入集成测试**：测试环境关闭 APScheduler，`auto_end_reservation`（21%）、`auto_violation`（27%）、`login_attempt_cleanup`（56%）、`scheduler`（53%）只有部分函数被执行。建议为任务函数补“冻结时间 + 直接调用”的单元测试，再单独验证调度注册；白盒已补强任务函数，但真实调度仍未覆盖。
4. **前端交互层缺少自动化**：座位悬停信息卡、缩略导航、Ctrl+滚轮缩放属于浏览器行为，当前只覆盖纯布局计算。建议后续补 Playwright E2E 或 Vue Test Utils 组件测试。
5. **数据库差异**：本报告结果基于 SQLite 内存库/文件库，未验证 MySQL 的时间精度、唯一约束错误码与迁移脚本。MySQL 并发与迁移已由《测试报告-阶段4》§8.5 在临时 MySQL 8.0.21 实例验证（4 条并发用例 3 轮通过）；生产库上线前仍需执行 `alembic upgrade head` 并复核。
6. **依赖与产物**：本次使用 pytest-cov 7.1.0，而 `backend/requirements.txt` 限定 `pytest-cov>=6.0,<7.0`；直接 `pip install -r` 会降级到 6.x 并可能改变覆盖率小数。复现前需二选一：放宽清单到 `<8.0`，或把 venv 降到 6.x 后重跑并更新 §4 数字。
7. **改动状态**：本报告引用的 4 个本地文件尚未提交 Git：新增 `backend/tests/test_rate_limit_service.py`、`backend/tests/test_reservation_state.py`、`frontend/src/utils/__tests__/seatMapLayout.test.ts`，修改 `frontend/src/stores/__tests__/auth.test.ts`。本次执行还把 `auth.test.ts` 的 CRLF 行尾规范为 LF（无逻辑改动）。未提交前，本报告的 185 / 78 只能在本机复现，团队基线仍是 174 / 65。
8. **覆盖率配置**：`frontend/vitest.config.ts` 的 `coverage.include` 尚未包含 `src/utils/seatMapLayout.ts`，本次通过 CLI 单独统计；建议后续将其加入 include，避免新增工具类不出现在常规覆盖率报表中。
9. **报告定位**：本报告是本地回归快照，不是全项目质量结论；发布前仍需真实 MySQL、多 worker 限流共享与浏览器 E2E 验证。

---

## 6. 测试结论

- 用例基线内 **263 / 263 通过（100%）**；后端 185 条 28.58 s、前端 78 条 3.81 s；另跑含白盒的全量后端 271 条通过（33.50 s）。
- 覆盖结构：后端语句 86.2%、分支 81.0%；前端语句 93.92%、分支 85.06%；新增布局工具语句 90.61%、分支 80.18%。
- `room_service`（52%）、`violation_service`（65%）、`blacklist_service`（76%）与定时任务（21%–56%）仍是覆盖缺口；这些缺口已由白盒用例补强（另一环境口径），但本报告基线不能据此宣称“管理端无风险”。
- 本轮远端新增的安全逻辑（登录/注册限流、登出令牌撤销、登录失败按 IP 隔离、预约状态条件更新）已有直接用例覆盖；`reservation_state` 覆盖率 100%，`rate_limit_service` 94%。
- 新增前端座位布局用例固化了「筛选不重排地图」等关键约定，布局几何边界无溢出；前端类型检查、ESLint、Prettier 全部通过。
- 结论：本地回归结果满足进入下一阶段（真实 MySQL 联调、多 worker 验证、浏览器 E2E）的前提条件；由于存在上述覆盖缺口，不能替代生产发布前的数据库与端到端验证。

---

## 7. 复现命令与实测输出

```bash
# === 首次准备（在仓库根目录执行；依赖已安装可跳过）===
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
(cd frontend && npm ci)

# === 后端：报告范围（185 条，排除白盒）===
cd backend
.venv/Scripts/python.exe -m pytest --ignore=tests/whitebox
# 实测：185 passed in 28.58s

# 后端：仅 QA 集成套件
.venv/Scripts/python.exe -m pytest tests/qa
# 实测：37 passed in 10.83s

# 后端：覆盖率（语句 + 分支）
.venv/Scripts/python.exe -m pytest --ignore=tests/whitebox \
  --cov=app --cov-branch --cov-report=term-missing
# 实测：TOTAL 82%（语句 86.2%，分支 81.0%）

# 后端：当前全量（含白盒 86 条）
.venv/Scripts/python.exe -m pytest
# 实测：271 passed in 33.50s

# === 前端：单元测试 + 覆盖率 + 类型检查 ===
cd ../frontend
npm test
# 实测：8 files / 78 tests passed，3.81s
npm run test:coverage
# 实测：语句 93.92% / 分支 85.06% / 函数 93.05% / 行 93.92%
npm run type-check
# 实测：0 error

# 前端：规范检查（新增/修改文件）
npx eslint src/utils/__tests__/seatMapLayout.test.ts src/stores/__tests__/auth.test.ts
npx prettier --check src/utils/__tests__/seatMapLayout.test.ts src/stores/__tests__/auth.test.ts
# 实测：0 error；Prettier 全部符合
```

---

## 8. 修订记录

| 日期 | 修订内容 |
| --- | --- |
| 2026-11-25 | 初稿：`a0c94ec` 本地回归，185 后端 + 78 前端，263 / 263 通过。 |
| 2026-11-26 | 补充 §0 报告状态与统计口径；补测并记录后端分支覆盖 81.0%（538/664）；新增低覆盖模块业务影响表；与《测试报告-阶段4》§8.5、《白盒测试报告》建立交叉引用。 |
| 2026-11-26 | 以《测试用例清单(xwj)》v1.2 为用例基线重新生成本报告：按单元/集成层级重算（78 / 107 / 78），重新执行并记录本次实测耗时、覆盖率与覆盖缺口；补记 `auth.test.ts` 行尾规范化；结论仍为 263 / 263 通过。 |
