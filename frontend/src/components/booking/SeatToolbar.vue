<script setup lang="ts">
import { Minus, Plus, RefreshLeft } from '@element-plus/icons-vue'

import { SEAT_STATE_CLASS, SEAT_STATE_ICON, SEAT_STATE_NOTE } from '@/components/booking/seatState'
import type { MatrixCell } from '@/components/booking/types'
import { SEAT_STATE_ORDER } from '@/utils/bookingRules'

/** 图例用短标签：完整说法只放在 tooltip 里，条形工具条才不挤 */
const LEGEND_TEXT: Record<MatrixCell['state'], string> = {
  free: '可约',
  taken: '已约',
  unknown: '占用未知',
  closed: '临时关闭',
  fix: '维修中',
  off: '停用',
}

defineProps<{
  counts: Record<MatrixCell['state'], number>
  zoomText: string
  canZoomOut: boolean
  canZoomIn: boolean
  canReset: boolean
}>()

const emit = defineEmits<{
  (e: 'zoom-out'): void
  (e: 'zoom-in'): void
  (e: 'zoom-reset'): void
}>()
</script>

<template>
  <header class="seat-bar">
    <ul class="seat-bar__legend">
      <li
        v-for="state in SEAT_STATE_ORDER"
        :key="state"
        class="seat-bar__item"
        :class="{ 'seat-bar__item--empty': counts[state] === 0 }"
      >
        <span class="seat-bar__chip" :class="SEAT_STATE_CLASS[state]" :title="SEAT_STATE_NOTE[state]">
          <el-icon><component :is="SEAT_STATE_ICON[state]" /></el-icon>
        </span>
        <span class="seat-bar__text">{{ LEGEND_TEXT[state] }}</span>
        <strong class="seat-bar__count">{{ counts[state] }}</strong>
      </li>
    </ul>

    <div class="seat-zoom" role="group" aria-label="座位图缩放">
      <el-button :icon="Minus" :disabled="!canZoomOut" aria-label="缩小座位图" @click="emit('zoom-out')" />
      <span class="seat-zoom__value">{{ zoomText }}</span>
      <el-button :icon="Plus" :disabled="!canZoomIn" aria-label="放大座位图" @click="emit('zoom-in')" />
      <el-button :icon="RefreshLeft" :disabled="!canReset" aria-label="恢复默认大小" @click="emit('zoom-reset')" />
    </div>
  </header>
</template>

<style scoped>
.seat-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 16px;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  margin-bottom: 12px;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius);
}

.seat-bar__legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.seat-bar__item {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  font-size: var(--ssr-font-note);
}

/* 图例小圆点与座位同形同纹：一眼能把图例和地图上的椅子对上 */
.seat-bar__chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  font-size: 11px;
  border-width: 1.5px;
  border-radius: 50%;
  box-shadow: 0 1px 2px var(--ssr-line);
}

.seat-bar__item--empty .seat-bar__chip {
  opacity: 0.4;
}

.seat-bar__text {
  color: var(--ssr-muted-ink);
}

.seat-bar__count {
  font-weight: 600;
  color: var(--ssr-ink);
  font-variant-numeric: tabular-nums;
}

.seat-bar__item--empty .seat-bar__count {
  color: var(--ssr-muted);
  font-weight: 500;
}

.seat-zoom {
  display: inline-flex;
  gap: 4px;
  align-items: center;
  padding: 2px 4px;
  background: var(--ssr-bg);
  border: 1px solid var(--ssr-line);
  border-radius: 999px;
}

.seat-zoom__value {
  min-width: 44px;
  font-size: var(--ssr-font-note);
  font-weight: 600;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
</style>
