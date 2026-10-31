<script setup lang="ts">
/**
 * 手动加入黑名单对话框（ST-041）。
 *
 * 必填项：用户、限制原因；期限可选。手动限制无论是否设期限都不会自动解除（ST-042）。
 * 提交前会弹一次 `ElMessageBox.confirm` 二次确认（含审计提示），因此本组件本身不是确认环节。
 */
import { computed, reactive, ref, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'

import AuditNotice from '@/components/admin/AuditNotice.vue'
import type { AdminDirectory } from '@/utils/adminData'
import { formatApiDateTime } from '@/utils/format'

const props = defineProps<{
  modelValue: boolean
  directory: AdminDirectory | null
  scopeLabel: string
  submitting: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'submit', payload: { user_id: number; reason: string; expire_at: string | null }): void
}>()

const formRef = ref<FormInstance>()

/** FR-044 的常见做法：默认 7 天后到期（RULES.restrictionDays）；管理员可改成「不设期限」 */
function defaultExpireAt(): string {
  return formatApiDateTime(new Date(Date.now() + 7 * 86_400_000))
}

const form = reactive<{
  user_id: number | null
  reason: string
  expire_at: string
  hasExpire: boolean
}>({
  user_id: null,
  reason: '',
  expire_at: defaultExpireAt(),
  hasExpire: true,
})

const rules: FormRules = {
  user_id: [{ required: true, message: '请选择要限制的用户', trigger: 'change' }],
  reason: [
    { required: true, message: '请填写限制原因：原因会写入审计日志', trigger: 'blur' },
    { max: 255, message: '原因不超过 255 字', trigger: 'blur' },
  ],
}

const candidates = computed(() =>
    (props.directory?.users ?? []).filter((user) => user.role !== '系统管理员'),
)

watch(
  () => props.modelValue,
  (visible) => {
    if (!visible) return
    form.user_id = null
    form.reason = ''
    form.hasExpire = true
    form.expire_at = defaultExpireAt()
    formRef.value?.clearValidate()
  },
)

async function onSubmit(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (valid !== true || form.user_id === null) return
  emit('submit', {
    user_id: form.user_id,
    reason: form.reason,
    expire_at: form.hasExpire ? form.expire_at : null,
  })
}
</script>

<template>
  <el-dialog
    :model-value="props.modelValue"
    title="手动加入黑名单"
    width="560px"
    :close-on-click-modal="false"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <AuditNotice
      :scope="props.scopeLabel"
      :extra="'黑名单记录保留 1 年；加入时必须填写限制原因，加入后账户转为「受限」，该用户无法创建新预约。'"
    />

    <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
      <el-form-item label="用户" prop="user_id">
        <el-select
          v-model="form.user_id"
          class="w-full"
          filterable
          placeholder="按姓名 / 学号搜索用户"
        >
          <el-option
            v-for="user in candidates"
            :key="user.id"
            :label="`${user.name}（${user.student_no}）· ${user.role} · 违约 ${user.violation_count} 次`"
            :value="user.id"
          />
        </el-select>
        <p class="ssr-text-muted hint">
          候选列表来自用户目录（不含系统管理员）。列表为空时请先在「用户管理」确认用户是否存在。
        </p>
      </el-form-item>

      <el-form-item label="限制原因" prop="reason">
        <el-input
          v-model="form.reason"
          type="textarea"
          :rows="2"
          maxlength="255"
          show-word-limit
          placeholder="如：多次占座不到场，经核实后限制"
        />
      </el-form-item>

      <el-form-item label="限制期限">
        <el-switch v-model="form.hasExpire" active-text="指定期限" inactive-text="不设期限" />
        <el-date-picker
          v-if="form.hasExpire"
          v-model="form.expire_at"
          class="w-datetime"
          type="datetime"
          value-format="YYYY-MM-DDTHH:mm:ss"
          placeholder="解除时间"
        />
        <p class="ssr-text-muted hint">
          手动加入的限制<strong>无论是否设定期限，系统都不会自动解除</strong>；
          「期限」仅作计划解除时间，到期后仍须管理员手动解除。
        </p>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="props.submitting" @click="onSubmit">提交</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.hint {
  display: block;
  margin: 4px 0 0;
  line-height: 1.6;
}
</style>



