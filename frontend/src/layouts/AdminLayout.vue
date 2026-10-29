<script setup lang="ts">
import AppShell from '@/layouts/components/AppShell.vue'
import { adminMenus } from '@/layouts/menu'
</script>

<template>
  <!-- 管理端暂无个人资料页，不传 profile-path，下拉项置灰 -->
  <AppShell :menus="adminMenus" role-label="管理端" />
</template>
