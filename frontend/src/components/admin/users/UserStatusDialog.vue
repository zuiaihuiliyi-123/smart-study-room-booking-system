<script setup lang="ts">
import { computed } from 'vue'

import type { CurrentUser } from '@/types'

const visible = defineModel<boolean>({ required: true })
const reason = defineModel<string>('reason', { required: true })

const props = defineProps<{
  target: CurrentUser | null
  targetValue: '停用' | '正常'
  submitting: boolean
  error: string
}>()

const emit = defineEmits<{
  (e: 'submit'): void
  (e: 'close'): void
}>()

const isDisable = computed(() => props.targetValue === '停用')
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="isDisable ? '停用账户' : '恢复账户'"
    width="480px"
    :close-on-click-modal="false"
    @closed="emit('close')"
  >
    <p class="status-line">
      目标用户：<strong>{{ props.target?.name ?? '—' }}</strong>
      <span class="ssr-text-muted">（{{ props.target?.student_no ?? '' }}）</span>
    </p>

    <el-alert
      class="block"
      :type="isDisable ? 'warning' : 'info'"
      :closable="false"
      show-icon
      :title="
        isDisable
          ? '停用后该账户将无法登录；既有预约与历史记录不受影响。'
          : '恢复后该账户可重新登录并创建预约。'
      "
    />

    <el-form label-position="top" class="block">
      <el-form-item label="变更原因（必填，将记入审计日志）">
        <el-input
          v-model="reason"
          type="textarea"
          :rows="3"
          maxlength="255"
          show-word-limit
          placeholder="如：多次冒用他人账号 / 核实完毕，恢复使用"
        />
      </el-form-item>
    </el-form>

    <el-alert
      v-if="props.error"
      class="block"
      type="error"
      :closable="false"
      show-icon
      :title="props.error"
    />

    <template #footer>
      <el-button :disabled="props.submitting" @click="emit('close')">取消</el-button>
      <el-button
        :type="isDisable ? 'danger' : 'primary'"
        :loading="props.submitting"
        @click="emit('submit')"
      >
        确认{{ isDisable ? '停用' : '恢复' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.status-line {
  margin: 0 0 10px;
  font-size: var(--ssr-font-body);
}

.block {
  margin-bottom: 12px;
}
</style>
