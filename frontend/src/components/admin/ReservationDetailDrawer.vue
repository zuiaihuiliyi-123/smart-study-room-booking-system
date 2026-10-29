<script setup lang="ts">
/**
 * 预约单详情抽屉（FR-030 / FR-011 / FR-023）。
 *
 * 两个写操作**在同一抽屉内**完成（不叠第二个弹窗）：原因就地填写，点击后只弹
 * `ElMessageBox.confirm` 做二次确认（含审计提示），符合「详情一律 drawer、不叠弹窗」的约束。
 *
 * 互斥口径（BR-015，界面必须直接说明）：
 * - 强制取消：仅「待使用」，不产生违约记录、不累加次数；
 * - 手动违约登记：仅「使用中」，会累加违约次数（累计 3 次 → 限制 7 天）；
 * - 同一预约单绝不会同时出现两个可用按钮。
 */
import { computed, ref, watch } from 'vue'

import AuditNotice from '@/components/admin/AuditNotice.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import StatusTag from '@/components/StatusTag.vue'
import type { Reservation } from '@/types'
import { seatIdLabel, userLabelOf, type AdminDirectory } from '@/utils/adminData'
import { bracketRangeText, durationText, slotMinutes } from '@/utils/bookingRules'
import { formatDateTime } from '@/utils/format'

const props = defineProps<{
  modelValue: boolean
  detail: Reservation | null
  loading: boolean
  loadingError: string
  directory: AdminDirectory | null
  scopeLabel: string
  canForceCancel: boolean
  canRegisterViolation: boolean
  userViolationCount: number | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'force-cancel', reason: string): void
  (e: 'register-violation', reason: string): void
}>()

const reason = ref('')

watch(
  () => props.detail?.id,
  () => {
    reason.value = ''
  },
)

const title = computed(() =>
    props.detail === null ? '预约单详情' : `预约单详情 · #${props.detail.id}`,
)

const slot = computed(() => {
  const item = props.detail
  if (item === null) return '—'
  return `${item.reserve_date} ${bracketRangeText(item.start_time, item.end_time)}（${durationText(slotMinutes(item.start_time, item.end_time))}）`
})

const reasonLabel = computed(() => (props.canForceCancel ? '取消原因（必填）' : '登记原因（必填）'))

const stateNote = computed(() => {
  const status = props.detail?.status ?? ''
  if (props.canForceCancel) return '当前为「待使用」：可使用「强制取消」，该操作不计违约。'
  if (props.canRegisterViolation) return '当前为「使用中」：可登记「手动违约」，该操作会累加违约次数。'
  return `当前为「${status}」：强制取消仅适用于「待使用」、手动违约登记仅适用于「使用中」，因此两个操作均不可用。`
})
</script>

<template>
  <el-drawer
    :model-value="props.modelValue"
    :title="title"
    size="620px"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <AuditNotice
      :scope="props.scopeLabel"
      :extra="'强制取消与 手动违约登记互斥；两者都要求填写原因并写入审计日志。'"
    />

    <LoadingBlock v-if="props.loading" :rows="4" text="正在读取预约单…" />

    <el-alert
      v-else-if="props.loadingError"
      type="error"
      :closable="false"
      show-icon
      title="预约单详情读取失败"
    >
      <p>{{ props.loadingError }}</p>
      <p class="ssr-text-muted">下方展示的是列表中的快照，状态可能已过期，请关闭后刷新列表再试。</p>
    </el-alert>

    <template v-if="props.detail">
      <div class="head">
        <strong>#{{ props.detail.id }}</strong>
        <StatusTag kind="reservation" :value="props.detail.status" />
      </div>

      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="使用人">
          {{ userLabelOf(props.directory, props.detail.user_id) }}
        </el-descriptions-item>
        <el-descriptions-item label="累计违约次数">
          <span v-if="props.userViolationCount === null">—</span>
          <span v-else>{{ props.userViolationCount }} / 3（达到 3 次限制 7 天）</span>
        </el-descriptions-item>
        <el-descriptions-item label="座位" :span="2">
          {{ seatIdLabel(props.directory, props.detail.seat_id) }}
        </el-descriptions-item>
        <el-descriptions-item label="预约时段" :span="2">{{ slot }}</el-descriptions-item>
        <el-descriptions-item label="签到时间">
          {{ formatDateTime(props.detail.check_in_time) }}
        </el-descriptions-item>
        <el-descriptions-item label="签退时间">
          {{ formatDateTime(props.detail.check_out_time) }}
        </el-descriptions-item>
        <el-descriptions-item label="取消时间">
          {{ formatDateTime(props.detail.cancel_time) }}
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ formatDateTime(props.detail.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="取消 / 变更原因" :span="2">
          {{ props.detail.cancel_reason ?? '—' }}
        </el-descriptions-item>
      </el-descriptions>

      <el-alert class="notice" type="info" :closable="false" show-icon :title="stateNote" />

      <section class="action-box">
        <h4 class="drawer-section">管理操作</h4>

        <p class="drawer-note">
          两个操作的区别：<strong>强制取消</strong>用于事前终止（不收违约、不累加次数）；
          <strong>手动违约登记</strong>用于事后追责（会累加违约次数，累计 3 次触发 7 天限制）。
            同一预约单只会出现其中一个可用按钮。
            </p>

            <el-form label-width="112px" @submit.prevent>
              <el-form-item :label="reasonLabel">
                <el-input
                  v-model="reason"
                  type="textarea"
                  :rows="2"
                  maxlength="255"
                  show-word-limit
                  :placeholder="
                  props.canForceCancel
                  ? '如：场地临时检修，已电话告知用户'
                  : '如：已签到但超时未签退，且座位被长时间空占'
                  "
                />
              </el-form-item>
            </el-form>

            <div class="drawer-actions">
              <el-button
                v-if="props.canForceCancel"
                type="danger"
                :disabled="reason.trim() === ''"
                @click="emit('force-cancel', reason)"
              >
                强制取消（不产生违约记录、不累加次数）
              </el-button>
              <el-button
                v-else-if="props.canRegisterViolation"
                type="warning"
                :disabled="reason.trim() === ''"
                @click="emit('register-violation', reason)"
              >
                手动违约登记（将累加违约次数）
              </el-button>
              <el-tooltip
                v-else
                content="强制取消仅适用于「待使用」，手动违约登记仅适用于「使用中」"
                placement="top"
              >
                <span>
                  <el-button disabled>当前状态无可用操作</el-button>
                </span>
              </el-tooltip>
            </div>
          </section>
        </template>
      </el-drawer>
</template>

<style scoped>
.head {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
  font-size: 15px;
}

.notice {
  margin: 12px 0;
}

.notice :deep(p) {
  margin: 0;
}

.action-box {
  padding: 12px;
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius);
}
</style>
