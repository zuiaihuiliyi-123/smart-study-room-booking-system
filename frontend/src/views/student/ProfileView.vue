<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
</script>

<template>
  <div class="page">
    <el-card>
      <template #header>个人资料</template>
      <el-descriptions v-if="auth.user" :column="2" border>
        <el-descriptions-item label="姓名">{{ auth.user.name }}</el-descriptions-item>
        <el-descriptions-item label="学号 / 工号">{{ auth.user.student_no }}</el-descriptions-item>
        <el-descriptions-item label="角色">{{ auth.user.role }}</el-descriptions-item>
        <el-descriptions-item label="账户状态">{{ auth.user.account_status }}</el-descriptions-item>
        <el-descriptions-item label="累计违约">{{ auth.user.violation_count }} 次</el-descriptions-item>
        <el-descriptions-item label="联系方式">{{ auth.user.contact ?? '未填写' }}</el-descriptions-item>
      </el-descriptions>
      <el-empty v-else description="暂无用户信息" />
      <p class="tip">身份信息由统一身份认证同步，仅联系方式可修改（FR-040）。</p>
    </el-card>
  </div>
</template>

<style scoped>
.tip {
  margin-top: 16px;
  color: #909399;
  font-size: 13px;
}
</style>
