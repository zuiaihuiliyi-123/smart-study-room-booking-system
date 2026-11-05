import { http } from './request'
import type { PageResult, Reservation, Seat } from '@/types'

/**
 * 预约列表查询参数。
 *
 * 管理端按「日期区间 / 自习室 / 状态 / 学号」全量查询（FR-030 的管理端口径、FR-031、FR-032）。
 */
export interface ReservationQuery {
  status?: string
  /** 预约日期区间（含端点），形如 `2026-10-01` */
  reserve_date_from?: string
  reserve_date_to?: string
  room_id?: number
  seat_id?: number
  /** 学号精确匹配（管理端按用户过滤） */
  student_no?: string
  page?: number
  page_size?: number
}

export const createReservation = (data: {
  seat_id: number
  reserve_date: string
  start_time: string
  end_time: string
  idempotency_key: string
}) => http.post<Reservation>('/reservations', data)

export const listMyReservations = (params: ReservationQuery) =>
  http.get<PageResult<Reservation>>('/reservations/me', params)

export const listAllReservations = (params: ReservationQuery) =>
  http.get<PageResult<Reservation>>('/reservations', params)

/** 预约单详情（管理端详情抽屉）。 */
export const getReservation = (reservationId: number) =>
  http.get<Reservation>(`/reservations/${reservationId}`)

export const listAvailableSeats = (params: {
  room_id: number
  reserve_date: string
  start_time: string
  end_time: string
}) => http.get<Seat[]>('/reservations/available-seats', params)

export const cancelReservation = (reservationId: number, reason?: string) =>
  http.post<{ message: string }>(`/reservations/${reservationId}/cancel`, { reason })

/** FR-011：管理员强制取消（仅「待使用」，必填原因，不产生违约记录、不累加次数）。 */
export const forceCancelReservation = (reservationId: number, reason: string) =>
  http.post<{ message: string }>(`/reservations/${reservationId}/force-cancel`, { reason })

export const checkIn = (reservationId: number) =>
  http.post<{ message: string }>(`/reservations/${reservationId}/check-in`)

export const checkOut = (reservationId: number) =>
  http.post<{ message: string }>(`/reservations/${reservationId}/check-out`)
