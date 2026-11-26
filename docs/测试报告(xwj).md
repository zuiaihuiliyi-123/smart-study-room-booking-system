# 智慧自习室预约与管理系统 · 单元与集成测试报告

- 报告日期：2026-11-25（2026-11-26 修订统计口径与交叉引用）
- 代码基线：`main` @ `a0c94ec`（报告写作时与 `origin/main` 一致；当前 `origin/main` 为 `7594cae`，应用代码未变）
- 测试环境：
  - 操作系统：Windows 10.0.26200.9974（x64）
  - 后端：Python 3.14.2、pytest 8.4.2、pytest-cov 7.1.0、SQLAlchemy 2.0.57、FastAPI 0.162.5
  - 前端：Node.js v24.21.0、npm 11.19.0、Vitest 2.1.9、happy-dom
- 执行方式：本地执行，新增用例与仓库原有回归用例一起运行
- 总结论：**通过**。后端 185 个用例、前端 78 个用例全部通过；TypeScript 类型检查与 ESLint 均无错误。

## 0. 报告状态与统计口径

| 项目 | 内容 |
| --- | --- |
| 报告性质 | 本地回归快照（初稿），用于验证本地新增用例与既有回归，不是团队发布口径 |
| 基线 | `main` @ `a0c94ec`。应用代码与当前 `origin/main` `7594cae` 相同，后者仅新增白盒用例与文档 |
| 本报告范围 | 后端 185（既有 174 + 本地新增 11）+ 前端 78（既有 65 + 本地新增 13）= **263** |
| 当前仓库全量 | 后端 **271**（185 + 白盒 86）+ 前端 78 = **349**（2026-11-26 复核） |
| 复现限制 | 引用的 4 个本地测试文件尚未提交（清单见 §6.2 第 7 条）；其他人克隆仓库只能复现远端基线 174 + 65 |
| 关联报告 | 缺陷发现与修复见《测试报告-阶段4》；覆盖率补强见《白盒测试报告》；本报告定位为本地回归快照 |
| 依赖口径 | 本报告环境为 pytest-cov 7.1.0；当前 `requirements.txt` 限定 `>=6.0,<7.0`，两者需统一后才能逐位复现覆盖率小数（见 §6.2 第 6 条） |

---

## 1. 测试目的与依据

- 测试目的：对更新后的本地基线（`a0c94ec`）做一轮可复现的单元与集成回归，重点验证本轮远端引入的安全加固（限流、登出撤销、登录失败按 IP 隔离、预约状态原子流转）与座位图布局改动，并补充此前没有直接用例覆盖的 service 层逻辑。
- 测试依据：
  - 《智慧自习室预约与管理系统-需求规格说明书（课程结构版）》V2.2
  - `docs/测试用例清单-阶段2.md`（用例设计与裁决口径）
  - `docs/测试报告-阶段4.md`（历史缺陷与修复回归）
  - 仓库测试配置：`backend/pytest.ini`、`backend/tests/conftest.py`、`frontend/vitest.config.ts`
- 入口准则：代码可导入、测试依赖可用、无阻塞性环境问题（本次均已满足）。
- 出口准则：全量自动化用例通过率 100%；无 P0/P1 缺陷；前端类型检查与代码规范检查通过。覆盖率仅作为观察指标，项目未配置强制阈值。

---

## 2. 测试范围与策略

| 层级 | 覆盖内容 | 实现方式 | 是否执行 |
| --- | --- | --- | --- |
| 后端单元测试 | 限流固定窗口、预约状态原子流转 | 直接调用 service 函数 + 内存 SQLite | 是 |
| 后端集成测试 | API 路由、参数校验、权限、状态机、并发、限流与登录锁定 | FastAPI `TestClient` + 内存 SQLite（覆盖 `get_db`） | 是 |
| 前端单元测试 | 座位布局几何、座位筛选契约、登录态与异常路径 | Vitest + happy-dom，mock API 层 | 是 |
| 前端类型/规范 | TypeScript 类型、ESLint | `vue-tsc --noEmit`、`eslint` | 是 |
| 浏览器 E2E | 座位图悬停卡、缩略导航、Ctrl+滚轮缩放等交互 | Playwright | 未执行（需启动前后端与浏览器） |
| 真实数据库 | MySQL 并发、迁移、多 worker 限流共享 | 本机 MySQL | 本报告范围未执行（测试使用 SQLite）；MySQL 并发与迁移已由《测试报告-阶段4》§8.5 单独验证 |

测试基座说明：`backend/tests/conftest.py` 为每个用例创建独立的内存 SQLite 数据库，并关闭 APScheduler，因此测试不会读写本机真实数据库。

测试数据与隔离：

- 后端每个用例独享内存 SQLite（`sqlite://` + `StaticPool`），通过 `make_user` / `make_room` / `make_seat` / `make_reservation` 工厂构造数据；时间敏感用例通过冻结 `time_utils.now()` 或显式传入 `now` 固定时钟。
- 前端使用 Vitest + happy-dom，API 层通过 `vi.mock` 替换，`localStorage` / `sessionStorage` 在每个用例前后清空。
- 集成用例通过 FastAPI `TestClient` 覆盖 `get_db` 依赖，真实经过路由、服务层与 ORM，不启动真实 MySQL 与调度器。

执行边界：

- 本报告不验证真实 MySQL 的并发锁、迁移脚本与多 worker 限流共享；这部分由《测试报告-阶段4》§8.5 的临时 MySQL 8.0.21 实例单独覆盖。
- 不执行 Playwright E2E 与浏览器视觉验收；座位图交互仅覆盖布局计算。

---

## 3. 新增测试用例

### 3.1 后端新增用例（11 个）

文件：`backend/tests/test_rate_limit_service.py`

| 用例 ID | 用例名称 | 验证点 / 预期 | 结果 |
| --- | --- | --- | --- |
| UT-RL-01 | 首次命中建桶并整分钟对齐 | 返回 1；`window_start=10:30:00`；scope/key 正确 | 通过 |
| UT-RL-02 | 窗口内累计且只保留一行 | 连续 3 次返回 1、2、3；桶表仅 1 行且 hits=3 | 通过 |
| UT-RL-03 | 上限边界与 429 响应 | 第 3 次仍放行；第 4 次抛 `RATE_LIMITED`（429），`Retry-After=18` | 通过 |
| UT-RL-04 | IP 与接口维度隔离 | 一个 IP 超限不影响其他 IP；login 与 register 独立计数 | 通过 |
| UT-RL-05 | 跨窗口重新计数 | 10:31:01 新窗口计数从 1 开始；旧窗口记录保留 | 通过 |
| UT-RL-06 | 自定义 30 秒窗口对齐 | `window_start=10:30:30`，按窗口长度向下对齐 | 通过 |
| UT-RL-07 | 过期窗口清理 | 2 天前的桶被删除，1 小时前的桶与新桶保留 | 通过 |

文件：`backend/tests/test_reservation_state.py`

| 用例 ID | 用例名称 | 验证点 / 预期 | 结果 |
| --- | --- | --- | --- |
| UT-RS-01 | 状态匹配时原子写入 | 待使用 → 已取消，状态、取消时间、原因一并写入 | 通过 |
| UT-RS-02 | 状态不匹配不写入 | 已完成预约保持原样，返回 False | 通过 |
| UT-RS-03 | 重复流转仅首次成功 | 两次「待使用 → 已取消」返回 True/False，原因保留第一次 | 通过 |
| UT-RS-04 | 不提交事务、可回滚 | 事务内可见更新；回滚后状态恢复为待使用 | 通过 |

### 3.2 前端新增用例（13 个）

文件：`frontend/src/utils/__tests__/seatMapLayout.test.ts`

| 用例 ID | 用例名称 | 验证点 / 预期 | 结果 |
| --- | --- | --- | --- |
| UT-SM-01 | 空输入返回默认布局 | 空 groups/空 cells 返回 760×580 空布局 | 通过 |
| UT-SM-02 | 座位与椅子一一对应 | 椅子数=座位数、座位 id 不重复、桌子 id 唯一 | 通过 |
| UT-SM-03 | 相同输入可复现 | 同一输入两次构建结果完全一致 | 通过 |
| UT-SM-04 | 筛选不重排布局（回归） | `matched` 标记变化不影响分区、桌子、椅子坐标 | 通过 |
| UT-SM-05 | 中央区 2 人桌拆分 | 5 个座位拆为 3 张桌，每桌不超过 2 座 | 通过 |
| UT-SM-06 | 桌号取座位号前缀 | `B-01` 所在桌编号为 `B1` | 通过 |
| UT-SM-07 | 分区名称推断与标签 | 「窗边静区」「电源长桌」识别为 window/power，并带「窗」「电」标签 | 通过 |
| UT-SM-08 | 属性推断与 hasWindow | 名称无线索时按靠窗/插座属性推断；任一靠窗座位使 `hasWindow=true` | 通过 |
| UT-SM-09 | 窗边区 4 人桌拆分 | 6 个座位拆为 2 张桌 | 通过 |
| UT-SM-10 | 桌椅不越出分区 | 四分区（窗边/电源/静音/中央）的桌与椅均在所属分区边界内 | 通过 |

文件：`frontend/src/stores/__tests__/auth.test.ts`（在原有用例基础上新增）

| 用例 ID | 用例名称 | 验证点 / 预期 | 结果 |
| --- | --- | --- | --- |
| UT-AU-01 | 登录失败不落盘凭据 | 接口 reject 后无 token/user，两种存储均为空 | 通过 |
| UT-AU-02 | 登出接口失败仍本地登出 | 服务端 401/网络错误不阻断，本地状态与存储清空 | 通过 |
| UT-AU-03 | 改密失败保留原令牌 | 旧密码错误时当前会话不被踢下线 | 通过 |

---

## 4. 执行统计

| 套件 | 命令 | 用例数 | 结果 | 耗时 |
| --- | --- | --- | --- | --- |
| 后端全量（本报告范围，排除白盒） | `python -m pytest --ignore=tests/whitebox` | 185 | 185 passed | 31.41 s |
| 后端 QA 集成（全量子集） | `python -m pytest tests/qa` | 37 | 37 passed | 14.75 s |
| 前端全量 | `npm test` / `npm run test:coverage` | 78（8 个文件） | 78 passed | 3.88 s |
| 前端类型检查 | `npm run type-check` | — | 0 error | — |
| 前端 ESLint（新增/修改文件） | `npx eslint ...` | — | 0 error | — |
| 前端 Prettier（新增/修改文件） | `npx prettier --check ...` | — | 0 error | — |

通过率：**263 / 263 = 100%**（后端 185 + 前端 78）。后端 QA 套件为全量子集，不重复计入。

说明：

- 后端原有 174 个用例，本次新增 11 个，共 185 个；前端原有 65 个，本次新增 13 个，共 78 个。
- `tests/qa` 是集成度最高的子集（真实路由 + 服务层 + ORM + 权限/并发），单独执行用于确认集成链路。
- 全量后端运行包含该子集，因此两行数据存在包含关系，不重复计数。
- **快照说明**：上表是 `a0c94ec` 的数字。2026-11-26 合并远端白盒用例后复核，后端全量为 **271 passed**（185 + 86 白盒），前端仍 **78 passed**；本报告的 185 不包含白盒补充用例，两组数字不冲突。

### 4.1 后端执行分布（24 个文件，185 个用例）

| 文件 | 用例数 | 结果 |
| --- | --- | --- |
| `tests/qa/test_qa_boundaries.py` | 15 | 通过 |
| `tests/qa/test_qa_state_security.py` | 18 | 通过 |
| `tests/qa/test_qa_concurrency.py` | 4 | 通过 |
| `tests/test_api_audit.py` | 2 | 通过 |
| `tests/test_api_dashboard_top.py` | 2 | 通过 |
| `tests/test_api_fixes.py` | 6 | 通过 |
| `tests/test_api_flow.py` | 2 | 通过 |
| `tests/test_api_login_lock.py` | 6 | 通过 |
| `tests/test_api_password.py` | 3 | 通过 |
| `tests/test_api_phase2.py` | 6 | 通过 |
| `tests/test_api_reviews.py` | 2 | 通过 |
| `tests/test_api_skeleton.py` | 5 | 通过 |
| `tests/test_auth_register.py` | 7 | 通过 |
| `tests/test_backend_hardening.py` | 7 | 通过 |
| `tests/test_blocking_fixes.py` | 26 | 通过 |
| `tests/test_bootstrap_db.py` | 8 | 通过 |
| `tests/test_concurrency.py` | 2 | 通过 |
| `tests/test_health.py` | 1 | 通过 |
| `tests/test_m1_resource.py` | 16 | 通过 |
| `tests/test_m2_m3_flow.py` | 9 | 通过 |
| `tests/test_m5_governance.py` | 22 | 通过 |
| `tests/test_rate_limit_service.py` | 7 | 通过 |
| `tests/test_reservation_state.py` | 4 | 通过 |
| `tests/test_time_utils.py` | 5 | 通过 |

### 4.2 前端执行分布（8 个文件，78 个用例）

| 文件 | 用例数 | 结果 |
| --- | --- | --- |
| `src/utils/__tests__/bookingRules.test.ts` | 24 | 通过 |
| `src/utils/__tests__/seatMapLayout.test.ts` | 10 | 通过 |
| `src/stores/__tests__/auth.test.ts` | 9 | 通过 |
| `src/utils/__tests__/messageLinks.test.ts` | 8 | 通过 |
| `src/utils/__tests__/format.test.ts` | 7 | 通过 |
| `src/utils/__tests__/mask.test.ts` | 7 | 通过 |
| `src/utils/__tests__/workday.test.ts` | 7 | 通过 |
| `src/stores/__tests__/message.test.ts` | 6 | 通过 |

---

## 5. 覆盖率

### 5.1 后端（`pytest --cov=app --cov-branch`）

整体：语句覆盖 **86.2%**（2527 / 2930，未覆盖 403 行）；分支覆盖 **81.0%**（538 / 664，未覆盖 126 个分支）；语句 + 分支综合 **82%**（2026-11-26 复核，185 passed）。

> 口径说明：本报告使用 Python 3.14.2 + pytest-cov 7.1.0；《白盒测试报告》使用另一环境（pytest-cov 6.3.0，语句分母 3053），其“补充前”语句覆盖 86.8%、分支覆盖 81.0%（538/664）。两边分支口径一致，语句分母不同，覆盖率小数不能直接横向比较。初稿记录“86% / 未覆盖 406 行”，本次复核为 86.2% / 403 行，差异来自统计环境，结论不变。

本次新增代码及核心安全模块：

| 模块 | 语句覆盖率 | 未覆盖行 |
| --- | --- | --- |
| `app/services/reservation_state.py` | 100% | — |
| `app/services/rate_limit_service.py` | 93% | 69–70（唯一约束冲突后的自增回退分支） |
| `app/services/auth_service.py` | 93% | 91–93、279–285 |
| `app/services/availability_service.py` | 87% | 54–55、82–83、194、209–214 等 |
| `app/services/blacklist_service.py` | 82% | 63、116–156、172 等 |
| `app/services/reservation_command_service.py` | 80% | 117–118、203–226、249–254 等 |
| `app/services/room_service.py` | 58% | 102–160、169–229、475–482 等（管理端低频分支） |
| `app/tasks/auto_end_reservation.py` | 27% | 20–60 |
| `app/tasks/auto_violation.py` | 36% | 24–66 |
| `app/tasks/login_attempt_cleanup.py` | 56% | 14–17 |
| `app/tasks/scheduler.py` | 58% | 15、21–71、76 |

**低覆盖模块的业务影响与后续状态**

| 模块 | 本报告语句覆盖 | 未覆盖内容的业务影响 | 白盒合并后（另一环境，仅参考） |
| --- | ---: | --- | ---: |
| `app/services/room_service.py` | 58% | 管理端创建/修改/关闭/分区低频分支；关闭流程直接影响关闭窗口内预约 | 96% |
| `app/tasks/auto_end_reservation.py` | 27% | 到点自动结束；漏测会导致槽位释放与“已完成”状态流转异常 | 91% |
| `app/tasks/auto_violation.py` | 36% | 自动违约判定；影响违约计数、黑名单触发与通知 | 91% |
| `app/tasks/scheduler.py` | 58% | 调度注册与失败记录；影响定时任务可靠性 | 100% |
| `app/services/availability_service.py` | 87% | 可约座位查询边界；错误会放行无效日期/时间查询 | 99% |
| `app/services/blacklist_service.py` | 82% | 限制解除与计数清零；影响重复限制与误封 | 97% |
| `app/services/reservation_command_service.py` | 80% | 取消/强制取消/幂等分支；影响并发终态与重复通知 | 92% |

> 本报告基线下管理端与定时任务路径覆盖偏低，属于“已执行范围内未发现缺陷”，不能推定这些路径无缺陷。上述缺口已由《白盒测试报告》的 86 条用例补强（右列），但那组数字来自另一环境，不能与本报告小数直接相减。

### 5.2 前端（`vitest run --coverage`）

配置范围内整体：语句 **93.92%**、分支 **85.06%**、函数 **93.05%**、行 **93.92%**。

| 文件 | 语句 | 分支 | 函数 | 行 |
| --- | --- | --- | --- | --- |
| `src/stores/auth.ts` | 89.02% | 96.00% | 88.88% | 89.02% |
| `src/stores/message.ts` | 78.94% | 68.18% | 85.71% | 78.94% |
| `src/utils/bookingRules.ts` | 97.24% | 82.65% | 90.32% | 97.24% |
| `src/utils/format.ts` | 100% | 83.33% | 100% | 100% |
| `src/utils/mask.ts` | 100% | 84.37% | 100% | 100% |
| `src/utils/messageLinks.ts` | 100% | 93.10% | 100% | 100% |
| `src/utils/workday.ts` | 100% | 100% | 100% | 100% |

新增布局工具单独统计（不在 vitest 配置的 coverage include 列表中）：

| 文件 | 语句 | 分支 | 函数 | 行 |
| --- | --- | --- | --- | --- |
| `src/utils/seatMapLayout.ts` | 90.61% | 80.18% | 92.85% | 90.61% |

---

## 6. 缺陷、风险与建议

### 6.1 缺陷统计

| 级别 | 发现 | 已修复 | 遗留 |
| --- | --- | --- | --- |
| P0（数据一致性 / 阻塞） | 0 | 0 | 0 |
| P1（业务规则 / 安全边界） | 0 | 0 | 0 |
| P2（校验 / 配置 / 可维护性） | 0 | 0 | 0 |
| 用例失败或错误 | 0 | — | 0 |

本报告已执行范围（185 后端 + 78 前端）内未发现产品缺陷，也未出现失败用例；这不等于未覆盖的管理端路径与定时任务不存在缺陷（见 §5.1 低覆盖模块表）。历史阶段的缺陷与修复记录见 `docs/测试报告-阶段4.md`。

### 6.2 风险与改进建议

1. **已执行范围内未发现阻塞性缺陷**：新增与既有用例全部通过，未出现失败或错误；布局边界探针实测四分区均无溢出。
2. **并发插入回退分支未覆盖**：`rate_limit_service.py` 第 69–70 行处理「两个请求同时首次建桶」的唯一约束冲突回退，SQLite 顺序测试难以触发。建议在真实 MySQL + 多 worker 下补一次压测，或使用线程并发用例验证。该分支已由白盒用例 `tests/whitebox/test_whitebox_rate_limit.py` 覆盖（《白盒测试报告》`rate_limit_service` 100%）；真实 MySQL + 多 worker 压测仍未执行。
3. **定时任务调度未纳入集成测试**：测试环境关闭 APScheduler，`auto_end_reservation`、`auto_violation`、`login_attempt_cleanup` 只有部分函数被执行。建议为任务函数补「冻结时间 + 直接调用」的单元测试，再单独验证调度注册。任务函数已由白盒 `tests/whitebox/test_whitebox_tasks.py`（11 条）补强，`tasks` 覆盖提升至 91%–100%；真实 APScheduler 调度集成仍未覆盖。
4. **前端交互层缺少自动化**：座位悬停信息卡、缩略导航、Ctrl+滚轮缩放属于浏览器行为，当前只覆盖纯布局计算。建议后续补 Playwright E2E 或 Vue Test Utils 组件测试。
5. **数据库差异**：本报告结果基于 SQLite 内存库，未验证 MySQL 的时间精度、唯一约束错误码与迁移脚本。MySQL 并发与迁移已由《测试报告-阶段4》§8.5 在临时 MySQL 8.0.21 实例验证（4 条并发用例 3 轮通过）；生产库上线前仍需执行 `alembic upgrade head` 并复核。
6. **依赖与产物**：本报告用 pytest-cov 7.1.0 采集覆盖率；当前 `backend/requirements.txt` 限定 `pytest-cov>=6.0,<7.0`（与远端一致），直接执行 `pip install -r` 会降级到 6.x 并可能改变覆盖率小数。复现前需二选一：放宽清单到 `<8.0`，或把 venv 降到 6.x 后重跑并更新 §5 数字。前端覆盖率输出目录已在 `.gitignore` 中；仓库仍跟踪 `frontend/.tmp`（2,612 个文件）与 `frontend/dist`（7 个文件，2026-11-26 核对），建议后续清理。
7. **改动状态**：本报告引用的 4 个本地文件尚未提交 Git：新增 `backend/tests/test_rate_limit_service.py`、`backend/tests/test_reservation_state.py`、`frontend/src/utils/__tests__/seatMapLayout.test.ts`，修改 `frontend/src/stores/__tests__/auth.test.ts`。初稿时另有一处依赖清单修改（pytest-cov 行）；2026-11-26 同步远端后该行已与 `origin/main` 一致（`>=6.0,<7.0`），不再构成本地差异，但与本报告 venv 的 7.1.0 不一致（见第 6 条）。未提交前，本报告的 185 / 78 只能在本机复现，团队基线仍是 174 / 65。
8. **覆盖率配置**：`frontend/vitest.config.ts` 的 `coverage.include` 尚未包含 `src/utils/seatMapLayout.ts`，本次通过 CLI 单独统计；建议后续将其加入 include，避免新增工具类不出现在常规覆盖率报表中。截至 2026-11-26 该项仍未处理。
9. **报告定位**：本报告是本地回归快照，不是全项目质量结论；发布前仍需真实 MySQL、多 worker 限流共享与浏览器 E2E 验证。

---

## 7. 测试结论

- 基线 `a0c94ec` 的本地自动化回归全部通过（263 / 263，通过率 100%）；在已执行范围内未发现 P0/P1/P2 缺陷。
- 覆盖结构：后端语句 86.2%、分支 81.0%；`room_service` 58%、`tasks` 21%–36% 等管理端与定时任务路径仍是缺口。这些缺口已由《白盒测试报告》补强（合并后后端语句 97.0%、分支 91.3%，另一环境口径），但本报告基线本身不能据此宣称“管理端无风险”。
- 本轮远端新增的安全逻辑（登录/注册限流、登出令牌撤销、登录失败按 IP 隔离、预约状态条件更新）已有直接用例覆盖；`reservation_state` 覆盖率 100%，`rate_limit_service` 93%。
- 新增前端座位布局用例固化了「筛选不重排地图」等关键约定，布局几何边界无溢出；前端类型检查、ESLint、Prettier 全部通过。
- 结论：本地回归结果满足进入下一阶段（真实 MySQL 联调、多 worker 验证、浏览器 E2E）的前提条件；由于存在上述覆盖缺口，不能替代生产发布前的数据库与端到端验证。

---

## 8. 复现命令

```bash
# === 首次准备（在仓库根目录执行；依赖已安装可跳过）===
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
(cd frontend && npm ci)

# === 后端：本报告范围（185 条，排除白盒）===
cd backend
.venv/Scripts/python.exe -m pytest --ignore=tests/whitebox

# 后端：仅 QA 集成套件
.venv/Scripts/python.exe -m pytest tests/qa

# 后端：覆盖率（本报告口径：语句 + 分支）
.venv/Scripts/python.exe -m pytest --ignore=tests/whitebox --cov=app --cov-branch --cov-report=term-missing

# 后端：当前全量（271 条，含白盒 86 条）
.venv/Scripts/python.exe -m pytest

# === 前端：单元测试 + 覆盖率 + 类型检查 ===
cd ../frontend
npm test
npm run test:coverage
npm run type-check

# 前端：规范检查（新增/修改文件）
npx eslint src/utils/__tests__/seatMapLayout.test.ts src/stores/__tests__/auth.test.ts
npx prettier --check src/utils/__tests__/seatMapLayout.test.ts src/stores/__tests__/auth.test.ts
```

---

## 9. 修订记录

| 日期 | 修订内容 |
| --- | --- |
| 2026-11-25 | 初稿：`a0c94ec` 本地回归，185 后端 + 78 前端，263 / 263 通过。 |
| 2026-11-26 | 补充 §0 报告状态与统计口径；补测并记录后端分支覆盖 81.0%（538/664）；新增 §5.1 低覆盖模块业务影响表；与《测试报告-阶段4》§8.5、《白盒测试报告》建立交叉引用；更新依赖版本、未提交文件与仓库卫生说明。测试结果未变，仍为 263 / 263 通过。 |
