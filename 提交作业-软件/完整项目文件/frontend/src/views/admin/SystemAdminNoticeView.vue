<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

function logout() {
  auth.logout()
  router.replace({ name: 'login' })
}
</script>

<template>
  <div class="sysadmin-notice">
    <el-result icon="info" title="系统管理员" sub-title="本版尚未开放业务管理功能">
      <template #extra>
        <p class="sysadmin-notice__hint">
          依据权限矩阵（BR-018），系统管理员本版仅拥有全局参数配置权限，
          该功能本期尚未实现。如需管理自习室业务，请使用「自习室管理员」账号登录。
        </p>
        <el-button type="primary" @click="logout">切换账号</el-button>
      </template>
    </el-result>
  </div>
</template>

<style scoped>
.sysadmin-notice {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sysadmin-notice__hint {
  max-width: 480px;
  margin: 12px 0 0;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
  line-height: 1.7;
  text-align: left;
}
</style>
