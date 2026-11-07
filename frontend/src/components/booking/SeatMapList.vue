<script setup lang="ts">
import { computed } from 'vue'

import { SEAT_STATE_CLASS, SEAT_STATE_ICON } from '@/components/booking/seatState'
import type { MatrixCell } from '@/components/booking/types'
import type { SeatMapLayout, SeatMapTable } from '@/utils/seatMapLayout'
import { SEAT_STATE_TEXT, seatAriaLabel } from '@/utils/bookingRules'

/**
 * 地图的无障碍兜底列表：与地图共用同一份 layout / cell 状态，
 * 保证键盘、读屏或小屏用户拿到的座位集合与地图完全一致。
 */
const props = defineProps<{
  layout: SeatMapLayout
  selectedSeatId: number | null
  mineIds?: readonly number[]
}>()

const emit = defineEmits<{ (e: 'select', cell: MatrixCell): void }>()

const mineSet = computed(() => new Set(props.mineIds ?? []))
const tableByZone = computed(() =>
  props.layout.zones.map((zone) => ({
    zone,
    tables: props.layout.tables
      .filter((table) => table.zoneId === zone.id)
      .map((table) => ({
        table,
        chairs: props.layout.chairs.filter((chair) => chair.tableId === table.id),
      })),
  })),
)

function mineOf(cell: MatrixCell): boolean {
  return mineSet.value.has(cell.seat.id)
}

function stateText(cell: MatrixCell): string {
  return mineOf(cell) ? '我的预约' : SEAT_STATE_TEXT[cell.state]
}

function tableLabel(table: SeatMapTable): string {
  return `${table.label} · ${table.meta}`
}
</script>

<template>
  <div class="seat-map-list" aria-label="座位列表">
    <section v-for="zone in tableByZone" :key="zone.zone.id" class="seat-map-list__zone">
      <header class="seat-map-list__zone-head">
        <div>
          <h4>{{ zone.zone.label }}</h4>
          <p>{{ zone.zone.en }} · {{ zone.tables.reduce((sum, item) => sum + item.chairs.length, 0) }} 座</p>
        </div>
      </header>

      <div v-for="item in zone.tables" :key="item.table.id" class="seat-map-list__table">
        <p class="seat-map-list__table-label">
          {{ tableLabel(item.table) }}
          <span v-for="tag in item.table.tags" :key="tag" class="seat-map-list__tag">{{ tag }}</span>
        </p>
        <div class="seat-map-list__chairs">
          <button
            v-for="chair in item.chairs"
            :key="chair.key"
            type="button"
            class="seat-map-list__chair"
            :class="[
              SEAT_STATE_CLASS[chair.cell.state],
              {
                'seat-map-list__chair--mine': mineOf(chair.cell),
                'seat-map-list__chair--selected': props.selectedSeatId === chair.cell.seat.id,
              },
            ]"
            :aria-pressed="props.selectedSeatId === chair.cell.seat.id"
            :aria-label="seatAriaLabel(chair.cell.seat, chair.cell.state)"
            @click="emit('select', chair.cell)"
          >
            <span class="seat-map-list__state-icon" aria-hidden="true">
              <el-icon><component :is="SEAT_STATE_ICON[chair.cell.state]" /></el-icon>
            </span>
            <strong>{{ chair.cell.seat.seat_no }}</strong>
            <span>{{ stateText(chair.cell) }}</span>
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.seat-map-list {
  display: grid;
  gap: 14px;
  padding: 14px;
  background: var(--ssr-bg);
  border: 1px solid var(--ssr-line);
  border-top: 0;
  border-radius: 0 0 var(--ssr-radius) var(--ssr-radius);
}

.seat-map-list__zone {
  padding: 12px;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius-sm);
}

.seat-map-list__zone-head {
  display: flex;
  gap: 10px;
  align-items: baseline;
  justify-content: space-between;
  padding-bottom: 8px;
  margin-bottom: 8px;
  border-bottom: 1px solid var(--ssr-line);
}

.seat-map-list__zone-head h4 {
  margin: 0;
  font-size: 14px;
}

.seat-map-list__zone-head p {
  margin: 2px 0 0;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
}

.seat-map-list__table + .seat-map-list__table {
  margin-top: 10px;
}

.seat-map-list__table-label {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin: 0 0 6px;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
}

.seat-map-list__tag {
  padding: 0 5px;
  color: var(--ssr-primary-ink);
  background: var(--ssr-primary-light);
  border-radius: 4px;
  font-size: 11px;
}

.seat-map-list__chairs {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 6px;
}

.seat-map-list__chair {
  display: grid;
  grid-template-columns: 18px 1fr auto;
  gap: 6px;
  align-items: center;
  padding: 7px 8px;
  color: var(--ssr-ink);
  text-align: left;
  cursor: pointer;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius-sm);
}

/* 列表与地图 / 图例共用同一套状态 token */
.seat-map-list__chair.ssr-seat--free {
  color: var(--ssr-seat-free-fg);
  background: var(--ssr-seat-free-bg);
  border-color: var(--ssr-seat-free-line);
}

.seat-map-list__chair.ssr-seat--taken {
  color: var(--ssr-seat-taken-fg);
  background: var(--ssr-seat-taken-bg);
  border-color: var(--ssr-seat-taken-line);
}

.seat-map-list__chair.ssr-seat--unknown {
  color: var(--ssr-muted-ink);
  background: var(--ssr-bg);
  border-color: var(--ssr-line-strong);
}

.seat-map-list__chair.ssr-seat--closed {
  color: var(--ssr-warning-ink);
  background: var(--ssr-warning-bg);
  border-color: var(--ssr-warning);
}

.seat-map-list__chair.ssr-seat--fix {
  color: var(--ssr-seat-fix-fg);
  background: var(--ssr-seat-fix-bg);
  border-color: var(--ssr-seat-fix-line);
}

.seat-map-list__chair.ssr-seat--off {
  color: var(--ssr-seat-off-fg);
  background: var(--ssr-seat-off-bg);
  border-color: var(--ssr-seat-off-line);
}

.seat-map-list__chair:hover {
  border-color: var(--ssr-primary);
}

.seat-map-list__chair--selected {
  outline: 2px solid var(--ssr-primary);
  outline-offset: 1px;
}

.seat-map-list__chair--mine {
  border-color: var(--ssr-warning);
  background: var(--ssr-warning-bg);
}

.seat-map-list__state-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border: 1px solid currentColor;
  border-radius: 50%;
}

.seat-map-list__chair strong {
  font-family: var(--ssr-font-mono, monospace);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.seat-map-list__chair > span:last-child {
  color: var(--ssr-muted-ink);
  font-size: 11px;
}

@media (max-width: 720px) {
  .seat-map-list {
    padding: 10px;
  }

  .seat-map-list__chairs {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
