<script setup lang="ts">
/**
 * 管理端座位网格（FR-003 / FR-031）。
 *
 * 每个格子同时呈现**两个维度**，且都不靠颜色单独承载（AGENTS.md §4、index.scss 第 5 节）：
 * - 资源状态：可用 / 维修中 / 停用（`seat.status`）；
 * - 该时段占用：可约 / 已约 / 占用未判定（由 `/seats/occupancy` 实时计算）。
 *
 * 与预约座位页的 `SeatMatrix` 的差别只有一处：这里是**多选**，因为 FR-004 / BR-022
 * 需要支持批量调整资源状态并先列影响清单。单选的筛选、四态判定与图例口径完全复用。
 */
import { SEAT_STATE_CLASS, SEAT_STATE_ICON, SEAT_STATE_NOTE } from '@/components/booking/seatState'
import type { MatrixCell } from '@/components/booking/types'
import type { Seat } from '@/types'
import { SEAT_STATE_ORDER, type SeatCellState } from '@/utils/bookingRules'
import type { SeatGridGroup } from '@/utils/useSeatManage'

const props = defineProps<{
  groups: SeatGridGroup[]
  selectedIds: number[]
}>()

const emit = defineEmits<{
  (e: 'toggle', seat: Seat): void
  (e: 'selectGroup', cells: MatrixCell[]): void
}>()

/** 格子里的第二个维度用短标签，完整文案放在 tooltip 与 aria-label 里 */
const OCCUPANCY_SHORT: Record<SeatCellState, string> = {
  free: '可约',
  taken: '已约',
  fix: '占用未判定',
  off: '占用未判定',
}

function isSelected(seatId: number): boolean {
  return props.selectedIds.includes(seatId)
}

function tip(cell: MatrixCell): string {
  return [
    `座位 ${cell.seat.seat_no}`,
    `资源状态：${cell.seat.status}`,
    `该时段占用：${cell.occupancy}`,
    '点击可多选，选中后可批量调整资源状态',
  ].join('\n')
}

function aria(cell: MatrixCell): string {
  return `座位 ${cell.seat.seat_no}，资源状态${cell.seat.status}，时段${OCCUPANCY_SHORT[cell.state]}`
}
</script>

<template>
  <div class="grid-panel">
    <ul class="seat-legend">
      <li v-for="state in SEAT_STATE_ORDER" :key="state" class="seat-legend__item">
        <span class="seat-legend__swatch" :class="SEAT_STATE_CLASS[state]" />
        <el-icon><component :is="SEAT_STATE_ICON[state]" /></el-icon>
        <span>{{ SEAT_STATE_NOTE[state] }}</span>
      </li>
    </ul>

    <section v-for="group in props.groups" :key="group.key" class="grid-group">
      <header class="grid-group__head">
        <strong>{{ group.title }}</strong>
        <span class="ssr-text-muted">{{ group.note }}</span>
        <el-button link type="primary" size="small" @click="emit('selectGroup', group.cells)">
          全选本分区
        </el-button>
      </header>

      <div class="seat-grid">
        <button
          v-for="cell in group.cells"
          :key="cell.seat.id"
          class="seat-grid__cell"
          :class="[SEAT_STATE_CLASS[cell.state], { 'is-selected': isSelected(cell.seat.id) }]"
          type="button"
          :title="tip(cell)"
          :aria-pressed="isSelected(cell.seat.id)"
          :aria-label="aria(cell)"
          @click="emit('toggle', cell.seat)"
        >
          <span class="seat-grid__no">{{ cell.seat.seat_no }}</span>
          <span>{{ cell.seat.status }}</span>
          <span class="seat-grid__occ">{{ OCCUPANCY_SHORT[cell.state] }}</span>
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.grid-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.grid-group__head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
  margin-bottom: 8px;
  color: var(--ssr-ink);
  font-size: var(--ssr-font-note);
}

.grid-group__head strong {
  font-size: var(--ssr-font-body);
}

.seat-grid__occ {
  opacity: 0.9;
}
</style>
