import { http } from './request'
import type { PageResult, Reservation, Seat } from '@/types'

export interface ReservationQuery {
  status?: string
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

export const listAvailableSeats = (params: {
  room_id: number
  reserve_date: string
  start_time: string
  end_time: string
}) => http.get<Seat[]>('/reservations/available-seats', params)

export const cancelReservation = (reservationId: number, reason?: string) =>
  http.post<{ message: string }>(`/reservations/${reservationId}/cancel`, { reason })

export const forceCancelReservation = (reservationId: number, reason: string) =>
  http.post<{ message: string }>(`/reservations/${reservationId}/force-cancel`, { reason })

export const checkIn = (reservationId: number) =>
  http.post<{ message: string }>(`/reservations/${reservationId}/check-in`)

export const checkOut = (reservationId: number) =>
  http.post<{ message: string }>(`/reservations/${reservationId}/check-out`)
