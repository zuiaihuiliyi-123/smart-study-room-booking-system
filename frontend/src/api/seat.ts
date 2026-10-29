import { http } from './request'
import type { Seat } from '@/types'

export const listSeats = (roomId: number) =>
  http.get<Seat[]>(`/rooms/${roomId}/seats`)

export const createSeat = (data: Partial<Seat>) => http.post<Seat>('/seats', data)

export const updateSeatStatus = (seatId: number, status: Seat['status'], reason?: string) =>
  http.patch<Seat>(`/seats/${seatId}/status`, { status, reason })
