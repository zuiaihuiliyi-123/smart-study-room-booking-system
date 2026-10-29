# 智慧自习室预约与管理系统

面向高校自习空间的座位预约、使用管理与数据分析平台。

> **当前阶段：需求分析 + 开发骨架。** 本仓库包含需求分析阶段的文档与图模型，以及基于 FastAPI + Vue 3 的前后端项目骨架；业务逻辑尚未实现。

## 仓库结构

```
.
├── README.md
├── LICENSE
├── .gitignore
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
    └── src/
        ├── api/             # 接口封装
        ├── layouts/         # 学生端 / 管理端布局
        ├── router/          # 路由与角色守卫
        ├── stores/          # Pinia
        └── views/           # 学生端、管理端页面
```

## 开发骨架

| 部分 | 技术栈 | 启动说明 |
|---|---|---|
| `backend/` | FastAPI · Pydantic 2 · SQLAlchemy 2 · Alembic · MySQL 8.4 · JWT · APScheduler · Pytest | 见 [`backend/README.md`](backend/README.md) |
| `frontend/` | Vue 3 · TypeScript · Vite · Element Plus · Pinia · ECharts | 见 [`frontend/README.md`](frontend/README.md) |

后端已实现登录与健康检查，数据库表结构已通过 Alembic 迁移建立；其余接口为骨架（统一返回 501）。前端已完成登录、角色路由与各模块页面占位。模块划分与功能需求编号的对应关系见 `backend/README.md`。

三周交付安排、P0 基座冻结、任务分工与 VS 验收矩阵见 [`docs/项目开发计划-三周冲刺版.md`](docs/项目开发计划-三周冲刺版.md)。

系统启动、演示账号、当前实现状态与数据库表/约束核对见 [`docs/系统使用说明.md`](docs/系统使用说明.md)。数据库采用“每人本地 MySQL + Alembic 迁移”的协作方式，首次配置、日常拉取和迁移负责人流程见 [`docs/数据库协作说明.md`](docs/数据库协作说明.md)。

## 文档与模型

| 文件 | 说明 | 版本 |
|---|---|---|
| `docs/智慧自习室预约与管理系统-需求规格说明书.md` | 系统的业务目标、范围、功能、业务规则、权限、数据、状态及质量要求。**V0.4 新增第 4.7 节领域类图（CD-01）**，并在 §1.3 登记 `CD-nn`、统一图模型路径为 `models/`。 | V0.4 |
| `docs/需求分析质量验证报告.md` | 需求分析质量验证报告（A 报告）：关键事实与规则确认、图模型提交、状态转换说明、场景走查、原型走查与验证、问题处理与复核、成员贡献与人工责任。**其中 A.5 场景走查、A.6 原型走查、A.8 成员贡献按实际状态标注为「未开展 / 待填写」，A.7 登记 13 项问题（V-01～V-13，均尚未人工复核）。** | V1.1 |
| `docs/学生需求分析与AI智能体使用验证报告.md` | 课程作业的要求说明，A、B 两部分分别作为「需求分析质量验证报告」与「AI 智能体使用验证报告」的编写依据。 | — |
| `docs/系统使用说明.md` | 本地启动、演示账号、当前实现状态、数据库表与约束核对。 | V1.0 |
| `docs/数据库表结构说明.md` | 实际数据库全部表、字段、类型、索引、外键与 CHECK 约束。 | V1.0 |
| `docs/数据库协作说明.md` | 每人本地 MySQL + Alembic 迁移的协作流程、组员分工与常见错误。 | V1.0 |
| `docs/项目开发计划-三周冲刺版.md` | 三周排期、P0 基座冻结、任务分工与 VS 验收矩阵。 | V1.0 |
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
3. 发起 Pull Request，由至少一名小组成员复核后合并。

**注意：** 附件与证据材料在提交前应移除密码、令牌及与核验无关的个人敏感信息。

## 许可证

本项目采用 [MIT License](LICENSE)。
