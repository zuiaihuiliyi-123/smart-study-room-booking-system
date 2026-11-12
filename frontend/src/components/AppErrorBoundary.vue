<script setup lang="ts">
/**
 * 全局渲染错误边界（Vue 3 `onErrorCaptured`）。
 *
 * 组件树任意后代在渲染 / 生命周期 / setup 中抛错时，这里接住并展示可恢复的兜底页，
 * 避免整页变成空白。事件处理函数里的错误由 main.ts 的 `app.config.errorHandler` 兜底。
 */
import { computed, onErrorCaptured, ref } from 'vue'

const error = ref<Error | null>(null)
const errorInfo = ref('')
const renderKey = ref(0)
const isDev = import.meta.env.DEV

const message = computed(() => error.value?.message || '页面渲染时发生未知错误')

onErrorCaptured((caught, _instance, info) => {
  error.value = caught instanceof Error ? caught : new Error(String(caught))
  errorInfo.value = info
  console.error('[ssr] 组件错误边界捕获到异常', caught, info)
  // 返回 false 阻止继续向上冒泡，避免控制台重复打印
  return false
})

function retry(): void {
  error.value = null
  errorInfo.value = ''
  renderKey.value += 1
}

function goHome(): void {
  window.location.href = '/'
}
</script>

<template>
  <el-result
    v-if="error"
    class="error-boundary"
    icon="error"
    title="页面出现异常"
    :sub-title="message"
  >
    <template #extra>
      <el-button type="primary" @click="retry">重试</el-button>
      <el-button @click="goHome">返回首页</el-button>
    </template>
    <template v-if="isDev">
      <pre class="error-boundary__stack">{{ error.stack }}</pre>
      <p class="ssr-text-muted">错误位置：{{ errorInfo }}</p>
    </template>
  </el-result>

  <div v-else :key="renderKey" class="error-boundary__host">
    <slot />
  </div>
</template>

<style scoped>
/*
 * 这一层必须把高度传下去：外壳 `#app` 是 height:100%，而登录页 `.auth` / `.app-shell`
 * 都用 `height/min-height: 100%` 占满视口。如果这层 div 高度为 auto，百分比高度会退化成
 * 内容高度，登录页就只占屏幕上半部分。
 */
.error-boundary__host {
  height: 100%;
}

.error-boundary {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 60vh;
}

.error-boundary__stack {
  max-width: min(880px, 92vw);
  padding: 12px;
  margin: 8px auto 0;
  overflow: auto;
  font-size: 12px;
  line-height: 1.6;
  text-align: left;
  white-space: pre-wrap;
  background: var(--ssr-bg);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius-sm);
}
</style>
