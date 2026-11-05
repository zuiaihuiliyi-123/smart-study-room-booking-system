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

function refresh(): void {
  if (document.visibilityState === 'visible') void messages.load(true)
}

function onVisible(): void {
  refresh()
}

// 未读消息的唯一数据源：壳层与「站内消息」页、首页摘要共用同一个 store，
// 避免三处各自拉取导致角标与列表不一致（FR-060 / SCOPE-07）。
onMounted(() => {
  void messages.load()
  timer = window.setInterval(refresh, REFRESH_INTERVAL_MS)
  document.addEventListener('visibilitychange', onVisible)
})

onUnmounted(() => {
  if (timer !== null) window.clearInterval(timer)
  document.removeEventListener('visibilitychange', onVisible)
})

// 进入消息页时强制取一次，避免「角标 3 条、列表 0 条未读」这种前后不一致
watch(
  () => route.path,
  (path) => {
    if (path === '/student/messages') void messages.load(true)
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
