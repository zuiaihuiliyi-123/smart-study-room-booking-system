<script setup lang="ts">
/**
 * 修改登录密码弹窗（B1）。
 *
 * - 必须输入原密码；新密码 8～64 位，且不能与原密码相同；
 * - 后端成功后返回新令牌，当前设备保持登录；
 * - 其他设备此前签发的令牌会立即失效（token_version 已递增）。
 */
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Lock } from '@element-plus/icons-vue'

import { useAuthStore } from '@/stores/auth'

const props = defineProps<{ modelValue: boolean }>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'success'): void
}>()

const auth = useAuthStore()
const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({
  old_password: '',
  new_password: '',
  confirm: '',
})

const rules: FormRules = {
  old_password: [
    { required: true, message: '请输入原密码', trigger: 'blur' },
    { min: 6, max: 64, message: '密码长度为 6–64 位', trigger: 'blur' },
  ],
  new_password: [
    { required: true, message: '请设置新密码', trigger: 'blur' },
    { min: 8, max: 64, message: '新密码长度为 8–64 位', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback: (error?: Error) => void) => {
        if (value && value === form.old_password) {
          callback(new Error('新密码不能与原密码相同'))
          return
        }
        callback()
      },
      trigger: ['blur', 'change'],
    },
  ],
  confirm: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback: (error?: Error) => void) => {
        callback(value === form.new_password ? undefined : new Error('两次输入的新密码不一致'))
      },
      trigger: ['blur', 'change'],
    },
  ],
}

function close(): void {
  emit('update:modelValue', false)
}

function reset(): void {
  form.old_password = ''
  form.new_password = ''
  form.confirm = ''
  formRef.value?.clearValidate()
}

async function submit(): Promise<void> {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await auth.changePassword({
      old_password: form.old_password,
      new_password: form.new_password,
    })
    ElMessage.success('密码已修改，其他设备需重新登录')
    emit('success')
    close()
    reset()
  } catch {
    // 失败提示由 request.ts 拦截器统一给出（原密码错误 / 新密码不合规）
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="props.modelValue"
    title="修改登录密码"
    width="440px"
    :close-on-click-modal="false"
    @update:model-value="emit('update:modelValue', $event)"
    @closed="reset"
  >
    <el-alert class="tip" type="info" :closable="false" show-icon title="修改后会发生什么">
      <p>当前设备会保持登录；其他设备此前登录的会话会立即失效，需要重新登录。</p>
      <p>新密码长度为 8–64 位，不能与原密码相同。</p>
    </el-alert>

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      @submit.prevent="submit"
    >
      <el-form-item label="原密码" prop="old_password">
        <el-input
          v-model="form.old_password"
          type="password"
          show-password
          placeholder="请输入当前登录密码"
          autocomplete="current-password"
          :prefix-icon="Lock"
        />
      </el-form-item>

      <el-form-item label="新密码" prop="new_password">
        <el-input
          v-model="form.new_password"
          type="password"
          show-password
          placeholder="8–64 位，建议字母与数字组合"
          autocomplete="new-password"
          :prefix-icon="Lock"
        />
      </el-form-item>

      <el-form-item label="确认新密码" prop="confirm">
        <el-input
          v-model="form.confirm"
          type="password"
          show-password
          placeholder="请再次输入新密码"
          autocomplete="new-password"
          :prefix-icon="Lock"
          @keyup.enter="submit"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存新密码</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.tip {
  margin-bottom: 16px;
}

.tip p {
  margin: 0 0 4px;
  font-size: var(--ssr-font-note);
  line-height: 1.6;
}

.tip p:last-child {
  margin-bottom: 0;
}
</style>
