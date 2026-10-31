<script setup lang="ts">
import { computed } from 'vue'

import RuleChecklist from '@/components/booking/RuleChecklist.vue'
import SeatSummaryList from '@/components/booking/SeatSummaryList.vue'
import type { BookingFailure, JudgementItem, SubmitState, SubmitSuccess } from '@/components/booking/types'
import type { Room, Seat } from '@/types'
import {
  BOOKING_RULES,
  durationText,
  restrictUntilText,
  slotMinutes,
  timeRangeText,
} from '@/utils/bookingRules'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  seat: Seat | null
  room: Room | null
  areaTitle: string
  reserveDate: string
  startTime: string
  endTime: string
  judgements: JudgementItem[]
  submitState: SubmitState
  failure: BookingFailure | null
  success: SubmitSuccess | null
  /** 已选座位不在当前筛选结果中时的说明 */
  staleReason: string
  canSubmit: boolean
}>()

const emit = defineEmits<{
  (e: 'submit'): void
  (e: 'close'): void
}>()

const minutes = computed(() => slotMinutes(props.startTime, props.endTime))

/** 时段占用（派生结论）与上面的资源状态分开呈现，两者不合并（AGENTS.md §4）。 */
const occupancyLabel = computed(() => {
  const state = props.judgements.find((item) => item.id === 'C3')?.state ?? 'unknown'
  if (state === 'pass') return '可约（该时段无其他有效预约）'
  if (state === 'fail') return '该时段已被预约'
  return '未判定'
})

const durationNote = computed(() => {
  const total = minutes.value
  if (total <= 0) return '结束时间须晚于开始时间'
  return `时长 ${durationText(total)}（上限 ${BOOKING_RULES.maxHours} 小时）；区间按左闭右开 [s, e) 判定，结束后该时段自动重新可预约。`
})

const failureTitle = computed(() => {
  const failure = props.failure
  if (!failure) return ''
  if (failure.kind === 'conflict') return '该时段已被预约，请重新选择'
  if (failure.kind === 'restricted') return '账户受限，暂不可预约'
  if (failure.kind === 'expired') return '所选时段已过期'
  return failure.message
})

const failureType = computed<'error' | 'warning'>(() =>
    props.failure?.kind === 'conflict' || props.failure?.kind === 'expired' ? 'warning' : 'error',
)

const failedJudgementText = computed(() => {
  const failure = props.failure
  if (!failure?.judgement) return ''
  const hit = props.judgements.find((item) => item.id === failure.judgement)
  return `${failure.judgement} ${hit ? hit.title : ''}`.trim()
})

const submitLabel = computed(() => {
  if (props.submitState === 'submitting') return '提交中'
  if (props.submitState === 'submitted') return '已提交，请勿重复操作'
  return '提交预约'
})

function onClose() {
  visible.value = false
  emit('close')
}
</script>

<template>
  <el-drawer
    v-model="visible"
    :modal="false"
    :close-on-click-modal="false"
    size="min(480px, 94vw)"
    :title="props.seat ? `座位详情 · ${props.seat.seat_no}` : '座位详情'"
    class="seat-drawer"
    @close="emit('close')"
  >
    <template v-if="props.seat">
      <SeatSummaryList
        :seat="props.seat"
        :room="props.room"
        :area-title="props.areaTitle"
        :occupancy-label="occupancyLabel"
        :reserve-date="props.reserveDate"
        :start-time="props.startTime"
        :end-time="props.endTime"
        :duration-note="durationNote"
      />

      <section class="drawer-block">
        <h4 class="drawer-block__title">
          规则校验
          <span v-if="props.submitState === 'submitted'" class="ssr-text-muted">
            提交成功后的重新评估：该时段此刻已归你占用，因此「时段占用」「本人时段冲突」「每日次数」会转为未通过
          </span>
          <span v-else class="ssr-text-muted">本地预估，提交结果以服务端为准</span>
        </h4>
        <RuleChecklist :items="props.judgements" />
      </section>

      <el-alert
        v-if="props.staleReason"
        class="drawer-alert"
        type="warning"
        :closable="false"
        show-icon
        title="已选座位不在当前筛选结果中"
        :description="props.staleReason"
      />

      <el-alert
        v-if="props.failure"
        class="drawer-alert"
        :type="failureType"
        :closable="false"
        show-icon
        :title="failureTitle"
      >
        <p>{{ props.failure.message }}</p>
        <p v-if="props.failure.kind === 'restricted' && props.failure.restrictUntil">
          预计解除时间：{{ restrictUntilText(props.failure.restrictUntil) }}
          <span class="ssr-text-muted">（仅自动限制有自动解除时间）</span>
        </p>
        <p v-else-if="props.failure.kind === 'restricted'">
          该限制为管理员手动限制，须由管理员解除，没有自动解除时间。
        </p>
        <p v-if="failedJudgementText">
          未通过判定项：{{ failedJudgementText }}
        </p>
        <p v-if="props.failure.kind === 'conflict'">
          同一座位同一时段至多一条预约成功，请改选其他座位或时段后重新提交。
        </p>
      </el-alert>

      <el-alert
        v-if="props.success"
        class="drawer-alert"
        type="success"
        :closable="false"
        show-icon
        title="已提交，请勿重复操作"
      >
        <p>
          预约单号 #{{ props.success.id }} · {{ props.success.seatText }} ·
          {{ props.success.reserveDate }} {{ timeRangeText(props.success.startTime, props.success.endTime) }}
        </p>
        <p>
          签到时间窗：<strong>{{ props.success.window.rangeText }}</strong>
          （{{ props.success.window.opensText }} 至 {{ props.success.window.closesText }}，开始前
          {{ BOOKING_RULES.checkinEarly }} 分钟至开始后 {{ BOOKING_RULES.checkinLate }} 分钟）
        </p>
        <p class="ssr-text-muted">
          该时段对他人已变为不可预约；座位资源状态保持「可用」不变（D-04）。
        </p>
      </el-alert>
    </template>

    <template #footer>
      <div class="drawer-footer">
        <el-button @click="onClose">关闭</el-button>
        <el-button
          type="primary"
          :loading="props.submitState === 'submitting'"
          :disabled="props.submitState !== 'idle' || !props.canSubmit"
          @click="emit('submit')"
        >
          {{ submitLabel }}
        </el-button>
      </div>
    </template>
  </el-drawer>
</template>

<style scoped>
  .drawer-block + .drawer-block {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--ssr-line);
}

  .drawer-block__title {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
}

  .drawer-block__title .ssr-text-muted {
  font-weight: 400;
}


  .drawer-alert {
  margin-top: 14px;
}

  .drawer-alert p {
  margin: 2px 0 0;
  font-size: var(--ssr-font-note);
  line-height: 1.7;
}

  .drawer-footer {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
</style>

<!--
 非模态抽屉：Element Plus 即使 modal=false 也会渲染一个铺满视口的外层容器（.el-modal-drawer），
 它会拦截指针事件，导致打开抽屉后左侧筛选栏与座位矩阵点不动。
 这里只把「包含本组件 .seat-drawer 的那个外层容器」放开，抽屉面板本身仍可交互；
 其它对话框 / 抽屉不受影响。
-->
<style>
.el-modal-drawer:has(> .seat-drawer) {
  pointer-events: none;
}

.el-modal-drawer:has(> .seat-drawer) > .seat-drawer {
  pointer-events: auto;
}
</style>


