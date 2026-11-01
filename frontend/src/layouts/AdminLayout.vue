<script setup lang="ts">
import AppShell from '@/layouts/components/AppShell.vue'
import { adminMenus } from '@/layouts/menu'
</script>

<template>
  <!-- 管理端暂无个人资料页与站内消息页：不传 profile-path 并关闭消息入口 -->
  <AppShell :menus="adminMenus" role-label="管理端" :show-messages="false" />
</template>
