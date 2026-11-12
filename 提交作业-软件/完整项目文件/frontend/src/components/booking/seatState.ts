import { Check, CircleClose, Clock, Lock, QuestionFilled, Tools } from '@element-plus/icons-vue'
import type { Component } from 'vue'

import type { SeatCellState } from '@/utils/bookingRules'

/**
 * 座位各态的图标与非颜色标记。
 * 各态不只用颜色区分：图标 + 底纹方向 + 边框线型各不相同（见 index.scss 第 5 节），
 * 保证色盲、灰度打印与高对比模式下也能分辨。
 *
 * `unknown` = 占用不可知：本人该时段已有预约时，服务端不返回占用清单，
 * 此时只显示资源状态，不把座位误标成「已约」。
 */
export const SEAT_STATE_ICON: Record<SeatCellState, Component> = {
  free: Check,
  taken: Clock,
  unknown: QuestionFilled,
  closed: Lock,
  fix: Tools,
  off: CircleClose,
}

export const SEAT_STATE_CLASS: Record<SeatCellState, string> = {
  free: 'ssr-seat--free',
  taken: 'ssr-seat--taken',
  unknown: 'ssr-seat--unknown',
  closed: 'ssr-seat--closed',
  fix: 'ssr-seat--fix',
  off: 'ssr-seat--off',
}

/** 图例补充说明：明确「资源状态」与「时段占用」是两个维度（AGENTS.md §4）。 */
export const SEAT_STATE_NOTE: Record<SeatCellState, string> = {
  free: '这个时段可以预约',
  taken: '该时段已被预约',
  unknown: '占用暂不显示（你在这个时段已有预约）',
  closed: '该时段场地临时关闭',
  fix: '座位维修中',
  off: '座位已停用',
}