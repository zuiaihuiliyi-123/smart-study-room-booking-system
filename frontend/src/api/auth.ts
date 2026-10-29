import { http } from './request'
import type { CurrentUser, LoginRequest, TokenResponse } from '@/types'

export const login = (payload: LoginRequest) =>
  http.post<TokenResponse>('/auth/login', payload)

export const getMe = () => http.get<CurrentUser>('/auth/me')
