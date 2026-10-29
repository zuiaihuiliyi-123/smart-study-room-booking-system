<script setup lang="ts">
import { watch } from 'vue'

import BookingFilter from '@/components/booking/BookingFilter.vue'
import BookingResultPanel from '@/components/booking/BookingResultPanel.vue'
import SeatDetailDrawer from '@/components/booking/SeatDetailDrawer.vue'
import type { MatrixCell } from '@/components/booking/types'
import PageHeader from '@/components/PageHeader.vue'
import { useSeatBooking } from '@/utils/useSeatBooking'

const {
  rooms,
  filters,
  loading,
  loadError,
  dateOptions,
  room,
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
  query,
  resetFilters,
  applyRoomChange,
  applyDateChange,
  openSeat,
  submit,
  findAlternative,
} = useSeatBooking()

function onSelect(cell: MatrixCell) {
  openSeat(cell.seat)
}

function clearSeatFilter() {
  filters.seatType = ''
  filters.powerOnly = false
}

// 切回「今天」时若原时段已过，自动收敛到下一个可预约时段
watch(() => filters.reserveDate, applyDateChange)
</script>

<template>
  <div class="page booking-page">
    <PageHeader
      title="预约座位"
      subtitle="按自习室、日期与时段查询可预约座位；选中座位后逐项校验并创建预约"
    />

    <div class="booking-layout">
      <BookingFilter
        :filters="filters"
        :rooms="rooms"
        :date-options="dateOptions"
        :seat-types="seatTypes"
        :open-time="openTime"
        :close-time="closeTime"
        :min-start-time="minStartTime"
        :loading="loading"
        :hint="hint"
        @search="query"
        @reset="resetFilters"
        @room-change="applyRoomChange"
      />

      <BookingResultPanel
        :loading="loading"
        :error="loadError"
        :user-block="userBlock"
        :blocked-hint="blockedHint"
        :groups="groups"
        :selected-seat-id="selectedSeatId"
        :summary="summary"
        :hint="hint"
        :free-count="freeCount"
        :visible-count="visibleCount"
        @retry="query"
        @alternative="findAlternative"
        @clear-seat-filter="clearSeatFilter"
        @select="onSelect"
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
      @submit="submit"
    />
  </div>
</template>

<style scoped>
.booking-layout {
  display: grid;
  grid-template-columns: minmax(240px, 300px) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.booking-page {
  /* 抽屉为非模态，右侧留出 8px 视觉呼吸位；窄屏由抽屉自身宽度兜底 */
  padding-bottom: 40px;
}

/* 三档宽度：≤1024px 筛选栏置顶、矩阵整宽；≥1025px 左筛选 + 右矩阵（抽屉从右侧覆盖） */
@media (min-width: 1025px) {
  .booking-layout > :first-child {
    position: sticky;
    top: 12px;
  }
}

@media (max-width: 1024px) {
  .booking-layout {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
