/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'

  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>
  export default component
}

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  /** 开发期是否启用 MSW mock：仅 'true' 且 DEV 时生效，生产构建不包含 mock */
  readonly VITE_USE_MOCK?: string
  /** 是否在登录页展示演示账号：DEV 默认展示；生产构建需显式设为 'true' 才展示 */
  readonly VITE_SHOW_DEMO_ACCOUNTS?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
