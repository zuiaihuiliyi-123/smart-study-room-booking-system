<script setup lang="ts">
import { computed, watch } from 'vue'

import BookingActionBar from '@/components/booking/BookingActionBar.vue'
import BookingFilter from '@/components/booking/BookingFilter.vue'
import BookingResultPanel from '@/components/booking/BookingResultPanel.vue'
import SeatDetailDrawer from '@/components/booking/SeatDetailDrawer.vue'
import type { MatrixCell } from '@/components/booking/types'
import PageHeader from '@/components/PageHeader.vue'
import { type SeatCellState, timeRangeText } from '@/utils/bookingRules'
import { useSeatBooking } from '@/utils/useSeatBooking'

/** 底部操作条里的状态用短词，括号里的解释留给座位详情 */
const STATE_SHORT: Record<SeatCellState, string> = {
  free: '可约',
  taken: '已被预约',
  unknown: '占用暂不显示',
  closed: '临时关闭',
  fix: '维修中',
  off: '已停用',
}

const {
  rooms,
  filters,
  loading,
  loadError,
  dateOptions,
  dateCounts,
  dateLoading,
  room,
  seats,
  areas,
  openTime,
  closeTime,
  seatTypes,
  minStartTime,
  groups,
  freeCount,
  visibleCount,
  userBlock,
  blockedHint,
  summary,
  hint,
  slotStarted,
  mySeatIds,
  drawerVisible,
  selectedSeat,
  selectedSeatId,
  selectedAreaTitle,
  staleReason,
  judgements,
  canSubmit,
  submitState,
  failure,
  success,
  autoNotice,
  dismissAutoNotice,
  query,
  resetFilters,
  applyRoomChange,
  applyDateChange,
  openSeat,
  submit,
  findAlternative,
} = useSeatBooking()

const dateText = computed(
  () => dateOptions.value.find((item) => item.value === filters.reserveDate)?.label ?? filters.reserveDate,
)

const timeText = computed(() => timeRangeText(filters.startTime, filters.endTime))

const seatStateText = computed(() => {
  if (!selectedSeat.value) return ''
  const cell = groups.value.flatMap((group) => group.cells).find((item) => item.seat.id === selectedSeat.value?.id)
  return cell ? STATE_SHORT[cell.state] : ''
})

/** 这间自习室一个座位都没有（新开馆还没录入座位时会出现） */
const roomEmpty = computed(() => !loading.value && seats.value.length === 0)

/** 换到下一间有座位的自习室 */
function switchRoom() {
  const next = rooms.value.find((item) => item.id !== filters.roomId)
  if (!next) return
  filters.roomId = next.id
  applyRoomChange()
}

function onSelect(cell: MatrixCell) {
  openSeat(cell.seat)
}

function clearSeatFilter() {
  filters.seatType = ''
  filters.powerOnly = false
  filters.windowOnly = false
}

/** 底部操作条的「确认预约」：把抽屉重新打开，让用户看判断结果再提交 */
function confirmPick() {
  if (selectedSeat.value) drawerVisible.value = true
}

// 切回「今天」时若原时段已过，自动收敛到下一个可预约时段
watch(() => filters.reserveDate, applyDateChange)
</script>

<template>
  <div class="page booking-page">
    <PageHeader title="预约座位" />

    <div class="booking-layout">
      <!-- 自动切日期 / 顺延时段改页面内联提示，不再连续弹 toast -->
      <el-alert
        v-if="autoNotice"
        class="auto-notice"
        type="info"
        show-icon
        :closable="true"
        :title="autoNotice"
        @close="dismissAutoNotice"
      />

      <BookingFilter
        :filters="filters"
        :rooms="rooms"
        :date-options="dateOptions"
        :seat-types="seatTypes"
        :open-time="openTime"
        :close-time="closeTime"
        :min-start-time="minStartTime"
        :loading="loading"
        :date-counts="dateCounts"
        :date-loading="dateLoading"
        @search="query"
        @reset="resetFilters"
        @room-change="applyRoomChange"
        @date-change="applyDateChange"
      />

      <BookingResultPanel
        :loading="loading"
        :error="loadError"
        :groups="groups"
        :areas="areas"
        :selected-seat-id="selectedSeatId"
        :mine-ids="mySeatIds"
        :summary="summary"
        :hint="hint"
        :slot-started="slotStarted"
        :free-count="freeCount"
        :visible-count="visibleCount"
        :room-empty="roomEmpty"
        :no-room="rooms.length === 0"
        @retry="query"
        @clear-seat-filter="clearSeatFilter"
        @switch-room="switchRoom"
        @select="onSelect"
      />

      <BookingActionBar
        :seat="selectedSeat"
        :date-text="dateText"
        :time-text="timeText"
        :state-text="seatStateText"
        :blocked="userBlock !== null || slotStarted"
        :blocked-text="slotStarted ? '该时段已开始，仅供查看占用；请改选后面的时段。' : blockedHint"
        @confirm="confirmPick"
        @alternative="findAlternative"
      />
    </div>

    <SeatDetailDrawer
      v-model:visible="drawerVisible"
      :seat="selectedSeat"
      :room="room"
      :area-title="selectedAreaTitle"
      :reserve-date="filters.reserveDate"
      :start-time="filters.startTime"
      :end-time="filters.endTime"
      :judgements="judgements"
      :submit-state="submitState"
      :failure="failure"
      :success="success"
      :stale-reason="staleReason"
      :can-submit="canSubmit"
      :mine="selectedSeat ? mySeatIds.includes(selectedSeat.id) : false"
      @submit="submit"
    />
  </div>
</template>

<style scoped>
/* 筛选条置顶、座位图整宽、操作条吸底：横向空间全部留给座位矩阵 */
.booking-layout {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.booking-page {
  /* 抽屉为非模态，右侧留出 8px 视觉呼吸位；窄屏由抽屉自身宽度兜底 */
  padding-bottom: 8px;
}

.auto-notice {
  margin: 0;
}
</style>
