# 前端开发骨架（Vue 3 + TypeScript + Vite）

## 技术栈

Vue 3 · TypeScript · Vite · Element Plus · Pinia · Vue Router · ECharts · Axios

## 目录结构

```
frontend/
├── src/
│   ├── api/                 # Axios 封装与按模块拆分的接口
│   ├── components/          # PageHeader、ModulePlaceholder、BaseChart
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

需先启动后端。演示账户：`student / student123`、`admin / admin123`。

## 约定

- 登录后 token 存于 `localStorage`（`ssr_token`），Axios 请求拦截器统一附加 `Authorization: Bearer`。
- 路由守卫按角色区分学生端（`/student/*`）与管理端（`/admin/*`）。
- 所有路由页面均已实现，`ModulePlaceholder` 已删除；页面直接对接 API 或 MSW mock。
- 管理端看板已接入 ECharts 与真实聚合接口，按 FR-053 每 10 秒刷新。
