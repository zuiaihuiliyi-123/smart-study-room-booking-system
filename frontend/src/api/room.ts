import { http } from './request'
import type { Area, Room } from '@/types'

export const listRooms = () => http.get<Room[]>('/rooms')

export const createRoom = (data: Partial<Room>) => http.post<Room>('/rooms', data)

export const createArea = (roomId: number, name: string) =>
  http.post<Area>(`/rooms/${roomId}/areas`, { name })
