import { http } from './request'
import type { CurrentUser, LoginRequest, RegisterRequest, TokenResponse } from '@/types'

export const login = (payload: LoginRequest) =>
  http.post<TokenResponse>('/auth/login', payload)

export const register = (payload: RegisterRequest) =>
  http.post<TokenResponse>('/auth/register', payload)

export const getMe = () => http.get<CurrentUser>('/auth/me')

/**
 * 登出：服务端递增令牌版本，旧令牌立即失效。
 * 显式传入即将丢弃的令牌——本地凭据会先被清除，不能再依赖请求拦截器读取。
 */
export const logout = (token: string) =>
  http.post<{ message: string }>('/auth/logout', undefined, {
    headers: { Authorization: `Bearer ${token}` },
    // 旧令牌失效是登出的正常结果，不应触发全局 401 跳转
    silent: true,
    skipAuthRedirect: true,
  })

/** B1：本人自助修改密码；成功返回新令牌（旧令牌立即失效）。 */
export const changePassword = (payload: {
  old_password: string
  new_password: string
}) => http.patch<TokenResponse>('/users/me/password', payload)
