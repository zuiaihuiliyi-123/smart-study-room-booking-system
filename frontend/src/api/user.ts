import { http } from './request'
import type { CurrentUser, PageResult } from '@/types'

export const getMyProfile = () => http.get<CurrentUser>('/users/me')

export const updateMyProfile = (data: { contact?: string }) =>
  http.patch<CurrentUser>('/users/me', data)

export const listUsers = (params: { page?: number; page_size?: number }) =>
  http.get<PageResult<CurrentUser>>('/users', params)
