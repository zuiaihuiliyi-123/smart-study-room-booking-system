<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'

import BrandPanel from '@/components/auth/BrandPanel.vue'
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
  <div class="login">
    <BrandPanel class="login__brand" />

    <section class="login__panel">
      <div class="login__card">
        <h2>统一身份登录</h2>
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
            <p>后端目前仅 /auth/login 与 /health 可用，其余接口统一返回 501。</p>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.login {
  display: flex;
  min-height: 100%;
  background: var(--ssr-surface);
}

/* 品牌区的视觉样式在 components/auth/BrandPanel.vue；这里只管栅格占位 */
.login__brand {
  flex: 0 0 60%;
}

/* ---- 右：400px 表单卡 ---- */
.login__panel {
  display: flex;
  flex: 1 1 40%;
  align-items: center;
  justify-content: center;
  min-width: 0;
  padding: 24px 20px;
  background: var(--ssr-surface);
  border-left: 1px solid var(--ssr-line);
}

.login__card {
  width: 400px;
  max-width: 100%;
}

.login__card h2 {
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

@media (max-width: 900px) {
  .login__brand {
    display: none;
  }

  .login__panel {
    flex: 1 1 auto;
    border-left: 0;
  }
}
</style>


