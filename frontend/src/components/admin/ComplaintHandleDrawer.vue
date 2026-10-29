<script setup lang="ts">
/**
 * 投诉处理抽屉（FR-043 + BR-014）。
 *
 * 只允许第 5.4 节状态转换表定义的流转（ST-060～ST-063）：
 * - 待处理 → 处理中（受理） / 待处理 → 已驳回（必填驳回理由）；
 * - 处理中 → 已处理（必填处理说明）；
 * - 已处理 → 已关闭由**投诉人确认或系统超时**触发，管理端不提供入口。
 *
 * 处理说明 / 驳回理由必填，既同步给投诉人（站内消息），也写入审计日志（NFR-009）。
 */
import { computed, ref, watch } from 'vue'

import AuditNotice from '@/components/admin/AuditNotice.vue'
import StatusTag from '@/components/StatusTag.vue'
import type { Complaint } from '@/types'
import { complaintTargetLabel, userLabelOf, type AdminDirectory } from '@/utils/adminData'
import { formatDateTime } from '@/utils/format'
import { complaintSla } from '@/utils/workday'

const props = defineProps<{
  modelValue: boolean
  complaint: Complaint | null
  directory: AdminDirectory | null
  scopeLabel: string
  submitting: boolean
  /** 允许的下一步状态（由 composable 的 nextActions 计算，界面不自算） */
  actions: Complaint['status'][]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'handle', status: Complaint['status'], note: string): void
}>()

const target = ref<Complaint['status'] | ''>('')
const note = ref('')

const ACTION_LABEL: Record<string, string> = {
  处理中: '受理（待处理 → 处理中）',
  已驳回: '驳回（必填驳回理由）',
  已处理: '录入处理结果（处理中 → 已处理）',
}

watch(
  () => [props.modelValue, props.complaint?.id] as const,
  () => {
    if (!props.modelValue) return
    target.value = props.actions[0] ?? ''
    note.value = props.complaint?.handle_note ?? ''
  },
  { immediate: true },
)

const sla = computed(() => complaintSla(props.complaint?.created_at ?? null, new Date()))

/** 只有尚未给出处理结果的投诉才谈得上「超时」；已处理 / 已驳回只回溯是否曾经超出时限 */
const pending = computed(
  () => props.complaint?.status === '待处理' || props.complaint?.status === '处理中',
)

const noteLabel = computed(() => (target.value === '已驳回' ? '驳回理由（必填）' : '处理说明（必填）'))

const title = computed(() =>
    props.complaint === null ? '投诉处理' : `投诉处理 · #${props.complaint.id}`,
)
</script>

<template>
  <el-drawer
    :model-value="props.modelValue"
    :title="title"
    size="620px"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template v-if="props.complaint">
      <AuditNotice
        :scope="props.scopeLabel"
        :extra="'处理说明 / 驳回理由必填，会同步给投诉人并记入审计日志。'"
      />

      <div class="head">
        <strong>#{{ props.complaint.id }}</strong>
        <StatusTag kind="complaint" :value="props.complaint.status" />
        <el-tag v-if="sla.overdue && pending" class="ssr-tag ssr-tag--err" disable-transitions>
          已超时 {{ sla.overdueDays }} 天
        </el-tag>
      </div>

      <el-descriptions :column="1" border size="small">
        <el-descriptions-item label="提交人">
          {{ userLabelOf(props.directory, props.complaint.user_id) }}
        </el-descriptions-item>
        <el-descriptions-item label="投诉对象">
          {{ complaintTargetLabel(props.directory, props.complaint.target_type, props.complaint.target_id) }}
        </el-descriptions-item>
        <el-descriptions-item label="投诉内容">{{ props.complaint.content }}</el-descriptions-item>
        <el-descriptions-item label="提交时间">
          {{ formatDateTime(props.complaint.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="处理时限">
          {{ sla.deadlineText }}
          <span class="ssr-text-muted">{{ sla.note }}</span>
          <span v-if="sla.overdue && pending" class="ssr-text-muted">已超时 {{ sla.overdueDays }} 天（按自然日计）</span>
          <span v-else-if="sla.overdue" class="ssr-text-muted">
            处理结果超出时限 {{ sla.overdueDays }} 天（按自然日计，要求 3 个工作日内给出处理结果）
          </span>
          <span v-else-if="pending" class="ssr-text-muted">距截止尚余 {{ sla.remainingWorkdays }} 个工作日</span>
        </el-descriptions-item>
        <el-descriptions-item label="当前处理记录">
          <span v-if="props.complaint.handle_note === null" class="ssr-text-muted">尚未处理</span>
          <span v-else>
            {{ props.complaint.handle_note }}
            <span class="ssr-text-muted">
              （处理人：{{
              props.complaint.handler_id === null
              ? '系统'
              : userLabelOf(props.directory, props.complaint.handler_id)
              }}，{{ formatDateTime(props.complaint.handled_at) }}）
            </span>
          </span>
        </el-descriptions-item>
      </el-descriptions>

      <el-alert class="notice" type="info" :closable="false" show-icon title="状态流转口径（～）">
        <p>待处理 →（受理）处理中 →（录入处理结果）已处理；待处理 →（驳回）已驳回。</p>
        <p>
          已处理 → 已关闭 由<strong>投诉人确认</strong>或<strong>系统超过关闭时限</strong>触发，
          管理端不提供直接置为「已关闭」的入口；关闭时限属实现层、本版不规定。
        </p>
      </el-alert>

      <template v-if="props.actions.length > 0">
        <el-form label-width="104px" @submit.prevent>
          <el-form-item label="流转为">
            <el-radio-group v-model="target">
              <el-radio v-for="action in props.actions" :key="action" :value="action">
                {{ ACTION_LABEL[action] ?? action }}
              </el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item :label="noteLabel">
            <el-input
              v-model="note"
              type="textarea"
              :rows="3"
              maxlength="500"
              show-word-limit
              placeholder="如：已联系物业更换台灯，维修完成后回复；驳回时请写明驳回理由"
            />
          </el-form-item>
        </el-form>

        <div class="drawer-actions">
          <el-button @click="emit('update:modelValue', false)">取消</el-button>
          <el-button
            type="primary"
            :loading="props.submitting"
            :disabled="target === '' || note.trim() === ''"
            @click="target !== '' && emit('handle', target, note)"
          >
            提交处理结果
          </el-button>
        </div>
      </template>

      <el-alert
        v-else
        class="notice"
        type="warning"
        :closable="false"
        show-icon
        title="当前状态没有管理端可执行的流转"
      >
        <p>
          「{{ props.complaint.status }}」是管理员流程的终态：
          {{
          props.complaint.status === '已处理'
          ? '等待投诉人确认后由系统关闭'
          : '如需重新处理，属于需求未定义的操作，本版不提供（见问题清单）'
          }}。
        </p>
      </el-alert>
    </template>
  </el-drawer>
</template>

<style scoped>
.head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
  font-size: 15px;
}

.notice {
  margin: 12px 0;
}

.notice p {
  margin: 0 0 4px;
  font-size: var(--ssr-font-note);
  line-height: 1.6;
}
</style>
