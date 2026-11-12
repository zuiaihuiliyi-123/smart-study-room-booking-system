import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  // Vitest 2 内置的 Vite 版本与项目 Vite 6 的 Plugin 泛型不一致；
  // 运行时插件完全兼容，这里只放宽类型声明。
  plugins: [vue() as never],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'happy-dom',
    include: ['src/**/*.test.ts'],
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reportsDirectory: 'coverage',
      reporter: ['text', 'html'],
      include: [
        'src/utils/format.ts',
        'src/utils/bookingRules.ts',
        'src/utils/mask.ts',
        'src/utils/workday.ts',
        'src/utils/messageLinks.ts',
        'src/stores/auth.ts',
        'src/stores/message.ts',
      ],
    },
  },
})
