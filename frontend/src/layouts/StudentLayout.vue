<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="brand">智慧自习室 · 学生端</div>
      <el-menu router :default-active="route.path">
        <el-menu-item index="/student/home">首页</el-menu-item>
        <el-menu-item index="/student/booking">预约座位</el-menu-item>
        <el-menu-item index="/student/reservations">我的预约</el-menu-item>
        <el-menu-item index="/student/violations">我的违约</el-menu-item>
        <el-menu-item index="/student/complaints">我的投诉</el-menu-item>
        <el-menu-item index="/student/profile">个人资料</el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span>{{ route.meta.title }}</span>
        <div class="user">
          <span>{{ auth.user?.name ?? '未登录' }}</span>
          <el-button link type="primary" @click="logout">退出登录</el-button>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  height: 100%;
}
.aside {
  background: #fff;
  border-right: 1px solid #ebeef5;
}
.brand {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #409eff;
  font-weight: 600;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}
.user {
  display: flex;
  align-items: center;
  gap: 12px;
}
.main {
  background: #f5f7fa;
}
</style>
