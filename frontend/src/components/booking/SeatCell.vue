<script setup lang="ts">
import { Lightning } from '@element-plus/icons-vue'

import { SEAT_STATE_CLASS, SEAT_STATE_ICON } from '@/components/booking/seatState'
import type { MatrixCell } from '@/components/booking/types'
import { seatAriaLabel } from '@/utils/bookingRules'

const props = defineProps<{
  cell: MatrixCell
  selected: boolean
}>()

const emit = defineEmits<{ (e: 'select', cell: MatrixCell): void }>()
</script>

<template>
  <el-tooltip placement="top" effect="light" :show-after="120">
    <template #content>
      <div class="seat-tip">
        <p class="seat-tip__title">座位 {{ props.cell.seat.seat_no }}</p>
        <p><span class="seat-tip__key">座位类型</span>{{ props.cell.seat.seat_type }}</p>
        <p>
          <span class="seat-tip__key">插座</span>
          {{ props.cell.seat.has_power ? '有插座' : '无插座' }}
        </p>
        <p><span class="seat-tip__key">资源状态</span>{{ props.cell.seat.status }}</p>
        <p class="seat-tip__occ">
          <span class="seat-tip__key">该时段占用</span>{{ props.cell.occupancy }}
            </p>
          </div>
        </template>

        <button
          class="seat-cell"
          :class="[SEAT_STATE_CLASS[props.cell.state], { 'seat-cell--selected': props.selected }]"
          type="button"
          :aria-label="seatAriaLabel(props.cell.seat, props.cell.state)"
          :aria-pressed="props.selected"
          @click="emit('select', props.cell)"
        >
          <el-icon class="seat-cell__icon">
            <component :is="SEAT_STATE_ICON[props.cell.state]" />
          </el-icon>
          <span class="seat-cell__no">{{ props.cell.seat.seat_no }}</span>
          <el-icon v-if="props.cell.seat.has_power" class="seat-cell__power" aria-hidden="true">
            <Lightning />
          </el-icon>
          <span class="seat-cell__sr">{{ props.cell.occupancy }}</span>
        </button>
      </el-tooltip>
</template>

<style scoped>
.seat-cell {
  display: flex;
  position: relative;
  flex-direction: column;
  gap: 1px;
  align-items: center;
  justify-content: center;
  min-width: 0;
  min-height: 46px;
  padding: 3px 2px;
  font-family: inherit;
  font-size: var(--ssr-font-note);
  border-width: 1px;
  border-radius: var(--ssr-radius-sm);
  cursor: pointer;
}

.seat-cell:hover {
  filter: brightness(0.97);
}

.seat-cell__icon {
  font-size: 13px;
}

.seat-cell__no {
  font-weight: 600;
  letter-spacing: 0.02em;
}

.seat-cell__power {
  position: absolute;
  top: 2px;
  right: 3px;
  font-size: 11px;
}

.seat-cell--selected {
  outline: 2px solid var(--ssr-primary);
  outline-offset: 1px;
}

/* 屏幕阅读器与 tooltip 之外的兜底：不依赖颜色的文字标签 */
.seat-cell__sr {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

.seat-tip {
  max-width: 240px;
  font-size: var(--ssr-font-note);
  line-height: 1.7;
}

.seat-tip__title {
  margin: 0 0 4px;
  font-weight: 600;
}

.seat-tip p {
  margin: 0;
}

.seat-tip__key {
  display: inline-block;
  min-width: 68px;
  color: var(--ssr-muted-ink);
}

.seat-tip__occ {
  padding-top: 2px;
  margin-top: 4px !important;
  border-top: 1px dashed var(--ssr-line);
}
</style>
