<script setup lang="ts">
/**
 * 新增 / 编辑自习室对话框（FR-001）。
 *
 * 校验口径：
 * - 名称 ≤50、位置 ≤100（与后端 `RoomCreate` 的 Field 约束一致）；
 * - 闭馆时间必须晚于开放时间（跨字段校验，两条时间都改动时即时提示）；
 * - 「变更说明」为审计事由（NFR-009），必填。
 *
 * 口径提示：本对话框的「启用状态」只改自习室**自身**的启用标记（FR-001 用停用代替删除）。
 * 后端第 4.4.2 节的 C1 判定目前不引用 `room.enabled`，所以停用自习室**不会**让它的座位
 * 变为不可预约——要立即阻止预约须走「临时关闭」（FR-016 / BR-022），界面已就地说明。
 */
import { computed, reactive, ref, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'

import AuditNotice from '@/components/admin/AuditNotice.vue'
import type { Room } from '@/types'
import type { RoomFormPayload } from '@/utils/useRoomManage'

const props = defineProps<{
  modelValue: boolean
  /** null = 新增；否则为编辑目标 */
  room: Room | null
  submitting: boolean
  scopeLabel: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'submit', payload: RoomFormPayload): void
}>()

const formRef = ref<FormInstance>()

const form = reactive<RoomFormPayload>({
  name: '',
  location: '',
  open_time: '08:00',
  close_time: '22:00',
  capacity: 30,
  enabled: true,
  reason: '',
})

const rules: FormRules = {
  name: [
    { required: true, message: '请填写自习室名称', trigger: 'blur' },
    { max: 50, message: '名称不超过 50 字', trigger: 'blur' },
  ],
  location: [
    { required: true, message: '请填写位置', trigger: 'blur' },
    { max: 100, message: '位置不超过 100 字', trigger: 'blur' },
  ],
  open_time: [{ required: true, message: '请选择开放时间', trigger: 'change' }],
  close_time: [{ required: true, message: '请选择闭馆时间', trigger: 'change' }],
  reason: [
    { required: true, message: '请填写变更说明：该说明会写入审计日志', trigger: 'blur' },
    { max: 255, message: '说明不超过 255 字', trigger: 'blur' },
  ],
}

/** 跨字段校验：闭馆必须晚于开放（字符串比较对 `HH:mm` 有效） */
const timeError = computed(() =>
    form.open_time !== '' && form.close_time !== '' && form.close_time <= form.open_time
    ? `闭馆时间必须晚于开放时间（当前 ${form.open_time} → ${form.close_time}）`
    : '',
)

const title = computed(() => (props.room === null ? '新增自习室' : `编辑自习室 · ${props.room.name}`))

watch(
  () => props.modelValue,
  (visible) => {
    if (!visible) return
    const target = props.room
    form.name = target?.name ?? ''
    form.location = target?.location ?? ''
    form.open_time = target?.open_time?.slice(0, 5) ?? '08:00'
    form.close_time = target?.close_time?.slice(0, 5) ?? '22:00'
    form.capacity = target?.capacity ?? 30
    form.enabled = target?.enabled ?? true
    form.reason = ''
    formRef.value?.clearValidate()
  },
)

async function onSubmit(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (valid !== true || timeError.value !== '') return
  emit('submit', { ...form })
}

function close(): void {
  emit('update:modelValue', false)
}
</script>

<template>
  <el-dialog
    :model-value="props.modelValue"
    :title="title"
    width="560px"
    :close-on-click-modal="false"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <AuditNotice :scope="props.scopeLabel" :extra="`本次为${props.room === null ? '新增' : '修改'}自习室：名称、位置、开放时间与容量将写入资源表。`" />

    <el-form ref="formRef" :model="form" :rules="rules" label-width="96px" label-position="right">
      <el-form-item label="自习室名称" prop="name">
        <el-input v-model="form.name" maxlength="50" show-word-limit placeholder="如：第一自习室" />
      </el-form-item>

      <el-form-item label="位置" prop="location">
        <el-input v-model="form.location" maxlength="100" placeholder="如：图书馆 A 区 3 楼" />
      </el-form-item>

      <el-form-item label="开放时间" prop="open_time">
        <el-time-select
          v-model="form.open_time"
          class="time-select"
          start="06:00"
          step="00:30"
          end="23:30"
          placeholder="开放时间"
          aria-label="开放时间（开始）"
        />
        <span class="range-sep">至</span>
        <el-time-select
          v-model="form.close_time"
          class="time-select"
          start="06:30"
          step="00:30"
          end="23:30"
          placeholder="闭馆时间"
          aria-label="闭馆时间（结束）"
        />
      </el-form-item>

      <el-form-item v-if="timeError" label=" ">
        <el-alert type="error" :closable="false" show-icon :title="timeError" />
      </el-form-item>

      <el-form-item label="容量" prop="capacity">
        <el-input-number v-model="form.capacity" :min="0" :max="999" :step="1" />
        <span class="ssr-text-muted hint">座位数由「座位管理」维护，此处为自习室的公示容量</span>
      </el-form-item>

      <el-form-item v-if="props.room !== null" label="启用状态">
        <el-switch v-model="form.enabled" active-text="启用" inactive-text="停用" />
        <p class="ssr-text-muted hint">
          停用仅改变自习室自身的启用标记，不影响座位是否可被预约；若要立即阻止其座位被预约，
          请改用列表中的「临时关闭」，该操作会把范围内座位置为「停用」并列出受影响预约。
        </p>
      </el-form-item>

      <el-form-item label="变更说明" prop="reason">
        <el-input
          v-model="form.reason"
          type="textarea"
          :rows="2"
          maxlength="255"
          show-word-limit
          placeholder="如：新增自习室 / 调整闭馆时间至 22:00"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button
        type="primary"
        :loading="props.submitting"
        :disabled="timeError !== ''"
        @click="onSubmit"
      >
        保存
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.time-select {
  width: 132px;
}

.range-sep {
  padding: 0 8px;
  color: var(--ssr-muted-ink);
}

.hint {
  display: block;
  margin: 4px 0 0;
  line-height: 1.6;
}
</style>



