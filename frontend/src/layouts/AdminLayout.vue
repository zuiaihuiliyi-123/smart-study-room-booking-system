<script setup lang="ts">
import { computed } from 'vue'

import AppShell from '@/layouts/components/AppShell.vue'
import { adminMenus } from '@/layouts/menu'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
// 系统管理员（R-04）本版无业务操作权限（BR-018），不展示业务菜单，
// 仅由 /admin/notice 提示页承接（参数配置功能本期未实现）。
const menus = computed(() => (auth.isSystemAdmin ? [] : adminMenus))
</script>

<template>
  <!-- 管理端暂无个人资料页与站内消息页：不传 profile-path 并关闭消息入口 -->
  <AppShell :menus="menus" role-label="管理端" :show-messages="false" />
</template>
