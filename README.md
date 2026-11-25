# 智慧自习室预约与管理系统

面向高校自习空间的座位预约、使用管理与数据分析平台。

> **当前阶段：可演示闭环。** 本仓库包含需求分析阶段的文档与图模型，以及基于 FastAPI + Vue 3 的前后端实现；M1～M7 业务接口均不再返回 501。前端学生端 7 页、管理端 12 页与登录/注册/404 默认直连真实后端演示，也可切换为 MSW mock 独立演示；前端已接入 ESLint、Prettier、Vitest 与 Playwright 质量门禁。

## 一键启动（Windows，推荐）

前提：电脑上已安装 **Python 3.11+**、**Node.js 18+**、**MySQL 8.x**，并知道本机 MySQL 的 root 密码。启动脚本会自动完成建库、建账号、迁移、演示数据和前后端启动；它不负责安装 MySQL 服务本身。

1. 双击仓库根目录的 `start.bat`（或在仓库根目录的 cmd 中执行 `start.bat`）。
2. 首次运行按提示输入 MySQL root 密码。脚本会自动创建：
   - 数据库 `smart_study_room`（utf8mb4）
   - 应用账号 `study_app`（随机密码，只写入被 Git 忽略的 `backend/.env`）
   - JWT 密钥（随机生成，写入 `backend/.env`）
   - 表结构（`alembic upgrade head`）与演示数据
3. 脚本会打开两个服务窗口，并访问 <http://127.0.0.1:5173>。

| 地址 | 说明 |
|---|---|
| <http://127.0.0.1:5173> | 前端页面 |
| <http://127.0.0.1:8000/docs> | Swagger API 文档 |
| <http://127.0.0.1:8000/health> | 后端健康检查 |

演示账户：`student / student123`、`admin / admin123`。

> 开发服务器（`npm run dev`）的登录页会展示演示账号；生产构建默认隐藏，如需在生产预览中演示，构建前设置 `VITE_SHOW_DEMO_ACCOUNTS=true`。
>
> 学生自助注册默认开放；可在 `backend/.env` 用 `REGISTRATION_ENABLED=false` 关闭自助注册，或用 `REGISTRATION_WHITELIST=学号1,学号2` 启用学号白名单（留空表示不限制）。

重复运行 `start.bat` 是安全的：已存在的数据库、账号、迁移和演示数据会被跳过。停止时运行根目录的 `stop.bat`（MySQL 服务会保留运行）。只想启动、不打开浏览器时使用 `start.bat --no-browser`。

> 第一次运行需要联网安装前后端依赖。若数据库连接串不可用或 JWT 密钥仍是占位符，脚本会自动修复，并把原 `backend/.env` 备份为 `backend/.env.bak`。
>
> 没有安装 MySQL？先按 <https://dev.mysql.com/downloads/installer/> 安装并记住 root 密码，再运行 `start.bat`；也可以参照 [`docs/系统使用说明.md`](docs/系统使用说明.md) 手工配置。

## 仓库结构

```
.
├── README.md
├── LICENSE
├── .gitignore
├── start.bat                # Windows 一键启动（数据库 + 后端 + 前端）
├── stop.bat                 # 停止由 start.bat 启动的服务
├── docs/                    # 需求规格说明书、质量验证报告
├── models/                  # 用例图、类图、活动图、时序图
├── backend/                 # FastAPI + SQLAlchemy + Alembic + MySQL
│   ├── app/
│   │   ├── api/v1/          # M1～M7 REST 路由
│   │   ├── core/            # 配置、数据库、JWT、依赖
│   │   ├── models/          # ORM 模型
│   │   ├── schemas/         # Pydantic 模型
│   │   ├── services/        # 业务逻辑
│   │   ├── tasks/           # APScheduler 定时任务
│   │   └── utils/
│   ├── alembic/
│   └── tests/
└── frontend/                # Vue 3 + TypeScript + Vite + Element Plus
    ├── e2e/                 # Playwright 主流程（MSW，不依赖后端）
    ├── eslint.config.js     # ESLint 9 flat config
    ├── playwright.config.ts
    ├── vitest.config.ts
    └── src/
        ├── api/             # 接口封装
        ├── components/admin/audit/  # 审计日志筛选/表格/详情（拆分）
        ├── components/admin/users/  # 用户筛选/表格/状态弹窗（拆分）
        ├── layouts/         # 学生端 / 管理端布局
        ├── router/          # 路由与角色守卫
        ├── stores/          # Pinia
        └── views/           # 学生端、管理端页面
```

## 开发骨架

| 部分 | 技术栈 | 启动说明 |
|---|---|---|
| `backend/` | FastAPI · Pydantic 2 · SQLAlchemy 2 · Alembic · MySQL 8.4 · JWT · APScheduler · Pytest | 见 [`backend/README.md`](backend/README.md) |
| `frontend/` | Vue 3 · TypeScript · Vite · Element Plus · Pinia · ECharts · Vitest · Playwright · ESLint · Prettier | 见 [`frontend/README.md`](frontend/README.md) |

后端已实现登录、M1 资源、M2 预约、M3 签到与违约、M4 查询、M5 治理、M6 看板与 M7 站内通知；数据库表结构通过单链 Alembic 迁移建立，自动违约/自动结束任务已落地。前端学生端 7 页、管理端 12 页、登录/注册与 404 均可演示，`.env.development` 默认直连后端。前端已接入 ESLint、Prettier、Vitest、Playwright 质量门禁，`npm run lint`、`npm run test`、`npm run test:e2e` 与 `npm run build` 可作为提交前检查。模块划分与功能需求编号的对应关系见 `backend/README.md`。

三周交付安排、P0 基座冻结、任务分工与 VS 验收矩阵见 [`docs/项目开发计划-三周冲刺版.md`](docs/项目开发计划-三周冲刺版.md)。

系统启动、演示账号、当前实现状态与数据库表/约束核对见 [`docs/系统使用说明.md`](docs/系统使用说明.md)。数据库采用“每人本地 MySQL + Alembic 迁移”的协作方式，首次配置、日常拉取和迁移负责人流程见 [`docs/数据库协作说明.md`](docs/数据库协作说明.md)。

## 前端质量与测试

```bash
cd frontend
npm install
npm run lint            # ESLint
npm run format:check    # Prettier 检查（npm run format 自动修复）
npm run type-check      # vue-tsc
npm run test            # Vitest：工具函数 + Pinia store
npm run test:coverage   # v8 覆盖率
npx playwright install chromium   # 首次运行 E2E 前安装
npm run test:e2e        # Playwright 5 条主流程 + 管理页拆分冒烟
npm run build           # vue-tsc + vite build
```

- 单测覆盖日期/预约规则、脱敏、工作日、消息跳转与 `auth` / `message` store，共 65 个用例；核心 utils/store 行覆盖率 93%+。
- E2E 使用 `frontend/.env.e2e` + MSW，不依赖 FastAPI / MySQL，覆盖登录、预约、取消、签到/签退、管理员临时关闭自习室；浏览器时间固定，保证签到窗口可复现。
- 生产构建通过 `manualChunks` 拆分 ECharts / Element Plus / Vue，ECharts 在 `BaseChart.vue` 中按需注册，主入口 JS 与重型第三方库分离。
- 运行时已接入全局错误边界、离线提示、轮询/防抖请求切页取消；审计日志与用户管理页面已按筛选、表格、详情/状态弹窗拆分。

## 文档与模型

| 文件 | 说明 | 版本 |
|---|---|---|
| `docs/智慧自习室预约与管理系统-需求规格说明书.md` | 系统的业务目标、范围、功能、业务规则、权限、数据、状态及质量要求。**V0.4 新增第 4.7 节领域类图（CD-01）**，并在 §1.3 登记 `CD-nn`、统一图模型路径为 `models/`。 | V0.4 |
| `docs/需求分析质量验证报告.md` | 需求分析质量验证报告（A 报告）：关键事实与规则确认、图模型提交、状态转换说明、场景走查、原型走查与验证、问题处理与复核、成员贡献与人工责任。**其中 A.5 场景走查、A.6 原型走查、A.8 成员贡献按实际状态标注为「未开展 / 待填写」，A.7 登记 13 项问题（V-01～V-13，均尚未人工复核）。** | V1.1 |
| `docs/学生需求分析与AI智能体使用验证报告.md` | 课程作业的要求说明，A、B 两部分分别作为「需求分析质量验证报告」与「AI 智能体使用验证报告」的编写依据。 | — |
| `docs/系统使用说明.md` | 本地启动、演示账号、前端质量门禁（ESLint/Prettier/Vitest/Playwright）、当前实现状态、数据库表与约束核对。 | V1.2 |
| `docs/数据库表结构说明.md` | 实际数据库全部表、字段、类型、索引、外键与 CHECK 约束。 | V1.0 |
| `docs/数据库协作说明.md` | 每人本地 MySQL + Alembic 迁移的协作流程、组员分工与常见错误。 | V1.0 |
| `docs/项目开发计划-三周冲刺版.md` | 三周排期、P0 基座冻结、任务分工与 VS 验收矩阵。 | V1.0 |
| `docs/architecture/ARCHITECTURE_CONSTRAINTS.md` | 软件架构约束：分层边界、错误处理、数据库重试/事务/缓存与前端质量门禁。 | V1.0 |
| `models/UCD-01-用例图.puml` | 用例图：参与者与用例的静态关系（说明书第 4.3 节）。 | V0.3 |
| `models/UCD-01.svg` | 用例图的 SVG 导出版本（清晰版，可直接查看／打印）。 | V0.4 导出 |
| `models/CD-01-领域类图.puml` | 领域类图：核心业务实体及其关联（对应说明书 V0.4 新增的第 4.7 节）。 | V0.3 |
| `models/CD-01.svg` | 领域类图的 SVG 导出版本。 | V0.4 导出 |

图模型使用 [PlantUML](https://plantuml.com/) 编写。渲染 SVG / PNG：

```bash
# 需先安装 PlantUML（或使用 VS Code 的 PlantUML 扩展）
plantuml -tsvg models/*.puml
```

## 重要约定

**候选状态的规则未获确认。** 需求规格说明书与图模型中标注为【AI 候选】或【分析推导】的内容，确认状态均为「待确认」，代表尚未经业务方或任课教师确认，不应视为已生效的业务规则。详见说明书第 11 节及附录 A。

**A 报告中的「未开展」是真实状态。** `docs/需求分析质量验证报告.md` 的 A.5 节（场景走查）、A.6 节（原型走查与验证）、A.8 节（成员贡献）均按实际状态标注为「未开展 / 待填写」；A.7 节的 V-01～V-13 全部**尚未经人工复核**。**不得**把"已修改"理解为"已复核通过"，也不得把设计意图表述为已验证。

## 参与贡献

1. 从 `main` 分支切出特性分支：`git checkout -b docs/your-topic`
2. 提交时使用清晰的提交信息，说明改动的文档与章节。
3. 提交前端改动前至少运行 `cd frontend && npm run lint && npm run test && npm run build`；改动 E2E 时再运行 `npm run test:e2e`。
4. 发起 Pull Request，由至少一名小组成员复核后合并。

**注意：** 附件与证据材料在提交前应移除密码、令牌及与核验无关的个人敏感信息。

## 许可证

本项目采用 [MIT License](LICENSE)。
