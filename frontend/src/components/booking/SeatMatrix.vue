<script setup lang="ts">
import SeatCell from '@/components/booking/SeatCell.vue'
import { SEAT_STATE_CLASS, SEAT_STATE_ICON, SEAT_STATE_NOTE } from '@/components/booking/seatState'
import type { MatrixCell, MatrixGroup } from '@/components/booking/types'
import { SEAT_STATE_ORDER, SEAT_STATE_TEXT } from '@/utils/bookingRules'

const props = defineProps<{
  groups: MatrixGroup[]
  selectedSeatId: number | null
}>()

const emit = defineEmits<{ (e: 'select', cell: MatrixCell): void }>()

function freeCount(cells: readonly MatrixCell[]): number {
  return cells.filter((cell) => cell.state === 'free').length
}
</script>

<template>
  <section class="seat-matrix" aria-label="座位矩阵">
    <div class="seat-legend">
      <p class="seat-legend__head">
        四态图例（图标 + 底纹 + 边框线型均不同，不只靠颜色区分）
      </p>
      <ul class="seat-legend__list">
        <li v-for="state in SEAT_STATE_ORDER" :key="state" class="seat-legend__item">
          <span class="seat-legend__chip" :class="SEAT_STATE_CLASS[state]">
            <el-icon><component :is="SEAT_STATE_ICON[state]" /></el-icon>
          </span>
          <span>
            <strong>{{ SEAT_STATE_TEXT[state] }}</strong>
            <em>{{ SEAT_STATE_NOTE[state] }}</em>
          </span>
        </li>
      </ul>
      <p class="seat-legend__twodim">
        说明：<strong>资源状态</strong>（可用 / 维修中 / 停用）与<strong>时段占用</strong>
        （是否已被有效预约）是两个独立维度，鼠标悬停座位可同时看到两者。
      </p>
    </div>

    <div v-for="group in props.groups" :key="group.key" class="seat-group">
      <header class="seat-group__head">
        <h4>{{ group.title }}</h4>
        <span class="ssr-text-muted">
          {{ group.note }} · 可约 {{ freeCount(group.cells) }} / {{ group.cells.length }}
        </span>
      </header>

      <ul class="seat-group__grid">
        <li v-for="cell in group.cells" :key="cell.seat.id">
          <SeatCell
            :cell="cell"
            :selected="props.selectedSeatId === cell.seat.id"
            @select="emit('select', $event)"
          />
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.seat-legend {
  padding: 10px 12px;
  margin-bottom: 14px;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius);
}

.seat-legend__head {
  margin: 0 0 6px;
  font-size: var(--ssr-font-note);
  font-weight: 600;
}

.seat-legend__list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 20px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.seat-legend__item {
  display: flex;
  gap: 8px;
  align-items: center;
}

.seat-legend__item strong {
  display: block;
  font-size: var(--ssr-font-note);
  font-weight: 600;
}

.seat-legend__item em {
  display: block;
  color: var(--ssr-muted-ink);
  font-size: 11.5px;
  font-style: normal;
}

.seat-legend__chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  font-size: 13px;
  border-width: 1px;
  border-radius: var(--ssr-radius-sm);
}

.seat-legend__twodim {
  padding-top: 8px;
  margin: 8px 0 0;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
  border-top: 1px dashed var(--ssr-line);
}

.seat-group + .seat-group {
  margin-top: 14px;
}

.seat-group__head {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: baseline;
  justify-content: space-between;
  padding-bottom: 6px;
  margin-bottom: 8px;
  border-bottom: 1px solid var(--ssr-line);
}

.seat-group__head h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.seat-group__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(64px, 1fr));
  gap: 8px;
  padding: 0;
  margin: 0;
  list-style: none;
}
</style>
