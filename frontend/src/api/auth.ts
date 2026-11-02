import { http } from './request'
import type { CurrentUser, LoginRequest, RegisterRequest, TokenResponse } from '@/types'

export const login = (payload: LoginRequest) =>
  http.post<TokenResponse>('/auth/login', payload)

export const register = (payload: RegisterRequest) =>
  http.post<TokenResponse>('/auth/register', payload)

export const getMe = () => http.get<CurrentUser>('/auth/me')
