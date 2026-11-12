<script setup lang="ts">
import { Minus, Plus, RefreshLeft } from '@element-plus/icons-vue'
import type { Component } from 'vue'

import { SEAT_STATE_CLASS, SEAT_STATE_ICON, SEAT_STATE_NOTE } from '@/components/booking/seatState'
import { SEAT_STATE_ORDER, type SeatCellState } from '@/utils/bookingRules'

/**
 * 预约地图工具条：状态计数 + 缩放 / 适配 / 复位 + 地图/列表切换。
 *
 * 状态计数来自 MatrixCell.state，与地图上的椅子共用同一套图标、线型与文案；
 * “我的预约”是额外的用户态，单独统计，不混入座位资源状态。
 */
const props = defineProps<{
  counts: Record<SeatCellState, number>
  mineCount: number
  zoomText: string
  canZoomOut: boolean
  canZoomIn: boolean
  view: 'map' | 'list'
}>()

const emit = defineEmits<{
  (e: 'zoom-out'): void
  (e: 'zoom-in'): void
  (e: 'fit'): void
  (e: 'reset'): void
  (e: 'toggle-view', view: 'map' | 'list'): void
}>()

const LEGEND_TEXT: Record<SeatCellState, string> = {
  free: '可约',
  taken: '已约',
  unknown: '占用未知',
  closed: '临时关闭',
  fix: '维修中',
  off: '停用',
}

const stateIcon = (state: SeatCellState): Component => SEAT_STATE_ICON[state]
</script>

<template>
  <header class="map-toolbar" aria-label="座位图工具条">
    <ul class="map-legend" aria-label="座位状态图例">
      <li
        v-for="state in SEAT_STATE_ORDER"
        :key="state"
        class="map-legend__item"
        :class="{ 'map-legend__item--empty': props.counts[state] === 0 }"
      >
        <span class="map-legend__chip" :class="SEAT_STATE_CLASS[state]" :title="SEAT_STATE_NOTE[state]">
          <el-icon><component :is="stateIcon(state)" /></el-icon>
        </span>
        <span class="map-legend__text">{{ LEGEND_TEXT[state] }}</span>
        <strong class="map-legend__count">{{ props.counts[state] }}</strong>
      </li>
      <li v-if="props.mineCount > 0" class="map-legend__item map-legend__item--mine">
        <span class="map-legend__chip map-legend__chip--mine" title="你在这个时段已经预约的座位">
          <el-icon><component :is="stateIcon('free')" /></el-icon>
        </span>
        <span class="map-legend__text">我的预约</span>
        <strong class="map-legend__count">{{ props.mineCount }}</strong>
      </li>
    </ul>

    <div class="map-actions">
      <div class="map-zoom" role="group" aria-label="地图缩放">
        <button type="button" class="map-action" :disabled="!props.canZoomOut" aria-label="缩小地图" @click="emit('zoom-out')">
          <el-icon><Minus /></el-icon>
        </button>
        <span class="map-zoom__value">{{ props.zoomText }}</span>
        <button type="button" class="map-action" :disabled="!props.canZoomIn" aria-label="放大地图" @click="emit('zoom-in')">
          <el-icon><Plus /></el-icon>
        </button>
        <button type="button" class="map-action map-action--text" aria-label="适配全图" @click="emit('fit')">
          适配
        </button>
        <button type="button" class="map-action" aria-label="复位到 100%" @click="emit('reset')">
          <el-icon><RefreshLeft /></el-icon>
        </button>
      </div>

      <div class="map-view-switch" role="group" aria-label="地图或列表视图">
        <button
          type="button"
          class="map-view-switch__btn"
          :class="{ 'is-active': props.view === 'map' }"
          :aria-pressed="props.view === 'map'"
          @click="emit('toggle-view', 'map')"
        >
          地图
        </button>
        <button
          type="button"
          class="map-view-switch__btn"
          :class="{ 'is-active': props.view === 'list' }"
          :aria-pressed="props.view === 'list'"
          @click="emit('toggle-view', 'list')"
        >
          列表
        </button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.map-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 16px;
  align-items: center;
  justify-content: space-between;
  padding: 9px 12px;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-bottom: 0;
  border-radius: var(--ssr-radius) var(--ssr-radius) 0 0;
}

.map-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.map-legend__item {
  display: inline-flex;
  gap: 5px;
  align-items: center;
  font-size: var(--ssr-font-note);
}

.map-legend__chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  font-size: 11px;
  border-width: 1.5px;
  border-radius: 50%;
}

.map-legend__text {
  color: var(--ssr-muted-ink);
}

.map-legend__count {
  color: var(--ssr-ink);
  font-variant-numeric: tabular-nums;
}

.map-legend__item--empty {
  opacity: 0.42;
}

.map-legend__item--mine .map-legend__text {
  color: var(--ssr-warning-ink);
}

.map-legend__chip--mine {
  color: var(--ssr-warning-ink);
  background: var(--ssr-warning-bg);
  border: 2px solid var(--ssr-warning);
}

.map-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.map-zoom,
.map-view-switch {
  display: inline-flex;
  align-items: center;
  padding: 2px;
  background: var(--ssr-bg);
  border: 1px solid var(--ssr-line);
  border-radius: 999px;
}

.map-action {
  display: inline-grid;
  width: 28px;
  height: 28px;
  padding: 0;
  color: var(--ssr-muted-ink);
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 50%;
  place-items: center;
}

.map-action:hover:not(:disabled) {
  color: var(--ssr-ink);
  background: var(--ssr-surface);
}

.map-action:disabled {
  cursor: not-allowed;
  opacity: 0.35;
}

.map-action--text {
  width: auto;
  padding: 0 7px;
  font-size: var(--ssr-font-note);
  border-radius: 999px;
}

.map-zoom__value {
  min-width: 38px;
  color: var(--ssr-ink);
  font-size: var(--ssr-font-note);
  font-variant-numeric: tabular-nums;
  text-align: center;
}

.map-view-switch__btn {
  padding: 5px 10px;
  color: var(--ssr-muted-ink);
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 999px;
  font-size: var(--ssr-font-note);
}

.map-view-switch__btn.is-active {
  color: var(--ssr-primary-ink);
  background: var(--ssr-surface);
  box-shadow: 0 1px 2px var(--ssr-line);
}

@media (max-width: 720px) {
  .map-toolbar {
    gap: 6px;
    align-items: flex-start;
  }

  .map-legend {
    flex-wrap: nowrap;
    max-width: 100%;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .map-legend::-webkit-scrollbar {
    display: none;
  }

  .map-legend__text {
    max-width: 4.5em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .map-actions {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
