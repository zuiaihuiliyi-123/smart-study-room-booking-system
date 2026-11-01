<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'

import AuthLayout from '@/components/auth/AuthLayout.vue'
import { useAuthStore } from '@/stores/auth'

/** 仅缓存"记住我"的学号/工号，token 仍由 stores/auth.ts 管理 */
const REMEMBER_KEY = 'ssr_remember_no'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const loading = ref(false)
const remembering = ref(false)
const showDemo = ref(false)

const form = reactive({
  student_no: '',
  password: '',
})

onMounted(() => {
  const saved = localStorage.getItem(REMEMBER_KEY)
  if (saved) {
    form.student_no = saved
    remembering.value = true
  }
})

async function submit() {
  if (!form.student_no || !form.password) {
    ElMessage.warning('请输入学号/工号和密码')
    return
  }

  loading.value = true
  try {
    await auth.login(form)

    if (remembering.value) {
      localStorage.setItem(REMEMBER_KEY, form.student_no)
    } else {
      localStorage.removeItem(REMEMBER_KEY)
    }

    ElMessage.success('登录成功')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    await router.replace(redirect || (auth.isAdmin ? '/admin/dashboard' : '/student/home'))
  } catch {
    // 错误提示由 axios 拦截器统一处理
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthLayout>
    <h2 class="login__title">统一身份登录</h2>
    <p class="login__hint">学生 / 教师 / 管理员使用同一入口</p>

    <el-form label-position="top" @submit.prevent="submit">
      <el-form-item label="学号 / 工号">
        <el-input
          v-model="form.student_no"
          placeholder="请输入学号或工号"
          autocomplete="username"
          :prefix-icon="User"
        />
      </el-form-item>

      <el-form-item label="密码">
        <el-input
          v-model="form.password"
          type="password"
          show-password
          placeholder="请输入密码"
          autocomplete="current-password"
          :prefix-icon="Lock"
          @keyup.enter="submit"
        />
      </el-form-item>

      <div class="login__row">
        <el-checkbox v-model="remembering">记住我</el-checkbox>
        <span class="ssr-text-muted">忘记密码请联系信息中心</span>
      </div>

      <el-button type="primary" class="login__submit" :loading="loading" @click="submit">
        登录
      </el-button>
    </el-form>

    <p class="login__signup">
      还没有账号？
      <RouterLink class="login__signup-link" to="/register">立即注册</RouterLink>
    </p>

    <div class="login__demo">
      <button
        class="login__demo-toggle"
        type="button"
        :aria-expanded="showDemo"
        aria-controls="login-demo-body"
        @click="showDemo = !showDemo"
      >
        演示账号说明
        <span aria-hidden="true">{{ showDemo ? '收起 ▲' : '展开 ▼' }}</span>
      </button>
      <div v-show="showDemo" id="login-demo-body" class="login__demo-body">
        <p>学生：student / student123</p>
        <p>管理员：admin / admin123</p>
        <p>也可在注册页创建新的学生账号，注册成功后会直接登录。</p>
      </div>
    </div>
  </AuthLayout>
</template>

<style scoped>
.login__title {
  margin: 0;
  color: var(--ssr-ink);
  font-size: 20px;
  font-weight: 600;
}

.login__hint {
  margin: 6px 0 22px;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
}

.login__row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.login__submit {
  width: 100%;
}

.login__signup {
  margin: 14px 0 0;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
  text-align: center;
}

.login__signup-link {
  color: var(--ssr-primary);
  font-weight: 600;
  text-decoration: none;
}

.login__signup-link:hover,
.login__signup-link:focus-visible {
  text-decoration: underline;
}

.login__demo {
  padding-top: 16px;
  margin-top: 18px;
  border-top: 1px solid var(--ssr-line);
}

.login__demo-toggle {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  padding: 4px 0;
  color: var(--ssr-primary);
  font-family: inherit;
  font-size: var(--ssr-font-note);
  background: transparent;
  border: 0;
  cursor: pointer;
}

.login__demo-body {
  padding: 10px 12px;
  margin-top: 8px;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
  background: var(--ssr-primary-light);
  border-radius: var(--ssr-radius-sm);
}

.login__demo-body p {
  margin: 0 0 4px;
}

.login__demo-body p:last-child {
  margin-bottom: 0;
}
</style>
