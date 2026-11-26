<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from '@/layouts/components/AppShell.vue'
import { studentMenus, studentNavMenus } from '@/layouts/menu'
import { useAuthStore } from '@/stores/auth'
import { useMessageStore } from '@/stores/message'

const router = useRouter()
const route = useRoute()
const messages = useMessageStore()
const auth = useAuthStore()

/**
 * 顶部导航选中项：个人中心是一级模块，其下所有二级页（我的预约 / 我的违约 /
 * 我的投诉 / 站内消息 / 个人资料）都算「个人中心」，避免顶栏没有任何高亮。
 */
const navActivePath = computed(() => {
  if (route.path === '/student/home') return '/student/home'
  if (route.path === '/student/booking') return '/student/booking'
  return '/student/profile'
})

/**
 * 个人中心二级页：只有这些页面显示侧栏（侧栏就是「个人中心」的栏目本身）。
 * 首页与选座页属于独立模块，正文占满整宽，不再被侧栏挤压座位图。
 */
const PERSONAL_CENTER_PATHS = [
  '/student/reservations',
  '/student/violations',
  '/student/complaints',
  '/student/messages',
  '/student/profile',
]

const showSider = computed(() => PERSONAL_CENTER_PATHS.includes(route.path))

/** 侧栏用户卡：姓名取登录用户，角色用学生端固定文案（不是权限角色码） */
const siderUser = computed(() => ({
  name: auth.user?.name ?? '同学',
  role: '学生账号',
}))

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
    :nav-items="studentNavMenus"
    :nav-active-path="navActivePath"
    :sider-user="siderUser"
    :show-sider="showSider"
    fill-width
    :show-crumb="false"
    plain-user
    role-label="学生端"
    profile-path="/student/profile"
    :unread-count="messages.unreadCount"
    @messages="router.push('/student/messages')"
  />
</template>
