<script setup lang="ts">
/**
 * 离线提示条：浏览器离线时全局展示，恢复后自动消失。
 * 只提示、不阻断操作——本地已有数据仍可浏览，写操作会在请求层给出失败提示。
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

const online = ref(typeof navigator === 'undefined' ? true : navigator.onLine)

function onOnline(): void {
  online.value = true
}

function onOffline(): void {
  online.value = false
}

onMounted(() => {
  window.addEventListener('online', onOnline)
  window.addEventListener('offline', onOffline)
})

onBeforeUnmount(() => {
  window.removeEventListener('online', onOnline)
  window.removeEventListener('offline', onOffline)
})
</script>

<template>
  <Transition name="offline-fade">
    <div v-if="!online" class="offline-banner" role="status" aria-live="polite">
      <span class="offline-banner__dot" aria-hidden="true"></span>
      网络连接已断开：页面仍可浏览，提交类操作会在恢复网络后生效
    </div>
  </Transition>
</template>

<style scoped>
.offline-banner {
  position: fixed;
  top: 0;
  right: 0;
  left: 0;
  z-index: 3000;
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
  color: var(--ssr-warning-ink);
  font-size: var(--ssr-font-note);
  background: var(--ssr-warning-bg);
  border-bottom: 1px solid color-mix(in srgb, var(--ssr-warning) 36%, transparent);
}

.offline-banner__dot {
  width: 8px;
  height: 8px;
  background: var(--ssr-warning);
  border-radius: 50%;
}

.offline-fade-enter-active,
.offline-fade-leave-active {
  transition: opacity 0.2s ease;
}

.offline-fade-enter-from,
.offline-fade-leave-to {
  opacity: 0;
}
</style>
