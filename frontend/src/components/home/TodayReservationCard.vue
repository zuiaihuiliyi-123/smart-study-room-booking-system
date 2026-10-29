<script setup lang="ts">
import { computed } from 'vue'

import EmptyState from '@/components/EmptyState.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import StatusTag from '@/components/StatusTag.vue'
import type { SeatRef } from '@/utils/bookingData'
import { seatDisplayName } from '@/utils/bookingData'
import {
  checkinWindow,
  countdownText,
  shortTime,
  timeRangeText,
  type CheckinWindow,
} from '@/utils/bookingRules'
import { formatDateTime } from '@/utils/format'
import type { Reservation } from '@/types'

type Phase = 'before' | 'open' | 'expired' | 'inuse'

const props = defineProps<{
  reservations: Reservation[]
  directory: Map<number, SeatRef> | null
  now: Date
  loading: boolean
  errorMessage: string
}>()

const emit = defineEmits<{
  (e: 'checkin', reservation: Reservation): void
  (e: 'checkout', reservation: Reservation): void
  (e: 'retry'): void
  (e: 'booking'): void
}>()

interface Row {
  reservation: Reservation
  seatText: string
  window: CheckinWindow
  phase: Phase
  countdown: string
  actionText: string
  action: 'checkin' | 'checkout' | 'none'
  actionDisabled: boolean
  actionTip: string
}

function phaseOf(reservation: Reservation, now: Date, window: CheckinWindow): Phase {
  if (reservation.status === '使用中') return 'inuse'
  if (now < window.opensAt) return 'before'
  if (now < window.closesAt) return 'open'
  return 'expired'
}

function countdownOf(phase: Phase, reservation: Reservation, window: CheckinWindow, now: Date): string {
  if (phase === 'before') return `距签到开始 ${countdownText(window.opensAt.getTime() - now.getTime())}`
  if (phase === 'open') return `剩余可签到 ${countdownText(window.closesAt.getTime() - now.getTime())}`
  if (phase === 'inuse') {
    return reservation.check_in_time
      ? `已签到 ${formatDateTime(reservation.check_in_time)}`
      : '使用中（签退后该时段自动重新可预约）'
  }
  return `签到窗口已于 ${window.closesText} 结束，未签到将判定为违约`
}

const rows = computed<Row[]>(() =>
    props.reservations.map((reservation) => {
    const window = checkinWindow(reservation.reserve_date, reservation.start_time)
    const phase = phaseOf(reservation, props.now, window)
    const action: Row['action'] =
      phase === 'open' ? 'checkin' : phase === 'inuse' ? 'checkout' : 'none'
    return {
      reservation,
      seatText: seatDisplayName(props.directory, reservation.seat_id),
      window,
      phase,
      countdown: countdownOf(phase, reservation, window, props.now),
      actionText: phase === 'open' ? '签到' : phase === 'inuse' ? '签退' : '签到',
      action,
      actionDisabled: action === 'none',
      actionTip:
      phase === 'before'
        ? `签到窗口 ${window.rangeText}，开始前 ${shortTime(reservation.start_time)} 的 15 分钟才可签到`
        : phase === 'expired'
        ? '签到窗口已结束，无法再签到'
        : phase === 'inuse'
        ? '签退后该时段立即重新可预约'
        : `签到窗口 ${window.rangeText}`,
    }
  }),
)
</script>

<template>
  <section class="today-card">
    <header class="today-card__head">
      <h3>今日预约</h3>
      <span class="ssr-text-muted">仅显示"待使用 / 使用中"的有效预约</span>
    </header>

    <LoadingBlock v-if="props.loading" :rows="3" text="正在读取今日预约…" />

    <div v-else-if="props.errorMessage" class="today-card__panel">
      <el-alert type="error" :closable="false" show-icon title="今日预约读取失败">
        <p>{{ props.errorMessage }}</p>
      </el-alert>
      <el-button type="primary" plain @click="emit('retry')">重试</el-button>
    </div>

    <EmptyState
      v-else-if="rows.length === 0"
      description="今天还没有预约"
      action-text="去预约座位"
      :image-size="70"
      @action="emit('booking')"
    />

    <ul v-else class="today-list">
      <li v-for="row in rows" :key="row.reservation.id" class="today-item">
        <div class="today-item__main">
          <p class="today-item__time">
            {{ timeRangeText(row.reservation.start_time, row.reservation.end_time) }}
            <StatusTag kind="reservation" :value="row.reservation.status" />
          </p>
          <p class="today-item__seat">
            {{ row.seatText }}
            <span class="ssr-text-muted">预约单 #{{ row.reservation.id }}</span>
          </p>
          <p class="today-item__count" :class="`today-item__count--${row.phase}`">
            {{ row.countdown }}
          </p>
        </div>

        <el-tooltip :content="row.actionTip" placement="top">
          <span class="today-item__action">
            <el-button
              :type="row.action === 'checkin' ? 'primary' : 'default'"
              :disabled="row.actionDisabled"
              size="small"
              @click="
              row.action === 'checkin'
              ? emit('checkin', row.reservation)
              : row.action === 'checkout'
              ? emit('checkout', row.reservation)
              : undefined
              "
            >
              {{ row.actionText }}
            </el-button>
          </span>
        </el-tooltip>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.today-card {
  padding: 14px 16px;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius);
}

.today-card__head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
  justify-content: space-between;
  padding-bottom: 8px;
  margin-bottom: 10px;
  border-bottom: 1px solid var(--ssr-line);
}

.today-card__head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.today-card__panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
}

.today-list {
  padding: 0;
  margin: 0;
  list-style: none;
}

.today-item {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
}

.today-item + .today-item {
  border-top: 1px dashed var(--ssr-line);
}

.today-item__main {
  min-width: 0;
}

.today-item__time {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.today-item__seat {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
  margin: 4px 0 0;
  font-size: var(--ssr-font-note);
}

.today-item__count {
  margin: 4px 0 0;
  font-size: var(--ssr-font-note);
  font-weight: 600;
}

.today-item__count--before {
  color: var(--ssr-muted-ink);
}

.today-item__count--open {
  color: var(--ssr-success);
}

.today-item__count--expired {
  color: var(--ssr-danger);
}

.today-item__count--inuse {
  color: var(--ssr-primary);
}

.today-item__action {
  display: inline-flex;
}
</style>
