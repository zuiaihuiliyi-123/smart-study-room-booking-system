import { rmSync } from 'node:fs'
import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig, type Plugin } from 'vite'

/**
 * 生产构建删除 public/ 里仅开发期使用的 MSW worker。
 * Vite 会把 publicDir 整体拷进 dist，而 mockServiceWorker.js 只服务于 dev。
 */
function dropMockServiceWorker(): Plugin {
  return {
    name: 'ssr-drop-mock-service-worker',
    apply: 'build',
    closeBundle() {
      rmSync(fileURLToPath(new URL('./dist/mockServiceWorker.js', import.meta.url)), {
        force: true,
      })
    },
  }
}

export default defineConfig({
  plugins: [vue(), dropMockServiceWorker()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    // 拆包目标：ECharts / Element Plus / Vue 运行时各自独立，
    // 避免首屏与图表库、组件库一起下载。
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('echarts') || id.includes('zrender')) return 'vendor-echarts'
          if (id.includes('element-plus') || id.includes('@element-plus')) {
            return 'vendor-element-plus'
          }
          if (id.includes('/vue/') || id.includes('@vue/') || id.includes('vue-router') || id.includes('pinia')) {
            return 'vendor-vue'
          }
          if (id.includes('axios') || id.includes('dayjs')) return 'vendor-utils'
          return 'vendor'
        },
      },
    },
    chunkSizeWarningLimit: 900,
  },
  server: {
    // 显式绑定 IPv4：Node 17+ 的 localhost 可能只解析到 ::1，
    // 而文档、代理和启动脚本统一使用 http://127.0.0.1:5173。
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        // VITE_USE_MOCK=true 时请求由 MSW 在浏览器内拦截，不会到达这里；
        // 关闭 mock 后才真正代理到后端。
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
