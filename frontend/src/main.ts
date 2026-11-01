import { createPinia } from 'pinia'
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import 'element-plus/dist/index.css'
// Element Plus 暗色变量（挂在 html.dark 上）；必须排在 index.scss 之前，
// 让 index.scss 第 2 节能用同层选择器 html.dark 覆盖主色与圆角。
import 'element-plus/theme-chalk/dark/css-vars.css'
import '@/assets/styles/index.scss'

import App from './App.vue'
import router from './router'

async function bootstrap() {
  // 开发期 mock：仅 DEV + VITE_USE_MOCK=true 时加载。
  // 生产构建下 import.meta.env.DEV 为常量 false，该分支与 msw 都会被摇树移除。
  if (import.meta.env.DEV && import.meta.env.VITE_USE_MOCK === 'true') {
    const { worker } = await import('./mocks/browser')
    await worker.start({ onUnhandledRequest: 'bypass' })
  }

  const app = createApp(App)

  app.use(createPinia())
  app.use(router)
  app.use(ElementPlus, { locale: zhCn })
  app.mount('#app')
}

void bootstrap()
