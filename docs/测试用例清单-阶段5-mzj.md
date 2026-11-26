# 智慧自习室预约与管理系统 · 测试用例清单（阶段 5 · mzj）

- 版本：v1.0
- 日期：2026-11-26
- 代码基线：`main` @ `7594cae`（执行前已 `git pull --ff-only`，与 `origin/main` 一致）
- 责任人：mzj
- 范围：认证/权限 + M5（用户、投诉、评价、审计）+ M6 数据看板 + M7 站内消息
- 依据：需求规格说明书（课程结构版）、`AGENTS.md` §5/§10、`docs/测试用例清单-阶段2.md`（TC-XXX-NN）

> 编号规则：`TC-U-*` 为单元测试（不经过 HTTP），`TC-I-*` 为集成测试（TestClient + 数据库），`TC-F-*` 为前端 composable 单测。
> 断言统一三层：HTTP 状态码 → 业务 `code`/关键字段 → 数据库终态。
> 本文“结果”为 2026-11-26 本轮真实执行结果，未执行项单独标注。

---

## 1. 用例与执行汇总

| 层次 | 用例条目 | 实际执行 | 通过 | 失败 | 文件 |
|---|---:|---:|---:|---:|---|
| 后端单元 | 31 | 36（含参数化展开 5） | 36 | 0 | `backend/tests/mzj/unit/` |
| 后端集成 | 24 | 24 | 24 | 0 | `backend/tests/mzj/integration/` |
| 前端单元 | 13 | 13 | 13 | 0 | `frontend/src/utils/__tests__/` |
| **合计** | **68** | **73** | **73** | **0** | — |

按模块：认证/权限 15、M5 用户 8、M5 投诉 11、M5 评价 4、M5 审计 2、M6 看板 11、M7 消息 7、前端 13。

---

## 2. 认证与权限

### 2.1 单元测试（`unit/test_auth_rules.py`）

| ID | 断言点 | 预期 | 结果 |
|---|---|---|---|
| TC-U-AUTH-01 | `_normalize_ip`：None / 全空白 / IPv6 / 50 字符超长 | 依次 `unknown`、`unknown`、原样、截断到 45 | 通过 |
| TC-U-AUTH-02 | `_lock_remaining_minutes`：-30s、0.5s、59s、60s、61s、120s | 均向上取整且至少 1 分钟 → 1/1/1/1/2/2 | 通过（6 组参数） |
| TC-U-AUTH-03 | `_registration_whitelist`：空串；逗号/分号/换行混排并含重复项 | 空集合；`{S1,S2,S3,S4}` | 通过 |
| TC-U-AUTH-04 | 失败窗口外的历史失败记录 | 窗口重置后本次失败只计 1 次，`first_failed_at=now` | 通过 |
| TC-U-AUTH-05 | 第 5 次失败达到阈值 | 返回 `now+15min` 锁定时间、写入 `locked_until`、审计 `LOGIN_LOCKED` | 通过 |
| TC-U-AUTH-06 | 并发首写同一「学号+IP」触发唯一键冲突 | 回滚重读后成功累加到 2 次，不抛 500、不返回锁定 | 通过 |

### 2.2 集成测试（`integration/test_auth_permission_flow.py`）

| ID | 前置/步骤 | 预期 | 结果 |
|---|---|---|---|
| TC-I-AUTH-01 | 学生访问 `/users`、`/audit-logs`、`/dashboard/overview`、`/complaints`、`/reviews` | 5 个接口均 403，并写入 5 条 `UNAUTHORIZED_ATTEMPT` 审计（`target_type=api`） | 通过 |
| TC-I-AUTH-02 | 管理员提交投诉/评价；访问管理端接口 | 学生专属接口 403；`/users/me`、`/users`、`/audit-logs`、`/dashboard/overview` 均 200 | 通过 |
| TC-I-AUTH-03 | 系统管理员访问 4 个业务管理接口 | 全部 403（R-04 无业务权限） | 通过 |
| TC-I-AUTH-04 | 登录 → 登出 → 旧令牌访问 → 重新登录 → 旧令牌再登出 | 依次 200 / 200 / 401 / 200 / 401 | 通过 |
| TC-I-AUTH-05 | 改密后旧令牌访问、新令牌访问、查审计 | 旧令牌 401、新令牌 200；审计 `PASSWORD_CHANGED` 不含明文口令与 `$2b$` 哈希 | 通过 |
| TC-I-AUTH-06 | 停用账户（存在失败计数）登录；再用已签发令牌访问 `/auth/me` | 登录 403 `ACCOUNT_DISABLED`；失败计数被清除；令牌访问 403 | 通过 |

---

## 3. M5 用户管理

### 3.1 单元（`unit/test_user_masking.py`）

| ID | 断言点 | 预期 | 结果 |
|---|---|---|---|
| TC-U-USER-01 | 管理员视角 / 本人视角读取联系方式 | 手机 `138****1234`、邮箱 `s******@zju.edu.cn`、空值 `—`；本人保持明文 | 通过 |
| TC-U-USER-02 | `_restrict_until`：手动限制、自动限制、已解除、已过期 | 仅未解除且未到期的自动限制返回 `expire_at`，其余 `None` | 通过 |
| TC-U-USER-03 | `list_users(keyword="   ")` 与 `keyword="%"` | 当前实现均返回全部用户（记录为 S1-11 LIKE 通配符观察项） | 通过（观察项） |
| TC-U-USER-04 | `list_users(page=5)` 越界 | `items=[]`，`total` 不变，`page` 回显 5 | 通过 |

### 3.2 集成（`integration/test_m5_user_flow.py`）

| ID | 前置/步骤 | 预期 | 结果 |
|---|---|---|---|
| TC-I-USER-01 | 管理员拉取用户列表；本人读 `/users/me`；存在自动/手动限制 | 列表联系方式脱敏；自动限制 `restrict_until=2026-12-02T10:00:00`，手动为 `null`；本人明文 | 通过 |
| TC-I-USER-02 | 管理员停用 → 学生登录 → 恢复 → 再登录 | 停用 200；登录 403 `ACCOUNT_DISABLED`；恢复 200；再登录 200；审计两条 `ACCOUNT_STATUS_UPDATE`（正常→停用、停用→正常） | 通过 |
| TC-I-USER-03 | 关键词筛选 + 第 2 页 + 角色筛选 | 关键词 total=3；第 2 页 1 条；管理员角色 total=1 | 通过 |

---

## 4. M5 投诉

### 4.1 单元（`unit/test_complaint_rules.py`）

| ID | 断言点 | 预期 | 结果 |
|---|---|---|---|
| TC-U-COMP-01 | 管理员状态迁移表不变量 | 待处理→{处理中,已驳回}；处理中→{已处理}；已处理/已驳回/已关闭无管理员迁移 | 通过 |
| TC-U-COMP-02 | `_ensure_target_exists` 四类对象 + 不存在 + 非法类型 | 四类均通过；不存在 404 `COMPLAINT_TARGET_NOT_FOUND`；非法 422 `COMPLAINT_TARGET_TYPE_INVALID` | 通过 |
| TC-U-COMP-03 | `close_stale` 恰好 7 天 / 7 天零 1 秒 / 重复执行 | 前者关闭且发 1 条消息；后者不关；第二次返回 0 且不重复发消息 | 通过 |
| TC-U-COMP-04 | 处理说明全空白 / 前后空格 / 审计 | 空白 422 `COMPLAINT_NOTE_REQUIRED`；`"  已受理  "` 落库为 `已受理`；审计 before/after 正确 | 通过 |
| TC-U-COMP-05 | 非本人确认、非「已处理」确认、已关闭再确认 | 403 `COMPLAINT_NOT_OWNER`；409 + `details.status`；409 | 通过 |
| TC-U-COMP-06 | `created_to` 当天边界 | 23:59:59 命中、次日 00:00 不命中，`total=1` | 通过 |

### 4.2 集成（`integration/test_m5_complaint_flow.py`）

| ID | 前置/步骤 | 预期 | 结果 |
|---|---|---|---|
| TC-I-COMP-01 | 学生对座位/自习室/预约单/用户各提交 1 条投诉 | 4 条均 201，初始状态「待处理」 | 通过 |
| TC-I-COMP-02 | 提交 → 受理 → 处理 → 学生未读/列表 → 确认关闭 | 两次处理各发 1 条「投诉反馈」；未读 2；确认后「已关闭」；审计处理 2 条 + 确认 1 条 | 通过 |
| TC-I-COMP-03 | 学生查全量/处理；他人确认；管理员确认；已关闭再处理 | 403 / 403 / 403 `COMPLAINT_NOT_OWNER` / 403 / 409 `COMPLAINT_STATE_INVALID` | 通过 |
| TC-I-COMP-04 | 状态、对象类型、提交人、关键词、分页筛选 | 待处理 2；自习室 2；指定用户 1；关键词 1；第 2 页 1 条且 total=3 | 通过 |
| TC-I-COMP-05 | 管理员驳回待处理投诉 | 200，状态「已驳回」；学生 `/complaints/me` 可见 | 通过 |

---

## 5. M5 评价

| ID | 层次/文件 | 前置/步骤 | 预期 | 结果 |
|---|---|---|---|---|
| TC-U-REVIEW-01 | 单元 `test_review_rules.py` | 绕过预检后重复提交同一预约单 | 唯一约束触发 → 409 `REVIEW_ALREADY_EXISTS`，且已回滚（并发分支覆盖） | 通过 |
| TC-U-REVIEW-02 | 单元 | score=0/6、content=500/501 | 0/6 与 501 均校验失败；500 通过 | 通过 |
| TC-U-REVIEW-03 | 单元 | `created_to` 当天 23:59:59 / 次日 00:00 | 仅当天记录命中 | 通过 |
| TC-U-REVIEW-04 | 单元 | 本人 3 条、他人 1 条，按 2 条分页 | total 3；第 1 页 2 条、第 2 页 1 条；他人 total 1 | 通过 |
| TC-I-REVIEW-01 | 集成 `test_m5_review_audit_flow.py` | 完成预约评价、重复、他人、未完成、score=6、管理员筛选、本人列表 | 201 / 409 / 403 / 409 / 422；管理员 score=5 total 1；本人 1、他人 0 | 通过 |

---

## 6. M5 审计

| ID | 层次 | 前置/步骤 | 预期 | 结果 |
|---|---|---|---|---|
| TC-I-AUDIT-01 | 集成 | 依次制造登录失败、越权、投诉处理、账户停用、登出；再按动作/操作人/日期/分页查询 | 5 类动作均有记录；动作筛选 total=1；操作人 ≥3；当日 ≥5；`page_size=1` 返回 1 条且 total ≥5 | 通过 |
| TC-I-AUDIT-02 | 集成 | 改密后以管理员查询审计列表 | 响应全文不含新旧口令、`$2b$`、`access_token` | 通过 |

---

## 7. M6 数据看板

### 7.1 单元（`unit/test_dashboard_metrics.py`）

| ID | 断言点 | 预期 | 结果 |
|---|---|---|---|
| TC-U-DASH-01 | `get_seat_usage`：30min / 4h / 5min / 已取消 / 已违约 / 跨房间 | 同一座位计 1+8+0=9；取消/违约不计；房间过滤生效；备用座位为 0 | 通过 |
| TC-U-DASH-02 | 单房单座单日 08–10 桶 | capacity=4、occupied=1.0、rate=0.25；空桶 0 | 通过 |
| TC-U-DASH-03 | 5 分钟短预约折算 | occupied=0.17、rate=0.0425（不因整数除法归零） | 通过 |
| TC-U-DASH-04 | 无座位房间、结束早于开始 | 7 个时段桶 capacity=0/rate=0；倒置区间返回 `[]` | 通过 |
| TC-U-DASH-05 | `get_overview` 房间过滤 | 房间内可用座位 2、使用中 1、今日预约 2、今日违约 1；全局 3/2/3/1；受限账户始终全局 1 | 通过 |
| TC-U-DASH-06 | `get_violation_top` | 只统计学生（total=5）；limit=2；并列按 `user_id` 升序；姓名学号齐全 | 通过 |
| TC-U-DASH-07 | `get_trend` 区间与去重 | 2 天返回 2 点；同日签到+签退计 1；32 天返回 `[]`；31 天返回 31 点 | 通过 |

### 7.2 集成（`integration/test_m6_dashboard_api.py`）

| ID | 前置/步骤 | 预期 | 结果 |
|---|---|---|---|
| TC-I-DASH-01 | 种子数据后查询 overview（带/不带 room_id） | 房间口径 `{2,1,2,1,1}`；全局 `{3,2,3,1,1}` | 通过 |
| TC-I-DASH-02 | seat-usage（seat/slot）、trend、32 天、倒置、非法 group_by、limit=0/51、学生访问 | 正常 200（trend 7 点）；超区间/倒置 422 `INVALID_ARGUMENT`；非法分组与 limit 422；学生 403 | 通过 |
| TC-I-DASH-03 | 连续两次 overview、换 room_id、清缓存 | 服务层调用 1→2→3 次，缓存 key 含 `room_id` | 通过 |
| TC-I-DASH-04 | 违约 Top limit=1、学生访问 | total_records=5（管理员不计）；仅 1 条且为最高分用户；学生 403 | 通过 |

---

## 8. M7 站内消息

| ID | 层次/文件 | 前置/步骤 | 预期 | 结果 |
|---|---|---|---|---|
| TC-U-MSG-01 | 单元 `test_message_notification.py` | `notify()` 写入消息 | 类型/标题/内容/关联对象正确，默认未读 | 通过 |
| TC-U-MSG-02 | 单元 | 独立会话不可用时 `notify_safe()` | 不向外抛异常，记录“站内通知写入失败”日志 | 通过 |
| TC-U-MSG-03 | 单元 | 重复标记已读、他人标记、缺失消息 | 已读时不重复提交；403 `FORBIDDEN`；404 `MESSAGE_NOT_FOUND` | 通过 |
| TC-U-MSG-04 | 单元 | 未读数与类型筛选分页 | 未读 2；系统通知 total 2、第 2 页 1 条 | 通过 |
| TC-I-MSG-01 | 集成 `test_m7_message_flow.py` | 投诉处理产生消息 → 未读 → 标记已读 → 重复 → 他人 → 不存在 | 1 条「投诉反馈」；未读 1→0；重复 200；403；404 | 通过 |
| TC-I-MSG-02 | 集成 | 系统通知 3 条 + 投诉反馈 1 条 + 他人 1 条；按类型第 2 页 | total 3、第 2 页 1 条；他人仅见本人 1 条 | 通过 |
| TC-I-MSG-03 | 集成 | 通知会话不可用时处理投诉 | 接口 200，投诉状态已变「处理中」，消息表 0 条（业务不回滚） | 通过 |

---

## 9. 前端 composable 单元测试

| ID | 文件 | 断言点 | 预期 | 结果 |
|---|---|---|---|---|
| TC-F-COMP-01 | `useMyComplaints.test.ts` | `load` 成功 | 写入列表/总数，`loading=false`，无错误文案 | 通过 |
| TC-F-COMP-02 | 同上 | `load` 失败 | 清空列表与总数，错误文案「加载失败」 | 通过 |
| TC-F-COMP-03 | 同上 | `submit` 提交带首尾空格内容 | 提交内容被 trim，回到第 1 页，提示成功并刷新 | 通过 |
| TC-F-COMP-04 | 同上 | 非「已处理」投诉确认关闭 | 不弹确认框、不调用接口 | 通过 |
| TC-F-COMP-05 | 同上 | 「已处理」投诉确认关闭 | 调用确认接口并原地替换为「已关闭」 | 通过 |
| TC-F-COMP-06 | 同上 | 翻页 | 页码更新，高亮/聚焦清空并重新加载 | 通过 |
| TC-F-AUDIT-01 | `useAuditManage.test.ts` | 空筛选加载 | 只传分页参数，筛选字段为 undefined | 通过 |
| TC-F-AUDIT-02 | 同上 | 筛选条件与日期区间 | 原样透传（含 operator_id 与起止日期） | 通过 |
| TC-F-AUDIT-03 | 同上 | 当前页为空 | 自动退回上一页并再查一次 | 通过 |
| TC-F-AUDIT-04 | 同上 | 加载失败 | 清空列表/总数并给出错误文案 | 通过 |
| TC-F-AUDIT-05 | 同上 | 重置筛选 | 条件清空、页码回 1 并重新加载 | 通过 |
| TC-F-AUDIT-06 | 同上 | 修改每页条数 | 页大小更新、页码回 1 | 通过 |
| TC-F-AUDIT-07 | 同上 | 操作人下拉 | 由管理端用户目录映射为 `姓名（学号）` | 通过 |

---

## 10. 执行与复现

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\mzj -q
.\.venv\Scripts\python.exe -m pytest tests -q

cd ..\frontend
npm run test -- --run src/utils/__tests__/useMyComplaints.test.ts src/utils/__tests__/useAuditManage.test.ts
npm run test
```

JUnit 证据：`docs/test-reports/pytest-junit-mzj.xml`。

---

## 11. 本轮未覆盖（如实标注）

1. 真实 MySQL 下的并发与锁行为（本组用例统一使用 SQLite 内存库）。
2. 浏览器端 E2E（Playwright）未新增场景，沿用既有 5 条主流程。
3. `core/database.get_db` 真实会话生命周期仍未覆盖（共享测试基座限制，非本组范围）。
4. 前端覆盖率统计口径只含 7 个 utils/store 文件，新增 composable 未纳入 `vitest.config.ts` 的 `coverage.include`，因此 13 条新用例不计入覆盖率分子/分母。
