<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

import AppShell from '@/layouts/components/AppShell.vue'
import { studentMenus } from '@/layouts/menu'
import { useMessageStore } from '@/stores/message'

const router = useRouter()
const messages = useMessageStore()

// 未读消息的唯一数据源：壳层与「站内消息」页、首页摘要共用同一个 store，
// 避免三处各自拉取导致角标与列表不一致（FR-060 / SCOPE-07）。
onMounted(() => {
  void messages.load()
})
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
