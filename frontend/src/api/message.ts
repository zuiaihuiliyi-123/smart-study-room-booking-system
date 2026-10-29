import { http } from './request'
import type { PageResult, StationMessage } from '@/types'

export const listMyMessages = (params: { page?: number; page_size?: number }) =>
  http.get<PageResult<StationMessage>>('/messages/me', params)

export const markMessageRead = (messageId: number) =>
  http.post<StationMessage>(`/messages/${messageId}/read`)
