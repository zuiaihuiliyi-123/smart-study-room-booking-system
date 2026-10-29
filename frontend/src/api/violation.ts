import { http } from './request'
import type { PageResult, Violation } from '@/types'

export const listMyViolations = (params: { page?: number; page_size?: number }) =>
  http.get<PageResult<Violation>>('/violations/me', params)

export const listAllViolations = (params: { page?: number; page_size?: number }) =>
  http.get<PageResult<Violation>>('/violations', params)

export const registerManualViolation = (data: {
  reservation_id: number
  reason: string
}) => http.post<Violation>('/violations/manual', data)
