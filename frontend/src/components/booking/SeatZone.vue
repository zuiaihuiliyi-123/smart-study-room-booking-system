<script setup lang="ts">
import { computed } from 'vue'

import SeatCell from '@/components/booking/SeatCell.vue'
import type { MatrixCell } from '@/components/booking/types'

/** 一个分区：标题 + 若干张「长桌」，桌上按 2 排摆圆座位 */
const props = defineProps<{
  title: string
  cells: readonly MatrixCell[]
  desks: readonly (readonly MatrixCell[])[]
  /** 每张桌的列数（2 或 3）：座位少时收窄，避免出现孤零零的一个座位 */
  columns: number
  selectedSeatId: number | null
  mineIds?: readonly number[]
}>()

const emit = defineEmits<{ (e: 'select', cell: MatrixCell): void }>()

const mineSet = computed(() => new Set(props.mineIds ?? []))
const freeCount = computed(() => props.cells.filter((cell) => cell.state === 'free').length)
</script>

<template>
  <article class="seat-zone">
    <header class="seat-zone__head">
      <h4 class="seat-zone__name">{{ props.title }}</h4>
      <span class="seat-zone__count">可约 {{ freeCount }} / {{ props.cells.length }}</span>
    </header>

    <div class="seat-zone__desks">
      <div
        v-for="(desk, deskIndex) in props.desks"
        :key="deskIndex"
        class="desk"
        :style="{ '--desk-cols': props.columns }"
      >
        <span class="desk__top" aria-hidden="true" />
        <ul class="desk__seats">
          <li v-for="cell in desk" :key="cell.seat.id">
            <SeatCell
              :cell="cell"
              :selected="props.selectedSeatId === cell.seat.id"
              :mine="mineSet.has(cell.seat.id)"
              @select="emit('select', $event)"
            />
          </li>
        </ul>
      </div>
    </div>
  </article>
</template>

<style scoped>
/* 分区 = 房间里的一个区域，用虚线框与主墙区分 */
.seat-zone {
  min-width: 0;
  padding: calc(6px * var(--seat-zoom, 1)) calc(12px * var(--seat-zoom, 1))
    calc(12px * var(--seat-zoom, 1));
  background: var(--ssr-bg);
  border: 1px dashed var(--ssr-line-strong);
  border-radius: calc(12px * var(--seat-zoom, 1));
  box-shadow: inset 0 1px 0 var(--ssr-surface);
}

/* 分区头：左边牌子，中间一条虚线把视线带到右侧计数 */
.seat-zone__head {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 0 2px 10px;
}

.seat-zone__head::after {
  content: '';
  flex: 1;
  height: 0;
  border-top: 1px dashed var(--ssr-line);
}

.seat-zone__name {
  padding: 1px 8px;
  margin: 0;
  font-size: calc(var(--ssr-font-note) - 1px);
  font-weight: 600;
  color: var(--ssr-primary-ink);
  background: var(--ssr-primary-light);
  border-radius: 999px;
}

.seat-zone__count {
  order: 3;
  font-size: calc(var(--ssr-font-note) - 1px);
  color: var(--ssr-muted-ink);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.seat-zone__desks {
  display: flex;
  flex-direction: column;
  gap: calc(10px * var(--seat-zoom, 1));
}

/* 一张桌子：一条木色台面，座位沿台面上下两排（像平面图里的长桌 + 椅子） */
.desk {
  position: relative;
  width: 100%;
  padding: calc(6px * var(--seat-zoom, 1)) calc(4px * var(--seat-zoom, 1));
}

.desk__top {
  position: absolute;
  top: 50%;
  right: 0;
  left: 0;
  height: calc(11px * var(--seat-zoom, 1));
  border-radius: 999px;
  box-shadow:
    0 3px 6px -3px var(--ssr-desk-line),
    inset 0 1px 0 var(--ssr-desk-top);
  background: linear-gradient(
    180deg,
    var(--ssr-desk-top) 0%,
    var(--ssr-desk-mid) 55%,
    var(--ssr-desk-bottom) 100%
  );
  border: 1px solid var(--ssr-desk-line);
  border-radius: calc(3px * var(--seat-zoom, 1));
  transform: translateY(-50%);
}

.desk__seats {
  position: relative;
  display: grid;
  z-index: 1;
  grid-template-columns: repeat(var(--desk-cols, 3), 1fr);
  justify-items: center;
  gap: calc(13px * var(--seat-zoom, 1)) calc(8px * var(--seat-zoom, 1));
  padding: 0;
  margin: 0;
  list-style: none;
}
</style>
