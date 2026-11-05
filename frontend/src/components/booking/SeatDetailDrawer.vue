<script setup lang="ts">
import { CircleCheckFilled, CircleCloseFilled, WarningFilled } from '@element-plus/icons-vue'
import { computed, type Component } from 'vue'

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
  /** 这个座位是不是你自己在这个时段已经约下的 */
  mine?: boolean
}>()

const emit = defineEmits<{
  (e: 'submit'): void
  (e: 'close'): void
}>()

const minutes = computed(() => slotMinutes(props.startTime, props.endTime))

/** 时段占用（派生结论）与上面的资源状态分开呈现，两者不合并（AGENTS.md §4）。 */
const occupancyLabel = computed(() => {
  const state = props.judgements.find((item) => item.id === 'C3')?.state ?? 'unknown'
  if (state === 'pass') return '可约'
  if (state === 'fail') return props.mine ? '你已预约这个座位' : '该时段已被预约'
  return '暂无法判断'
})

const durationNote = computed(() => {
  const total = minutes.value
  if (total <= 0) return '结束时间须晚于开始时间'
  return `${durationText(total)}`
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
  return hit ? hit.title : ''
})

/** 只回答「能不能约」：一句结论 + 一句原因，不再逐条展开检查项 */
const verdict = computed<{ tone: 'ok' | 'no' | 'wait'; icon: Component; title: string; note: string }>(() => {
  if (props.submitState === 'submitted') {
    return {
      tone: 'ok',
      icon: CircleCheckFilled,
      title: '已提交成功',
      note: '再次打开时会显示该时段属于你',
    }
  }

  const failed = props.judgements.filter((item) => item.state === 'fail')
  const firstFailed = failed[0]
  if (firstFailed) {
    const extra = failed.length > 1 ? `（另有 ${failed.length - 1} 项不满足）` : ''
    return {
      tone: 'no',
      icon: CircleCloseFilled,
      title: '暂时不能预约',
      note: `${firstFailed.detail}${extra}`,
    }
  }

  const unknown = props.judgements.find((item) => item.state === 'unknown')
  if (unknown) {
    return { tone: 'wait', icon: WarningFilled, title: '暂无法判断', note: unknown.detail }
  }

  return {
    tone: 'ok',
    icon: CircleCheckFilled,
    title: '可以预约',
    note: '所选时段空闲，确认后点「提交预约」即可',
  }
})

const submitLabel = computed(() => {
  if (props.submitState === 'submitting') return '提交中'
  if (props.submitState === 'submitted') return '已提交'
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

      <section v-if="props.submitState !== 'submitted'" class="drawer-block">
        <div class="verdict" :class="`verdict--${verdict.tone}`">
          <el-icon class="verdict__icon"><component :is="verdict.icon" /></el-icon>
          <div class="verdict__body">
            <strong class="verdict__title">{{ verdict.title }}</strong>
            <p class="verdict__note">{{ verdict.note }}</p>
          </div>
        </div>
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
          <span class="ssr-text-muted">（限制 7 天，期满自动解除）</span>
        </p>
        <p v-else-if="props.failure.kind === 'restricted'">
          该限制为管理员手动限制，须由管理员解除，没有自动解除时间。
        </p>
        <p v-if="failedJudgementText">
          未通过检查：{{ failedJudgementText }}
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
        title="预约成功"
        :description="`${props.success.seatText} · ${props.success.reserveDate} ${timeRangeText(props.success.startTime, props.success.endTime)}`"
      >
        <p>
          签到时间：<strong>{{ props.success.window.rangeText }}</strong>，请按时到座签到。
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
.drawer-block + .drawer-block { margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--ssr-line); }
.drawer-block__title { display: flex; flex-wrap: wrap; gap: 8px; align-items: baseline; margin: 0 0 8px; font-size: 15px; font-weight: 600; }
.drawer-block__title .ssr-text-muted { font-weight: 400; }

/* 一句结论：能不能约。底色 + 图标 + 文字三重区分，不只靠颜色 */
.verdict { display: flex; gap: 10px; align-items: flex-start; padding: 12px 14px; border: 1px solid var(--ssr-line); border-radius: var(--ssr-radius); }
.verdict__icon { margin-top: 1px; font-size: 18px; }
.verdict__body { min-width: 0; }
.verdict__title { display: block; font-size: 15px; line-height: 1.4; }
.verdict__note { margin: 3px 0 0; font-size: var(--ssr-font-note); line-height: 1.7; color: var(--ssr-muted-ink); }
.verdict--ok { border-color: color-mix(in srgb, var(--ssr-success) 32%, transparent); background: var(--ssr-success-bg); }
.verdict--ok .verdict__icon,
.verdict--ok .verdict__title { color: var(--ssr-success); }
.verdict--no { border-color: color-mix(in srgb, var(--ssr-danger) 32%, transparent); background: var(--ssr-danger-bg); }
.verdict--no .verdict__icon,
.verdict--no .verdict__title { color: var(--ssr-danger); }
.verdict--wait { border-color: color-mix(in srgb, var(--ssr-warning) 32%, transparent); background: var(--ssr-warning-bg); }
.verdict--wait .verdict__icon,
.verdict--wait .verdict__title { color: var(--ssr-warning-ink); }

.drawer-alert { margin-top: 14px; }
.drawer-alert p { margin: 2px 0 0; font-size: var(--ssr-font-note); line-height: 1.7; }
.drawer-footer { display: flex; gap: 8px; justify-content: flex-end; }
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
