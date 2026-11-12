import { http } from './request'
import type { CurrentUser, LoginRequest, RegisterRequest, TokenResponse } from '@/types'

export const login = (payload: LoginRequest) =>
  http.post<TokenResponse>('/auth/login', payload)

export const register = (payload: RegisterRequest) =>
  http.post<TokenResponse>('/auth/register', payload)

export const getMe = () => http.get<CurrentUser>('/auth/me')

/** B1：本人自助修改密码；成功返回新令牌（旧令牌立即失效）。 */
export const changePassword = (payload: {
  old_password: string
  new_password: string
}) => http.patch<TokenResponse>('/users/me/password', payload)
