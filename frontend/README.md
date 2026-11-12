# 前端开发骨架（Vue 3 + TypeScript + Vite）

## 技术栈

Vue 3 · TypeScript · Vite · Element Plus · Pinia · Vue Router · ECharts · Axios

## 目录结构

```
frontend/
├── src/
│   ├── api/                 # Axios 封装与按模块拆分的接口
│   ├── components/          # PageHeader、BaseChart 等通用组件
│   ├── layouts/             # 学生端 / 管理端布局
│   ├── router/              # 路由与角色守卫
│   ├── stores/              # Pinia（登录状态、用户信息）
│   ├── types/               # 与后端 schema 对应的 TS 类型
│   ├── utils/               # 日期与状态格式化
│   ├── views/
│   │   ├── auth/            # 登录
│   │   ├── student/         # 学生端：预约、记录、投诉、资料
│   │   └── admin/           # 管理端：看板、资源、预约、违约、投诉、用户
│   ├── App.vue
│   └── main.ts
├── index.html
├── vite.config.ts           # /api 代理到 http://127.0.0.1:8000
└── package.json
```

## 启动

```bash
cd frontend
npm install
npm run dev          # http://127.0.0.1:5173
```

仓库根目录的 `start.bat` 会连同数据库和后端一起启动，无需手工执行上面的命令。

需先启动后端。演示账户：`student / student123`、`admin / admin123`。

`vite.config.ts` 已显式绑定 `host: '127.0.0.1'`：Node 17+ 的 `localhost` 可能只解析到 `::1`，会与文档、代理统一使用的 `127.0.0.1` 不一致。

`.env.development` 默认 `VITE_USE_MOCK=false`，所有请求经 Vite 代理到真实后端；如需脱离后端独立演示，改为 `true` 后重启（MSW 在浏览器内拦截）。

## 质量工具与测试

```bash
npm run lint              # ESLint
npm run format:check      # Prettier 检查（npm run format 自动修复）
npm run test              # Vitest（工具函数 + Pinia store）
npm run test:coverage     # Vitest + v8 覆盖率
npx playwright install chromium   # 首次运行 E2E 前安装浏览器
npm run test:e2e          # Playwright 5 条主流程
```

E2E 使用 `.env.e2e` + MSW，不依赖 FastAPI / MySQL，覆盖登录、预约、取消、签到/签退、管理员临时关闭自习室；
浏览器时间固定在 `2026-11-12 10:00`，保证种子数据与签到窗口可复现。构建通过 `manualChunks` 拆分
`vendor-echarts` / `vendor-element-plus` / `vendor-vue`，ECharts 在 `BaseChart.vue` 中按需注册。

## 约定

- 登录后 token 存于 `localStorage`（`ssr_token`），Axios 请求拦截器统一附加 `Authorization: Bearer`。
- 路由守卫按角色区分学生端（`/student/*`）与管理端（`/admin/*`）。
- 所有路由页面均已实现，`ModulePlaceholder` 已删除；页面直接对接 API，开发期可按开关切换 MSW mock。
- 管理端看板已接入 ECharts 与真实聚合接口，按 FR-053 每 10 秒刷新。
