<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Lock, Message, Postcard, User } from '@element-plus/icons-vue'

import AuthLayout from '@/components/auth/AuthLayout.vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  name: '',
  student_no: '',
  contact: '',
  password: '',
  confirm: '',
})

function validateConfirm(
  _rule: unknown,
  value: string,
  callback: (error?: string | Error) => void,
) {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
    return
  }
  callback()
}

/** 与 backend/app/schemas/auth.py 的 RegisterRequest 保持一致 */
const rules: FormRules = {
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' },
    { min: 2, max: 50, message: '姓名长度为 2-50 个字符', trigger: 'blur' },
  ],
  student_no: [
    { required: true, message: '请输入学号/工号', trigger: 'blur' },
    {
      pattern: /^[A-Za-z0-9_-]{4,32}$/,
      message: '学号/工号为 4-32 位字母、数字、下划线或短横线',
      trigger: 'blur',
    },
  ],
  contact: [{ max: 100, message: '联系方式不能超过 100 个字符', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 64, message: '密码长度为 8-64 个字符', trigger: 'blur' },
  ],
  confirm: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
}

async function submit() {
  if (!formRef.value) return

  // 先按后端口径去掉首尾空白，再触发校验，避免空格导致“看起来输入正确却注册失败”
  form.name = form.name.trim()
  form.student_no = form.student_no.trim()
  form.contact = form.contact.trim()

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await auth.register({
      name: form.name,
      student_no: form.student_no,
      password: form.password,
      contact: form.contact || null,
    })
    ElMessage.success('注册成功，已自动登录')
    await router.replace('/student/home')
  } catch {
    // 错误提示由 axios 拦截器统一处理（重复学号返回 409）
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthLayout>
    <h2 class="register__title">创建账号</h2>
    <p class="register__hint">
      注册后即可预约自习座位；管理员 / 教师账号由信息中心统一开通
    </p>

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      @submit.prevent="submit"
    >
      <el-form-item label="姓名" prop="name">
        <el-input
          v-model="form.name"
          placeholder="请输入真实姓名"
          autocomplete="name"
          :prefix-icon="User"
        />
      </el-form-item>

      <el-form-item label="学号 / 工号" prop="student_no">
        <el-input
          v-model="form.student_no"
          placeholder="4-32 位字母、数字、下划线或短横线"
          autocomplete="username"
          :prefix-icon="Postcard"
        />
      </el-form-item>

      <el-form-item label="联系方式（选填）" prop="contact">
        <el-input
          v-model="form.contact"
          placeholder="手机号或邮箱，用于接收预约提醒"
          autocomplete="tel"
          :prefix-icon="Message"
        />
      </el-form-item>

      <el-form-item label="密码" prop="password">
        <el-input
          v-model="form.password"
          type="password"
          show-password
          placeholder="至少 8 位"
          autocomplete="new-password"
          :prefix-icon="Lock"
        />
      </el-form-item>

      <el-form-item label="确认密码" prop="confirm">
        <el-input
          v-model="form.confirm"
          type="password"
          show-password
          placeholder="请再次输入密码"
          autocomplete="new-password"
          :prefix-icon="Lock"
          @keyup.enter="submit"
        />
      </el-form-item>

      <p class="register__note">密码建议混合字母、数字与符号；注册成功后自动登录。</p>

      <el-button
        type="primary"
        class="register__submit"
        :loading="loading"
        @click="submit"
      >
        注册并登录
      </el-button>
    </el-form>

    <p class="register__login">
      已有账号？
      <RouterLink class="register__login-link" to="/login">返回登录</RouterLink>
    </p>
  </AuthLayout>
</template>

<style scoped>
.register__title {
  margin: 0;
  color: var(--ssr-ink);
  font-size: 20px;
  font-weight: 600;
}

.register__hint {
  margin: 6px 0 18px;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
  line-height: 1.6;
}

.register__note {
  margin: 2px 0 14px;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
  line-height: 1.5;
}

.register__submit {
  width: 100%;
}

.register__login {
  margin: 14px 0 0;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
  text-align: center;
}

.register__login-link {
  color: var(--ssr-primary);
  font-weight: 600;
  text-decoration: none;
}

.register__login-link:hover,
.register__login-link:focus-visible {
  text-decoration: underline;
}
</style>
