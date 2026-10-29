import type { Seat } from '@/types'
import type {
  BookingFailure,
  CheckinWindow,
  JudgementItem,
  MySlotUsage,
  SeatCellState,
} from '@/utils/bookingRules'

/** 预约座位页的筛选条件（左栏表单唯一数据源，页面持有） */
export interface BookingFilters {
  roomId: number | null
  reserveDate: string
  startTime: string
  endTime: string
  /** 空串表示不限 */
  seatType: string
  powerOnly: boolean
}

/** 矩阵单元格：资源状态（fix / off）与时段占用（free / taken）两个维度都已算好 */
export interface MatrixCell {
  seat: Seat
  state: SeatCellState
  /** tooltip 里的「该时段占用」文案，与资源状态分开呈现 */
  occupancy: string
}

export interface MatrixGroup {
  key: string
  title: string
  note: string
  cells: MatrixCell[]
}

export type SubmitState = 'idle' | 'submitting' | 'submitted'

export interface SubmitSuccess {
  id: number
  seatText: string
  reserveDate: string
  startTime: string
  endTime: string
  window: CheckinWindow
}

export type { BookingFailure, MySlotUsage, JudgementItem, CheckinWindow }
