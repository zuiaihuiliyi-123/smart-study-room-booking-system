<script setup lang="ts">
import { computed } from 'vue'
import { Lightning } from '@element-plus/icons-vue'

import { SEAT_STATE_CLASS, SEAT_STATE_ICON } from '@/components/booking/seatState'
import type { MatrixCell } from '@/components/booking/types'
import { seatAriaLabel } from '@/utils/bookingRules'

const props = defineProps<{
  cell: MatrixCell
  selected: boolean
  /** 这个座位在当前时段属于我自己 */
  mine?: boolean
}>()

const emit = defineEmits<{ (e: 'select', cell: MatrixCell): void }>()

/** 圆形座位直径有限，标签只留座号末两位（完整座号在 tooltip / 底部操作条里） */
const shortNo = computed(() => {
  const label = props.cell.seat.seat_no
  const cut = label.lastIndexOf('-')
  return cut >= 0 ? label.slice(cut + 1) : label
})
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
        <p v-if="props.mine" class="seat-tip__mine">这个时段你已经约了这个座位</p>
      </div>
    </template>

    <button
      class="seat-cell"
      :class="[
        SEAT_STATE_CLASS[props.cell.state],
        { 'seat-cell--selected': props.selected, 'seat-cell--mine': props.mine },
      ]"
      type="button"
      :aria-label="seatAriaLabel(props.cell.seat, props.cell.state)"
      :aria-pressed="props.selected"
      @click="emit('select', props.cell)"
    >
      <span class="seat-cell__no">{{ shortNo }}</span>
      <el-icon v-if="props.cell.state !== 'free'" class="seat-cell__icon" aria-hidden="true">
        <component :is="SEAT_STATE_ICON[props.cell.state]" />
      </el-icon>
      <el-icon v-if="props.cell.seat.has_power" class="seat-cell__power" aria-hidden="true">
        <Lightning />
      </el-icon>
      <span v-if="props.mine" class="seat-cell__mine">我的</span>
      <span class="seat-cell__sr">{{ props.cell.occupancy }}</span>
    </button>
  </el-tooltip>
</template>

<style scoped>
/* 座位画成一张圆椅面：像平面图里的椅子，圆形还能一眼区分「可约 / 已约 / 关闭」 */
.seat-cell {
  display: flex;
  position: relative;
  flex-direction: column;
  gap: 0;
  align-items: center;
  justify-content: center;
  width: calc(44px * var(--seat-zoom, 1));
  height: calc(44px * var(--seat-zoom, 1));
  min-width: 0;
  padding: 0;
  font-family: inherit;
  font-size: calc(12px * var(--seat-zoom, 1));
  font-weight: 600;
  line-height: 1;
  border-width: 2px;
  border-radius: 50%;
  cursor: pointer;
  transition:
    transform 0.12s ease,
    box-shadow 0.12s ease;
}

/* 悬停：轻微抬起 + 一圈外描边，像鼠标停在真实椅子上 */
.seat-cell:hover:not(:disabled) {
  z-index: 2;
  filter: brightness(1.04);
  transform: translateY(-2px) scale(1.05);
  box-shadow:
    var(--ssr-shadow-md),
    0 0 0 3px var(--ssr-primary-light);
}

.seat-cell:active:not(:disabled) {
  transform: translateY(0) scale(0.97);
}

.seat-cell:focus-visible {
  outline: 2px solid var(--ssr-primary);
  outline-offset: 3px;
}

.seat-cell:disabled {
  cursor: not-allowed;
}

.seat-cell__no {
  letter-spacing: 0.02em;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.seat-cell__icon {
  position: absolute;
  right: -2px;
  bottom: -2px;
  padding: 1px;
  font-size: calc(11.5px * var(--seat-zoom, 1));
  background: var(--ssr-surface);
  border: 1px solid currentColor;
  border-radius: 50%;
  opacity: 0.95;
}

.seat-cell__power {
  position: absolute;
  top: -3px;
  left: -3px;
  padding: 1px;
  font-size: calc(9px * var(--seat-zoom, 1));
  color: var(--ssr-warning-ink);
  background: var(--ssr-warning-bg);
  border-radius: 50%;
}

/* 选中：外圈主色环 + 一圈底色把环与座位隔开，深浅主题都清楚 */
.seat-cell--selected {
  outline: 2px solid var(--ssr-primary);
  outline-offset: 3px;
  box-shadow: 0 0 0 6px var(--ssr-primary-light);
}

/* 我的座位：右上角挂一枚小标，颜色之外还有文字，不只靠颜色区分 */
.seat-cell__mine {
  position: absolute;
  top: calc(-7px * var(--seat-zoom, 1));
  left: 50%;
  padding: 0 4px;
  font-size: 9px;
  line-height: 1.5;
  color: var(--ssr-on-primary);
  background: var(--ssr-primary);
  border-radius: 4px;
  transform: translateX(-50%);
}

.seat-cell--mine {
  box-shadow: inset 0 0 0 1.5px var(--ssr-primary);
}

.seat-tip__mine {
  padding-top: 2px;
  margin-top: 4px !important;
  font-weight: 600;
  color: var(--ssr-primary-ink);
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
