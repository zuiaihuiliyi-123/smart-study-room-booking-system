<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const loading = ref(false)
const form = reactive({
  student_no: '',
  password: '',
})

async function submit() {
  if (!form.student_no || !form.password) {
    ElMessage.warning('请输入学号/工号和密码')
    return
  }

  loading.value = true
  try {
    await auth.login(form)
    ElMessage.success('登录成功')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    await router.replace(
      redirect || (auth.isAdmin ? '/admin/dashboard' : '/student/home'),
    )
  } catch {
    // 错误提示由 axios 拦截器统一处理
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <el-card class="login-card">
      <h1>智慧自习室预约与管理系统</h1>
      <p class="hint">学生端 / 管理端统一登录</p>

      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="学号 / 工号">
          <el-input v-model="form.student_no" placeholder="请输入学号或工号" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button type="primary" class="submit" :loading="loading" @click="submit">
          登录
        </el-button>
      </el-form>

      <p class="demo">演示账户：student / student123；admin / admin123</p>
    </el-card>
  </div>
</template>

<style scoped>
.login-page {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e8f3ff 0%, #f5f7fa 100%);
}
.login-card {
  width: 400px;
  padding: 8px 12px 16px;
}
h1 {
  margin: 0;
  font-size: 20px;
  text-align: center;
}
.hint {
  margin: 8px 0 24px;
  color: #909399;
  font-size: 13px;
  text-align: center;
}
.submit {
  width: 100%;
}
.demo {
  margin: 16px 0 0;
  color: #c0c4cc;
  font-size: 12px;
  text-align: center;
}
</style>
