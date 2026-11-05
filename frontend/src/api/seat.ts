import { http } from './request'
import type { Reservation, Seat, SeatOccupancy, SeatStatusBatchResult } from '@/types'

export const listSeats = (roomId: number) =>
  http.get<Seat[]>(`/rooms/${roomId}/seats`)

export const createSeat = (data: Partial<Seat>) => http.post<Seat>('/seats', data)

export const updateSeatStatus = (seatId: number, status: Seat['status'], reason?: string) =>
  http.patch<Seat>(`/seats/${seatId}/status`, { status, reason })

export interface SeatOccupancyQuery {
  room_id: number
  reserve_date: string
  start_time: string
  end_time: string
}

/**
 * FR-003 / FR-031：按自习室与时段返回「座位资源状态 + 该时段占用」。
 * 占用是实时计算的派生结论，不写进 `seat.status`（AGENTS.md §4）。
 */
export const listSeatOccupancy = (params: SeatOccupancyQuery) =>
  http.get<SeatOccupancy[]>('/seats/occupancy', params)

export interface SeatConflictQuery {
  seat_ids: number[]
  /** 调整窗口起点（含），形如 `2026-10-30T08:00` */
  start_at: string
  /** 调整窗口终点（不含） */
  end_at: string
}

/** BR-019：列出与「座位 + 窗口」冲突的未来有效预约，仅供提示，不自动取消。 */
export const listSeatConflicts = (params: SeatConflictQuery) =>
  http.get<Reservation[]>('/seats/conflicts', {
  seat_ids: params.seat_ids.join(','),
  start_at: params.start_at,
  end_at: params.end_at,
})

export interface SeatStatusBatchRequest {
  seat_ids: number[]
  status: Seat['status']
  /** 调整原因，必填（FR-004 输入项 + NFR-009 留痕） */
  reason: string
}

/** FR-004 + BR-022：批量调整资源状态；影响面超过一条时前端已先列清单并二次确认。 */
export const updateSeatStatusBatch = (data: SeatStatusBatchRequest) =>
  http.patch<SeatStatusBatchResult>('/seats/status', data)
