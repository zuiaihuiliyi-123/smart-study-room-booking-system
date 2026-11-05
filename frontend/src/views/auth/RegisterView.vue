<script setup lang="ts">
/**
 * 学生自助注册（后端 POST /api/v1/auth/register）。
 *
 * 校验口径与后端 `RegisterRequest` 的字段约束保持一致：
 * - 姓名 2–50 字；学号 / 工号 4–32 位字母、数字、下划线或连字符；
 * - 密码 8–64 位；确认密码需与密码一致；
 * - 联系方式选填，填了则限定手机号或邮箱（后端只做长度 ≤100 的宽松校验）。
 *
 * 后端只开放「学生用户」角色，注册成功后直接签发令牌，因此这里注册即登录并进入学生端首页；
 * 管理员账号由信息中心分配，不在本页开通（R-03 教师角色已于 V2.1 取消）。
 */
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Lock, Message, User, UserFilled } from '@element-plus/icons-vue'

import AuthLayout from '@/components/auth/AuthLayout.vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  name: '',
  student_no: '',
  password: '',
  confirm: '',
  contact: '',
})

const rules: FormRules = {
  name: [
    { required: true, message: '请填写姓名', trigger: 'blur' },
    { min: 2, max: 50, message: '姓名长度为 2–50 个字', trigger: 'blur' },
  ],
  student_no: [
    { required: true, message: '请填写学号 / 工号', trigger: 'blur' },
    {
      pattern: /^[A-Za-z0-9_-]{4,32}$/,
      message: '学号 / 工号为 4–32 位字母、数字、下划线或连字符',
      trigger: 'blur',
    },
  ],
  password: [
    { required: true, message: '请设置密码', trigger: 'blur' },
    { min: 8, max: 64, message: '密码长度为 8–64 位', trigger: 'blur' },
  ],
  confirm: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback: (error?: Error) => void) => {
        callback(value === form.password ? undefined : new Error('两次输入的密码不一致'))
      },
      trigger: ['blur', 'change'],
    },
  ],
  contact: [
    {
      pattern: /^(1[3-9]\d{9}|[^\s@]+@[^\s@]+\.[^\s@]+)$/,
      message: '请填写 11 位手机号或邮箱地址',
      trigger: 'blur',
    },
  ],
}

async function submit() {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await auth.register({
      name: form.name.trim(),
      student_no: form.student_no.trim(),
      password: form.password,
      contact: form.contact.trim() || null,
    })
    ElMessage.success('注册成功，已为你登录')
    await router.replace('/student/home')
  } catch {
    // 失败提示（学号已被占用等）由 axios 拦截器统一处理，这里保留用户已填内容
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthLayout>
    <h2 class="reg__title">学生注册</h2>
    <p class="reg__hint">注册后即可预约座位；管理员账号由信息中心分配</p>

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      @submit.prevent="submit"
    >
      <el-form-item label="姓名" prop="name">
        <el-input v-model="form.name" placeholder="请输入真实姓名" :prefix-icon="UserFilled" />
      </el-form-item>

      <el-form-item label="学号 / 工号" prop="student_no">
        <el-input
          v-model="form.student_no"
          placeholder="4–32 位字母或数字"
          autocomplete="username"
          :prefix-icon="User"
        />
      </el-form-item>

      <el-form-item label="密码" prop="password">
        <el-input
          v-model="form.password"
          type="password"
          show-password
          placeholder="8–64 位，建议字母与数字组合"
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

      <el-form-item label="联系方式（选填）" prop="contact">
        <el-input
          v-model="form.contact"
          placeholder="手机号或邮箱，用于接收预约提醒"
          :prefix-icon="Message"
          @keyup.enter="submit"
        />
      </el-form-item>

      <el-button type="primary" class="reg__submit" :loading="loading" @click="submit">
        注册并登录
      </el-button>
    </el-form>

    <p class="reg__foot">
      已有账号？
      <router-link class="reg__link" to="/login">返回登录</router-link>
    </p>
  </AuthLayout>
</template>

<style scoped>
.reg__title {
  margin: 0;
  color: var(--ssr-ink);
  font-size: 20px;
  font-weight: 600;
}

.reg__hint {
  margin: 6px 0 18px;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
}

.reg__submit {
  width: 100%;
}

.reg__foot {
  margin: 14px 0 0;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
  text-align: center;
}

.reg__link {
  color: var(--ssr-primary-ink);
  font-weight: 600;
}
</style>
