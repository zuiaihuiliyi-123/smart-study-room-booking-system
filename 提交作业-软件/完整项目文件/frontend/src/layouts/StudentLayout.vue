<script setup lang="ts">
import { onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from '@/layouts/components/AppShell.vue'
import { studentMenus } from '@/layouts/menu'
import { useMessageStore } from '@/stores/message'

const router = useRouter()
const route = useRoute()
const messages = useMessageStore()

/** 角标最长 60 秒刷一次：新消息（预约、违约、投诉反馈）到达后角标不会一直停在旧数字。 */
const REFRESH_INTERVAL_MS = 60_000
let timer: number | null = null

/**
 * 壳层只关心**未读数**：消息列表已改为服务端分页，
 * 拉整页列表既浪费请求，也无法代表「全部未读」。
 */
function refresh(): void {
  if (document.visibilityState === 'visible') void messages.loadUnreadCount()
}

function onVisible(): void {
  refresh()
}

// 未读数与「站内消息」页、首页摘要共用同一个 store，避免三处数字不一致（FR-060 / SCOPE-07）。
onMounted(() => {
  void messages.loadUnreadCount()
  timer = window.setInterval(refresh, REFRESH_INTERVAL_MS)
  document.addEventListener('visibilitychange', onVisible)
})

onUnmounted(() => {
  if (timer !== null) window.clearInterval(timer)
  document.removeEventListener('visibilitychange', onVisible)
})

// 进入消息页时刷新一次角标；列表本身由 MessagesView 自行按页加载
watch(
  () => route.path,
  (path) => {
    if (path === '/student/messages') void messages.loadUnreadCount()
  },
)
</script>

<template>
  <AppShell
    :menus="studentMenus"
    role-label="学生端"
    profile-path="/student/profile"
    :unread-count="messages.unreadCount"
    @messages="router.push('/student/messages')"
  />
</template>
