import { Check, CircleClose, Clock, Tools } from '@element-plus/icons-vue'
import type { Component } from 'vue'

import type { SeatCellState } from '@/utils/bookingRules'

/**
 * 座位四态的图标与非颜色标记。
 * 四态不只用颜色区分：图标 + 底纹方向 + 边框线型各不相同（见 index.scss 第 5 节），
 * 保证色盲、灰度打印与高对比模式下也能分辨。
 */
export const SEAT_STATE_ICON: Record<SeatCellState, Component> = {
  free: Check,
  taken: Clock,
  fix: Tools,
  off: CircleClose,
}

export const SEAT_STATE_CLASS: Record<SeatCellState, string> = {
  free: 'ssr-seat--free',
  taken: 'ssr-seat--taken',
  fix: 'ssr-seat--fix',
  off: 'ssr-seat--off',
}

/** 图例补充说明：明确「资源状态」与「时段占用」是两个维度（AGENTS.md §4）。 */
export const SEAT_STATE_NOTE: Record<SeatCellState, string> = {
  free: '「可用」且该时段无其他有效预约',
  taken: '「可用」但该时段已存在其他有效预约',
  fix: '资源状态为「维修中」',
  off: '资源状态为「停用」',
}
