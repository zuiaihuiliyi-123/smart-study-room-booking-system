import { defineConfig, devices } from '@playwright/test'

/**
 * 系统测试配置：真实 FastAPI + MySQL，不使用 MSW。
 *
 * 前置条件：
 *   1. 后端运行在 8010（隔离数据库，SCHEDULER_ENABLED=false）
 *   2. 前端 dev server 运行在 5180，且：
 *        VITE_API_BASE_URL=http://127.0.0.1:8010/api/v1
 *        VITE_USE_MOCK=false
 *
 * 运行：
 *   npx playwright test --config playwright.system.config.ts
 */
const executablePath = process.env.PLAYWRIGHT_CHROMIUM_PATH

export default defineConfig({
  testDir: './e2e-system',
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: [['list'], ['html', { outputFolder: 'playwright-report-system', open: 'never' }]],
  use: {
    baseURL: process.env.SYSTEM_WEB_URL ?? 'http://127.0.0.1:5180',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
    // 本机已有旧版 Chromium 时可通过环境变量复用，避免重复下载
    launchOptions: executablePath ? { executablePath } : {},
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 5180',
    url: 'http://127.0.0.1:5180',
    reuseExistingServer: true,
    timeout: 120_000,
    env: {
      VITE_API_BASE_URL: process.env.SYSTEM_API_URL ?? 'http://127.0.0.1:8010/api/v1',
      VITE_USE_MOCK: 'false',
      VITE_SHOW_DEMO_ACCOUNTS: 'true',
    },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
