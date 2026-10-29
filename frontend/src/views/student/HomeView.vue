<script setup lang="ts">
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const entries = [
  { title: '预约座位', description: '查询可预约座位并提交预约', to: '/student/booking' },
  { title: '我的预约', description: '查看预约、签到与签退', to: '/student/reservations' },
  { title: '我的违约', description: '查看违约记录与账户状态', to: '/student/violations' },
]
</script>

<template>
  <div class="page">
    <el-card class="welcome">
      <h2>你好，{{ auth.user?.name ?? '同学' }}</h2>
      <p>
        当前账户状态：{{ auth.user?.account_status ?? '-' }}；累计违约
        {{ auth.user?.violation_count ?? 0 }} 次。
      </p>
    </el-card>

    <el-row :gutter="16">
      <el-col v-for="entry in entries" :key="entry.to" :span="8">
        <el-card class="entry" shadow="hover" @click="router.push(entry.to)">
          <h3>{{ entry.title }}</h3>
          <p>{{ entry.description }}</p>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.welcome {
  margin-bottom: 16px;
}
.welcome h2 {
  margin: 0 0 8px;
}
.welcome p {
  margin: 0;
  color: #606266;
}
.entry {
  cursor: pointer;
}
.entry h3 {
  margin: 0 0 8px;
}
.entry p {
  margin: 0;
  color: #909399;
  font-size: 13px;
}
</style>
